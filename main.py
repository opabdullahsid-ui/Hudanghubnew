import threading
import os
import telebot
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
import database
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers

# --- BACKGROUND SERVER FOR UPTIMEROBOT ---
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

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
    
    # 1. Clear any stuck background queues
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
        
    # 2. THE FIX: Force Telegram to deliver button clicks!
    bot.infinity_polling(
        allowed_updates=['message', 'callback_query']
    )
    
