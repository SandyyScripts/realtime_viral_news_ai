from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

from app.config import PROMPT, EMAIL_SUBJECT
from app.services.perplexity_service import call_perplexity, extract_text,transform_rss_with_perplexity
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
    news_content = transform_rss_with_perplexity()

    if not news_content:
        logging.error("Failed to get response from Perplexity. Aborting job.")
        return
    
    send_email(
        news_items=news_content,
        model_name="LLM"
    )
    logging.info("--- Job finished ---")


if __name__ == "__main__":
    run_job()