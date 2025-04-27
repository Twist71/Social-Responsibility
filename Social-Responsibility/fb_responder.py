#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from datetime import datetime
import dotenv
import botright
import json

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s,%(msecs)d %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('fb_automation.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
console = logging.StreamHandler()
logger.addHandler(console)

# Load environment variables
dotenv.load_dotenv()
FB_EMAIL = os.getenv("FB_EMAIL")
FB_PASSWORD = os.getenv("FB_PASSWORD")

VERSION = "1.5.1"  # Updated version number

async def capture_screenshot(page, filename_prefix):
    """Capture a screenshot with the given prefix"""
    if not page:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("screenshots", exist_ok=True)
    filename = f"screenshots/{filename_prefix}_{timestamp}.png"
    
    try:
        await page.screenshot(path=filename)
        logger.info(f"Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Screenshot error: {str(e)}")
        return None

async def run_facebook_automation():
    """Main function to run the Facebook automation"""
    logger.info(f"Starting Facebook Automation Script v{VERSION}")
    
    client = None
    browser = None
    page = None
    
    try:
        # Initialize Botright - Fixes for parameter issues
        client = await botright.Botright()
        
        # Create browser without problematic parameters
        browser = await client.new_browser(headless=False)
        
        # Create page
        page = await browser.new_page()
        
        # Navigate to Facebook
        logger.info("Navigating to Facebook")
        await page.goto("https://www.facebook.com/")
        await capture_screenshot(page, "facebook_login")
        
        # Check if already logged in
        if await page.title() != "Facebook - Log In or Sign Up":
            logger.info("Already logged in to Facebook")
        else:
            # Login to Facebook
            logger.info("Logging into Facebook")
            await page.wait_for_selector("#email")
            await page.human_type("#email", FB_EMAIL)
            await page.human_type("#pass", FB_PASSWORD)
            await page.human_click('[data-testid="royal_login_button"]')
            
            # Wait for login to complete
            try:
                await page.wait_for_navigation(timeout=10000)
                logger.info("Login navigation completed")
                await capture_screenshot(page, "after_login")
            except Exception as e:
                logger.warning(f"Navigation timeout after login: {str(e)}")
                await capture_screenshot(page, "login_timeout")
        
        # Continue with your Facebook automation...
        logger.info("Facebook automation completed")
        
    except Exception as e:
        logger.error(f"Error during automation: {str(e)}")
        if page:
            await capture_screenshot(page, "error")
    
    finally:
        # Clean up
        logger.info("Cleaning up resources")
        try:
            if browser:
                await browser.close()
                logger.info("Browser closed")
            if client:
                await client.close()
                logger.info("Client closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(run_facebook_automation())
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
