from playwright.sync_api import sync_playwright
import os

def run_cuj(page):
    page.goto(f"file://{os.path.abspath('reports/huawei_c_model/html/ca_visualizer.html')}")
    page.wait_for_timeout(500)

    # Click next twice
    page.locator("#btn-next").click()
    page.wait_for_timeout(200)
    page.locator("#btn-next").click()
    page.wait_for_timeout(200)

    # Change slider to 25 (max is 49 according to the error)
    page.locator("#cycle-slider").fill("25")
    page.locator("#cycle-slider").evaluate("e => e.dispatchEvent(new Event('input'))")
    page.wait_for_timeout(200)

    # Play for a bit
    page.locator("#btn-play").click()
    page.wait_for_timeout(1500)
    page.locator("#btn-play").click() # Pause

    page.wait_for_timeout(500)

    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    page.screenshot(path="/home/jules/verification/screenshots/ca_visualizer.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        os.makedirs("/home/jules/verification/videos", exist_ok=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/videos")
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
