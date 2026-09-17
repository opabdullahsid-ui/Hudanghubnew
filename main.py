import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
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
    HTTPServer(('0.0.0.0', port), Ping).serve_forever()

# Start the server in the background
threading.Thread(target=run_ping, daemon=True).start()
# -----------------------------------------

# Initialize database tables
database.init_db()

# Initialize Bot
bot = telebot.TeleBot(config.BOT_TOKEN)

# Register Admin Handlers FIRST so admin buttons take precedence
register_admin_handlers(bot)
register_user_handlers(bot)

if __name__ == "__main__":
    print("🚀 ZerekDrop Store Bot is running...")
    bot.infinity_polling()
