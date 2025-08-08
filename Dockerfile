# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | cut -d " " -f3 | cut -d "." -f1-3) \
    && CHROMEDRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}) \
    && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver* \
    && chmod +x /usr/local/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Copy cron job file
COPY crontab /etc/cron.d/stock-split-checker

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/stock-split-checker

# Apply cron job
RUN crontab /etc/cron.d/stock-split-checker

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose any ports if needed (optional)
# EXPOSE 8080

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
