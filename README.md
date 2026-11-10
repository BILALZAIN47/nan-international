# nan-international

NandN International — Premier Textile Directory & Multi-Role Commerce Portal

## Overview
A comprehensive digital marketplace and directory for over 500 bedsheet, blanket, and textile businesses across Faisalabad and Punjab, Pakistan.

## Multi-Role Architecture
1. **Buyer Portal (`/buyer/login`)**:
   - Browse 500+ verified textile storefronts, search products, filter by market area, check live in-stock inventory, and contact merchants directly.
   - Demo Credentials: `buyer@nandn.local` / `BuyerPass@123`

2. **Seller & Merchant Portal (`/seller/login`)**:
   - Digital storefront management: edit business profile, list bedsheets/blankets, and manage shop catalog stock.
   - Demo Credentials: `seller@nandn.local` / `SellerPass@456`

3. **Central Inventory Control Room (`/inventory/login`)**:
   - Warehouse-level stock governance, inbound shipment intake logging, live quantity updates, and automated low-stock/out-of-stock alerts.
   - Demo Credentials: `inventory@nandn.local` / `InventoryPass@789`

4. **Super Admin Dashboard (`/admin/login`)**:
   - System governance, registered user management, shop registry audits.
   - Demo Credentials: `admin@nandn.local` / `AdminPass@999`

5. **Central Portals Gateway (`/portals` or `/login`)**:
   - Master portal selector for all roles.

## Quick Start on Windows
1. Make sure Python 3.10+ is installed with `Add Python to PATH`.
2. Double-click `run_windows.bat` or run:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
3. Open http://127.0.0.1:5000 in your web browser.

## Credits
- Developed by: **NandN Associates**
- Company: **NandN International**
