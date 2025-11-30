#!/usr/bin/env python3
"""
agentThreshold.py
Monitors Hyperliquid vault perpetual positions and emails alerts when any position
value (Size × Mark Price) exceeds the configured USD threshold.
"""

import re
import ssl
import smtplib
from decimal import Decimal
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------
VAULT_URL = "https://app.hyperliquid.xyz/vaults/0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

EMAIL_SENDER = "cryptosscalp@gmail.com"
EMAIL_PASSWORD = "gfke olcu ulud zpnh"
EMAIL_RECEIVER = "25harshitgarg12345@gmail.com"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

POSITION_VALUE_THRESHOLD = Decimal("50000")

NUMERIC_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


# ------------------------------------------
# Helpers
# ------------------------------------------
def extract_decimal(text: str) -> Decimal:
    """Extract first number from text, return Decimal."""
    if not text:
        return Decimal("0")

    cleaned = (
        text.replace(",", "")
        .replace("$", "")
        .replace("USD", "")
        .strip()
    )

    match = NUMERIC_PATTERN.search(cleaned)
    if not match:
        return Decimal("0")

    return Decimal(match.group())


def send_email(subject: str, body: str):
    """Send email notification."""
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)


# ------------------------------------------
# Scraper
# ------------------------------------------
def fetch_positions():
    """Scrape PERP positions table using Playwright."""
    positions = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("[INFO] Loading vault page...")
        page.goto(VAULT_URL, wait_until="networkidle")

        # Wait until table exists
        page.wait_for_timeout(3000)

        rows = page.locator("table tbody tr")
        row_count = rows.count()

        if row_count == 0:
            print("[WARN] No rows found in PERP table.")
            browser.close()
            return []

        for i in range(row_count):
            cells = rows.nth(i).locator("td")
            if cells.count() < 4:
                continue

            coin = cells.nth(0).inner_text().strip()
            leverage = cells.nth(1).inner_text().strip()
            size = extract_decimal(cells.nth(2).inner_text())
            mark = extract_decimal(cells.nth(3).inner_text())

            if size == 0 or mark == 0:
                continue

            positions.append({
                "coin": coin,
                "leverage": leverage,
                "size": size,
                "mark": mark,
                "value": size * mark
            })

        browser.close()

    print(f"[INFO] Extracted {len(positions)} positions.")
    return positions


# ------------------------------------------
# MAIN LOGIC
# ------------------------------------------
def main():
    print("[INFO] Starting threshold monitor...")

    positions = fetch_positions()

    exceeding = [
        pos for pos in positions
        if pos["value"].copy_abs() > POSITION_VALUE_THRESHOLD
    ]

    if exceeding:
        lines = ["🚨 PERP Position Exceeds $50,000 🚨", ""]
        for pos in exceeding:
            lines.append(
                f"{pos['coin']} | Value: ${pos['value']:,} | Size: {pos['size']} | Mark: {pos['mark']}"
            )
        body = "\n".join(lines)

        send_email("⚠️ Hyperliquid Threshold Alert", body)
        print("[INFO] Alert sent.")
    else:
        send_email("Hyperliquid Threshold Status", "No positions exceed $50,000.")
        print("[INFO] No exceeding positions. Email sent.")


if __name__ == "__main__":
    main()
