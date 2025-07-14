FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    curl \
    unzip \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy app files
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Expose port
EXPOSE 5000

CMD ["python", "app.py"]


