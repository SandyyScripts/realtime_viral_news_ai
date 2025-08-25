from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

from app.config import PROMPT, EMAIL_SUBJECT
from app.services.perplexity_service import call_perplexity, extract_text
from app.services.email_service import send_email

def run_job():
    """The main job to be scheduled."""
    logging.info("--- Running job ---")
    
    # 1. Get content from Perplexity
    perplexity_response = call_perplexity(PROMPT)
    if not perplexity_response:
        logging.error("Failed to get response from Perplexity. Aborting job.")
        return

    extracted_text = extract_text(perplexity_response)
    if not extracted_text or extracted_text.startswith('{'): # Check for fallback JSON
        logging.error("Failed to extract text from Perplexity response. Aborting job.")
        return

    # 2. Send the email
    send_email(EMAIL_SUBJECT, extracted_text)
    logging.info("--- Job finished ---")

if __name__ == "__main__":
    run_job()