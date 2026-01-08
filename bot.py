import logging

from telegram.ext import Application

import config
from handlers import (
    cart_callback_handler,
    checkout_handler,
    menu_handler,
    payment_callback_handler,
    phone_handler,
    start_handler,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        return

    if not config.AIPAY_BEARER_TOKEN:
        logger.error("AIPAY_BEARER_TOKEN not set in environment")
        return

    if not config.AIPAY_COMPANY_EXTERNAL_ID:
        logger.error("AIPAY_COMPANY_EXTERNAL_ID not set in environment")
        return

    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Add handlers (order matters!)
    application.add_handler(start_handler)
    application.add_handler(checkout_handler)  # ConversationHandler first
    application.add_handler(menu_handler)
    application.add_handler(cart_callback_handler)
    application.add_handler(phone_handler)  # show_cart handler
    application.add_handler(payment_callback_handler)  # clear_cart handler

    # Start polling
    logger.info("Bot starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
