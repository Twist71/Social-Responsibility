#!/bin/bash
# Fixed script that properly installs and uses browsers

# Update Playwright and install browsers correctly
pip install playwright==1.51.0
python -m playwright install webkit firefox

# Create a more robust script that tries multiple browsers
cat > fb_automation_fixed.py << 'EOF'
import asyncio
import logging
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[])
logger = logging.getLogger(__name__)

# File handler for detailed logs
file_handler = logging.FileHandler("fb_automation.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Console handler for summary logs
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console)

logger.setLevel(logging.DEBUG)

# Load environment variables
load_dotenv()

async def try_browser(playwright, browser_type, name):
    """Try to launch a specific browser type with error handling"""
    logger.info(f"Attempting to use {name} browser...")
    try:
        browser = await browser_type.launch(headless=False, slow_mo=50)
        logger.info(f"Successfully launched {name}")
        return browser
    except Exception as e:
        logger.debug(f"Failed to launch {name}: {str(e)}")
        return None

async def main():
    logger.info("Starting Facebook Automation v1.5.1 with multi-browser support")
    
    async with async_playwright() as p:
        # Try browsers in order of preference for macOS
        for browser_type, name in [
            (p.webkit, "WebKit"),
            (p.firefox, "Firefox"),
            (p.chromium, "Chromium")
        ]:
            browser = await try_browser(p, browser_type, name)
            if browser:
                break
        
        if not browser:
            logger.error("Failed to launch any browser. Exiting.")
            return
        
        try:
            # Create a context with a reasonable timeout
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            context.set_default_timeout(30000)
            
            # Create a new page
            logger.info("Opening a new page")
            page = await context.new_page()
            
            # Navigate to Facebook
            logger.info("Navigating to Facebook")
            await page.goto("https://facebook.com")
            
            # Take a screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=f"fb_login_{timestamp}.png")
            logger.debug(f"Screenshot captured: fb_login_{timestamp}.png")
            
            # Check if already logged in
            title = await page.title()
            logger.debug(f"Page title: {title}")
            
            if "Log In or Sign Up" not in title:
                logger.info("Already logged in to Facebook")
            else:
                # Get credentials from environment variables
                email = os.environ.get("FB_EMAIL", "")
                password = os.environ.get("FB_PASSWORD", "")
                
                if not email or not password:
                    logger.error("Facebook credentials not set in environment variables")
                    return
                
                logger.info("Logging in to Facebook...")
                
                # Fill in login form - using more reliable selectors
                await page.fill("input[name='email']", email)
                await page.fill("input[name='pass']", password)
                
                # Click login button and wait for navigation
                login_button = page.locator("button[name='login']")
                await login_button.click()
                
                # Wait for navigation to complete
                await page.wait_for_load_state("networkidle")
                
                # Take a post-login screenshot
                await page.screenshot(path=f"fb_logged_in_{timestamp}.png")
                logger.info("Login completed successfully")
            
            # Continue with Facebook automation...
            logger.info("Facebook automation completed")
            
        except Exception as e:
            logger.error(f"Error during automation: {str(e)}")
            # Try to take a screenshot of the error state
            try:
                if 'page' in locals() and page:
                    await page.screenshot(path=f"fb_error_{timestamp}.png")
            except:
                pass
        finally:
            # Clean up
            if 'context' in locals() and context:
                await context.close()
            if 'browser' in locals() and browser:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run the fixed script
echo "Running the fixed script with proper browser installation..."
python fb_automation_fixed.py