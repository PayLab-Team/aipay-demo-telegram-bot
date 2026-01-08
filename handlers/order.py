import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from models import MENU_ITEMS, get_menu_item_by_id

# Conversation states
WAITING_PHONE = 1


async def add_item_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add selected item to cart."""
    query = update.callback_query
    await query.answer()

    # Extract item ID from callback data
    item_id = int(query.data.split("_")[-1])
    item = get_menu_item_by_id(item_id)

    if item:
        if "order_items" not in context.user_data:
            context.user_data["order_items"] = []
        context.user_data["order_items"].append(item)

        await query.answer(f"{item.name} добавлен в корзину!")

    # Show updated menu
    await show_menu_after_add(query, context)


async def show_menu_after_add(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu with updated cart info."""
    keyboard = []
    for item in MENU_ITEMS:
        keyboard.append([
            InlineKeyboardButton(
                f"{item.name} - {item.price} ₸",
                callback_data=f"add_item_{item.id}",
            )
        ])

    order_items = context.user_data.get("order_items", [])
    if order_items:
        total = sum(item.price for item in order_items)
        # Визуальный разделитель
        keyboard.append([
            InlineKeyboardButton("─────────────────", callback_data="noop")
        ])
        # Кнопка корзины с эмодзи
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 Корзина ({len(order_items)}) - {total} ₸",
                callback_data="show_cart",
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите позицию из меню:", reply_markup=reply_markup)


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display cart contents with checkout option."""
    query = update.callback_query
    await query.answer()

    order_items = context.user_data.get("order_items", [])

    if not order_items:
        keyboard = [[InlineKeyboardButton("Меню", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Корзина пуста.", reply_markup=reply_markup)
        return

    # Build cart text
    cart_lines = []
    for i, item in enumerate(order_items, 1):
        cart_lines.append(f"{i}. {item.name} - {item.price} ₸")

    total = sum(item.price for item in order_items)
    cart_text = "\n".join(cart_lines)

    keyboard = [
        [InlineKeyboardButton("Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton("Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("Добавить ещё", callback_data="show_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Ваш заказ:\n\n{cart_text}\n\n"
        f"Итого: {total} ₸",
        reply_markup=reply_markup,
    )


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the cart."""
    query = update.callback_query
    await query.answer("Корзина очищена")

    context.user_data["order_items"] = []

    keyboard = [[InlineKeyboardButton("Меню", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Корзина очищена.", reply_markup=reply_markup)


async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start checkout process - ask for phone number."""
    query = update.callback_query
    await query.answer()

    order_items = context.user_data.get("order_items", [])
    if not order_items:
        await query.edit_message_text("Корзина пуста. Добавьте товары.")
        return ConversationHandler.END

    # Show phone sharing button
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await query.edit_message_text("Укажите номер телефона Kaspi для оплаты:")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Нажмите кнопку ниже или введите номер вручную\n(формат: +7XXXXXXXXXX)",
        reply_markup=keyboard,
    )

    return WAITING_PHONE


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive phone number from shared contact."""
    contact = update.message.contact
    phone = contact.phone_number

    # Normalize to +7 format
    if not phone.startswith("+"):
        phone = "+" + phone

    context.user_data["phone"] = phone

    # Remove reply keyboard
    await update.message.reply_text(
        f"Номер получен: {phone}",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Trigger payment
    from handlers.payment import process_payment
    return await process_payment(update, context)


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate phone number from text input."""
    phone = update.message.text.strip()

    # Normalize phone number
    phone = re.sub(r"[\s\-\(\)]", "", phone)

    # Validate Kazakhstan phone number
    if re.match(r"^(\+7|8|7)7\d{9}$", phone):
        # Normalize to +7 format
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        elif phone.startswith("7") and not phone.startswith("+"):
            phone = "+" + phone

        context.user_data["phone"] = phone

        # Remove reply keyboard
        await update.message.reply_text(
            f"Номер получен: {phone}",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Trigger payment
        from handlers.payment import process_payment
        return await process_payment(update, context)
    else:
        await update.message.reply_text(
            "Неверный формат номера. Введите номер в формате:\n"
            "+7XXXXXXXXXX или 87XXXXXXXXXX"
        )
        return WAITING_PHONE


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the checkout process."""
    await update.message.reply_text(
        "Оформление заказа отменено.",
    )
    return ConversationHandler.END


# Handlers
cart_callback_handler = CallbackQueryHandler(add_item_to_cart, pattern="^add_item_")
checkout_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(checkout, pattern="^checkout$")],
    states={
        WAITING_PHONE: [
            MessageHandler(filters.CONTACT, receive_contact),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
        ],
    },
    fallbacks=[MessageHandler(filters.COMMAND, cancel_checkout)],
)

phone_handler = CallbackQueryHandler(show_cart, pattern="^show_cart$")
