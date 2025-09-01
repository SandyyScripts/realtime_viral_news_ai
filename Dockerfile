FROM python:3.13-slim

# Install OS deps
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libgbm1 \
    libasound2 libpangocairo-1.0-0 libx11-xcb1 \
    libxdamage1 libxfixes3 libdrm2 libpango-1.0-0 libcairo2 \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install browsers
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "-m", "app.main"]