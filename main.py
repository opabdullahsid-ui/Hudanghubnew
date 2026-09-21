import html
import io
import re
import telebot
from telebot import types
import config
import database
import keyboards

user_deposit_states = {}

LANG_TEXTS = {
    'en': {
        'welcome': "🛍 *Welcome to ZerekDROPS!*\n────────────────────\nHello, {name}! We're glad to have you here.\n\nTake your time to browse our digital catalog. We offer instant, automated delivery directly to this chat so you never have to wait.\n\n🔹 *Explore:* Tap \"🛍️ Products\" to see what's in stock.\n🔹 *Account:* Track your history via \"🧾 Orders History\".\n🔹 *Support:* Have questions? Tap \"💬 Live Support\".\n\n*(Whenever you're ready to buy, you can seamlessly check out using your secure in-bot wallet!)*",
        'support': "💬 Need help with payments or missing items? Contact or call @Zerektos for support.",
        'profile': "👤 *User Profile*\n\nUser ID: `{chat_id}`\nUsername: @{username}\n💳 Wallet Balance: ${balance:.2f}",
        'products': "🛍 Available Products:",
        'add_funds': "🏦 *Wallet Top-Up*\n────────────────────\n⚡ Top up your balance for instant checkouts.\n🔒 Your balance is secure and never expires.\n\n👇 Select a payment method below to proceed:",
        'lang_changed': "✅ Language successfully changed to English!"
    },
    'vi': {
        'welcome': "🛍 *Chào mừng đến với ZerekDROPS!*\n────────────────────\nXin chào, {name}! Chúng tôi rất vui khi có bạn ở đây.\n\nHãy dành thời gian khám phá danh mục kỹ thuật số của chúng tôi. Chúng tôi cung cấp dịch vụ giao hàng tự động, ngay lập tức trực tiếp vào đoạn chat này để bạn không bao giờ phải chờ đợi.\n\n🔹 *Khám phá:* Bấm \"🛍️ Products\" để xem các sản phẩm hiện có.\n🔹 *Tài khoản:* Theo dõi lịch sử của bạn qua \"🧾 Orders History\".\n🔹 *Hỗ trợ:* Bạn có câu hỏi? Bấm \"💬 Live Support\".\n\n*(Bất cứ khi nào bạn sẵn sàng mua, bạn có thể thanh toán liền mạch bằng ví bảo mật trong bot của mình!)*",
        'support': "💬 Cần hỗ trợ thanh toán hoặc thiếu sản phẩm? Liên hệ @Zerektos để được trợ giúp.",
        'profile': "👤 *Hồ sơ người dùng*\n\nID: `{chat_id}`\nTên tài khoản: @{username}\n💳 Số dư ví: ${balance:.2f}",
        'products': "🛍 Sản phẩm có sẵn:",
        'add_funds': "Chọn phương thức thanh toán ưu tiên của bạn:",
        'lang_changed': "✅ Đã đổi ngôn ngữ sang Tiếng Việt thành công!"
    },
    'zh': {
        'welcome': "🛍 *欢迎来到 ZerekDROPS！*\n────────────────────\n你好，{name}！很高兴你能来。\n\n请慢慢浏览我们的数码产品目录。我们提供即时、自动的发货服务，直接发送到此聊天窗口，让你无需等待。\n\n🔹 *探索:* 点击 \"🛍️ Products\" 查看库存商品。\n🔹 *账户:* 通过 \"🧾 Orders History\" 追踪您的历史记录。\n🔹 *客服:* 有疑问吗？点击 \"💬 Live Support\"。\n\n*(当您准备好购买时，可以无缝使用安全的机器人内置钱包进行结账！)*",
        'support': "💬 需要支付或缺货帮助？请联系客服 @Zerektos。",
        'profile': "👤 *用户个人资料*\n\n用户 ID: `{chat_id}`\n用户名: @{username}\n💳 钱包余额: ${balance:.2f}",
        'products': "🛍 可用产品:",
        'add_funds': "请选择您偏好的支付方式:",
        'lang_changed': "✅ 语言已成功切换为中文！"
    },
    'ru': {
        'welcome': "🛍 *Добро пожаловать в ZerekDROPS!*\n────────────────────\nЗдравствуйте, {name}! Мы рады видеть вас здесь.\n\nНе торопитесь и изучите наш каталог цифровых товаров. Мы предлагаем мгновенную автоматическую доставку прямо в этот чат, так что вам никогда не придется ждать.\n\n🔹 *Каталог:* Нажмите \"🛍️ Products\", чтобы увидеть ассортимент.\n🔹 *Аккаунт:* Отслеживайте историю через \"🧾 Orders History\".\n🔹 *Поддержка:* Есть вопросы? Нажмите \"💬 Live Support\".\n\n*(Когда будете готовы к покупке, вы сможете легко оплатить её с помощью вашего безопасного встроенного кошелька!)*",
        'support': "💬 Нужна помощь с оплатой или товаром? Контакт для связи: @Zerektos.",
        'profile': "👤 *Профиль пользователя*\n\nID пользователя: `{chat_id}`\nИмя пользователя: @{username}\n💳 Баланс кошелька: ${balance:.2f}",
        'products': "🛍 Доступные товары:",
        'add_funds': "Выберите предпочитаемый способ оплаты:",
        'lang_changed': "✅ Язык успешно изменен на русский!"
    }
}

