import json, os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'nandn.db')
DATA_PATH = os.path.join(BASE_DIR, 'shops.json')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('NANDN_SECRET_KEY') or secrets.token_hex(32)

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def init_db():
    with connect() as db:
        # Tables creation
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS shops(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            market_area TEXT,
            address TEXT,
            phone TEXT,
            product_line TEXT,
            top_products TEXT,
            price_range TEXT,
            average_price TEXT,
            business_type TEXT,
            verification TEXT,
            product_image_name TEXT,
            photo1 TEXT,
            photo2 TEXT,
            seller_id INTEGER DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER,
            item_name TEXT NOT NULL,
            sku TEXT,
            category TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER NOT NULL DEFAULT 15,
            unit_price TEXT,
            status TEXT NOT NULL DEFAULT 'In Stock',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id)
        );
        ''')

        # Add seller_id column to shops if missing in older schema
        shop_cols = [c[1] for c in db.execute('PRAGMA table_info(shops)').fetchall()]
        if 'seller_id' not in shop_cols:
            db.execute('ALTER TABLE shops ADD COLUMN seller_id INTEGER DEFAULT NULL')

        # Load shops if empty
        if db.execute('SELECT COUNT(*) FROM shops').fetchone()[0] == 0:
            with open(DATA_PATH, encoding='utf-8') as f:
                data = json.load(f)
            db.executemany(
                'INSERT INTO shops(id,name,market_area,address,phone,product_line,top_products,price_range,average_price,business_type,verification,product_image_name,photo1,photo2) '
                'VALUES (:id,:name,:market_area,:address,:phone,:product_line,:top_products,:price_range,:average_price,:business_type,:verification,:product_image_name,:photo1,:photo2)',
                data
            )

        # 4 SEPARATE & DEDICATED ACCOUNTS (Different Email & Different Password for Each Role)
        demo_accounts = [
            ('NandN International Administrator', 'admin@nandn.local', 'AdminPass@999', 'admin'),
            ('Tariq Textile Mills (Seller)', 'seller@nandn.local', 'SellerPass@456', 'seller'),
            ('Central Warehouse Stock Controller', 'inventory@nandn.local', 'InventoryPass@789', 'inventory'),
            ('Zubair Fabrics & Home (Buyer)', 'buyer@nandn.local', 'BuyerPass@123', 'buyer')
        ]
        for name, email, pw, role in demo_accounts:
            existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
            if not existing:
                db.execute(
                    'INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',
                    (name, email, generate_password_hash(pw), role)
                )
            else:
                db.execute('UPDATE users SET role=?, name=?, password_hash=? WHERE email=?', (role, name, generate_password_hash(pw), email))

        # Link demo seller to shop #1 for instant demo experience
        seller_row = db.execute('SELECT id FROM users WHERE email=?', ('seller@nandn.local',)).fetchone()
        if seller_row:
            db.execute('UPDATE shops SET seller_id=? WHERE id=1', (seller_row['id'],))

        # Seed sample inventory if table is empty
        if db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0] == 0:
            sample_inventory = [
                (1, 'Egyptian Cotton King Bedsheet Set', 'SKU-EGY-001', 'Bedding', 140, 20, '4,800 PKR', 'In Stock'),
                (1, 'Embossed Floral Velvet Blanket (Double)', 'SKU-FLR-014', 'Blankets', 28, 15, '6,500 PKR', 'In Stock'),
                (1, 'Pure Percale Cotton Single Bedsheet', 'SKU-PRC-032', 'Bedding', 8, 15, '1,950 PKR', 'Low Stock'),
                (1, 'Microfibre Quilted Comforter (Queen)', 'SKU-COM-005', 'Comforters', 0, 10, '5,800 PKR', 'Out of Stock'),
                (2, 'Satin Stripe Hotel Luxury Duvet Cover', 'SKU-SAT-019', 'Linen', 85, 20, '3,600 PKR', 'In Stock'),
                (2, 'Traditional Jaipuri Floral Bedsheet', 'SKU-JAI-078', 'Printed Bedding', 11, 15, '2,400 PKR', 'Low Stock'),
                (3, 'Heavy Winter Korean Mink Blanket (2-Ply)', 'SKU-MNK-049', 'Blankets', 52, 12, '8,900 PKR', 'In Stock'),
                (3, 'Hypoallergenic Anti-Dust Pillow Pair', 'SKU-PIL-003', 'Pillows', 0, 25, '1,650 PKR', 'Out of Stock'),
                (4, 'Geometric Cotton Sateen Fitted Sheet', 'SKU-SAT-088', 'Fitted Sheets', 90, 15, '2,800 PKR', 'In Stock'),
                (5, 'Thermal Fleece Lightweight Throw Blanket', 'SKU-FLC-021', 'Throws', 6, 15, '2,200 PKR', 'Low Stock')
            ]
            db.executemany(
                'INSERT INTO inventory(shop_id, item_name, sku, category, quantity, low_stock_threshold, unit_price, status) '
                'VALUES (?,?,?,?,?,?,?,?)',
                sample_inventory
            )

# Strict Auth Decorators with Role Isolation
def login_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('user_id'):
            flash('Pehle login karein.', 'info')
            return redirect(url_for('buyer_login'))
        return fn(*a, **kw)
    return wrapped

def buyer_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('user_id'):
            flash('Pehle Buyer account se login karein.', 'info')
            return redirect(url_for('buyer_login'))
        if session.get('role') != 'buyer' and session.get('role') != 'admin':
            flash('Access Restricted: Yeh section sirf Buyer ke liye hai.', 'error')
            if session.get('role') == 'seller': return redirect(url_for('seller_dashboard'))
            if session.get('role') == 'inventory': return redirect(url_for('inventory_dashboard'))
            return redirect(url_for('index'))
        return fn(*a, **kw)
    return wrapped

def seller_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('user_id'):
            flash('Pehle Seller account se login karein.', 'info')
            return redirect(url_for('seller_login'))
        if session.get('role') != 'seller' and session.get('role') != 'admin':
            flash('Access Denied: Buyer ya Inventory ko Seller Dashboard access karne ki ijazat nahi hai.', 'error')
            if session.get('role') == 'buyer': return redirect(url_for('directory'))
            if session.get('role') == 'inventory': return redirect(url_for('inventory_dashboard'))
            return redirect(url_for('index'))
        return fn(*a, **kw)
    return wrapped

def inventory_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('user_id'):
            flash('Pehle Inventory Control account se login karein.', 'info')
            return redirect(url_for('inventory_login'))
        if session.get('role') != 'inventory' and session.get('role') != 'admin':
            flash('Access Denied: Buyer ya Seller ko Inventory Control Room access karne ki ijazat nahi hai.', 'error')
            if session.get('role') == 'buyer': return redirect(url_for('directory'))
            if session.get('role') == 'seller': return redirect(url_for('seller_dashboard'))
            return redirect(url_for('index'))
        return fn(*a, **kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('user_id'):
            flash('Pehle Admin account se login karein.', 'info')
            return redirect(url_for('admin_login'))
        if session.get('role') != 'admin':
            abort(403)
        return fn(*a, **kw)
    return wrapped

@app.context_processor
def globals_for_templates():
    return {
        'current_user': session.get('user_name'),
        'user_role': session.get('role')
    }

# Public Home & Portals Gateway
@app.route('/')
def index():
    with connect() as db:
        total = db.execute('SELECT COUNT(*) FROM shops').fetchone()[0]
        areas = db.execute('SELECT COUNT(DISTINCT market_area) FROM shops').fetchone()[0]
    return render_template('index.html', total=total, areas=areas)

@app.route('/portals')
@app.route('/login')
def portals_gateway():
    return render_template('portals_gateway.html')

@app.route('/register')
def register():
    return redirect(url_for('buyer_register'))

# ==================== 1. DEDICATED BUYER AUTH ====================
@app.route('/buyer/login', methods=['GET', 'POST'])
def buyer_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        
        if not user or not check_password_hash(user['password_hash'], pw):
            flash('Ghalt Buyer Email ya Password! Baraye meharbani dobara check karein.', 'error')
            return render_template('buyer_auth.html', mode='login')

        if user['role'] != 'buyer' and user['role'] != 'admin':
            flash(f'Ghalt Portal: Yeh login sirf Buyer ke liye hai. Aapka account "{user["role"].title()}" hai, baraye meharbani {user["role"].title()} Login istemal karein.', 'error')
            return render_template('buyer_auth.html', mode='login')

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']
        flash(f'Buyer Login Kamyab! Khush amdeed, {user["name"]}.', 'success')
        return redirect(url_for('directory'))

    return render_template('buyer_auth.html', mode='login')

@app.route('/buyer/register', methods=['GET', 'POST'])
def buyer_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or len(name) > 100 or not email or len(email) > 180 or '@' not in email:
            flash('Please enter a valid name and email address.', 'error')
        elif len(pw) < 8:
            flash('Password must be at least 8 characters long.', 'error')
        elif pw != confirm:
            flash('Passwords do not match.', 'error')
        else:
            try:
                with connect() as db:
                    db.execute(
                        'INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',
                        (name, email, generate_password_hash(pw), 'buyer')
                    )
                flash('Buyer account created successfully! Please sign in with your password.', 'success')
                return redirect(url_for('buyer_login'))
            except sqlite3.IntegrityError:
                flash('An account with that email already exists.', 'error')
    return render_template('buyer_auth.html', mode='register')

# ==================== 2. DEDICATED SELLER AUTH ====================
@app.route('/seller/login', methods=['GET', 'POST'])
def seller_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        
        if not user or not check_password_hash(user['password_hash'], pw):
            flash('Ghalt Seller Email ya Password! Baraye meharbani dobara check karein.', 'error')
            return render_template('seller_auth.html', mode='login')

        if user['role'] != 'seller' and user['role'] != 'admin':
            flash('Access Restricted: Yeh portal sirf Seller / Dukandar ke liye hai. Buyer ya Inventory staff yahan login nahi kar sakte.', 'error')
            return render_template('seller_auth.html', mode='login')

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']
        flash(f'Seller Login Kamyab! Merchant Portal mein khush amdeed, {user["name"]}.', 'success')
        return redirect(url_for('seller_dashboard'))

    return render_template('seller_auth.html', mode='login')

@app.route('/seller/register', methods=['GET', 'POST'])
def seller_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        shop_name = request.form.get('shop_name', '').strip()
        market_area = request.form.get('market_area', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not shop_name or not email or '@' not in email:
            flash('Please complete all required merchant fields.', 'error')
        elif len(pw) < 8:
            flash('Password must be at least 8 characters long.', 'error')
        elif pw != confirm:
            flash('Passwords do not match.', 'error')
        else:
            try:
                with connect() as db:
                    cursor = db.execute(
                        'INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',
                        (name, email, generate_password_hash(pw), 'seller')
                    )
                    uid = cursor.lastrowid
                    nid = db.execute('SELECT COALESCE(MAX(id),0)+1 FROM shops').fetchone()[0]
                    db.execute(
                        'INSERT INTO shops(id,name,market_area,address,phone,product_line,top_products,price_range,average_price,business_type,verification,product_image_name,photo1,photo2,seller_id) '
                        'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (nid, shop_name, market_area or 'Faisalabad Market', '', phone, 'Bedding & Home Textiles', '', 'Price on Request', '', 'Wholesale / Retail', 'Verified Seller', '', '', '', uid)
                    )
                flash(f'Store "{shop_name}" registered! Please sign in as Seller.', 'success')
                return redirect(url_for('seller_login'))
            except sqlite3.IntegrityError:
                flash('An account with that email already exists.', 'error')
    return render_template('seller_auth.html', mode='register')

# ==================== 3. DEDICATED INVENTORY CONTROLLER AUTH ====================
@app.route('/inventory/login', methods=['GET', 'POST'])
def inventory_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        
        if not user or not check_password_hash(user['password_hash'], pw):
            flash('Ghalt Inventory Staff Email ya Password! Baraye meharbani check karein.', 'error')
            return render_template('inventory_auth.html')

        if user['role'] != 'inventory' and user['role'] != 'admin':
            flash('Access Restricted: Yeh portal sirf Central Warehouse & Inventory Controllers ke liye hai. Buyer ya Seller yahan login nahi kar sakte.', 'error')
            return render_template('inventory_auth.html')

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']
        flash(f'Inventory Controller Login Kamyab! Welcome, {user["name"]}.', 'success')
        return redirect(url_for('inventory_dashboard'))

    return render_template('inventory_auth.html')

# ==================== 4. DEDICATED ADMIN AUTH ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        with connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        
        if not user or not check_password_hash(user['password_hash'], pw):
            flash('Invalid administrator credentials.', 'error')
            return render_template('admin_auth.html')

        if user['role'] != 'admin':
            flash('Access Denied: Super Admin privileges required.', 'error')
            return render_template('admin_auth.html')

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']
        flash('Administrator access granted.', 'success')
        return redirect(url_for('admin'))

    return render_template('admin_auth.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Aap successfully sign out ho chuke hain.', 'info')
    return redirect(url_for('index'))

# ==================== BUYER FUNCTIONALITY (SHOP DIRECTORY) ====================
@app.route('/directory')
@buyer_required
def directory():
    q = request.args.get('q', '').strip()
    area = request.args.get('area', '').strip()
    category = request.args.get('category', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per = 12
    where = []
    params = []

    if q:
        like = '%' + q + '%'
        where.append('(name LIKE ? OR market_area LIKE ? OR address LIKE ? OR phone LIKE ? OR product_line LIKE ? OR top_products LIKE ?)')
        params += [like] * 6
    if area:
        where.append('market_area=?')
        params.append(area)
    if category:
        where.append('(product_line LIKE ? OR top_products LIKE ?)')
        params += ['%' + category + '%'] * 2

    clause = (' WHERE ' + ' AND '.join(where)) if where else ''
    with connect() as db:
        total = db.execute('SELECT COUNT(*) FROM shops' + clause, params).fetchone()[0]
        shops = db.execute('SELECT * FROM shops' + clause + ' ORDER BY id LIMIT ? OFFSET ?', params + [per, (page - 1) * per]).fetchall()
        areas = [r[0] for r in db.execute("SELECT DISTINCT market_area FROM shops WHERE market_area IS NOT NULL AND market_area!='' ORDER BY market_area")]
        categories = [r[0] for r in db.execute("SELECT DISTINCT product_line FROM shops WHERE product_line IS NOT NULL AND product_line!='' ORDER BY product_line")]
    return render_template('directory.html', shops=shops, total=total, page=page, pages=max(1, (total + per - 1) // per), q=q, area=area, category=category, areas=areas, categories=categories)

@app.route('/shop/<int:shop_id>')
@buyer_required
def shop_detail(shop_id):
    with connect() as db:
        shop = db.execute('SELECT * FROM shops WHERE id=?', (shop_id,)).fetchone()
        if not shop:
            abort(404)
        inventory_items = db.execute('SELECT * FROM inventory WHERE shop_id=? ORDER BY id DESC', (shop_id,)).fetchall()
    return render_template('shop.html', shop=shop, inventory_items=inventory_items)

# ==================== SELLER FUNCTIONALITY (MERCHANT PORTAL) ====================
@app.route('/seller/dashboard')
@seller_required
def seller_dashboard():
    uid = session['user_id']
    role = session.get('role')
    with connect() as db:
        if role == 'admin':
            my_shops = db.execute('SELECT * FROM shops ORDER BY id LIMIT 10').fetchall()
            shop_id = request.args.get('shop_id', (my_shops[0]['id'] if my_shops else 1), type=int)
            active_shop = db.execute('SELECT * FROM shops WHERE id=?', (shop_id,)).fetchone() or (my_shops[0] if my_shops else None)
        else:
            my_shops = db.execute('SELECT * FROM shops WHERE seller_id=? ORDER BY id', (uid,)).fetchall()
            active_shop = my_shops[0] if my_shops else None

        items = []
        stats = {'total_items': 0, 'in_stock': 0, 'low_stock': 0}
        if active_shop:
            items = db.execute('SELECT * FROM inventory WHERE shop_id=? ORDER BY id DESC', (active_shop['id'],)).fetchall()
            stats['total_items'] = len(items)
            stats['in_stock'] = sum(1 for i in items if i['status'] == 'In Stock')
            stats['low_stock'] = sum(1 for i in items if i['status'] in ('Low Stock', 'Out of Stock'))

    return render_template('seller_dashboard.html', my_shops=my_shops, active_shop=active_shop, items=items, stats=stats)

@app.route('/seller/shop/update', methods=['POST'])
@seller_required
def seller_update_shop():
    uid = session['user_id']
    role = session.get('role')
    shop_id = request.form.get('shop_id', type=int)
    name = request.form.get('name', '').strip()
    market_area = request.form.get('market_area', '').strip()
    address = request.form.get('address', '').strip()
    phone = request.form.get('phone', '').strip()
    product_line = request.form.get('product_line', '').strip()
    top_products = request.form.get('top_products', '').strip()
    price_range = request.form.get('price_range', '').strip()

    if not name:
        flash('Shop name is required.', 'error')
        return redirect(url_for('seller_dashboard'))

    with connect() as db:
        if role == 'admin':
            db.execute(
                'UPDATE shops SET name=?, market_area=?, address=?, phone=?, product_line=?, top_products=?, price_range=? WHERE id=?',
                (name, market_area, address, phone, product_line, top_products, price_range, shop_id)
            )
        else:
            db.execute(
                'UPDATE shops SET name=?, market_area=?, address=?, phone=?, product_line=?, top_products=?, price_range=? WHERE id=? AND seller_id=?',
                (name, market_area, address, phone, product_line, top_products, price_range, shop_id, uid)
            )
    flash('Shop information updated successfully.', 'success')
    return redirect(url_for('seller_dashboard'))

@app.route('/seller/inventory/add', methods=['POST'])
@seller_required
def seller_add_inventory():
    shop_id = request.form.get('shop_id', type=int)
    item_name = request.form.get('item_name', '').strip()
    sku = request.form.get('sku', '').strip()
    category = request.form.get('category', '').strip()
    quantity = max(0, request.form.get('quantity', 0, type=int))
    unit_price = request.form.get('unit_price', '').strip()

    if not item_name:
        flash('Product name is required.', 'error')
        return redirect(url_for('seller_dashboard'))

    status = 'Out of Stock' if quantity == 0 else ('Low Stock' if quantity <= 10 else 'In Stock')

    with connect() as db:
        db.execute(
            'INSERT INTO inventory(shop_id, item_name, sku, category, quantity, unit_price, status) VALUES(?,?,?,?,?,?,?)',
            (shop_id, item_name, sku, category, quantity, unit_price, status)
        )
    flash(f'Product "{item_name}" added to your shop inventory.', 'success')
    return redirect(url_for('seller_dashboard'))

@app.route('/seller/inventory/<int:item_id>/delete', methods=['POST'])
@seller_required
def seller_delete_inventory(item_id):
    with connect() as db:
        db.execute('DELETE FROM inventory WHERE id=?', (item_id,))
    flash('Product removed from inventory.', 'info')
    return redirect(url_for('seller_dashboard'))

# ==================== INVENTORY FUNCTIONALITY (CONTROL ROOM) ====================
@app.route('/inventory/dashboard')
@inventory_required
def inventory_dashboard():
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    shop_filter = request.args.get('shop_id', '', type=str)

    where = []
    params = []
    if q:
        like = f'%{q}%'
        where.append('(i.item_name LIKE ? OR i.sku LIKE ? OR i.category LIKE ?)')
        params.extend([like, like, like])
    if status_filter:
        where.append('i.status=?')
        params.append(status_filter)
    if shop_filter and shop_filter.isdigit():
        where.append('i.shop_id=?')
        params.append(int(shop_filter))

    clause = (' WHERE ' + ' AND '.join(where)) if where else ''

    with connect() as db:
        total_items = db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0]
        total_units = db.execute('SELECT COALESCE(SUM(quantity), 0) FROM inventory').fetchone()[0]
        low_stock_count = db.execute("SELECT COUNT(*) FROM inventory WHERE status='Low Stock'").fetchone()[0]
        out_of_stock_count = db.execute("SELECT COUNT(*) FROM inventory WHERE status='Out of Stock'").fetchone()[0]

        sql = f'''
        SELECT i.*, s.name as shop_name 
        FROM inventory i 
        LEFT JOIN shops s ON i.shop_id = s.id 
        {clause} 
        ORDER BY i.id DESC
        '''
        items = db.execute(sql, params).fetchall()
        shops = db.execute('SELECT id, name FROM shops ORDER BY id LIMIT 50').fetchall()

    stats = {
        'total_items': total_items,
        'total_units': total_units,
        'low_stock': low_stock_count,
        'out_of_stock': out_of_stock_count
    }
    return render_template(
        'inventory_dashboard.html',
        items=items,
        stats=stats,
        shops=shops,
        q=q,
        status_filter=status_filter,
        shop_filter=shop_filter
    )

@app.route('/inventory/update/<int:item_id>', methods=['POST'])
@inventory_required
def inventory_update(item_id):
    quantity = max(0, request.form.get('quantity', 0, type=int))
    unit_price = request.form.get('unit_price', '').strip()
    threshold = max(1, request.form.get('low_stock_threshold', 15, type=int))

    if quantity == 0:
        status = 'Out of Stock'
    elif quantity <= threshold:
        status = 'Low Stock'
    else:
        status = 'In Stock'

    with connect() as db:
        db.execute(
            'UPDATE inventory SET quantity=?, unit_price=?, low_stock_threshold=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (quantity, unit_price, threshold, status, item_id)
        )
    flash(f'Stock updated for Item #{item_id} (Status: {status}).', 'success')
    return redirect(url_for('inventory_dashboard'))

@app.route('/inventory/add', methods=['POST'])
@inventory_required
def inventory_add():
    shop_id = request.form.get('shop_id', type=int)
    item_name = request.form.get('item_name', '').strip()
    sku = request.form.get('sku', '').strip()
    category = request.form.get('category', '').strip()
    quantity = max(0, request.form.get('quantity', 0, type=int))
    threshold = max(1, request.form.get('low_stock_threshold', 15, type=int))
    unit_price = request.form.get('unit_price', '').strip()

    if not item_name:
        flash('Item name is required.', 'error')
        return redirect(url_for('inventory_dashboard'))

    if quantity == 0:
        status = 'Out of Stock'
    elif quantity <= threshold:
        status = 'Low Stock'
    else:
        status = 'In Stock'

    with connect() as db:
        db.execute(
            'INSERT INTO inventory(shop_id, item_name, sku, category, quantity, low_stock_threshold, unit_price, status) VALUES (?,?,?,?,?,?,?,?)',
            (shop_id, item_name, sku, category, quantity, threshold, unit_price, status)
        )
    flash(f'New inventory item "{item_name}" recorded successfully.', 'success')
    return redirect(url_for('inventory_dashboard'))

@app.route('/inventory/delete/<int:item_id>', methods=['POST'])
@inventory_required
def inventory_delete(item_id):
    with connect() as db:
        db.execute('DELETE FROM inventory WHERE id=?', (item_id,))
    flash('Item deleted from inventory records.', 'info')
    return redirect(url_for('inventory_dashboard'))

# ==================== ADMIN DASHBOARD ====================
@app.route('/admin')
@admin_required
def admin():
    with connect() as db:
        stats = {
            'shops': db.execute('SELECT COUNT(*) FROM shops').fetchone()[0],
            'users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'inventory': db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0]
        }
        users = db.execute('SELECT id,name,email,role,created_at FROM users ORDER BY id DESC LIMIT 20').fetchall()
        shops = db.execute('SELECT id,name,market_area,phone FROM shops ORDER BY id DESC LIMIT 20').fetchall()
    return render_template('admin.html', stats=stats, users=users, shops=shops)

@app.route('/admin/shop', methods=['POST'])
@admin_required
def add_shop():
    d = {k: request.form.get(k, '').strip() for k in ['name', 'market_area', 'address', 'phone', 'product_line', 'top_products', 'price_range', 'average_price', 'business_type', 'verification']}
    if not d['name']:
        flash('Shop name is required.', 'error')
        return redirect(url_for('admin'))
    with connect() as db:
        nid = db.execute('SELECT COALESCE(MAX(id),0)+1 FROM shops').fetchone()[0]
        db.execute(
            'INSERT INTO shops(id,name,market_area,address,phone,product_line,top_products,price_range,average_price,business_type,verification,product_image_name,photo1,photo2) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (nid, d['name'], d['market_area'], d['address'], d['phone'], d['product_line'], d['top_products'], d['price_range'], d['average_price'], d['business_type'], d['verification'], '', '', '')
        )
    flash('Shop added to the directory.', 'success')
    return redirect(url_for('directory'))

@app.route('/admin/shop/<int:shop_id>', methods=['GET', 'POST'])
@admin_required
def edit_shop(shop_id):
    keys = ['name', 'market_area', 'address', 'phone', 'product_line', 'top_products', 'price_range', 'average_price', 'business_type', 'verification']
    with connect() as db:
        shop = db.execute('SELECT * FROM shops WHERE id=?', (shop_id,)).fetchone()
    if not shop:
        abort(404)
    if request.method == 'POST':
        d = {k: request.form.get(k, '').strip() for k in keys}
        if not d['name']:
            flash('Shop name is required.', 'error')
            return redirect(url_for('edit_shop', shop_id=shop_id))
        with connect() as db:
            db.execute(
                'UPDATE shops SET name=?,market_area=?,address=?,phone=?,product_line=?,top_products=?,price_range=?,average_price=?,business_type=?,verification=? WHERE id=?',
                tuple(d[k] for k in keys) + (shop_id,)
            )
        flash('Shop details updated.', 'success')
        return redirect(url_for('admin'))
    return render_template('edit_shop.html', shop=shop)

@app.route('/admin/shop/<int:shop_id>/delete', methods=['POST'])
@admin_required
def delete_shop(shop_id):
    with connect() as db:
        db.execute('DELETE FROM shops WHERE id=?', (shop_id,))
    flash('Shop record deleted.', 'info')
    return redirect(url_for('admin'))

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Access restricted: You do not have permission to view this role dashboard.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='We could not find that page, shop or inventory item.'), 404

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)), debug=False)
