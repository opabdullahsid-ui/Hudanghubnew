import threading
import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
import config
import database
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers

# Enable verbose logging to display any silent handler errors in Render
logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

# --- BACKGROUND SERVER FOR UPTIMEROBOT ---
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_ping():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Ping)
    server.serve_forever()

threading.Thread(target=run_ping, daemon=True).start()
# -----------------------------------------

# Initialize database tables
database.init_db()

# Initialize Bot
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode=None)

# Register Handlers
register_admin_handlers(bot)
register_user_handlers(bot)

if __name__ == "__main__":
    print("🚀 ZerekDrop Store Bot is running...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook cleanup warning: {e}")
        
    bot.infinity_polling(
        allowed_updates=['message', 'callback_query', 'inline_query'],
        timeout=20,
        long_polling_timeout=20
    )
    
