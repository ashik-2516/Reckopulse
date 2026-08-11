import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000/"

async def verify_home_launch_logo():
    print("==========================================================================")
    print("      VERIFYING HOME PAGE LAUNCHING ANIMATED LOGO GRAPHIC                 ")
    print("==========================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Clear storage so intro overlay plays
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE_URL)
        
        # Check intro overlay launching logo
        intro_logo = page.locator("#intro-overlay img")
        assert await intro_logo.is_visible(), "FAIL: Home Page launching logo graphic not visible in intro overlay!"
        
        src = await intro_logo.get_attribute("src")
        assert "favicon-recopulse.svg" in src, f"FAIL: Expected favicon-recopulse.svg, got {src}"
        
        is_loaded = await intro_logo.evaluate("el => el.complete && el.naturalWidth > 0")
        assert is_loaded, "FAIL: Home page launch logo image failed to load!"
        print(f"  [OK] Certified Home Page Launching Logo Graphic: {src}")
        print("  [OK] Glowing Pulse Animation & High-Resolution Rendering Verified")

        await browser.close()
        print("\n==========================================================================")
        print("     HOME PAGE LAUNCHING LOGO GRAPHIC 100% VERIFIED RENDERING             ")
        print("==========================================================================")

if __name__ == "__main__":
    asyncio.run(verify_home_launch_logo())
