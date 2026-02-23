"""
Room Booking AI Agent — main.py
Denisson's Beach Resort | booking.heykoala.ai
"""

import os
import json
import logging
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

# ── Twilio Client ──────────────────────────────────
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# ── Flask App ──────────────────────────────────────
app = Flask(__name__)


# ── Health Check ───────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return {"status": "running"}, 200


# ── WhatsApp Webhook ───────────────────────────────
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender       = request.values.get('From', '')

    log.info(f"Message from {sender}: {incoming_msg}")

    # Send instant acknowledgement
    send_whatsapp(sender, "Processing your booking request, please wait...")

    # Process and get reply
    reply = process_booking_request(incoming_msg)

    # Send final reply
    send_whatsapp(sender, reply)

    return Response("<Response></Response>", mimetype='text/xml')


# ── Core Booking Logic ─────────────────────────────
def process_booking_request(message: str) -> str:

    # Step 1: Extract with Gemini
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

    # Step 2: Check required fields
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

    # Step 3: Create booking
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
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=to
        )
        log.info(f"WhatsApp sent to {to}")
    except Exception as e:
        log.error(f"Failed to send WhatsApp: {e}")


# ── Run ────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)