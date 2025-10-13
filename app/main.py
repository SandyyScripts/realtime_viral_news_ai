from dotenv import load_dotenv
import logging
import os
import sys

# Load environment variables from .env file
load_dotenv()

from app.services.perplexity_service import transform_rss_with_perplexity
from app.services.news_emailer import send_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app/logs/news_pipeline.log', mode='a')
    ]
)

def validate_environment():
    """Validate required environment variables at startup"""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API for news processing",
        "EMAIL_USERNAME": "Email sender account",
        "EMAIL_PASSWORD": "Email password",
        "EMAIL_TO": "Email recipient(s)"
    }

    # At least one image generation API key required
    has_image_api = os.getenv("NEBIUS_API_KEY") or os.getenv("GOOGLE_API_KEY")

    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var} ({description})")

    if not has_image_api:
        missing.append("  - NEBIUS_API_KEY or GOOGLE_API_KEY (for background image generation)")

    if missing:
        logging.error("❌ Missing required environment variables:")
        for m in missing:
            logging.error(m)
        sys.exit(1)

    logging.info("✅ Environment validation passed")

def run_job():
    """The main job to be scheduled."""
    logging.info("="*60)
    logging.info("🚀 Starting news pipeline")
    logging.info("="*60)

    try:
        # Step 1: Fetch and process news
        logging.info("📰 Step 1: Fetching and filtering news from RSS feeds...")
        news_content = transform_rss_with_perplexity()

        if not news_content or len(news_content) == 0:
            logging.warning("⚠️ No viral-worthy news found in this cycle")
            logging.info("   This is normal - strict filtering rejects 70% of news")
            logging.info("   The pipeline will run again on next schedule")
            return

        logging.info(f"✅ Step 1 Complete: {len(news_content)} high-quality posts selected")

        # Step 2: Generate images and send email
        logging.info("📧 Step 2: Generating images and sending email...")
        send_email(
            news_items=news_content,
            model_name="GPT-4o-mini"
        )

        logging.info("="*60)
        logging.info(f"✅ Pipeline completed successfully - {len(news_content)} posts sent")
        logging.info("="*60)

    except KeyboardInterrupt:
        logging.info("⏹️ Pipeline stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error("="*60)
        logging.error(f"❌ Pipeline failed with error: {e}")
        logging.error("="*60)
        import traceback
        traceback.print_exc()
        # Don't sys.exit() - let scheduler retry
        raise


if __name__ == "__main__":
    # Validate environment before running
    validate_environment()
    run_job()