def is_admin_id(user_id):
    return str(user_id) in [str(x) for x in config.ADMIN_IDS]

def get_text(user_id, key, **kwargs):
    try:
        lang = database.get_language(user_id)
    except Exception:
        lang = 'en'
    if lang not in LANG_TEXTS:
        lang = 'en'
    text_template = LANG_TEXTS[lang].get(key, LANG_TEXTS['en'][key])
    return text_template.format(**kwargs)

def is_valid_image(image_id):
    if not image_id:
        return False
    if str(image_id).strip().lower() in ['none', 'null', '', '0']:
        return False
    return True

def process_deposit_amount(message, bot):
    chat_id = message.chat.id
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
        user_deposit_states[chat_id]['amount'] = amount
        method = user_deposit_states[chat_id]['method']
        
        if method == "UPI":
            inr_amount = int(amount * 100)
            deposit_msg = (
                "🇮🇳 *UPI Transfer Details*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Calculation:* Pay `{amount}` × 100 = *`{inr_amount} rs`* exactly.\n\n"
                "🏦 *UPI ID:* (Tap to copy)\n"
                "`helloyou@nyes`\n\n"
                "📌 *Next Steps:*\n"
                f"1. Pay exactly `{inr_amount} rs` to the UPI ID above.\n"
                "2. Wait for the transfer to complete.\n"
                "3. Tap *✅ I have done the payment* below and share your 12-digit UTR/Transaction ID."
            )
        elif method == "Binance":
            deposit_msg = (
                "🟡 *Payment Details: Binance Pay / ID*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Amount to Send:* `{amount} USDT`\n\n"
                "🏦 *Binance ID:* (Tap to copy)\n"
                "`1258402142`\n\n"
                "📌 *Next Steps:*\n"
                f"1. Send exactly `{amount} USDT` to the Binance ID above.\n"
                "2. Tap *✅ I have done the payment* below and share your Order ID or Screenshot."
            )
        elif method == "BEP20 Address":
            deposit_msg = (
                "🧾 *Payment Details: USDT (BEP20)*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Amount to Send:* `{amount} USDT`\n"
                "🌐 *Network:* `BNB Smart Chain (BEP20)`\n\n"
                "🏦 *Wallet Address:* (Tap to copy)\n"
                "`0x8896b47e05b9b59de157f1fe4c2359c184efe4fa`\n\n"
                "📌 *Next Steps:*\n"
                f"1. Send exactly `{amount} USDT` to the address above.\n"
                "2. Tap *✅ I have done the payment* below and share your Transaction Hash (TxID)."
            )
        else:
            deposit_msg = (
                "🧾 *Payment Details: USDT (TRC20)*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 *Amount to Send:* `{amount} USDT`\n"
                "🌐 *Network:* `TRON (TRC20)`\n\n"
                "🏦 *Wallet Address:* (Tap to copy)\n"
                "`TALGMuRLMoP3koxhTz8JmHfQ5LUYX8L2VR`\n\n"
                "📌 *Next Steps:*\n"
                f"1. Send exactly `{amount} USDT` to the address above.\n"
                "2. Tap *✅ I have done the payment* below and share your Transaction Hash (TxID)."
            )
            
        bot.send_message(chat_id, deposit_msg, parse_mode="Markdown", reply_markup=keyboards.payment_confirm_menu())
    except (ValueError, TypeError):
        bot.send_message(chat_id, "❌ Invalid amount. Please try adding funds again.")

