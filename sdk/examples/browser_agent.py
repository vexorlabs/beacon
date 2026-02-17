"""
Browser agent example: navigates Wikipedia using Playwright.

Requires:
    pip install beacon-sdk[playwright] playwright
    playwright install chromium

Usage:
    1. Start the Beacon backend:  make dev
    2. Run this script:           python sdk/examples/browser_agent.py
    3. Open http://localhost:5173 to see browser_action spans in the trace graph.
"""

import beacon_sdk
from playwright.sync_api import sync_playwright

# Initialize Beacon SDK with auto-patching enabled.
# This automatically instruments Playwright Page methods.
beacon_sdk.init(auto_patch=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Each of these calls creates a browser_action span automatically
    page.goto("https://en.wikipedia.org/wiki/Artificial_intelligence")
    page.wait_for_selector("h1")
    page.click("#mw-content-text a[href='/wiki/Machine_learning']")
    page.wait_for_selector("h1")
    page.screenshot(path="ml_page.png")

    browser.close()
