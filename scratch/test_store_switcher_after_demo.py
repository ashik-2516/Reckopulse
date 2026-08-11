import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000/store/clothing"

async def test_store_switcher():
    print("==========================================================================")
    print("    VERIFYING STORE SWITCHER & HEADER BUTTONS AFTER DEMO JOURNEY          ")
    print("==========================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        print("  [OK] Loaded Aura Threads Storefront")

        # 1. Run Live Journey
        await page.evaluate("() => window.runLiveCustomerJourney()")
        await page.wait_for_timeout(1000)
        
        # Advance & Skip Journey
        await page.evaluate("() => window.nextJourneyStep()")
        await page.wait_for_timeout(500)
        await page.evaluate("() => window.stopJourney()")
        await page.wait_for_timeout(500)
        print("  [OK] Completed & Stopped Live Journey")

        # 2. Test Store Switcher Dropdown & Navigation
        switcher_btn = page.locator(".store-switcher-btn")
        assert await switcher_btn.is_visible(), "Store switcher button not visible"
        
        # Hover over dropdown
        await switcher_btn.hover()
        await page.wait_for_timeout(300)
        
        general_link = page.locator("a[href='/store/general']")
        assert await general_link.is_visible(), "Store switcher menu did not open on hover after demo journey!"
        print("  [OK] Store switcher dropdown menu opened on hover after Demo Journey")

        # Click link to navigate to Nexus Marketplace
        await general_link.click()
        await page.wait_for_load_state("networkidle")
        
        current_url = page.url
        assert "/store/general" in current_url, f"Expected URL /store/general, got {current_url}"
        print(f"  [OK] Store switcher successfully navigated to Nexus Marketplace ({current_url})")

        await browser.close()
        print("\n==========================================================================")
        print("     STORE SWITCHER AFTER DEMO JOURNEY VERIFIED 100% WORKING               ")
        print("==========================================================================")

if __name__ == "__main__":
    asyncio.run(test_store_switcher())
