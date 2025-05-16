import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from stock_api import get_current_price, calculate_moving_averages
from plotter import generate_chart
from alerts import add_alert, get_alerts, remove_alert

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store paused state for each chat
PAUSED_CHATS = set()

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    from alerts import ALERTS, get_alerts, remove_alert
    for chat_id in list(ALERTS.keys()):
        if chat_id in PAUSED_CHATS:
            continue
        alerts = get_alerts(chat_id)
        for symbol, threshold in alerts.items():
            current_price = get_current_price(symbol)
            if current_price and current_price >= threshold:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Alert: {symbol} has reached ${current_price:.2f}, exceeding your threshold of ${threshold:.2f}!"
                )
                remove_alert(chat_id, symbol)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Get Price", callback_data="price")],
        [InlineKeyboardButton("Moving Averages", callback_data="ma")],
        [InlineKeyboardButton("Set Alert", callback_data="alert")],
        [InlineKeyboardButton("View Chart", callback_data="chart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Stock Bot! Select an option or use /help for commands.", reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Stock Bot Commands:\n"
        "/start - Show the menu\n"
        "/help - Show this message\n"
        "/cancel - Cancel current action\n"
        "/stop - Pause alerts\n"
        "/restart - Resume alerts\n\n"
        "Features (select from menu or use commands):\n"
        "- Get Price: Enter symbol (e.g., AAPL)\n"
        "- Moving Averages: Enter symbol (e.g., AAPL)\n"
        "- Set Alert: Enter symbol and threshold (e.g., AAPL 100)\n"
        "- View Chart: Enter symbol (e.g., AAPL)"
    )
    await update.message.reply_text(help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("action", None)
    await update.message.reply_text("Action cancelled. Use /start to begin again.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    PAUSED_CHATS.add(chat_id)
    await update.message.reply_text("Alerts paused. Use /restart to resume.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    PAUSED_CHATS.discard(chat_id)
    await update.message.reply_text("Alerts resumed.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    context.user_data["action"] = query.data
    context.user_data["user_id"] = user_id  # Store user_id to match later
    logger.info(f"User {user_id} selected action: {query.data} in chat {query.message.chat_id}")
    if query.data == "price":
        await query.message.reply_text("Enter stock symbol (e.g., AAPL):", reply_to_message_id=query.message.message_id)
    elif query.data == "ma":
        await query.message.reply_text("Enter stock symbol for moving averages:", reply_to_message_id=query.message.message_id)
    elif query.data == "alert":
        await query.message.reply_text("Enter stock symbol and price threshold (e.g., AAPL 100):", reply_to_message_id=query.message.message_id)
    elif query.data == "chart":
        await query.message.reply_text("Enter stock symbol for price chart:", reply_to_message_id=query.message.message_id)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    logger.info(f"Received text '{text}' from user {user_id} in chat {chat_id}")

    # Check if the user_id matches the one who initiated the action
    stored_user_id = context.user_data.get("user_id")
    if stored_user_id != user_id:
        logger.warning(f"User mismatch: Expected {stored_user_id}, got {user_id}")
        await update.message.reply_text("Please select an option from the menu first using /start.")
        return

    action = context.user_data.get("action")
    logger.info(f"Action for user {user_id}: {action}")

    if action == "price":
        if text.upper() == "USD":
            await update.message.reply_text("USD is the base currency and does not have a price. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
        else:
            price = get_current_price(text.upper())
            if isinstance(price, str):  # Rate limit message
                await update.message.reply_text(price)
            elif price:
                await update.message.reply_text(f"Current price of {text.upper()}: ${price:.2f}")
            else:
                await update.message.reply_text("Invalid symbol or API error.")
    elif action == "ma":
        if text.upper() == "USD":
            await update.message.reply_text("USD is the base currency and cannot be used for moving averages. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
        else:
            symbol = text.upper()
            ma7 = calculate_moving_averages(symbol, 7)
            ma14 = calculate_moving_averages(symbol, 14)
            logger.info(f"MA7: {ma7}, MA14: {ma14}")
            if isinstance(ma7, str):  # Rate limit message
                await update.message.reply_text(ma7)
            elif ma7 is not None and ma14 is not None:
                await update.message.reply_text(
                    f"{symbol} Moving Averages:\n7-day: ${ma7:.2f}\n14-day: ${ma14:.2f}"
                )
            else:
                await update.message.reply_text("Invalid symbol or API error.")
    elif action == "alert":
        try:
            symbol, threshold = text.split()
            symbol = symbol.upper()
            if symbol == "USD":
                await update.message.reply_text("USD is the base currency and cannot be used for alerts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
            else:
                threshold = float(threshold)
                add_alert(chat_id, symbol, threshold)
                await update.message.reply_text(
                    f"Alert set for {symbol} at ${threshold:.2f}."
                )
        except ValueError:
            await update.message.reply_text("Please enter symbol and threshold (e.g., AAPL 100).")
    elif action == "chart":
        if text.upper() == "USD":
            await update.message.reply_text("USD is the base currency and cannot be used for charts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
        else:
            symbol = text.upper()
            try:
                chart_path = generate_chart(symbol)
                if chart_path:
                    with open(chart_path, "rb") as photo:
                        await update.message.reply_photo(photo=photo)
                    os.remove(chart_path)
                else:
                    await update.message.reply_text("Invalid symbol or API error.")
            except Exception as e:
                logger.error(f"Error generating chart for {symbol}: {e}")
                await update.message.reply_text("Failed to generate chart. Please try again later.")
    else:
        await update.message.reply_text("Use /start for the menu or /help for commands.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.job_queue.run_repeating(check_alerts, interval=60, first=10)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()