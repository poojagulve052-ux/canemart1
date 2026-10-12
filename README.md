# 🌾 CaneMart - Sugarcane Management Platform

**CaneMart** is a modern, mobile-friendly web application designed for sugarcane businessmen and traders to manage sugarcane procurement from farmers (suppliers), sales to buyers (including animal feed / dairy fodder and sugar factories), financial transactions, transport logistics, and employees—with one-click Excel downloads.

Based on the **CaneMart ER Diagram & DFD Architecture**:
- **ER Entities**: Sugarcane Purchase & Sale, Farmers (Suppliers), Buyers (Animal Feed / Mills), Employees, Admin/Trader, Transporters.
- **Data Stores**: D1 Employees, D2 Purchase Records, D3 Sale Records, D4 Payment Records, D5 Transport Records.

---

## 🚀 Key Features

### 1. 📱 Mobile-First Responsive Design
- Optimized for mobile smartphones (Android & iOS) with app-style bottom navigation and quick-touch cards.
- **Wi-Fi Phone Sync**: View your local network IP and scan the on-screen **QR Code** to access CaneMart instantly on your mobile phone without installing an app!

### 2. 👨‍🌾 Supplier (Sugarcane Farmer) Management
- Register sugarcane farmers with village, phone number, farm acreage, cane varieties (e.g., Co 86032, Co 0238, Co 0118), and bank/UPI details.
- Comprehensive individual **Farmer Ledger** showing all historical deliveries, total tons supplied, payouts, and pending payable balance.

### 3. 🐄 Customer (Buyer & Animal Feed / Dairy) Management
- Add customers categorized into **Animal Feed / Dairy Farm**, **Sugar Mill**, **Jaggery / Gur Unit**, and **Fodder Traders**.
- Track total cane purchased, turnover billed, payment received, and outstanding receivables.

### 4. ⚖️ Sugarcane Purchases (Procurement)
- Record cane purchases with real-time auto-calculation:
  $$\text{Total Amount} = \text{Quantity (Tons)} \times \text{Rate per Ton}$$
  $$\text{Balance Due} = \text{Total Amount} - \text{Advance Paid}$$
- Record weighbridge slip numbers, vehicle numbers, cane variety, and payment status (Paid, Partial, Unpaid).
- Generate **Printable & WhatsApp-Shareable Purchase Bills**.

### 5. 🚛 Sugarcane Sales & Animal Feed Supply
- Dispatch cane to animal feed cattle farms, dairy silage producers, or sugar factories.
- Real-time billing and automatic remaining balance calculation.
- Generate **Printable & WhatsApp-Shareable Sale Invoices** with 1-click share directly to the customer's phone!

### 6. 📊 Excel Data Export (Download Data in Excel)
- **Master Audit Workbook (.xlsx)**: Multi-sheet consolidated Excel file containing Executive Summary, Farmer Ledger, Customer Ledger, Purchases, and Sales.
- **Purchases Excel Sheet (.xlsx)**: Full procurement records with totals and formulas.
- **Sales Excel Sheet (.xlsx)**: Full sales and fodder distribution records.

### 7. 💳 Payment Ledger & Cashbook
- Record customer receipts and farmer payouts.
- Supports **Cash**, **UPI (GPay / PhonePe / Paytm)**, **Bank Transfer (NEFT/RTGS)**, and **Cheque**.
- Automatically applies installment payments to settle the oldest pending bills.

### 8. 🚚 Logistics & Transporters (DFD D5)
- Record transport vehicles, driver names, phone numbers, trip routes (From Field $\rightarrow$ To Buyer), freight amounts, and payment status.

### 9. 👷 Staff & Attendance (DFD D1)
- Manage field supervisors, weighbridge operators, and cane harvesters.
- **1-Click Attendance Toggle**: Mark Present, Half Day, Absent, or Leave directly on mobile.
- Wage and pending salary tracking.

---

## 🛠️ How to Run CaneMart

### Option 1: One-Click Launch (Windows)
Double-click `run_canemart.bat` in the project folder.

### Option 2: Command Line
1. Open PowerShell or Terminal in `c:\Users\pc\Desktop\canemart`:
```powershell
python app.py
```
2. Open your web browser:
- **On this computer**: `http://127.0.0.1:5000`
- **On your mobile phone**: Open Wi-Fi, connect to the same network, and scan the QR code in the app header or navigate to `http://<your-ip>:5000`.

---

## 📁 Project Structure

```
canemart/
├── app.py                  # Core Flask web server & REST API
├── database.py             # SQLite database init, schema, migrations & seed data
├── excel_export.py         # Openpyxl Excel export engine (formatted with totals & styles)
├── canemart.db             # SQLite local database
├── run_canemart.bat        # Windows 1-click launcher
├── templates/
│   ├── base.html           # Responsive layout, mobile drawer, bottom tabs & QR modal
│   ├── index.html          # Executive Dashboard & analytics
│   ├── purchases.html      # Sugarcane procurement records & auto-calculating modal
│   ├── sales.html          # Cane sales / animal feed supply & modal
│   ├── suppliers.html      # Sugarcane farmers directory & cards
│   ├── supplier_detail.html# Individual farmer statement & ledger
│   ├── customers.html      # Buyers directory (Animal Feed / Mills)
│   ├── customer_detail.html# Individual buyer statement & ledger
│   ├── payments.html       # Financial cashbook & payments ledger
│   ├── transport.html      # Transporter & vehicle trips (DFD D5)
│   ├── employees.html      # Staff directory & daily attendance (DFD D1)
│   ├── receipt.html        # Official printable & WhatsApp-ready invoice slip
│   └── reports.html        # Excel reports & downloads hub
├── static/
│   ├── css/style.css       # Custom styles & print formatting
│   └── js/app.js           # Client-side helpers & Indian Rupee formatting
└── README.md
```
