from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from models import MENU_ITEMS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with menu button."""
    keyboard = [[InlineKeyboardButton("Меню", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать! Я бот для демонстрации AIPay.\n\n"
        "Нажмите 'Меню' для оформления заказа.",
        reply_markup=reply_markup,
    )

    # Initialize user's order in context
    context.user_data["order_items"] = []


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display menu with items as inline buttons."""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for item in MENU_ITEMS:
        keyboard.append([
            InlineKeyboardButton(
                f"{item.name} - {item.price} ₸",
                callback_data=f"add_item_{item.id}",
            )
        ])

    # Add cart button if items exist
    order_items = context.user_data.get("order_items", [])
    if order_items:
        total = sum(item.price for item in order_items)
        keyboard.append([
            InlineKeyboardButton(
                f"Корзина ({len(order_items)}) - {total} ₸",
                callback_data="show_cart",
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Выберите позицию из меню:",
        reply_markup=reply_markup,
    )


# Handlers
start_handler = CommandHandler("start", start)
menu_handler = CallbackQueryHandler(show_menu, pattern="^show_menu$")