def process_order_id(message, bot):
    chat_id = message.chat.id
    order_id = message.text.strip()
    data = user_deposit_states.get(chat_id, {})
    amount = data.get('amount', 0.0)
    method = data.get('method', 'Crypto')
    username = message.from_user.username or message.from_user.first_name

    bot.send_message(chat_id, "⏳ Payment details received. Sent to Admin for verification.")
    
    admin_text = (
        f"🚨 *New Payment Verification!*\n\n"
        f"👤 User: @{username}\n"
        f"🆔 User ID: `{chat_id}`\n"
        f"💳 Method: *{method}*\n"
        f"💰 Amount: *${amount}*\n"
        f"🧾 Reference / TxID: `{order_id}`"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            bot.send_message(admin_id, admin_text, parse_mode="Markdown", reply_markup=keyboards.admin_approval_menu(chat_id, amount))
        except Exception:
            pass

def execute_purchase(bot, chat_id, product_id, quantity):
    try:
        product = database.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "❌ Product not found.")
            return

        prod_id, prod_name = product[0], product[1]
        price = float(product[2])
        image_id = product[3] if len(product) > 3 else None
        stock_data = product[4] if len(product) > 4 else ""

        lines = [l.strip() for l in str(stock_data).split('\n') if l.strip() and str(l).lower() != 'none']
        stock_count = len(lines)

        if stock_count < quantity:
            bot.send_message(chat_id, f"❌ Not enough stock available! Remaining: *{stock_count} pcs*.", parse_mode="Markdown")
            return

        total_cost = price * quantity
        balance = float(database.get_balance(chat_id))

        if balance < total_cost:
            bot.send_message(
                chat_id,
                f"❌ *Insufficient Balance!*\n\n"
                f"• Total Required: *${total_cost:.2f}*\n"
                f"• Your Balance: *${balance:.2f}*\n\n"
                f"Please top up your wallet using *💎 Top-up Wallet*.",
                parse_mode="Markdown"
            )
            return

        database.update_balance(chat_id, -total_cost)
        items_delivered = database.consume_stock_items(prod_id, quantity, bot)
        
        numbered_items = [f"{idx}. {item}" for idx, item in enumerate(items_delivered, 1)]
        items_text_content = "\n".join(numbered_items)
        
        # Safe string conversion for DB and file names
        plain_name = re.sub('<[^<]+>', '', prod_name)
        short_title = plain_name.split('\n')[0].replace('*', '').strip()
        order_name_record = f"{short_title} (x{quantity})"
        database.add_order(chat_id, order_name_record, total_cost, items_text_content)

        remaining_bal = float(database.get_balance(chat_id))

        safe_filename = "".join(c for c in short_title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        if not safe_filename:
            safe_filename = "Product"
            
        file_buffer = io.BytesIO(items_text_content.encode('utf-8'))
        file_buffer.name = f"{safe_filename}_x{quantity}.txt"

        receipt_caption = (
            f"🎉 <b>Purchase Successful!</b>\n"
            f"────────────────────\n"
            f"🧾 <b>Order Summary</b>\n"
            f"• <b>Product:</b> {html.escape(short_title)}\n"
            f"• <b>Quantity:</b> {quantity} pcs\n"
            f"• <b>Unit Price:</b> ${price:.2f}\n"
            f"• <b>Total Deducted:</b> ${total_cost:.2f}\n"
            f"• <b>Payment Method:</b> 💳 Wallet Balance\n"
            f"• <b>Remaining Balance:</b> ${remaining_bal:.2f}\n"
            f"────────────────────\n"
            f"📎 <i>Your purchased items have been neatly numbered and attached in the text file below!</i>"
        )
        
        bot.send_document(chat_id, file_buffer, caption=receipt_caption, parse_mode="HTML")
    except Exception as e:
        bot.send_message(chat_id, f"🎉 Purchase Processed, but there was an error delivering the text file. Check Orders History or contact Support.\n\nError code: {e}")

def process_custom_quantity(message, bot, product_id):
    chat_id = message.chat.id
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError()
        execute_purchase(bot, chat_id, product_id, qty)
    except (ValueError, TypeError):
        bot.send_message(chat_id, "❌ Invalid quantity. Please select a product again from the catalog.")

def register_user_handlers(bot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        if database.get_maintenance_mode() and not is_admin_id(chat_id):
            bot.send_message(chat_id, "🛠 *Store Under Maintenance*\n\nWe are currently restocking and updating our systems. Please check back soon!", parse_mode="Markdown")
            return

        name = message.from_user.first_name or "User"
        username = message.from_user.username or "None"
        database.add_user(chat_id, username, name)
        
        bot.send_message(chat_id, "🌐 Select your preferred language / Chọn ngôn ngữ / 选择语言 / Выберите язык:", reply_markup=keyboards.language_menu())

    @bot.message_handler(func=lambda message: message.text in ["🚀 Start Hub", "🛍️ Products", "💎 Top-up Wallet", "👤 My Profile", "🧾 Orders History", "🌐 Change Language", "💬 Live Support"])
    def handle_reply_menu(message):
        chat_id = message.chat.id
        if database.get_maintenance_mode() and not is_admin_id(chat_id):
            bot.send_message(chat_id, "🛠 *Store Under Maintenance*\n\nWe are currently restocking. Please check back shortly!", parse_mode="Markdown")
            return

        text = message.text
        if text == "🚀 Start Hub":
            name = message.from_user.first_name or "User"
            welcome_text = get_text(chat_id, 'welcome', name=name)
            bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=keyboards.main_reply_menu())
        elif text == "💬 Live Support":
            bot.send_message(chat_id, get_text(chat_id, 'support'))
        elif text == "🌐 Change Language":
            bot.send_message(chat_id, "🌐 Select your preferred language / Chọn ngôn ngữ / 选择语言 / Выберите язык:", reply_markup=keyboards.language_menu())
        elif text == "👤 My Profile":
            username = message.from_user.username or message.from_user.first_name
            balance = float(database.get_balance(chat_id))
            profile_text = get_text(chat_id, 'profile', chat_id=chat_id, username=username, balance=balance)
            bot.send_message(chat_id, profile_text, parse_mode="Markdown")
        elif text == "🧾 Orders History":
            orders = database.get_user_orders(chat_id)
            if not orders:
                bot.send_message(chat_id, "🧾 *Your Purchase History*\n\nYou haven't made any purchases yet.", parse_mode="Markdown")
            else:
                history_html = "🧾 <b>Your Last Purchases:</b>\n\n"
                for idx, ord_item in enumerate(orders, 1):
                    p_name, p_price, item_data, p_date = ord_item
                    
                    plain_p_name = re.sub('<[^<]+>', '', p_name)
                    lines = item_data.split('\n')
                    if len(lines) > 5:
                        display_data = '\n'.join(lines[:5]) + f"\n... (+{len(lines)-5} more items in downloaded file)"
                    else:
                        display_data = item_data
                        
                    history_html += f"{idx}. <b>{html.escape(plain_p_name)}</b> — ${float(p_price):.2f}\n<pre>{html.escape(display_data)}</pre>\n<i>Date: {p_date}</i>\n\n"
                
                try:
                    bot.send_message(chat_id, history_html, parse_mode="HTML")
                except Exception:
                    bot.send_message(chat_id, "❌ Error loading history formatting. Try again.")
        elif text == "💎 Top-up Wallet":
            bot.send_message(chat_id, get_text(chat_id, 'add_funds'), reply_markup=keyboards.payment_method_menu(), parse_mode="Markdown")
        elif text == "🛍️ Products":
            bot.send_message(chat_id, get_text(chat_id, 'products'), reply_markup=keyboards.products_menu(0))

    @bot.callback_query_handler(func=lambda call: call.data and not (call.data.startswith("adm_") or call.data.startswith("approve_") or call.data.startswith("reject_")))
    def handle_callbacks(call):
        chat_id = call.message.chat.id
        data = call.data

        if database.get_maintenance_mode() and not is_admin_id(chat_id):
            try: bot.answer_callback_query(call.id, "🛠 Store is currently under maintenance.", show_alert=True)
            except: pass
            return

        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            try:
                database.set_language(chat_id, lang_code)
            except Exception:
                pass 
            try:
                bot.answer_callback_query(call.id, "Language Updated!")
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            name = call.from_user.first_name or "User"
            welcome_text = get_text(chat_id, 'welcome', name=name)
            bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=keyboards.main_reply_menu())

        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            try:
                bot.answer_callback_query(call.id)
                bot.edit_message_text(get_text(chat_id, 'products'), chat_id, call.message.message_id, reply_markup=keyboards.products_menu(page))
            except Exception:
                pass

        elif data == "back_to_catalog":
            try:
                bot.answer_callback_query(call.id)
                bot.edit_message_text(get_text(chat_id, 'products'), chat_id, call.message.message_id, reply_markup=keyboards.products_menu(0))
            except Exception:
                pass

        elif data == "pay_upi":
            try: bot.answer_callback_query(call.id)
            except: pass
            user_deposit_states[chat_id] = {"method": "UPI"}
            msg = bot.send_message(
                chat_id, 
                "🇮🇳 *UPI Payment Selected*\n\n"
                "⚠️ *Notice: 100rs = 1$*\n\n"
                "Enter the amount you want to deposit in USD ($) (e.g. `1.5` or `5`):", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_deposit_amount, bot)

        elif data == "pay_binance":
            try: bot.answer_callback_query(call.id)
            except: pass
            user_deposit_states[chat_id] = {"method": "Binance"}
            msg = bot.send_message(chat_id, "Enter the EXACT amount you want to deposit in USD ($) (e.g., `5`):")
            bot.register_next_step_handler(msg, process_deposit_amount, bot)

        elif data == "pay_bep20":
            try: bot.answer_callback_query(call.id)
            except: pass
            user_deposit_states[chat_id] = {"method": "BEP20 Address"}
            msg = bot.send_message(chat_id, "Enter the EXACT amount you want to deposit in your wallet (e.g., `10`):")
            bot.register_next_step_handler(msg, process_deposit_amount, bot)

        elif data == "pay_trc20":
            try: bot.answer_callback_query(call.id)
            except: pass
            user_deposit_states[chat_id] = {"method": "TRC20 Address"}
            msg = bot.send_message(chat_id, "Enter the EXACT amount you want to deposit in your wallet (e.g., `10`):")
            bot.register_next_step_handler(msg, process_deposit_amount, bot)

        elif data == "payment_cancel":
            user_deposit_states.pop(chat_id, None)
            try:
                bot.answer_callback_query(call.id, "Cancelled")
                bot.edit_message_text("❌ Deposit cancelled.", chat_id, call.message.message_id)
            except Exception:
                pass

        elif data == "payment_done":
            try: bot.answer_callback_query(call.id)
            except: pass
            msg = bot.send_message(chat_id, "Please enter your Order ID, TxID, or UPI UTR to verify your payment:")
            bot.register_next_step_handler(msg, process_order_id, bot)

        elif data.startswith("buy_"):
            try: bot.answer_callback_query(call.id)
            except: pass
                
            try:
                product_id = int(data.split("_")[1])
                product = database.get_product(product_id)
                
                if not product:
                    bot.send_message(chat_id, "❌ Product not found in database.")
                    return
                
                prod_id, name = product[0], product[1]
                price = float(product[2])
                image_id = product[3] if len(product) > 3 else None
                stock_data = product[4] if len(product) > 4 else ""

                lines = [l.strip() for l in str(stock_data).split('\n') if l.strip() and str(l).lower() != 'none']
                stock_count = len(lines)
                
                if stock_count <= 0:
                    bot.send_message(chat_id, "❌ Out of stock!")
                    return
                
                try: bot.delete_message(chat_id, call.message.message_id)
                except: pass

                # Retains the full description text and formatting exactly as the admin entered it
                prompt_text = (
                    f"{name}\n\n"
                    f"────────────────────\n"
                    f"💰 <b>Unit Price:</b> ${price:.2f}\n"
                    f"📦 <b>Available Stock:</b> {stock_count} pcs\n\n"
                    f"👉 Select how many you want to buy:"
                )
                
                menu = keyboards.quantity_menu(prod_id, stock_count)

                if is_valid_image(image_id):
                    if len(prompt_text) <= 1024:
                        try:
                            bot.send_photo(chat_id, image_id, caption=prompt_text, reply_markup=menu, parse_mode="HTML")
                        except Exception:
                            bot.send_photo(chat_id, image_id, caption=prompt_text, reply_markup=menu)
                    else:
                        bot.send_photo(chat_id, image_id)
                        try:
                            bot.send_message(chat_id, prompt_text, reply_markup=menu, parse_mode="HTML")
                        except Exception:
                            bot.send_message(chat_id, prompt_text, reply_markup=menu)
                else:
                    try:
                        bot.send_message(chat_id, prompt_text, reply_markup=menu, parse_mode="HTML")
                    except Exception:
                        bot.send_message(chat_id, prompt_text, reply_markup=menu)

            except Exception as e:
                bot.send_message(chat_id, f"⚠️ Error loading product. Please try again. System diagnostic: {e}")

        elif data.startswith("qty_"):
            try: bot.answer_callback_query(call.id)
            except: pass
                
            parts = data.split("_")
            prod_id = int(parts[1])
            qty = int(parts[2])
            execute_purchase(bot, chat_id, prod_id, qty)

        elif data.startswith("customqty_"):
            try: bot.answer_callback_query(call.id)
            except: pass
                
            prod_id = int(data.split("_")[1])
            product = database.get_product(prod_id)
            
            if not product:
                bot.send_message(chat_id, "❌ Product not found.")
                return
            
            _, name = product[0], product[1]
            stock_data = product[4] if len(product) > 4 else ""
            lines = [l.strip() for l in str(stock_data).split('\n') if l.strip() and str(l).lower() != 'none']
            stock_count = len(lines)

            if stock_count <= 0:
                bot.send_message(chat_id, "❌ Out of stock!")
                return

            plain_name = re.sub('<[^<]+>', '', name)
            short_title = plain_name.split('\n')[0].replace('*', '').strip()
            msg = bot.send_message(chat_id, f"Enter custom quantity for *{short_title}* (Max: {stock_count}):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, lambda m: process_custom_quantity(m, bot, prod_id))
                
