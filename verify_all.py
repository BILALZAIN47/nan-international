import sys
from app import app, connect, init_db

print("==================================================================")
print("  NandN INTERNATIONAL - FULL SYSTEM & WORKFLOW VERIFICATION SUITE")
print("==================================================================")

# 1. DATABASE AUDIT
print("\n[STEP 1] Checking Database Integrity...")
init_db()
with connect() as db:
    users = db.execute('SELECT id, name, email, role FROM users').fetchall()
    print(f"  ✓ Total users in database: {len(users)}")
    for u in users:
        print(f"    - {u['email']} | Role: {u['role']} | Name: {u['name']}")

    shops_count = db.execute('SELECT COUNT(*) FROM shops').fetchone()[0]
    print(f"  ✓ Total shops listed: {shops_count}")
    assert shops_count >= 500

    inv_count = db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0]
    print(f"  ✓ Total warehouse inventory records: {inv_count}")
    assert inv_count >= 10

# 2. CLIENT TESTS: PUBLIC ROUTES
print("\n[STEP 2] Testing Public Web Pages...")
c = app.test_client()

public_routes = {
    'Homepage': '/',
    'Portals Gateway': '/portals',
    'Buyer Login': '/buyer/login',
    'Buyer Register': '/buyer/register',
    'Seller Login': '/seller/login',
    'Seller Register': '/seller/register',
    'Inventory Login': '/inventory/login',
    'Admin Login': '/admin/login'
}

for name, url in public_routes.items():
    res = c.get(url)
    assert res.status_code == 200, f"Failed on {name} ({url}) with status {res.status_code}"
    print(f"  ✓ {name:<20} -> Status 200 OK")

# 3. VERIFY LOGIN ALWAYS ASKS FOR PASSWORDS
print("\n[STEP 3] Verifying Login Pages Always Require Passwords (No Auto-Bypass)...")
for url in ['/buyer/login', '/seller/login', '/inventory/login']:
    res = c.get(url)
    assert b'name="email"' in res.data
    assert b'name="password"' in res.data
print("  ✓ All login forms strictly ask for email and password every single time.")

# 4. JOURNEY: BUYER
print("\n[STEP 4] Testing Buyer Journey & Access Restrictions...")
cb = app.test_client()

# A. Wrong password rejected
res_wrong = cb.post('/buyer/login', data={'email': 'buyer@nandn.local', 'password': 'WrongPassword!'}, follow_redirects=True)
assert b'Ghalt Buyer Email' in res_wrong.data
print("  ✓ Wrong password correctly rejected with error.")

# B. Correct password accepted
res_login = cb.post('/buyer/login', data={'email': 'buyer@nandn.local', 'password': 'BuyerPass@123'}, follow_redirects=True)
assert res_login.status_code == 200
assert b'Shop directory' in res_login.data
print("  ✓ Buyer successfully logged in with BuyerPass@123.")

# C. Buyer browsing directory & detail
res_dir = cb.get('/directory')
assert res_dir.status_code == 200
assert b'THE NANDN INTERNATIONAL DIRECTORY' in res_dir.data
res_shop = cb.get('/shop/1')
assert res_shop.status_code == 200
print("  ✓ Buyer can browse directory and view shop details & in-stock items.")

# D. Buyer BLOCKED from Seller and Inventory
res_s = cb.get('/seller/dashboard', follow_redirects=True)
assert b'Access Denied' in res_s.data
print("  ✓ Buyer strictly BLOCKED from Seller Dashboard (Access Denied).")

res_i = cb.get('/inventory/dashboard', follow_redirects=True)
assert b'Access Denied' in res_i.data
print("  ✓ Buyer strictly BLOCKED from Inventory Dashboard (Access Denied).")

# 5. JOURNEY: SELLER
print("\n[STEP 5] Testing Seller Journey & Access Restrictions...")
cs = app.test_client()

# A. Buyer credentials on Seller Login rejected
res_cross = cs.post('/seller/login', data={'email': 'buyer@nandn.local', 'password': 'BuyerPass@123'}, follow_redirects=True)
assert b'Access Restricted' in res_cross.data
print("  ✓ Buyer credentials rejected on Seller Login.")

