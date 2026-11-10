NandN INTERNATIONAL — WEBSITE PROJECT
=====================================

MULTI-ROLE ARCHITECTURE
- Buyer (Customer / Wholesale Client): Browse directory, search shops, view verified stock & contact sellers
- Seller (Merchant / Storefront Owner): Seller Portal to manage shop profile, add products & live inventory
- Inventory Controller (Warehouse Manager): Central Control Room for live stock tracking, quantity adjustments & low-stock alerts
- Administrator: Manage system accounts, shops & directory overview

INCLUDED
- Premium responsive traditional-luxury design (burgundy, cream, antique gold)
- Role-based registration & unified login with smart dashboard routing
- SQLite database (`nandn.db`) created automatically on first run
- 500 shop records and 1,000 embedded images
- Search by shop, market, address, phone and product; market/product filters
- Shop detail pages with live inventory stock tables
- Seller Dashboard & Central Inventory Control Room

RUN ON WINDOWS
1. Install Python 3.10+ from https://www.python.org/downloads/ and enable Add Python to PATH.
2. Double-click `run_windows.bat`; it installs dependencies and starts the app.
3. Open http://127.0.0.1:5000 in your browser.

DEDICATED PORTAL LOGIN URLs & DEMO ACCOUNTS
--------------------------------------------
1. BUYER PORTAL:
   Login URL: http://127.0.0.1:5000/buyer/login
   Register URL: http://127.0.0.1:5000/buyer/register
   Demo Email: buyer@nandn.local
   Demo Password: BuyerPass@123
   Accesses: Shop Directory, In-Stock Bedding & Contact Details (Buyer only)

2. SELLER / MERCHANT PORTAL:
   Login URL: http://127.0.0.1:5000/seller/login
   Register URL: http://127.0.0.1:5000/seller/register
   Demo Email: seller@nandn.local
   Demo Password: SellerPass@456
   Accesses: Merchant Workspace, Store Profile, Add Products & Shop Stock (Seller only)

3. INVENTORY CONTROLLER PORTAL:
   Login URL: http://127.0.0.1:5000/inventory/login
   Demo Email: inventory@nandn.local
   Demo Password: InventoryPass@789
   Accesses: Central Warehouse Control Room, Stock Intake, Low Stock Alerts (Inventory only)

4. SUPER ADMIN PORTAL:
   Login URL: http://127.0.0.1:5000/admin/login
   Demo Email: admin@nandn.local
   Demo Password: AdminPass@999
   Accesses: Platform Administration, Users & Directory Management (Admin only)

5. PORTALS GATEWAY (All Portals in one place):
   URL: http://127.0.0.1:5000/portals (or /login)

IMPORTANT
- This is local by default. Deploy with HTTPS and production WSGI before public hosting.
- Data is stored in nandn.db. Back up this file regularly.
- Replace demo credentials before public deployment.

CREDITS
Developed by: NandN Associates
NandN International
