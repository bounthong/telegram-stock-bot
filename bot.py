import os
  import logging
  import tempfile
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
  from alerts import add_alert, get_alerts, remove_alert

  # Logging setup
  logging.basicConfig(
      format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
  )
  logger = logging.getLogger(__name__)

  # Store paused state for each chat
  PAUSED_CHATS = set()

  async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
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
          "/restart - Resume alerts\n"
          "/price <symbol> - Get current price (e.g., /price AAPL)\n"
          "/ma <symbol> - Get moving averages (e.g., /ma AAPL)\n"
          "/alert <symbol> <threshold> [interval] - Set alert (e.g., /alert AAPL 100 30)\n"
          "/chart <symbol> - View price chart (e.g., /chart AAPL)\n\n"
          "Features (select from menu or use commands):\n"
          "- Get Price: Enter symbol (e.g., AAPL)\n"
          "- Moving Averages: Enter symbol (e.g., AAPL)\n"
          "- Set Alert: Enter symbol, threshold, and optional interval (seconds)\n"
          "- View Chart: Enter symbol (e.g., AAPL)"
      )
      await update.message.reply_text(help_text)

  async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
      context.user_data.pop("action", None)
      context.user_data.pop("user_id", None)
      await update.message.reply_text("Action cancelled. Use /start to begin again.")

  async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
      chat_id = update.message.chat_id
      PAUSED_CHATS.add(chat_id)
      await update.message.reply_text("Alerts paused. Use /restart to resume.")

  async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
      chat_id = update.message.chat_id
      PAUSED_CHATS.discard(chat_id)
      await update.message.reply_text("Alerts resumed.")

  async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      if not context.args:
          await update.message.reply_text("Usage: /price <symbol> (e.g., /price AAPL)")
          return
      symbol = context.args[0].upper()
      if symbol == "USD":
          await update.message.reply_text("USD is the base currency and does not have a price. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
          return
      price = get_current_price(symbol)
      if isinstance(price, str):
          await update.message.reply_text(price)
      elif price:
          await update.message.reply_text(f"Current price of {symbol}: ${price:.2f}")
      else:
          await update.message.reply_text("Invalid symbol or API error.")

  async def ma_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      if not context.args:
          await update.message.reply_text("Usage: /ma <symbol> (e.g., /ma AAPL)")
          return
      symbol = context.args[0].upper()
      if symbol == "USD":
          await update.message.reply_text("USD is the base currency and cannot be used for moving averages. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
          return
      ma7 = calculate_moving_averages(symbol, 7)
      ma14 = calculate_moving_averages(symbol, 14)
      if isinstance(ma7, str):
          await update.message.reply_text(ma7)
      elif ma7 is not None and ma14 is not None:
          await update.message.reply_text(
              f"{symbol} Moving Averages:\n7-day: ${ma7:.2f}\n14-day: ${ma14:.2f}"
          )
      else:
          await update.message.reply_text("Invalid symbol or API error.")

  async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      chat_id = update.message.chat_id
      if len(context.args) < 2:
          await update.message.reply_text("Usage: /alert <symbol> <threshold> [interval] (e.g., /alert AAPL 100 30)")
          return
      symbol = context.args[0].upper()
      try:
          threshold = float(context.args[1])
          interval = int(context.args[2]) if len(context.args) > 2 else ALERT_CHECK_INTERVAL
      except ValueError:
          await update.message.reply_text("Threshold and interval must be numbers (e.g., /alert AAPL 100 30).")
          return
      if symbol == "USD":
          await update.message.reply_text("USD is the base currency and cannot be used for alerts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
          return
      add_alert(chat_id, symbol, threshold, interval)
      await update.message.reply_text(
          f"Alert set for {symbol} at ${threshold:.2f} with check interval {interval} seconds."
      )

  async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      if not context.args:
          await update.message.reply_text("Usage: /chart <symbol> (e.g., /chart AAPL)")
          return
      symbol = context.args[0].upper()
      if symbol == "USD":
          await update.message.reply_text("USD is the base currency and cannot be used for charts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
          return
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

  async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
      query = update.callback_query
      user_id = query.from_user.id
      await query.answer()
      context.user_data["action"] = query.data
      context.user_data["user_id"] = user_id
      logger.info(f"User {user_id} selected action: {query.data} in chat {query.message.chat_id}")
      if query.data == "price":
          await query.message.reply_text("Enter stock symbol (e.g., AAPL):", reply_to_message_id=query.message.message_id)
      elif query.data == "ma":
          await query.message.reply_text("Enter stock symbol for moving averages:", reply_to_message_id=query.message.message_id)
      elif query.data == "alert":
          await query.message.reply_text("Enter stock symbol, price threshold, and optional interval (e.g., AAPL 100 30):", reply_to_message_id=query.message.message_id)
      elif query.data == "chart":
          await query.message.reply_text("Enter stock symbol for price chart:", reply_to_message_id=query.message.message_id)

  async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.message.from_user.id
      chat_id = update.message.chat_id
      text = update.message.text.strip()
      logger.info(f"Received text '{text}' from user {user_id} in chat {chat_id}")

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
              if isinstance(price, str):
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
              if isinstance(ma7, str):
                  await update.message.reply_text(ma7)
              elif ma7 is not None and ma14 is not None:
                  await update.message.reply_text(
                      f"{symbol} Moving Averages:\n7-day: ${ma7:.2f}\n14-day: ${ma14:.2f}"
                  )
              else:
                  await update.message.reply_text("Invalid symbol or API error.")
      elif action == "alert":
          try:
              parts = text.split()
              symbol = parts[0].upper()
              threshold = float(parts[1])
              interval = int(parts[2]) if len(parts) > 2 else ALERT_CHECK_INTERVAL
              if symbol == "USD":
                  await update.message.reply_text("USD is the base currency and cannot be used for alerts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
              else:
                  add_alert(chat_id, symbol, threshold, interval)
                  await update.message.reply_text(
                      f"Alert set for {symbol} at ${threshold:.2f} with check interval {interval} seconds."
                  )
          except ValueError:
              await update.message.reply_text("Please enter symbol, threshold, and optional interval (e.g., AAPL 100 30).")
      elif action == "chart":
          if text.upper() == "USD":
              await update.message.reply_text("USD is the base currency and cannot be used for charts. Please enter a valid stock or crypto symbol (e.g., AAPL, USDT).")
          else:
              symbol = text.upper()
              try:
                  with tempfile.NamedTemporaryFile(delete=True) as temp_file:
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
      # Use ApplicationBuilder for better control
      application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

      # Add handlers
      application.add_handler(CommandHandler("start", start))
      application.add_handler(CommandHandler("help", help_command))
      application.add_handler(CommandHandler("cancel", cancel))
      application.add_handler(CommandHandler("stop", stop))
      application.add_handler(CommandHandler("restart", restart))
      application.add_handler(CommandHandler("price", price_command))
      application.add_handler(CommandHandler("ma", ma_command))
      application.add_handler(CommandHandler("alert", alert_command))
      application.add_handler(CommandHandler("chart", chart_command))
      application.add_handler(CallbackQueryHandler(button))
      application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

      # Schedule the alert check job
      application.job_queue.run_repeating(check_alerts, interval=ALERT_CHECK_INTERVAL, first=10)

      # Start the bot with webhook
      port = int(os.environ.get("PORT", 8443))
      webhook_url = os.environ.get("WEBHOOK_URL", f"https://telegram-stock-bot.onrender.com/webhook")
      
      # Set webhook
      application.run_webhook(
          listen="0.0.0.0",
          port=port,
          url_path="/webhook",
          webhook_url=webhook_url
      )
      logger.info(f"Bot started with webhook at {webhook_url}")

  if __name__ == "__main__":
      main()