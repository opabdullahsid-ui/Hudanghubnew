import re
from telebot import types
import database

def main_reply_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_start = types.KeyboardButton("🚀 Start Hub")
    btn_catalog = types.KeyboardButton("🛍️ Products")
    btn_wallet = types.KeyboardButton("💎 Top-up Wallet")
    btn_orders = types.KeyboardButton("🧾 Orders History")
    btn_profile = types.KeyboardButton("👤 My Profile")
    btn_lang = types.KeyboardButton("🌐 Change Language")
    btn_support = types.KeyboardButton("💬 Live Support")
    
    markup.add(btn_start)
    markup.add(btn_catalog, btn_wallet)
    markup.add(btn_orders, btn_profile)
    markup.add(btn_lang, btn_support)
    return markup

def language_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
        types.InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    return markup

def payment_method_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🇮🇳 𝗨𝗣𝗜 (1$ = 100₹)", callback_data="pay_upi"),
        types.InlineKeyboardButton("🟡 𝗕𝗶𝗻𝗮𝗻𝗰𝗲 𝗣𝗮𝘆 / 𝗜𝗗", callback_data="pay_binance"),
        types.InlineKeyboardButton("🔶 𝗨𝗦𝗗𝗧 (𝗕𝗘𝗣𝟮𝟬)", callback_data="pay_bep20"),
        types.InlineKeyboardButton("🔴 𝗨𝗦𝗗𝗧 (𝗧𝗥𝗖𝟮𝟬)", callback_data="pay_trc20")
    )
    return markup

def payment_confirm_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ I have done the payment", callback_data="payment_done"),
        types.InlineKeyboardButton("❌ Cancel Deposit", callback_data="payment_cancel")
    )
    return markup

def products_menu(page=0):
    markup = types.InlineKeyboardMarkup(row_width=1)
    products = database.get_all_products()
    if not products:
        markup.add(types.InlineKeyboardButton("❌ No products available right now", callback_data="none"))
        return markup
    
    per_page = 10
    total_pages = (len(products) + per_page - 1) // per_page
    
    for p in products[page*per_page : (page+1)*per_page]:
        p_id, name, price, image_id, stock_count = p if len(p) == 5 else (*p, None)[:5]
        
        # Removes HTML tags, grabs only the first line, and truncates if it exceeds 35 chars
        clean_name = re.sub('<[^<]+>', '', str(name)).split('\n')[0].replace('*', '').strip()
        if len(clean_name) > 35:
            clean_name = clean_name[:32] + "..."
            
        btn_text = f"{clean_name} — ${float(price):.2f} ({stock_count} in stock)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{p_id}"))
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
        
    return markup

def quantity_menu(product_id, max_stock):
    markup = types.InlineKeyboardMarkup(row_width=3)
    quick_options = [1, 2, 3, 5, 10]
    valid_options = [q for q in quick_options if q <= max_stock]
    
    buttons = [types.InlineKeyboardButton(f"{q} pcs", callback_data=f"qty_{product_id}_{q}") for q in valid_options]
    if buttons:
        markup.add(*buttons)
    
    markup.add(
        types.InlineKeyboardButton("✏️ Custom Quantity", callback_data=f"customqty_{product_id}"),
        types.InlineKeyboardButton("🔙 Back to Catalog", callback_data="back_to_catalog")
    )
    return markup

def admin_approval_menu(user_id, amount):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_approve_{user_id}_{amount}")
    btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_{user_id}_{amount}")
    markup.add(btn_approve, btn_reject)
    return markup
    
