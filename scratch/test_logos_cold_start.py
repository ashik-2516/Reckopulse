import asyncio
from playwright.async_api import async_playwright

PAGES_TO_TEST = [
    ("http://127.0.0.1:5000/", "Landing Page"),
    ("http://127.0.0.1:5000/store/clothing", "Aura Threads Apparel"),
    ("http://127.0.0.1:5000/store/general", "Nexus Marketplace"),
    ("http://127.0.0.1:5000/store/grocery", "FreshPantry Superstore"),
    ("http://127.0.0.1:5000/store/pickles", "SavorCraft Pickles"),
    ("http://127.0.0.1:5000/merchant/dashboard", "Merchant Dashboard")
]

async def verify_logos():
    print("==========================================================================")
    print("     VERIFYING INITIAL COLD-START LOGO GRAPHICS ACROSS ALL PAGES          ")
    print("==========================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for url, name in PAGES_TO_TEST:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            logo = page.locator(".brand-logo img, .navbar .brand-logo img")
            assert await logo.is_visible(), f"FAIL: Logo img not visible on {name} ({url})"
            
            # Verify image loaded successfully (naturalWidth > 0)
            is_loaded = await logo.evaluate("el => el.complete && el.naturalWidth > 0")
            assert is_loaded, f"FAIL: Logo image failed to load on {name} ({url})"
            
            src = await logo.get_attribute("src")
            print(f"  [OK] Certified Logo Graphic for {name}: {src} (Rendered Successfully)")

        await browser.close()
        print("\n==========================================================================")
        print("     ALL COLD-START LOGO GRAPHICS 100% VERIFIED RENDERING                 ")
        print("==========================================================================")

if __name__ == "__main__":
    asyncio.run(verify_logos())
