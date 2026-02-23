"""
ai_extractor.py
Uses Gemini 1.5 Flash (free) to extract structured booking details
from any natural language WhatsApp message.
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
- Convert dates like "March 10 2025" to "2025-03-10"
- If adults not mentioned, default to 1
- If children not mentioned, default to 0
- room_type options: Premium Suite, Deluxe Room, Executive Room, Family Suite, Deluxe Sea View Room, Presidential Suite
- Return ONLY the JSON object, nothing else
"""


def extract_booking_details(message: str) -> dict:
    """Send message to Gemini and extract structured booking data."""
    log.info("Sending to Gemini for extraction...")

    try:
        response = model.generate_content(
            EXTRACTION_PROMPT.format(message=message)
        )

        raw = response.text.strip()
        log.info(f"Gemini response: {raw}")

        # Strip any markdown fences
        raw = re.sub(r'```json|```', '', raw).strip()

        # Extract JSON safely
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in Gemini response")

        data = json.loads(match.group())
        log.info(f"Extracted: {data}")
        return data

    except json.JSONDecodeError as e:
        log.error(f"JSON parse error: {e}")
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    except Exception as e:
        log.error(f"Gemini extraction failed: {e}")
        raise