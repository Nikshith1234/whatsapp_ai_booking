import os
if not os.path.exists('logs'):
    os.makedirs('logs')
"""
Room Booking AI Agent — main.py
Denisson's Beach Resort | booking.heykoala.ai
Trigger: WhatsApp (Twilio)
AI: Gemini 1.5 Flash (free)
Booking: Direct HTTP API
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
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # whatsapp:+14155238886

# ── Flask App ──────────────────────────────────────
app = Flask(__name__)


# ── WhatsApp Webhook ───────────────────────────────
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender       = request.values.get('From', '')  # whatsapp:+91xxxxxxxxxx

    log.info(f"Message from {sender}: {incoming_msg}")

    # Send instant acknowledgement while processing
    send_whatsapp(sender, "Processing your booking request, please wait...")

    # Process and get reply
    reply = process_booking_request(incoming_msg)

    # Send final success or failure reply
    send_whatsapp(sender, reply)

    return Response("<Response></Response>", mimetype='text/xml')


# ── Core Booking Logic ─────────────────────────────
def process_booking_request(message: str) -> str:

    # Step 1: Extract booking details with Gemini
    try:
        details = extract_booking_details(message)
        log.info(f"Extracted: {json.dumps(details, indent=2)}")
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        return (
            "Booking Failed\n\n"
            "Sorry, I could not understand your booking request.\n\n"
            "Please try again with this format:\n"
            "Hi, I'd like to book a Deluxe room. "
            "My name is John Silva, email john@gmail.com. "
            "Check-in March 10, check-out March 15. 2 adults."
        )

    # Step 2: Check required fields are present
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
            f"I could not find the following details:\n"
            f"{missing_list}\n\n"
            f"Please resend your message including all the above. Thank you!"
        )

    # Step 3: Create the booking via hotel API
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
            f"A confirmation email has been sent to {details['email']}.\n\n"
            f"We look forward to welcoming you!"
        )

    except Exception as e:
        log.error(f"Booking API failed: {e}")
        return (
            f"Booking Failed\n\n"
            f"Sorry {details.get('guest_name', 'there')}, we could not complete your booking right now.\n\n"
            f"Please try again in a few minutes or contact us directly:\n"
            f"Phone: +1 (555) 123-4567\n"
            f"Email: reservations@denissonsbeach.com"
        )


# ── Send WhatsApp Message ──────────────────────────
def send_whatsapp(to: str, message: str):
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=to
        )
        log.info(f"WhatsApp sent to {to}")
    except Exception as e:
        log.error(f"Failed to send WhatsApp to {to}: {e}")


# ── Local Test ─────────────────────────────────────
def test_locally():
    tests = [
        "Hi, book a Deluxe room for John Silva (john@gmail.com). Check-in March 10 2025, check-out March 15 2025. 2 adults 1 child.",
        "I want a Standard room. Check-in April 1, check-out April 5. 2 adults.",
        "hello can you help me",
    ]
    for i, msg in enumerate(tests, 1):
        print(f"\n{'='*55}\nTEST {i}: {msg[:60]}...\n{'='*55}")
        reply = process_booking_request(msg)
        print(reply)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_locally()
    else:
        log.info("Starting server on port 5000...")
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)