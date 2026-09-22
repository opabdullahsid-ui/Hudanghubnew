import os
import config
import requests

DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

# --- DIAGNOSTIC BLOCK ---
diagnostic_url = (DATABASE_URL or "").replace("libsql://", "https://")

try:
    if diagnostic_url and AUTH_TOKEN:
        print("--- RUNNING TURSO DIAGNOSTIC ---")
        res = requests.post(
            f"{diagnostic_url}/v2/pipeline", 
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={"requests": []}
        )
        print("TURSO RESULT:", res.status_code, res.text)
        print("--------------------------------")
except Exception as e:
    print("TURSO DIAGNOSTIC FAILED:", e)
# ------------------------

# Connect to Turso if configured, fallback to local SQLite
if DATABASE_URL and AUTH_TOKEN:
    import libsql_client

    class TursoCursor:
        def __init__(self, client):
            self.client = client
            self.last_res = None
            self.lastrowid = None

        def execute(self, query, params=()):
            sql_query = query.replace('?', '?')
            res = self.client.execute(sql_query, list(params))
            self.last_res = res
            self.lastrowid = res.last_insert_rowid
            return self

        def fetchone(self):
            if self.last_res and self.last_res.rows:
                return tuple(self.last_res.rows[0])
            return None

        def fetchall(self):
            if self.last_res and self.last_res.rows:
                return [tuple(r) for r in self.last_res.rows]
            return []

    class TursoConnection:
        def __init__(self):
            self.client = libsql_client.create_client_sync(
                url=DATABASE_URL,
                auth_token=AUTH_TOKEN
            )

        def cursor(self):
            return TursoCursor(self.client)

        def commit(self):
            pass

        def close(self):
            self.client.close()

    def get_connection():
        return TursoConnection()
else:
    import sqlite3
    def get_connection():
        return sqlite3.connect('store.db')

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'en',
            username TEXT,
            name TEXT
        )
    ''')
    try: cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    except Exception: pass
    try: cursor.execute('ALTER TABLE users ADD COLUMN name TEXT')
    except Exception: pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image_id TEXT,
            stock_data TEXT NOT NULL
        )
    ''')
    try: cursor.execute('ALTER TABLE products ADD COLUMN image_id TEXT')
    except Exception: pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            price REAL,
            item_data TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_maintenance_mode(status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("maintenance", ?)', (str(status),))
    conn.commit()
    conn.close()

def get_maintenance_mode():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "maintenance"')
    row = cursor.fetchone()
    conn.close()
    return row[0] == 'True' if row else False

def add_user(user_id, username="", name=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, balance, language, username, name) 
        VALUES (?, 0.0, 'en', ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            username = COALESCE(NULLIF(?, ''), username),
            name = COALESCE(NULLIF(?, ''), name)
    ''', (user_id, username, name, username, name))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def set_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def set_language(user_id, lang):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def get_language(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 'en'

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM users')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_user_details(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, name, balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_order(user_id, product_name, price, item_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, product_name, price, item_data) VALUES (?, ?, ?, ?)', (user_id, product_name, price, item_data))
    conn.commit()
    conn.close()

def get_user_orders(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT product_name, price, item_data, date FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_users_detailed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.name, u.balance, 
               (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) as total_purchases
        FROM users u
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_product(name, price, stock_data, image_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, image_id, stock_data) VALUES (?, ?, ?, ?)', (name, price, image_id, stock_data.strip()))
    prod_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prod_id

def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, image_id, stock_data FROM products')
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        prod_id, name, price, image_id, stock_data = row
        lines = [line.strip() for line in str(stock_data).split('\n') if line.strip()]
        products.append((prod_id, name, price, image_id, len(lines)))
    return products

def get_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, image_id, stock_data FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def append_stock(product_id, new_stock_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT stock_data FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 0, 0
    
    current_stock = row[0] or ""
    current_lines = [l.strip() for l in current_stock.split('\n') if l.strip()]
    new_lines = [l.strip() for l in new_stock_data.split('\n') if l.strip()]
    
    combined_lines = current_lines + new_lines
    updated_stock = '\n'.join(combined_lines)
    
    cursor.execute('UPDATE products SET stock_data = ? WHERE id = ?', (updated_stock, product_id))
    conn.commit()
    conn.close()
    return len(new_lines), len(combined_lines)

def consume_stock_items(product_id, count=1, bot=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name, stock_data FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return []
    
    prod_name, stock_text = row
    lines = [line.strip() for line in (stock_text or "").split('\n') if line.strip()]
    if len(lines) < count:
        conn.close()
        return []
    
    consumed = []
    for _ in range(count):
        consumed.append(lines.pop(0))
        
    updated_stock = '\n'.join(lines)
    cursor.execute('UPDATE products SET stock_data = ? WHERE id = ?', (updated_stock, product_id))
    conn.commit()
    conn.close()

    remaining_count = len(lines)
    if remaining_count <= 2 and bot:
        alert_msg = f"⚠️ **Low Stock Alert!**\n\nProduct: **{prod_name}** (ID: {product_id})\nRemaining stock: **{remaining_count} items left**."
        for admin_id in config.ADMIN_IDS:
            try:
                bot.send_message(admin_id, alert_msg, parse_mode="Markdown")
            except Exception:
                pass

    return consumed

def consume_stock_item(product_id, bot=None):
    items = consume_stock_items(product_id, 1, bot)
    return items[0] if items else None

def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def get_store_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(price) FROM orders')
    total = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE date >= date('now', 'start of day')")
    today = cursor.fetchone()
    conn.close()
    return (total[0] if total and total[0] else 0,
            total[1] if total and total[1] else 0.0,
            today[0] if today and today[0] else 0,
            today[1] if today and today[1] else 0.0)

try:
    init_db()
except Exception:
    pass
    
