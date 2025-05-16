ALERTS = {}  # Format: {chat_id: {symbol: (threshold, interval)}}

def add_alert(chat_id, symbol, threshold, interval=60):
    if chat_id not in ALERTS:
        ALERTS[chat_id] = {}
    ALERTS[chat_id][symbol] = (threshold, interval)

def get_alerts(chat_id):
    return ALERTS.get(chat_id, {})

def remove_alert(chat_id, symbol):
    if chat_id in ALERTS and symbol in ALERTS[chat_id]:
        del ALERTS[chat_id][symbol]
    if chat_id in ALERTS and not ALERTS[chat_id]:
        del ALERTS[chat_id]