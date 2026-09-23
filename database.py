import os
import datetime
import config
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    pass

def set_maintenance_mode(status):
    supabase.table('settings').upsert({'key': 'maintenance', 'value': str(status)}).execute()

def get_maintenance_mode():
    res = supabase.table('settings').select('value').eq('key', 'maintenance').execute()
    if res.data:
        return res.data[0]['value'] == 'True'
    return False

def add_user(user_id, username="", name=""):
    existing = supabase.table('users').select('user_id').eq('user_id', user_id).execute()
    if not existing.data:
        supabase.table('users').insert({
            'user_id': user_id, 
            'balance': 0.0, 
            'language': 'en', 
            'username': username, 
            'name': name
        }).execute()
    else:
        update_data = {}
        if username: update_data['username'] = username
        if name: update_data['name'] = name
        if update_data:
            supabase.table('users').update(update_data).eq('user_id', user_id).execute()

def get_balance(user_id):
    res = supabase.table('users').select('balance').eq('user_id', user_id).execute()
    return float(res.data[0]['balance']) if res.data else 0.0

def update_balance(user_id, amount):
    current = get_balance(user_id)
    supabase.table('users').update({'balance': current + amount}).eq('user_id', user_id).execute()

def set_balance(user_id, amount):
    supabase.table('users').update({'balance': amount}).eq('user_id', user_id).execute()

def set_language(user_id, lang):
    supabase.table('users').update({'language': lang}).eq('user_id', user_id).execute()

def get_language(user_id):
    res = supabase.table('users').select('language').eq('user_id', user_id).execute()
    return res.data[0]['language'] if res.data else 'en'

def get_all_users():
    res = supabase.table('users').select('user_id, balance').execute()
    return [(r['user_id'], r['balance']) for r in res.data]

def get_user_details(user_id):
    res = supabase.table('users').select('user_id, username, name, balance').eq('user_id', user_id).execute()
    if res.data:
        r = res.data[0]
        return (r['user_id'], r['username'], r['name'], r['balance'])
    return None

def add_order(user_id, product_name, price, item_data):
    supabase.table('orders').insert({
        'user_id': user_id, 
        'product_name': product_name, 
        'price': price, 
        'item_data': item_data
    }).execute()

def get_user_orders(user_id):
    res = supabase.table('orders').select('product_name, price, item_data, date').eq('user_id', user_id).order('id', desc=True).limit(10).execute()
    return [(r['product_name'], r['price'], r['item_data'], r['date']) for r in res.data]

def get_all_users_detailed():
    users = supabase.table('users').select('user_id, username, name, balance').execute().data
    orders = supabase.table('orders').select('user_id').execute().data
    
    order_counts = {}
    for o in orders:
        uid = o['user_id']
        order_counts[uid] = order_counts.get(uid, 0) + 1
        
    return [(u['user_id'], u['username'], u['name'], u['balance'], order_counts.get(u['user_id'], 0)) for u in users]

def add_product(name, price, stock_data, image_id=None):
    res = supabase.table('products').insert({
        'name': name, 
        'price': price, 
        'stock_data': stock_data.strip(), 
        'image_id': image_id
    }).execute()
    return res.data[0]['id'] if res.data else None

def get_all_products():
    res = supabase.table('products').select('id, name, price, image_id, stock_data').execute()
    products = []
    for r in res.data:
        lines = [line.strip() for line in (r['stock_data'] or "").split('\n') if line.strip()]
        products.append((r['id'], r['name'], float(r['price']), r['image_id'], len(lines)))
    return products

def get_product(product_id):
    res = supabase.table('products').select('id, name, price, image_id, stock_data').eq('id', product_id).execute()
    if res.data:
        r = res.data[0]
        return (r['id'], r['name'], float(r['price']), r['image_id'], r['stock_data'])
    return None

def append_stock(product_id, new_stock_data):
    prod = get_product(product_id)
    if not prod: return 0, 0
    current_stock = prod[4] or ""
    current_lines = [l.strip() for l in current_stock.split('\n') if l.strip()]
    new_lines = [l.strip() for l in new_stock_data.split('\n') if l.strip()]
    combined_lines = current_lines + new_lines
    updated_stock = '\n'.join(combined_lines)
    supabase.table('products').update({'stock_data': updated_stock}).eq('id', product_id).execute()
    return len(new_lines), len(combined_lines)

def consume_stock_items(product_id, count=1, bot=None):
    prod = get_product(product_id)
    if not prod: return []
    
    prod_name, stock_text = prod[1], prod[4]
    lines = [line.strip() for line in (stock_text or "").split('\n') if line.strip()]
    if len(lines) < count: return []
    
    consumed = [lines.pop(0) for _ in range(count)]
    updated_stock = '\n'.join(lines)
    
    supabase.table('products').update({'stock_data': updated_stock}).eq('id', product_id).execute()
    
    remaining_count = len(lines)
    if remaining_count <= 2 and bot:
        alert_msg = f"⚠️ **Low Stock Alert!**\n\nProduct: **{prod_name}** (ID: {product_id})\nRemaining stock: **{remaining_count} items left**."
        for admin_id in config.ADMIN_IDS:
            try: bot.send_message(admin_id, alert_msg, parse_mode="Markdown")
            except: pass
            
    return consumed

def consume_stock_item(product_id, bot=None):
    items = consume_stock_items(product_id, 1, bot)
    return items[0] if items else None

def delete_product(product_id):
    supabase.table('products').delete().eq('id', product_id).execute()

def get_store_stats():
    orders = supabase.table('orders').select('price, date').execute().data
    total_orders = len(orders)
    total_revenue = sum(float(o['price']) for o in orders if o['price'] is not None)
    
    today = datetime.datetime.utcnow().date()
    today_orders = [o for o in orders if o['date'] and str(o['date']).startswith(str(today))]
    today_count = len(today_orders)
    today_revenue = sum(float(o['price']) for o in today_orders if o['price'] is not None)
    
    return (total_orders, total_revenue, today_count, today_revenue)
    