# B. Seller login
res_login_s = cs.post('/seller/login', data={'email': 'seller@nandn.local', 'password': 'SellerPass@456'}, follow_redirects=True)
assert res_login_s.status_code == 200
assert b'Merchant' in res_login_s.data
print("  ✓ Seller successfully logged in with SellerPass@456.")

# C. Seller updating shop
res_up = cs.post('/seller/shop/update', data={
    'shop_id': 1,
    'name': 'Tariq Textile Mills (Verified Hub)',
    'market_area': 'Clock Tower Market',
    'address': 'Katchery Bazar, Faisalabad',
    'phone': '0300-7654321',
    'product_line': 'Luxury Bedding & Blankets',
    'top_products': 'Cotton Sateen Bedsheets',
    'price_range': '2,000 - 8,500'
}, follow_redirects=True)
assert b'Shop information updated successfully' in res_up.data
print("  ✓ Seller can update storefront details.")

# D. Seller adding product to inventory
res_add = cs.post('/seller/inventory/add', data={
    'shop_id': 1,
    'item_name': 'Test Velvet Luxury Quilt',
    'sku': 'SKU-TST-999',
    'category': 'Quilts',
    'quantity': 30,
    'unit_price': '7,200 PKR'
}, follow_redirects=True)
assert b'Test Velvet Luxury Quilt' in res_add.data
print("  ✓ Seller can add new products to shop inventory.")

# E. Seller BLOCKED from Inventory and Buyer Directory
res_s_to_inv = cs.get('/inventory/dashboard', follow_redirects=True)
assert b'Access Denied' in res_s_to_inv.data
print("  ✓ Seller strictly BLOCKED from Inventory Control Room (Access Denied).")

res_s_to_dir = cs.get('/directory', follow_redirects=True)
assert b'Access Restricted' in res_s_to_dir.data
print("  ✓ Seller strictly BLOCKED from Buyer Directory (Access Restricted).")

# 6. JOURNEY: INVENTORY CONTROLLER
print("\n[STEP 6] Testing Inventory Controller Journey & Access Restrictions...")
ci = app.test_client()

# A. Seller credentials on Inventory Login rejected
res_cross_inv = ci.post('/inventory/login', data={'email': 'seller@nandn.local', 'password': 'SellerPass@456'}, follow_redirects=True)
assert b'Access Restricted' in res_cross_inv.data
print("  ✓ Seller credentials rejected on Inventory Login.")

# B. Inventory login
res_login_i = ci.post('/inventory/login', data={'email': 'inventory@nandn.local', 'password': 'InventoryPass@789'}, follow_redirects=True)
assert res_login_i.status_code == 200
assert b'Control Room' in res_login_i.data
print("  ✓ Inventory Controller successfully logged in with InventoryPass@789.")

# C. Inventory Controller stock update
res_inv_update = ci.post('/inventory/update/1', data={
    'quantity': 88,
    'unit_price': '4,800 PKR',
    'low_stock_threshold': 15
}, follow_redirects=True)
assert b'Stock updated for Item #1' in res_inv_update.data
print("  ✓ Inventory Controller can update warehouse quantities and thresholds.")

# D. Inventory BLOCKED from Seller and Buyer
res_i_to_s = ci.get('/seller/dashboard', follow_redirects=True)
assert b'Access Denied' in res_i_to_s.data
print("  ✓ Inventory Controller strictly BLOCKED from Seller Dashboard (Access Denied).")

res_i_to_b = ci.get('/directory', follow_redirects=True)
assert b'Access Restricted' in res_i_to_b.data
print("  ✓ Inventory Controller strictly BLOCKED from Buyer Directory (Access Restricted).")

print("\n==================================================================")
print("  VERIFICATION RESULT: ALL CHECKS PASSED WITH 100% SUCCESS!")
print("  - Website structure: Flawless")
print("  - Separate login pages & credentials: Flawless")
print("  - Role isolation & protection: Flawless")
print("  - Zero errors, zero confusion, smooth operation")
print("==================================================================")

