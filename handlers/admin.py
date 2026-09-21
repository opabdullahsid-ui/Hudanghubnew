import telebot
from telebot import types
import config
import database
import io
import os
import datetime
import html
import sqlite3
import re

admin_states = {}

def is_admin(user_id):
    return str(user_id) in [str(x) for x in config.ADMIN_IDS]

def register_admin_handlers(bot):
    @bot.message_handler(commands=['admin', 'panel'])
    def cmd_admin(message):
        if is_admin(message.from_user.id):
            admin_text = (
                "👑 *ZerekDROPS Admin Control Panel*\n"
                "────────────────────\n"
                "📦 *Inventory Management*\n"
                "• `/addproduct` — Add a new product\n"
                "• `/restock` — Add stock lines to an existing product\n"
                "• `/changeprice` — Update a product's price\n"
                "• `/deleteproduct` — Permanently delete a product\n\n"
                "👥 *User & Wallet Control*\n"
                "• `/users` — Download a .txt file of all users\n"
                "• `/stats` — View live sales and revenue\n"
                "• `/checkbalance USER_ID` — Inspect a user's wallet\n"
                "• `/addbalance USER_ID AMOUNT` — Credit/debit a user's balance\n\n"
                "📢 *Broadcasting & Support*\n"
                "• `/message USER_ID TEXT` — Send a direct PM to a user\n"
                "• `/announcement TEXT` — Broadcast a message to all users\n\n"
                "⚙️ *System & Maintenance*\n"
                "• `/maintenance on` — Lock store for non-admins\n"
                "• `/maintenance off` — Unlock store for everyone\n"
                "• `/maintenance` — Check current store status\n"
                "• `/backup` — Download the live SQLite database file\n"
                "────────────────────"
            )
            bot.send_message(message.chat.id, admin_text, parse_mode="Markdown")

    @bot.message_handler(commands=['stats', 'revenue'])
    def cmd_stats(message):
        if is_admin(message.from_user.id):
            t_orders, t_rev, d_orders, d_rev = database.get_store_stats()
            stats_text = (
                "📊 *Store Revenue Dashboard*\n"
                "────────────────────\n"
                f"📅 *Today's Activity*\n"
                f"• Orders: `{d_orders}`\n"
                f"• Revenue: `${d_rev:.2f}`\n\n"
                f"🌎 *All-Time Activity*\n"
                f"• Total Orders: `{t_orders}`\n"
                f"• Total Revenue: `${t_rev:.2f}`\n"
                "────────────────────"
            )
            bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")

    @bot.message_handler(commands=['backup'])
    def cmd_backup(message):
        if is_admin(message.from_user.id):
            db_path = 'store.db'
            if not os.path.exists(db_path):
                bot.send_message(message.chat.id, "❌ Database file `store.db` was not found.", parse_mode="Markdown")
                return
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(db_path, 'rb') as doc:
                    bot.send_document(
                        message.chat.id,
                        doc,
                        caption=f"📦 *Database Snapshot*\n📅 Timestamp: `{timestamp}`\n💾 File: `store.db`",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Error sending backup: {e}")

    @bot.message_handler(commands=['users'])
    def cmd_users(message):
        if is_admin(message.from_user.id):
            users = database.get_all_users_detailed()
            if not users:
                bot.send_message(message.chat.id, "👥 *User Base:* No users registered yet.", parse_mode="Markdown")
                return
            
            file_content = f"Hudang Hub - Total Registered Users: {len(users)}\n"
            file_content += "=" * 45 + "\n\n"
            
            for idx, u in enumerate(users, start=1):
                u_id, u_username, u_name, u_balance, u_purchases = u
                clean_name = str(u_name or "Unknown").replace("_", "").replace("*", "").replace("`", "").replace("[", "")
                clean_uname = str(u_username).replace("_", "").replace("*", "").replace("`", "") if u_username else "No username"
                uname_str = f"@{clean_uname}" if u_username else clean_uname
                
                file_content += f"{idx}. Name: {clean_name} ({uname_str})\n   ID: {u_id} | Wallet: ${u_balance:.2f} | Orders: {u_purchases}\n"
                file_content += "-" * 45 + "\n"
            
            try:
                file_buffer = io.BytesIO(file_content.encode('utf-8'))
                file_buffer.name = "HudangHub_Users.txt"
                bot.send_document(
                    message.chat.id, 
                    file_buffer, 
                    caption=f"👥 *Hudang Hub User Database*\nTotal Registered: `{len(users)}`", 
                    parse_mode="Markdown"
                )
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Failed to send user list file: {e}")

    @bot.message_handler(commands=['checkbalance'])
    def cmd_checkbalance(message):
        if is_admin(message.from_user.id):
            parts = message.text.split()
            if len(parts) == 2:
                try:
                    target_id = int(parts[1])
                    user = database.get_user_details(target_id)
                    if user:
                        u_id, u_username, u_name, u_balance = user
                        name_str = u_name or "Unknown"
                        uname = f"@{u_username}" if u_username else "No username"
                        bot.send_message(message.chat.id, f"👤 *User Details:*\n\nName: {name_str} ({uname})\nID: `{u_id}`\nWallet Balance: `${float(u_balance):.2f}`", parse_mode="Markdown")
                    else:
                        bot.send_message(message.chat.id, "❌ User not found in database.")
                except ValueError:
                    bot.send_message(message.chat.id, "❌ Invalid User ID format.")
            else:
                bot.send_message(message.chat.id, "❌ Usage: `/checkbalance USER_ID`", parse_mode="Markdown")

    @bot.message_handler(commands=['addbalance'])
    def cmd_addbalance(message):
        if is_admin(message.from_user.id):
            parts = message.text.split()
            if len(parts) == 3:
                try:
                    target_id = int(parts[1])
                    amount = float(parts[2])
                    database.update_balance(target_id, amount)
                    new_bal = float(database.get_balance(target_id))
                    bot.send_message(message.chat.id, f"✅ Successfully added `${amount:.2f}` to user `{target_id}`.\nNew Balance: `${new_bal:.2f}`", parse_mode="Markdown")
                    try:
                        bot.send_message(target_id, f"🎉 *Wallet Updated!*\nAn admin credited `${amount:.2f}` to your account.\nCurrent Balance: `${new_bal:.2f}`", parse_mode="Markdown")
                    except Exception:
                        pass
                except ValueError:
                    bot.send_message(message.chat.id, "❌ Invalid format. Use: `/addbalance USER_ID AMOUNT`", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Usage: `/addbalance USER_ID AMOUNT`", parse_mode="Markdown")

    @bot.message_handler(commands=['message'])
    def cmd_message(message):
        if is_admin(message.from_user.id):
            parts = message.text.split(maxsplit=2)
            if len(parts) >= 3:
                try:
                    target_id = int(parts[1])
                    text_to_send = parts[2]
                    bot.send_message(target_id, f"💬 *Message from Store Admin:*\n\n{text_to_send}", parse_mode="Markdown")
                    bot.send_message(message.chat.id, f"✅ Message successfully sent to user `{target_id}`.", parse_mode="Markdown")
                except ValueError:
                    bot.send_message(message.chat.id, "❌ Invalid User ID format.")
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Failed to send message: {e}")
            else:
                bot.send_message(message.chat.id, "❌ Usage: `/message USER_ID YOUR_TEXT`", parse_mode="Markdown")

    @bot.message_handler(commands=['announcement'])
    def cmd_announcement(message):
        if is_admin(message.from_user.id):
            parts = message.text.split(maxsplit=1)
            if len(parts) >= 2:
                announcement_text = parts[1]
                users = database.get_all_users()
                success_count = 0
                fail_count = 0
                for u in users:
                    u_id = u[0]
                    try:
                        bot.send_message(u_id, f"📢 *Announcement:*\n\n{announcement_text}", parse_mode="Markdown")
                        success_count += 1
                    except Exception:
                        fail_count += 1
                bot.send_message(message.chat.id, f"📢 *Broadcast Complete!*\n\n✅ Delivered: {success_count}\n❌ Failed: {fail_count}", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Usage: `/announcement YOUR_MESSAGE`", parse_mode="Markdown")

    @bot.message_handler(commands=['addproduct'])
    def cmd_addproduct(message):
        if is_admin(message.from_user.id):
            try:
                msg = bot.send_message(
                    message.chat.id, 
                    "📦 *Add Product*\n\n1️⃣ Send the *Short Title* for this product:\n_(This will be the small text shown on the inline buttons. Example: 'Nord VPN $3')_", 
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(msg, addproduct_shortname_step)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Error: {e}")

    def addproduct_shortname_step(message):
        short_name = message.text
        if not short_name:
            bot.send_message(message.chat.id, "❌ Short title must be text. Please try `/addproduct` again.")
            return
            
        admin_states[message.chat.id] = {'short_name': short_name.strip()}
        msg = bot.send_message(
            message.chat.id, 
            f"✅ Title saved!\n\n📝 2️⃣ Now, send the *Full Product Description*:\n_(Highlight your text and use Telegram's menu to add Bold, Italic, or Quotes!)_", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, addproduct_desc_step)

    def addproduct_desc_step(message):
        desc = getattr(message, 'html_text', None) or getattr(message, 'html_caption', None) or message.text or message.caption
        if not desc:
            bot.send_message(message.chat.id, "❌ Description must be text. Please try `/addproduct` again.")
            return
            
        short_name = admin_states[message.chat.id]['short_name']
        full_name = f"<b>{html.escape(short_name)}</b>\n{desc}"
        
        admin_states[message.chat.id]['name'] = full_name
        admin_states[message.chat.id]['image_id'] = None
        admin_states[message.chat.id]['price'] = 0
        admin_states[message.chat.id]['broadcast'] = None
        
        msg = bot.send_message(
            message.chat.id, 
            f"✅ Description saved!\n\n🖼️ 3️⃣ Now, send an *Image* for this product.\n*(If you don't want an image, just type `/skip`)*", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, addproduct_image_step)

    def addproduct_image_step(message):
        if message.photo:
            file_id = message.photo[-1].file_id
            admin_states[message.chat.id]['image_id'] = file_id
            msg = bot.send_message(message.chat.id, "✅ Image saved!\n\n💰 4️⃣ Send the *Price* (e.g. 14.99):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, addproduct_price_step)
        elif message.text and message.text.strip().lower() == '/skip':
            msg = bot.send_message(message.chat.id, "⏭️ Image skipped.\n\n💰 4️⃣ Send the *Price* (e.g. 14.99):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, addproduct_price_step)
        else:
            msg = bot.send_message(message.chat.id, "❌ Please send a valid photo, or type `/skip` to proceed without one:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, addproduct_image_step)
        
    def addproduct_price_step(message):
        try:
            p_price = float(message.text)
            admin_states[message.chat.id]['price'] = p_price
            msg = bot.send_message(
                message.chat.id, 
                "✅ Price set!\n\n📢 5️⃣ Send the *Custom Notification Message* that users will see when this drops.\n*(Or type `/skip` to use the standard default message)*", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, addproduct_broadcast_step)
        except (ValueError, TypeError):
            msg = bot.send_message(message.chat.id, "❌ Invalid price. Please enter a valid number (e.g., 14.99):")
            bot.register_next_step_handler(msg, addproduct_price_step)

    def addproduct_broadcast_step(message):
        if message.text and message.text.strip().lower() == '/skip':
            admin_states[message.chat.id]['broadcast'] = None
        else:
            admin_states[message.chat.id]['broadcast'] = getattr(message, 'html_text', None) or getattr(message, 'html_caption', None) or message.text or message.caption

        msg = bot.send_message(message.chat.id, "✅ Message saved!\n\n📦 6️⃣ Send the *Stock items*:\n*(Paste text lines OR upload a `.txt` file)*:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, addproduct_stock_step)

    def addproduct_stock_step(message):
        if message.chat.id not in admin_states:
            return
        
        stock_content = ""
        if message.document:
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded = bot.download_file(file_info.file_path)
                stock_content = downloaded.decode('utf-8', errors='ignore')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Error reading file: {e}")
                return
        elif message.text:
            stock_content = message.text
        else:
            msg = bot.send_message(message.chat.id, "❌ Please send text lines or upload a `.txt` file:")
            bot.register_next_step_handler(msg, addproduct_stock_step)
            return
        
        p_name = admin_states[message.chat.id]['name']
        p_price = float(admin_states[message.chat.id]['price'])
        image_id = admin_states[message.chat.id]['image_id']
        broadcast_custom = admin_states[message.chat.id].get('broadcast')
        
        prod_id = database.add_product(p_name, p_price, stock_content, image_id)
        
        lines = [l.strip() for l in stock_content.split('\n') if l.strip()]
        added_count = len(lines)
        
        bot.send_message(message.chat.id, f"🎉 *Success!* Product added with *{added_count}* item(s) in stock!", parse_mode="Markdown")
        
        plain_name = re.sub('<[^<]+>', '', p_name)
        short_title = plain_name.split('\n')[0].strip().replace('*', '')

        if broadcast_custom:
            broadcast_text = (
                f"🔥 <b>New Product Alert!</b>\n\n"
                f"{broadcast_custom}\n\n"
                f"📦 <b>{short_title}</b>\n"
                f"🏷 <b>Price:</b> ${p_price:.2f}"
            )
        else:
            broadcast_text = (
                f"🔥 <b>New stock available!</b>\n"
                f"────────────────────\n"
                f"📦 <b>{short_title}</b>\n"
                f"➕ <b>Added:</b> {added_count}\n"
                f"📊 <b>Current stock:</b> {added_count}\n"
                f"🏷 <b>Price:</b> ${p_price:.2f}"
            )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Buy now", callback_data=f"buy_{prod_id}"))
        
        users = database.get_all_users()
        for u in users:
            try:
                bot.send_message(u[0], broadcast_text, reply_markup=markup, parse_mode="HTML")
            except Exception:
                pass

        admin_states.pop(message.chat.id, None)

    @bot.message_handler(commands=['changeprice'])
    def cmd_changeprice(message):
        if is_admin(message.from_user.id):
            products = database.get_all_products()
            if not products:
                bot.send_message(message.chat.id, "❌ Store is currently empty.")
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for p in products:
                p_id, name, price, image, stock_count = p if len(p) == 5 else (*p, None)[:5]
                plain_name = re.sub('<[^<]+>', '', name)
                short_name = plain_name.split('\n')[0].replace('*', '')
                if len(short_name) > 35: short_name = short_name[:32] + "..."
                markup.add(types.InlineKeyboardButton(f"💲 {short_name} — ${float(price):.2f}", callback_data=f"adm_chgprice_{p_id}"))

            bot.send_message(message.chat.id, "💰 *Select a product to change its price:*", reply_markup=markup, parse_mode="Markdown")

    def changeprice_step(message, prod_id, prod_name, old_price):
        try:
            new_price = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Invalid price format. Operation cancelled.")
            return

        if new_price == old_price:
            bot.send_message(message.chat.id, "⚠️ The new price is the same as the old price. No changes made.")
            return

        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, prod_id))
        conn.commit()
        conn.close()

        plain_name = re.sub('<[^<]+>', '', prod_name)
        short_title = html.escape(plain_name.split('\n')[0].replace('*', ''))

        if new_price < old_price:
            broadcast_text = (
                f"❤️‍🔥 <b>NEW Price Drop Alert</b> 🚨\n\n"
                f"📦 <b>{short_title}</b>\n\n"
                f"☑️ Old Price : <s>${old_price:.2f}</s>\n"
                f"✅ New Price : ${new_price:.2f}\n\n"
                f"Buy Easily From Our BOT 🤝 /Start"
            )
        else:
            broadcast_text = (
                f"📈 <b>Price Change Alert</b> ⚠️\n\n"
                f"📦 <b>{short_title}</b>\n\n"
                f"☑️ Old Price : <s>${old_price:.2f}</s>\n"
                f"✅ New Price : ${new_price:.2f}\n\n"
                f"Buy Easily From Our BOT 🤝 /Start"
            )

        users = database.get_all_users()
        success = 0
        for u in users:
            try:
                bot.send_message(u[0], broadcast_text, parse_mode="HTML")
                success += 1
            except Exception:
                pass

        bot.send_message(message.chat.id, f"✅ Price successfully updated to ${new_price:.2f} and broadcasted to {success} users!")

    @bot.message_handler(commands=['restock'])
    def cmd_restock(message):
        if is_admin(message.from_user.id):
            products = database.get_all_products()
            if not products:
                bot.send_message(message.chat.id, "❌ No products found in the store to restock.")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p in products:
                p_id, name, price, image, stock_count = p if len(p) == 5 else (*p, None)[:5]
                plain_name = re.sub('<[^<]+>', '', name)
                short_name = plain_name.split('\n')[0].replace('*', '')
                if len(short_name) > 35: short_name = short_name[:32] + "..."
                markup.add(types.InlineKeyboardButton(f"📦 {short_name} — {stock_count} in stock", callback_data=f"adm_restock_{p_id}"))
            
            bot.send_message(message.chat.id, "📦 *Select a product to restock:*", reply_markup=markup, parse_mode="Markdown")

    def restock_stock_step(message, prod_id, prod_name, prod_price):
        stock_content = ""
        if message.document:
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded = bot.download_file(file_info.file_path)
                stock_content = downloaded.decode('utf-8', errors='ignore')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Error reading file: {e}")
                return
        elif message.text:
            stock_content = message.text
        else:
            msg = bot.send_message(message.chat.id, "❌ Please send text lines or upload a `.txt` file:")
            bot.register_next_step_handler(msg, lambda m: restock_stock_step(m, prod_id, prod_name, prod_price))
            return
        
        added_count, total_count = database.append_stock(prod_id, stock_content)
        bot.send_message(
            message.chat.id,
            f"✅ *Restocked Successfully!*\nAdded: *+{added_count}* items\nNew Total Stock: *{total_count}* items",
            parse_mode="Markdown"
        )
        
        plain_name = re.sub('<[^<]+>', '', prod_name)
        short_title = plain_name.split('\n')[0].replace('*', '')
        broadcast_text = (
            f"🔥 <b>New stock available!</b>\n"
            f"────────────────────\n"
            f"📦 <b>{short_title}</b>\n"
            f"➕ <b>Added:</b> {added_count}\n"
            f"📊 <b>Current stock:</b> {total_count}\n"
            f"🏷 <b>Price:</b> ${prod_price:.2f}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Buy now", callback_data=f"buy_{prod_id}"))
        
        users = database.get_all_users()
        for u in users:
            try:
                bot.send_message(u[0], broadcast_text, reply_markup=markup, parse_mode="HTML")
            except Exception:
                pass

    @bot.message_handler(commands=['deleteproduct'])
    def cmd_deleteproduct(message):
        if is_admin(message.from_user.id):
            products = database.get_all_products()
            if not products:
                bot.send_message(message.chat.id, "❌ Store is currently empty.")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p in products:
                p_id, name, price, image, stock_count = p if len(p) == 5 else (*p, None)[:5]
                plain_name = re.sub('<[^<]+>', '', name)
                short_name = plain_name.split('\n')[0].replace('*', '')
                if len(short_name) > 35: short_name = short_name[:32] + "..."
                markup.add(types.InlineKeyboardButton(f"🗑️ Delete {short_name} (${float(price):.2f})", callback_data=f"adm_delprod_{p_id}"))
            
            bot.send_message(message.chat.id, "⚠️ *Select a product to permanently delete:*\n*(Warning: This cannot be undone)*", reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(commands=['maintenance', 'maintanence', 'maintainence'])
    def cmd_maintenance(message):
        if is_admin(message.from_user.id):
            parts = message.text.split()
            if len(parts) == 2:
                status_arg = parts[1].lower()
                if status_arg in ['on', 'true', '1', 'enable']:
                    database.set_maintenance_mode(True)
                    bot.send_message(message.chat.id, "🛠 *Maintenance Mode Enabled.* Regular users are locked out.", parse_mode="Markdown")
                elif status_arg in ['off', 'false', '0', 'disable']:
                    database.set_maintenance_mode(False)
                    bot.send_message(message.chat.id, "✅ *Maintenance Mode Disabled.* Store is fully open.", parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, "❌ Usage: `/maintenance on` or `/maintenance off`", parse_mode="Markdown")
            else:
                current_status = database.get_maintenance_mode()
                status_text = "Enabled 🛠" if current_status else "Disabled ✅"
                bot.send_message(message.chat.id, f"ℹ️ Maintenance Status: *{status_text}*\nUsage: `/maintenance on` or `/maintenance off`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("adm_") or call.data.startswith("approve_") or call.data.startswith("reject_")))
    def handle_admin_callbacks(call):
        if not is_admin(call.from_user.id):
            try: bot.answer_callback_query(call.id, "❌ Unauthorized.", show_alert=True)
            except: pass
            return

        try: bot.answer_callback_query(call.id)
        except: pass

        data = call.data
        chat_id = call.message.chat.id

        if data.startswith("adm_chgprice_"):
            prod_id = int(data.split("_")[2])
            product = database.get_product(prod_id)
            if not product:
                bot.send_message(chat_id, "❌ Product not found.")
                return
            p_id, p_name = product[0], product[1]
            p_price = float(product[2])
            plain_name = re.sub('<[^<]+>', '', p_name)
            short_name = plain_name.split('\n')[0].replace('*', '')

            msg = bot.send_message(chat_id, f"💰 *Change Price for:*\n{short_name}\n\n*Current Price:* `${p_price:.2f}`\n\nEnter the new price (e.g. `12.50`):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, lambda m: changeprice_step(m, p_id, p_name, p_price))
            return

        if data.startswith("adm_delprod_"):
            prod_id = int(data.split("_")[2])
            database.delete_product(prod_id)
            try: bot.edit_message_text("✅ *Product successfully deleted from the store.*", chat_id, call.message.message_id, parse_mode="Markdown")
            except: pass
            return

        if data.startswith("adm_restock_"):
            prod_id = int(data.split("_")[2])
            product = database.get_product(prod_id)
            if not product:
                bot.send_message(chat_id, "❌ Product not found.")
                return
            p_id, p_name = product[0], product[1]
            p_price = float(product[2])
            plain_name = re.sub('<[^<]+>', '', p_name)
            short_name = plain_name.split('\n')[0].replace('*', '')
            
            msg = bot.send_message(chat_id, f"📦 *Restocking:*\n{short_name}\n\nSend the new stock lines or upload a `.txt` file:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, lambda m: restock_stock_step(m, p_id, p_name, p_price))
            return

        if data.startswith("adm_approve_"):
            parts = data.split("_")
            user_id = int(parts[2])
            amount = float(parts[3])
            database.update_balance(user_id, amount)
            try: bot.edit_message_text(f"✅ Deposit Approved\n\nUser ID: {user_id}\nCredited: ${amount:.2f}", chat_id, call.message.message_id)
            except: pass
            try: bot.send_message(user_id, f"✅ *Deposit Approved!*\n\nYour wallet has been credited with `${amount:.2f}`. You can now purchase products.", parse_mode="Markdown")
            except: pass
            return

        if data.startswith("adm_reject_"):
            parts = data.split("_")
            user_id = int(parts[2])
            amount = float(parts[3])
            try: bot.edit_message_text(f"❌ Deposit Rejected\n\nUser ID: {user_id}\nAmount: ${amount:.2f}", chat_id, call.message.message_id)
            except: pass
            try: bot.send_message(user_id, f"❌ *Deposit Rejected*\n\nYour deposit of `${amount:.2f}` could not be verified. Please contact support.", parse_mode="Markdown")
            except: pass
            return
                                    
