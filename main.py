import telebot
import config
import database
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers

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
