"""
Room Booking AI Agent — main.py
Denisson's Beach Resort
"""

import os
import json
import logging
import threading
import time
import requests as req
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client

from ai_extractor import extract_booking_details
from booking import create_booking

load_dotenv()

# ── Logging ────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Twilio ─────────────────────────────────────────
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# ── Flask ──────────────────────────────────────────
app = Flask(__name__)


# ── Keep Alive (prevents Render free tier sleep) ───
def keep_alive():
    url = os.getenv("RENDER_URL", "")
    if not url:
        return
    while True:
        time.sleep(600)  # ping every 10 minutes
        try:
            req.get(f"{url}/", timeout=10)
            log.info("Keep-alive ping sent")
        except Exception as e:
            log.warning(f"Keep-alive failed: {e}")

def start_keep_alive():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()


# ── Health Check ───────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return {"status": "running"}, 200


# ── Gemini Test ────────────────────────────────────
@app.route('/test-gemini', methods=['GET'])
def test_gemini():
    try:
        result = extract_booking_details(
            "Book a Deluxe Room for John Silva, john@gmail.com, "
            "check-in March 10 2026, check-out March 15 2026, 2 adults"
        )
        return {"status": "success", "extracted": result}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


# ── WhatsApp Webhook ───────────────────────────────
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender       = request.values.get('From', '')

    log.info(f"Message from {sender}: {incoming_msg}")

    send_whatsapp(sender, "Processing your booking request, please wait...")
    reply = process_booking_request(incoming_msg)
    send_whatsapp(sender, reply)

    return Response("<Response></Response>", mimetype='text/xml')


# ── Core Booking Logic ─────────────────────────────
def process_booking_request(message: str) -> str:
    try:
        details = extract_booking_details(message)
        log.info(f"Extracted: {json.dumps(details, indent=2)}")
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        return (
            "Booking Failed\n\n"
            "Sorry, I could not understand your booking request.\n\n"
            "Please try again with this format:\n"
            "Hi, I'd like to book a Deluxe Room. "
            "My name is John Silva, email john@gmail.com. "
            "Check-in March 10 2026, check-out March 15 2026. 2 adults."
        )

    required = {
        "guest_name": "your full name",
        "email":      "your email address",
        "check_in":   "check-in date",
        "check_out":  "check-out date",
        "room_type":  "room type",
        "adults":     "number of adults",
    }
    missing = [label for field, label in required.items() if not details.get(field)]

    if missing:
        missing_list = "\n".join(f"  - {m}" for m in missing)
        return (
            f"Booking Incomplete\n\n"
            f"I could not find:\n{missing_list}\n\n"
            f"Please resend with all details. Thank you!"
        )

    try:
        result = create_booking(details)
        log.info(f"Booking success: {result}")
        return (
            f"Booking Confirmed!\n\n"
            f"Denisson's Beach Resort\n"
            f"---------------------------\n"
            f"Guest:     {details['guest_name']}\n"
            f"Room:      {details['room_type']}\n"
            f"Check-in:  {details['check_in']}\n"
            f"Check-out: {details['check_out']}\n"
            f"Adults:    {details['adults']}\n"
            f"Children:  {details.get('children', 0)}\n"
            f"---------------------------\n"
            f"Confirmation sent to {details['email']}.\n\n"
            f"We look forward to welcoming you!"
        )
    except Exception as e:
        log.error(f"Booking API failed: {e}")
        return (
            f"Booking Failed\n\n"
            f"Sorry {details.get('guest_name', 'there')}, we could not complete your booking.\n\n"
            f"Please try again or contact us:\n"
            f"Phone: +1 (555) 123-4567\n"
            f"Email: reservations@denissonsbeach.com"
        )


# ── Send WhatsApp ──────────────────────────────────
def send_whatsapp(to: str, message: str):
    try:
        sender = TWILIO_NUMBER
        if not sender.startswith("whatsapp:"):
            sender = f"whatsapp:{sender}"

        twilio_client.messages.create(
            body=message,
            from_=sender,
            to=to
        )
        log.info(f"WhatsApp sent to {to}")
    except Exception as e:
        log.error(f"Failed to send WhatsApp: {e}")


# ── Run ────────────────────────────────────────────
if __name__ == '__main__':
    start_keep_alive()
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)