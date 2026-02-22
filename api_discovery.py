"""
api_discovery.py
Run this ONCE to capture the real API endpoints from booking.heykoala.ai
It opens a real browser, you log in and make a test booking,
and it prints all API calls made — so you can update booking.py

HOW TO USE:
    python api_discovery.py

Then copy the printed API URLs and payloads into booking.py
"""

import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

captured_requests = []


def run_discovery():
    print("="*60)
    print("API DISCOVERY MODE")
    print("Watch the browser — log in and make ONE test booking")
    print("All API calls will be captured and printed")
    print("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible browser
        page = browser.new_page()

        # Capture ALL network requests
        def on_request(req):
            if req.method in ('POST', 'PUT', 'PATCH'):
                captured_requests.append({
                    "method":  req.method,
                    "url":     req.url,
                    "headers": dict(req.headers),
                    "body":    req.post_data,
                })

        def on_response(res):
            if res.status in (200, 201) and any(
                r['url'] == res.url for r in captured_requests
            ):
                print(f"\n✅ SUCCESS RESPONSE from: {res.url}")
                try:
                    print(json.dumps(res.json(), indent=2))
                except:
                    print(res.text())

        page.on("request", on_request)
        page.on("response", on_response)

        # Step 1 — Auto login
        print("\nNavigating to site...")
        page.goto("https://booking.heykoala.ai")
        page.wait_for_load_state('networkidle')

        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")

        if username and password:
            print("Auto-filling login...")
            try:
                page.fill('input[placeholder="Enter username"]', username)
                page.fill('input[placeholder="Enter password"]', password)
                page.click('button:has-text("Login")')
                page.wait_for_load_state('networkidle')
                print("Logged in! Now navigate to create a booking...")
            except Exception as e:
                print(f"Auto-login failed ({e}), please log in manually")

        print("\n⏳ Waiting for you to complete a test booking...")
        print("   Create ONE booking then close the browser\n")
        page.wait_for_event('close', timeout=300000)  # 5 min timeout
        browser.close()

    # ── Print all captured requests ────────────────
    print("\n" + "="*60)
    print("CAPTURED API CALLS")
    print("="*60)

    for req in captured_requests:
        print(f"\n{'─'*40}")
        print(f"METHOD:  {req['method']}")
        print(f"URL:     {req['url']}")

        auth = req['headers'].get('authorization', '')
        if auth:
            print(f"AUTH:    {auth[:50]}...")

        if req['body']:
            print(f"BODY:")
            try:
                print(json.dumps(json.loads(req['body']), indent=2))
            except:
                print(req['body'])

    print("\n" + "="*60)
    print("Copy the booking URL and body fields into booking.py")
    print("="*60)


if __name__ == '__main__':
    run_discovery()
