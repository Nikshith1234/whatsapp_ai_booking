"""
ai_extractor.py
Uses Gemini 1.5 Flash (free) to extract structured booking details
from any natural language message (WhatsApp, email, etc.)
"""

import os
import json
import re
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

# ── Configure Gemini ───────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

EXTRACTION_PROMPT = """
You are a hotel booking assistant for Denisson's Beach Resort.
Extract booking details from the message below.
Return ONLY valid JSON — no explanation, no markdown, no extra text.

Message:
{message}

Return this exact JSON structure:
{{
  "guest_name": "full name or empty string",
  "email": "email address or empty string",
  "phone": "phone number or empty string",
  "check_in": "YYYY-MM-DD or empty string",
  "check_out": "YYYY-MM-DD or empty string",
  "room_type": "room type or empty string",
  "adults": 1,
  "children": 0,
  "special_requests": "any special requests or empty string"
}}

Rules:
- Convert dates like "March 10 2025" → "2025-03-10"
- If adults not mentioned, default to 1
- If children not mentioned, default to 0
- room_type options: Standard, Deluxe, Suite, Ocean View, Family Room
- Return ONLY the JSON object, nothing else
"""


def extract_booking_details(message: str) -> dict:
    """
    Send message to Gemini and extract structured booking data.
    Returns a dict with booking fields.
    """
    log.info("Sending to Gemini for extraction...")

    try:
        response = model.generate_content(
            EXTRACTION_PROMPT.format(message=message)
        )

        raw = response.text.strip()
        log.info(f"Gemini raw response: {raw}")

        # Strip any markdown fences Gemini might add
        raw = re.sub(r'```json|```', '', raw).strip()

        # Extract JSON object using regex (safety net)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in Gemini response")

        data = json.loads(match.group())
        log.info(f"Parsed booking data: {data}")
        return data

    except json.JSONDecodeError as e:
        log.error(f"JSON parse error: {e} | Raw: {raw}")
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    except Exception as e:
        log.error(f"Gemini extraction failed: {e}")
        raise


def test_extraction():
    """Quick test to verify Gemini key works."""
    test_msg = """
    Hello, I want to book a Deluxe room for 2 adults and 1 child.
    Name: Ana Costa, email: ana.costa@gmail.com
    Arriving March 20, leaving March 25, 2025.
    Can we get a sea view if possible?
    """

    print("Testing Gemini extraction...")
    result = extract_booking_details(test_msg)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    test_extraction()
