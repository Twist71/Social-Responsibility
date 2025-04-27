async def main():
    print("Starting browser launch diagnostic...")
    import os, platform, asyncio
    from playwright.async_api import async_playwright
    
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Running as user: {os.getuid()}")
    
    try:
        async with async_playwright() as p:
            print("Playwright initialized")
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            print("Browser launched successfully")
            context = await browser.new_context()
            print("Browser context created")
            page = await context.new_page()
            print("New page created")
            await page.goto("https://example.com")
            print("Navigation successful")
            await browser.close()
            print("Browser closed properly")
            return True
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    print(f"Diagnostic {'PASSED' if success else 'FAILED'}")
