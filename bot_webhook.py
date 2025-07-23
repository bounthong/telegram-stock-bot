import tempfile
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ApplicationBuilder,
)
from config import TELEGRAM_BOT_TOKEN, ALERT_CHECK_INTERVAL
from stock_api import get_current_price, calculate_moving_averages
from plotter import generate_chart
from alerts import add_alert, get_alerts, remove_alert, ALERTS
from user_plan import get_user_plan, is_premium, is_bmc, is_free, set_user_plan

# Configure matplotlib for headless environments
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global state
PAUSED_CHATS = set()
ADMIN_USER_IDS = [7087347278]  # Replace with your Telegram ID

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Check and trigger price alerts"""
    try:
        for chat_id in list(ALERTS.keys()):
            if chat_id in PAUSED_CHATS:
                continue
            alerts = get_alerts(chat_id)
            for symbol, (threshold, interval) in alerts.items():
                current_price = get_current_price(symbol)
                if isinstance(current_price, str):  # Rate limit message
                    continue
                if current_price and current_price >= threshold:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Alert: {symbol} has reached ${current_price:.2f}, exceeding your threshold of ${threshold:.2f}!"
                    )
                    remove_alert(chat_id, symbol)
    except Exception as e:
        logger.error(f"Error in check_alerts: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with inline keyboard"""
    keyboard = [
        [InlineKeyboardButton("Get Price", callback_data="price")],
        [InlineKeyboardButton("Moving Averages", callback_data="ma")],
        [InlineKeyboardButton("Set Alert", callback_data="alert")],
        [InlineKeyboardButton("View Chart", callback_data="chart")],
        [InlineKeyboardButton("Upgrade Plans", callback_data="upgrade")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Stock Bot! Select an option or use /help for commands.", 
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Stock Bot Commands:\n"
        "/start - Show the menu\n"
        "/help - Show this message\n"
        "/price <symbol> - Get current price\n"
        "/ma <symbol> - Get moving averages\n"
        "/alert <symbol> <threshold> - Set alert\n"
        "/chart <symbol> - View price chart\n"
        "/myplan - View your current plan\n"
        "/upgrade - View upgrade options"
    )
    await update.message.reply_text(help_text)

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💼 *Upgrade Plans*\n\n"
        "🆓 *Free Plan*\n"
        "• Price check\n"
        "• 1 alert\n"
        "• Basic charts\n\n"
        "☕ *BMC Plan* ($3 one-time)\n"
        "• All Free features\n"
        "• 3 alerts\n"
        "• Priority support\n\n"
        "💎 *Premium* ($5/month)\n"
        "• Unlimited alerts\n"
        "• Real-time notifications\n"
        "• Premium support\n\n"
        "🔗 [Donate](https://buymeacoffee.com/yourname)\n"
        "🔗 [Subscribe](https://yourlink.com/subscribe)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def myplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = get_user_plan(user_id)
    await update.message.reply_text(f"📊 Your current plan: *{plan.capitalize()}*", parse_mode="Markdown")

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price <symbol> (e.g., /price AAPL)")
        return
    symbol = context.args[0].upper()
    price = get_current_price(symbol)
    if isinstance(price, str):
        await update.message.reply_text(price)
    elif price:
        await update.message.reply_text(f"Current price of {symbol}: ${price:.2f}")
    else:
        await update.message.reply_text("Invalid symbol or API error.")

async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    # Check plan limits
    if is_free(user_id):
        existing = get_alerts(chat_id)
        if len(existing) >= 1:
            await update.message.reply_text("⚠️ Free plan allows only 1 alert. Upgrade for more.")
            return
    elif is_bmc(user_id):
        existing = get_alerts(chat_id)
        if len(existing) >= 3:
            await update.message.reply_text("☕ BMC plan allows 3 alerts. Upgrade to Premium for unlimited.")
            return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /alert <symbol> <threshold>")
        return
    
    symbol = context.args[0].upper()
    try:
        threshold = float(context.args[1])
        add_alert(chat_id, symbol, threshold, ALERT_CHECK_INTERVAL)
        await update.message.reply_text(f"Alert set for {symbol} at ${threshold:.2f}")
    except ValueError:
        await update.message.reply_text("Invalid threshold. Please enter a number.")

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /chart <symbol>")
        return
    symbol = context.args[0].upper()
    try:
        chart_path = generate_chart(symbol)
        if chart_path:
            with open(chart_path, "rb") as photo:
                await update.message.reply_photo(photo=photo)
            os.remove(chart_path)
        else:
            await update.message.reply_text("Invalid symbol or API error.")
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        await update.message.reply_text("Failed to generate chart.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "upgrade":
        await upgrade_command(update, context)
    # Add other button handlers as needed

async def post_init(application: Application):
    """Initialize webhook if in production"""
    if os.environ.get("ENV") == "prod":
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            await application.bot.set_webhook(
                url=f"{webhook_url}/webhook",
                drop_pending_updates=True
            )
            logger.info(f"Webhook configured for {webhook_url}")

async def setup_application() -> Application:
    """Configure and return the Telegram application"""
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("myplan", myplan_command))
    application.add_handler(CommandHandler("upgrade", upgrade_command))
    application.add_handler(CallbackQueryHandler(button))
    
    # Schedule jobs
    application.job_queue.run_repeating(check_alerts, interval=ALERT_CHECK_INTERVAL, first=10)
    
    return application

async def main():
    """Entry point for the bot"""
    application = await setup_application()
    
    if os.environ.get("ENV") == "prod":
        # Webhook mode for production
        port = int(os.getenv("PORT", 8080))
        await application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{os.getenv('WEBHOOK_URL')}/webhook"
        )
    else:
        # Polling mode for development
        await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
