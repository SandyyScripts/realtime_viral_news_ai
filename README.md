# Real-time Viral News AI

This project is a Python-based application that automates the process of fetching real-time viral news using the Perplexity AI API and sending it to a list of recipients via email. The application is designed to be deployed as a background worker on platforms like Render.

## Features

- **Automated News Fetching:** Fetches the latest viral news from Perplexity AI at scheduled intervals.
- **Email Delivery:** Sends the curated news to a list of recipients using a professional HTML template.
- **Scheduled Jobs:** Runs automatically at predefined times (11 AM, 2 PM, 5 PM, 7 PM, 9 PM, 11 PM IST) using a scheduler.
- **Robust and Production-Ready:** Includes features like centralized configuration, structured logging, and graceful error handling.
- **Easy to Deploy:** Comes with a `Procfile` for easy deployment on platforms like Render.

## Project Structure

```
.
├── app/
│   ├── config.py           # Centralized configuration and logging setup
│   ├── main.py             # Main job logic
│   ├── services/
│   │   ├── perplexity_service.py # Service for Perplexity AI API
│   │   └── email_service.py    # Service for sending emails
│   └── templates/
│       └── email_template.html # HTML template for the email
├── tests/
│   └── test_parsing.py     # Unit tests for the parsing logic
├── .env.example          # Example environment file
├── .gitignore
├── Procfile              # For deployment on Render
├── README.md
├── requirements.txt      # Python dependencies
└── scheduler.py          # Scheduler to run the main job
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd realtime_viral_news_ai
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create and configure the `.env` file:**
    Create a file named `.env` in the root directory of the project and add the following environment variables. You can use the `.env.example` file as a template.

## Usage

*   **To run the scheduler and start the application:**
    ```bash
    python scheduler.py
    ```

*   **To run the tests:**
    ```bash
    python -m unittest tests/test_parsing.py
    ```

## Deployment on Render

1.  **Push your code to a GitHub repository.**
2.  **Create a new "Background Worker" service on Render** and connect your GitHub repository.
3.  **Set the "Start Command"** to `python scheduler.py`. Render should automatically detect the `Procfile`.
4.  **Add your environment variables** from your `.env` file in the Render dashboard under the "Environment" section.
5.  **Deploy** the service.

## Configuration

The following table lists all the environment variables used in this project:

| Variable              | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `PERPLEXITY_API_KEY`  | Your API key for the Perplexity AI API.                                     |
| `PERPLEXITY_MODEL`    | (Optional) The Perplexity model to use. Defaults to `pplx-7b-online`.       |
| `PROMPT`              | (Optional) The prompt to use for fetching news.                             |
| `EMAIL_HOST`          | (Optional) The SMTP host for your email provider. Defaults to `smtp.gmail.com`. |
| `EMAIL_PORT`          | (Optional) The SMTP port. Defaults to `465`.                                |
| `EMAIL_USERNAME`      | The username for your email account.                                        |
| `EMAIL_PASSWORD`      | The password or App Password for your email account.                        |
| `EMAIL_FROM`          | The email address to send the emails from.                                  |
| `EMAIL_TO`            | A comma-separated list of recipient email addresses.                        |
| `EMAIL_SUBJECT`       | (Optional) The subject of the email.                                        |
