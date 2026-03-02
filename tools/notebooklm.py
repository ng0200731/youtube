import os
import sys
import time

PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.tmp', 'playwright-profile')


def create_notebook_with_urls(urls, headless=True):
    """Create a NotebookLM notebook and add YouTube URLs as sources.

    First run: set headless=False so user can log into Google.
    Subsequent runs: headless=True reuses the saved session.

    Returns the notebook URL or None on failure.
    """
    from playwright.sync_api import sync_playwright

    os.makedirs(PROFILE_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=headless,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 900},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        # Navigate to NotebookLM
        page.goto('https://notebooklm.google.com/', wait_until='networkidle', timeout=30000)
        time.sleep(2)

        # Check if we need to log in
        if 'accounts.google.com' in page.url:
            if headless:
                browser.close()
                return {'error': 'login_required', 'message': 'Google login required. Run with headless=False first.'}
            # Wait for user to log in manually (up to 2 minutes)
            print("Please log in to Google in the browser window...")
            page.wait_for_url('**/notebooklm.google.com/**', timeout=120000)
            time.sleep(2)

        # Create new notebook - click the "New notebook" or "+" button
        try:
            # Look for create/new notebook button
            new_btn = page.locator('button:has-text("New"), button:has-text("Create"), [aria-label*="new"], [aria-label*="New"], [aria-label*="Create"]').first
            new_btn.click(timeout=10000)
            time.sleep(3)
        except Exception:
            # May already be on a new notebook page
            pass

        notebook_url = page.url

        # Add each YouTube URL as a source
        for i, url in enumerate(urls):
            try:
                # Click "Add source" or "+" button in sources panel
                add_btn = page.locator('button:has-text("Add source"), button:has-text("Add Source"), [aria-label*="Add source"], [aria-label*="add source"]').first
                add_btn.click(timeout=10000)
                time.sleep(1)

                # Look for YouTube/URL option
                yt_option = page.locator('text=YouTube, text=Website, text=URL, text=Link').first
                yt_option.click(timeout=5000)
                time.sleep(1)

                # Paste the URL
                url_input = page.locator('input[type="url"], input[type="text"], input[placeholder*="URL"], input[placeholder*="url"], input[placeholder*="link"], input[placeholder*="paste"]').first
                url_input.fill(url)
                time.sleep(0.5)

                # Submit
                submit_btn = page.locator('button:has-text("Insert"), button:has-text("Add"), button:has-text("Submit"), button[type="submit"]').first
                submit_btn.click(timeout=5000)
                time.sleep(2)

            except Exception as e:
                print(f"Failed to add URL {i+1}/{len(urls)}: {url} - {e}")
                continue

        notebook_url = page.url
        browser.close()

        return {'url': notebook_url, 'sources_added': len(urls)}


def login_to_google():
    """Open browser for user to log in to Google (non-headless)."""
    from playwright.sync_api import sync_playwright

    os.makedirs(PROFILE_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 900},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto('https://notebooklm.google.com/')
        print("Please log in to Google in the browser window.")
        print("Close the browser when done.")

        # Wait until browser is closed by user
        try:
            page.wait_for_event('close', timeout=300000)
        except Exception:
            pass

        browser.close()
        return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', action='store_true', help='Open browser to log in to Google')
    parser.add_argument('--urls', nargs='+', help='YouTube URLs to add')
    args = parser.parse_args()

    if args.login:
        login_to_google()
    elif args.urls:
        result = create_notebook_with_urls(args.urls, headless=False)
        print(result)
