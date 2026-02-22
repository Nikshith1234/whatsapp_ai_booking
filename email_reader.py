"""
email_reader.py
Reads booking request emails from Gmail using IMAP.
No OAuth needed — uses Gmail App Password (free).

SETUP:
1. Enable 2FA on your Gmail account
2. Go to: myaccount.google.com/apppasswords
3. Create app password → copy it to .env as GMAIL_APP_PASSWORD
"""

import os
import imaplib
import email
import logging
from email.header import decode_header
from dotenv import load_dotenv

from ai_extractor import extract_booking_details
from booking import create_booking

load_dotenv()
log = logging.getLogger(__name__)

GMAIL_USER     = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
BOOKING_LABEL  = "INBOX"  # or set a Gmail label like "Bookings"


def get_email_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass

    return body.strip()


def check_new_emails() -> list:
    """
    Connect to Gmail, find unread booking emails, process them.
    Returns list of processed results.
    """
    if not GMAIL_USER or not GMAIL_PASSWORD:
        log.error("GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
        return []

    results = []

    try:
        log.info("Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select(BOOKING_LABEL)

        # Search for unread emails with booking keywords
        _, search_data = mail.search(None, 'UNSEEN SUBJECT "booking"')
        email_ids = search_data[0].split()

        log.info(f"Found {len(email_ids)} unread booking emails")

        for eid in email_ids:
            try:
                _, data = mail.fetch(eid, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()

                sender = msg.get("From", "")
                body   = get_email_body(msg)

                log.info(f"Processing email from {sender}: {subject}")

                # Extract booking details
                details = extract_booking_details(
                    f"From: {sender}\nSubject: {subject}\n\n{body}"
                )

                # Create booking
                result = create_booking(details)

                # Mark as read
                mail.store(eid, '+FLAGS', '\\Seen')

                results.append({
                    "email": sender,
                    "booking": details,
                    "result": result
                })

                log.info(f"Booking created for {details.get('guest_name')}")

            except Exception as e:
                log.error(f"Failed to process email {eid}: {e}")
                results.append({"error": str(e)})

        mail.logout()

    except Exception as e:
        log.error(f"Gmail connection failed: {e}")

    return results
