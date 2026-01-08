import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler

import config
from api_client import aipay_client
from models import InvoiceStatus

logger = logging.getLogger(__name__)


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create invoice and start polling for payment status."""
    order_items = context.user_data.get("order_items", [])
    phone = context.user_data.get("phone")

    if not order_items or not phone:
        await update.message.reply_text("Ошибка: данные заказа не найдены.")
        return ConversationHandler.END

    total = sum(item.price for item in order_items)
    item_names = ", ".join(item.name for item in order_items)
    message = f"Заказ: {item_names}"

    # Send "creating invoice" message
    status_message = await update.message.reply_text(
        f"Создаем счет на оплату...\n\n"
        f"Сумма: {total} ₸\n"
        f"Телефон: {phone}"
    )

    # Create invoice via API
    result = await aipay_client.create_invoice(phone, total, message)

    if not result:
        await status_message.edit_text(
            "Ошибка при создании счета. Попробуйте позже."
        )
        return ConversationHandler.END

    # Extract invoice ID from response
    # Response format: {'statusDto': {...}, 'obj': {'entity': {'id': '...', 'internal_id': ...}}}
    invoice_id = (
        result.get("obj", {}).get("entity", {}).get("id")
        or result.get("data", {}).get("id")
        or result.get("id")
    )

    if not invoice_id:
        logger.error(f"No invoice ID in response: {result}")
        await status_message.edit_text(
            "Ошибка: не удалось получить ID счета."
        )
        return ConversationHandler.END

    context.user_data["invoice_id"] = invoice_id

    # Update message with payment info
    await status_message.edit_text(
        f"Счет отправлен на ваш Kaspi!\n\n"
        f"Сумма: {total} ₸\n"
        f"Телефон: {phone}\n\n"
        f"Откройте приложение Kaspi и подтвердите оплату.\n"
        f"Ожидаем подтверждение..."
    )

    # Start polling for payment status
    asyncio.create_task(
        poll_payment_status(
            context.bot,
            update.effective_chat.id,
            status_message.message_id,
            invoice_id,
            context.user_data,
        )
    )

    return ConversationHandler.END


async def poll_payment_status(
    bot,
    chat_id: int,
    message_id: int,
    invoice_id: str,
    user_data: dict,
) -> None:
    """Poll for payment status until paid, cancelled, or timeout."""
    elapsed = 0

    while elapsed < config.PAYMENT_TIMEOUT:
        await asyncio.sleep(config.PAYMENT_POLL_INTERVAL)
        elapsed += config.PAYMENT_POLL_INTERVAL

        # Get current status
        response = await aipay_client.get_invoice_status(invoice_id)

        if not response:
            continue

        status = aipay_client.parse_status(response)

        if status == InvoiceStatus.PAID:
            # Payment successful
            keyboard = [[InlineKeyboardButton("Новый заказ", callback_data="show_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    "Оплата получена!\n\n"
                    "Ваш заказ готовится.\n"
                    "Спасибо за покупку!"
                ),
                reply_markup=reply_markup,
            )

            # Clear order
            user_data["order_items"] = []
            user_data["phone"] = None
            user_data["invoice_id"] = None
            return

        elif status in (InvoiceStatus.CANCELLED, InvoiceStatus.FAILED):
            keyboard = [[InlineKeyboardButton("Попробовать снова", callback_data="show_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Платеж отменен или произошла ошибка.\nПопробуйте снова.",
                reply_markup=reply_markup,
            )
            return

        elif status == InvoiceStatus.EXPIRED:
            keyboard = [[InlineKeyboardButton("Попробовать снова", callback_data="show_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Время ожидания оплаты истекло.\nПопробуйте снова.",
                reply_markup=reply_markup,
            )
            return

    # Timeout reached
    keyboard = [[InlineKeyboardButton("Попробовать снова", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            "Время ожидания оплаты истекло (2 мин).\n"
            "Если вы оплатили, платеж будет обработан.\n"
            "Попробуйте снова для нового заказа."
        ),
        reply_markup=reply_markup,
    )


async def clear_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle clear cart button."""
    query = update.callback_query
    await query.answer("Корзина очищена")

    context.user_data["order_items"] = []

    keyboard = [[InlineKeyboardButton("Меню", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Корзина очищена.", reply_markup=reply_markup)


# Handlers
payment_callback_handler = CallbackQueryHandler(clear_cart_callback, pattern="^clear_cart$")
