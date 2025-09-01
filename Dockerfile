FROM python:3.13-slim

# Install system dependencies (for Playwright, Pillow, fonts, etc.)
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libgbm1 \
    libasound2 libpangocairo-1.0-0 libx11-xcb1 \
    libxdamage1 libxfixes3 libdrm2 libpango-1.0-0 libcairo2 \
    libjpeg62-turbo libpng16-16 zlib1g \
    wget gnupg ca-certificates \
    fonts-unifont fonts-dejavu fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium for Playwright (matches pip-installed playwright version)
RUN playwright install chromium

# Copy project files
COPY . .

# Default command
CMD ["python", "-m", "app.main"]