import threading
import os
import logging
import telebot
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
import database
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers

# Setup logging to reveal hidden errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- BACKGROUND SERVER FOR RENDER ---
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
        
    def log_message(self, format, *args):
        # Suppress noisy web server spam in the logs
        pass

def run_ping():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Ping)
    server.serve_forever()

threading.Thread(target=run_ping, daemon=True).start()
# -----------------------------------------

# Initialize database tables
try:
    database.init_db()
except Exception as e:
    logger.error(f"Database init failed: {e}")

# Initialize Bot
if not config.BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing! Check your Render Environment Variables.")

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode=None)

# Register Handlers
register_admin_handlers(bot)
register_user_handlers(bot)

if __name__ == "__main__":
    print("🚀 ZerekDrop Store Bot is running...")
    
    # 1. Clear any stuck background queues
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook cleared successfully.")
    except Exception as e:
        print(f"⚠️ Failed to clear webhook: {e}")
        
    # 2. Force Telegram to deliver button clicks and messages
    print("⏳ Starting infinity polling...")
    bot.infinity_polling(
        allowed_updates=['message', 'callback_query'],
        timeout=60,
        long_polling_timeout=60,
        logger_level=logging.INFO
    )
    
