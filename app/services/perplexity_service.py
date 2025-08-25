import requests
import time
import json
import logging
from typing import Union
from app.config import PERPLEXITY_MODEL, PPLX_API_KEY

def redact(api_key):
    if api_key:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return "Not set"

# Using Union for type hinting for compatibility with Python < 3.10
def call_perplexity(prompt: str, model: str = PERPLEXITY_MODEL, retries: int = 3, timeout: int = 60) -> Union[dict, None]:
    if not PPLX_API_KEY or PPLX_API_KEY == "REPLACE_ME":
        logging.error("Missing PERPLEXITY_API_KEY (set as env var).")
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = { "Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json" }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Be precise, concise. India audience."},
            {"role": "user", "content": prompt},
        ],
    }

    logging.info("👉 Calling Perplexity…")
    logging.info(f"   URL: {url}")
    logging.info(f"   Model: {model}")
    logging.info(f"   Auth: {redact(PPLX_API_KEY)}")
    logging.info(f"   Prompt: {(prompt[:180] + '…') if len(prompt) > 180 else prompt}")

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            logging.info(f"   HTTP {resp.status_code}")
            if resp.status_code >= 400:
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    sleep_s = 2 ** (attempt - 1)
                    logging.warning(f"   Transient error; retrying in {sleep_s}s…")
                    time.sleep(sleep_s)
                    continue
                resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"   Attempt {attempt}/{retries} failed: {e}")
            if attempt == retries:
                raise
    return None

def extract_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        logging.error(f"Error extracting text from Perplexity response: {e}")
        # fallback: return readable JSON
        return json.dumps(data, indent=2)
