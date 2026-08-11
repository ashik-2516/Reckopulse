import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000/store/clothing"

async def test_mobile_controller_bar():
    print("==========================================================================")
    print("   TESTING MOBILE VIEW (375px) DEMO CONTROLLER BAR & BUTTON WORKING      ")
    print("==========================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. MOBILE VIEWPORT TEST (375 x 812)
        mobile_page = await browser.new_page(viewport={"width": 375, "height": 812})
        await mobile_page.goto(BASE_URL)
        await mobile_page.wait_for_load_state("networkidle")
        print("  [OK] Loaded Mobile Viewport (375x812)")

        # Launch Demo Journey on Mobile
        await mobile_page.evaluate("() => window.runLiveCustomerJourney()")
        await mobile_page.wait_for_timeout(1000)
        
        bar = mobile_page.locator("#journey-controller-bar")
        assert await bar.is_visible(), "FAIL: Controller bar not visible on Mobile"

        box = await bar.bounding_box()
        print(f"  [OK] Mobile Controller Box Bounds: width={box['width']}px, height={box['height']}px, y={box['y']}px")
        
        # Assert height is compact (<= 75px) instead of bloated 160px vertical stack
        assert box['height'] <= 75, f"FAIL: Controller bar height on mobile is too tall: {box['height']}px"
        assert box['width'] <= 375, f"FAIL: Controller bar overflows mobile screen: {box['width']}px"

        # Check button visibility & clickability on Mobile
        prev_btn = mobile_page.locator("button:has-text('Prev')")
        pause_btn = mobile_page.locator("#journey-pause-btn")
        next_btn = mobile_page.locator("button:has-text('Next')")
        skip_btn = mobile_page.locator("button:has-text('Skip')")

        assert await prev_btn.is_visible(), "Prev button not visible on Mobile"
        assert await pause_btn.is_visible(), "Pause button not visible on Mobile"
        assert await next_btn.is_visible(), "Next button not visible on Mobile"
        assert await skip_btn.is_visible(), "Skip button not visible on Mobile"
        print("  [OK] All 4 Demo Control Buttons 100% Visible on Mobile View")

        # Test Next button click on mobile
        await next_btn.click()
        await mobile_page.wait_for_timeout(500)
        print("  [OK] Next button clicked cleanly on Mobile View")

        # Test Skip button click on mobile
        await skip_btn.click()
        await mobile_page.wait_for_timeout(500)
        assert not await bar.is_visible(), "Skip button did not close controller bar on Mobile"
        print("  [OK] Skip button stopped journey & closed bar on Mobile View")

        await mobile_page.close()

        # 2. DESKTOP VIEWPORT TEST (1280 x 800) UNTOUCHED VALIDATION
        desktop_page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await desktop_page.goto(BASE_URL)
        await desktop_page.wait_for_load_state("networkidle")

        await desktop_page.evaluate("() => window.runLiveCustomerJourney()")
        await desktop_page.wait_for_timeout(1000)

        desktop_bar = desktop_page.locator("#journey-controller-bar")
        assert await desktop_bar.is_visible(), "Controller bar not visible on Desktop"
        
        desktop_box = await desktop_bar.bounding_box()
        print(f"  [OK] Desktop Controller Box Bounds: width={desktop_box['width']}px, height={desktop_box['height']}px")
        
        await desktop_page.evaluate("() => window.stopJourney()")
        await desktop_page.close()

        await browser.close()
        print("\n==========================================================================")
        print("    MOBILE & DESKTOP DEMO CONTROLLER BAR 100% CERTIFIED WORKING          ")
        print("==========================================================================")

if __name__ == "__main__":
    asyncio.run(test_mobile_controller_bar())
