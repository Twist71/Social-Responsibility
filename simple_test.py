#!/usr/bin/env python3
import asyncio
import botright
import time
import os

async def simple_test():
    print("\n===== BOTRIGHT SIMPLE TEST =====")
    start_time = time.time()
    
    # Verification step to see if print is working
    print("Print test - if you see this, print statements are working")
    
    try:
        print(f"Step 1: Creating Botright client at {time.strftime('%H:%M:%S')}")
        client = await botright.Botright()
        print(f"Step 2: Botright client created successfully after {time.time() - start_time:.2f}s")
        
        print(f"Step 3: Creating browser at {time.strftime('%H:%M:%S')}")
        browser = await client.new_browser()
        print("Step 4: Browser created successfully")
        
        print("Step 5: Creating page")
        page = await browser.new_page()
        print("Step 6: Page created successfully")
        
        print("Step 7: Navigating to Google")
        await page.goto("https://www.google.com")
        print("Step 8: Navigation successful")
        
        print("Step 9: Taking screenshot")
        os.makedirs("test_screenshots", exist_ok=True)
        await page.screenshot(path="test_screenshots/google.png")
        print("Step 10: Screenshot saved")
        
        print("Step 11: Cleaning up")
        await browser.close()
        await client.close()
        print("Step 12: Test completed successfully")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
    
    print(f"Total test time: {time.time() - start_time:.2f} seconds")
    print("===== TEST COMPLETE =====\n")

# Main execution
if __name__ == "__main__":
    print("Starting direct execution of simple_test.py")
    asyncio.run(simple_test())
    print("Execution complete")