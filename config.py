import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# AIPay API
AIPAY_API_URL = os.getenv("AIPAY_API_URL", "https://dev.aipay.kz")
AIPAY_BEARER_TOKEN = os.getenv("AIPAY_BEARER_TOKEN")
AIPAY_COMPANY_EXTERNAL_ID = os.getenv("AIPAY_COMPANY_EXTERNAL_ID")

# Payment polling settings
PAYMENT_POLL_INTERVAL = 3  # seconds
PAYMENT_TIMEOUT = 120  # seconds (2 minutes)
