from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

from app.config import PROMPT, EMAIL_SUBJECT
from app.services.perplexity_service import call_perplexity, extract_text
from app.parser.news_parser import parse_news_content
from app.services.news_emailer import send_email
from datetime import datetime, timezone

def run_job():
    """The main job to be scheduled."""
    logging.info("--- Running job ---")
    utc_now = datetime.now(timezone.utc)
    today_date = utc_now.astimezone().strftime("%d %B %Y")  # e.g., "08 September 2025"
    current_utc_hour = utc_now.hour
    current_prompt = PROMPT.format(
        today_date=today_date,
        current_utc_hour=current_utc_hour
    )
    
    # 1. Get content from Perplexity
    perplexity_response = call_perplexity(current_prompt)
    if not perplexity_response:
        logging.error("Failed to get response from Perplexity. Aborting job.")
        return

    extracted_text = extract_text(perplexity_response)
    if not extracted_text or extracted_text.startswith('{'): # Check for fallback JSON
        logging.error("Failed to extract text from Perplexity response. Aborting job.")
        return

    
    send_email(
        raw_content=extracted_text,
        model_name=perplexity_response.get("model", "LLM")
    )
    logging.info("--- Job finished ---")


if __name__ == "__main__":
    run_job()