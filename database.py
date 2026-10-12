import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'canemart.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Admin / Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'admin',
        pin TEXT DEFAULT '1234',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Suppliers (Sugarcane Farmers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT,
        village TEXT,
        farm_area_acres REAL DEFAULT 0,
        cane_variety TEXT,
        bank_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Customers (Animal Feed Buyers, Sugar Mills, Gur/Jaggery Units, Farmers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT,
        location TEXT,
        customer_type TEXT DEFAULT 'Animal Feed / Dairy',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Transporters
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transport (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_no TEXT NOT NULL,
        driver_name TEXT,
        driver_phone TEXT,
        transport_date TEXT NOT NULL,
        from_location TEXT,
        to_location TEXT,
        quantity REAL DEFAULT 0,
        freight_amount REAL DEFAULT 0,
        paid_freight REAL DEFAULT 0,
        freight_status TEXT DEFAULT 'Pending',
        trip_status TEXT DEFAULT 'Delivered',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Sugarcane Purchases (From Farmers / Suppliers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        supplier_name TEXT NOT NULL,
        purchase_date TEXT NOT NULL,
        variety TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'Tons',
        rate_per_unit REAL NOT NULL,
        total_amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0,
        remaining_amount REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'Unpaid',
        vehicle_no TEXT,
        weighbridge_slip_no TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
    )
    ''')

    # Sugarcane Sales (To Buyer Farmers for Animal Feed / Mills / Buyers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        sale_date TEXT NOT NULL,
        variety TEXT NOT NULL,
        purpose TEXT DEFAULT 'Animal Feed',
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'Tons',
        rate_per_unit REAL NOT NULL,
        total_amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0,
        remaining_amount REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'Unpaid',
        transport_id INTEGER,
        vehicle_no TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
        FOREIGN KEY (transport_id) REFERENCES transport(id) ON DELETE SET NULL
    )
    ''')

    # Payment Records (Transactions Ledger)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_type TEXT NOT NULL, -- 'supplier_payment' (we paid supplier) or 'customer_receipt' (customer paid us)
        party_type TEXT NOT NULL, -- 'supplier' or 'customer'
        party_id INTEGER NOT NULL,
        party_name TEXT NOT NULL,
        purchase_id INTEGER,
        sale_id INTEGER,
        payment_date TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_mode TEXT DEFAULT 'Cash', -- Cash, UPI, Bank Transfer, Cheque
        reference_no TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE SET NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE SET NULL
    )
    ''')

    # Employees
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        designation TEXT DEFAULT 'Field Staff',
        salary_type TEXT DEFAULT 'Monthly',
        daily_wage_or_salary REAL DEFAULT 0,
        total_leaves INTEGER DEFAULT 0,
        total_paid REAL DEFAULT 0,
        pending_amount REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Employee Attendance
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employee_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Present', -- Present, Absent, Half Day, Leave
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(employee_id, attendance_date),
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (name, mobile, role, pin)
            VALUES ('Ramesh Patil (Trader)', '9876543210', 'admin', '1234')
        ''')

    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        # Prepopulate sample sugarcane farmers
        suppliers_data = [
            ('Shivaji Shinde', '9822011223', 'Baramati, Pune', 12.5, 'Co 86032', 'SBI A/C: 38291048291'),
            ('Balasaheb Jadhav', '9765432101', 'Phaltan, Satara', 8.0, 'Co 0238', 'HDFC A/C: 50100234812'),
            ('Anand Pawar', '9423187654', 'Indapur, Pune', 15.0, 'Co 0118', 'Bank of Maharashtra A/C: 20048192837'),
            ('Sunil More', '9158334455', 'Pandharpur, Solapur', 6.5, 'Co 09022', 'CBI A/C: 49201948271')
        ]
        cursor.executemany('''
            INSERT INTO suppliers (name, mobile, village, farm_area_acres, cane_variety, bank_details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', suppliers_data)

    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        # Prepopulate sample buyers / dairy farmers / animal feed buyers
        customers_data = [
            ('Gokul Dairy & Cattle Farm', '9890123456', 'Kolhapur', 'Animal Feed / Dairy', 'Regular buyer for cattle green fodder & cane tops'),
            ('Shree Gur & Jaggery Udyog', '9766554433', 'Shirur', 'Jaggery / Gur Unit', 'High brix sugarcane buyer'),
            ('Chhatrapati Sugar Mill Yard', '9850987654', 'Bhor', 'Sugar Mill', 'Factory procurement gate'),
            ('Kisan Gaushala & Dairy', '9403215678', 'Ahmednagar', 'Animal Feed / Dairy', 'Bulk order for dairy silage & fodder'),
            ('Mahesh Deshmukh (Fodder Trader)', '9921443322', 'Nashik', 'Animal Feed / Dairy', 'Weekly 20 tons fodder transport')
        ]
        cursor.executemany('''
            INSERT INTO customers (name, mobile, location, customer_type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', customers_data)

    cursor.execute("SELECT COUNT(*) FROM transport")
    if cursor.fetchone()[0] == 0:
        transport_data = [
            ('MH-12-RN-4589', 'Tukaram Mane', '9823456711', date.today().strftime('%Y-%m-%d'), 'Baramati', 'Kolhapur Dairy', 24.5, 4500, 4500, 'Paid', 'Delivered', 'Eicher 14 Wheeler'),
            ('MH-11-AX-9021', 'Ganesh Kadam', '9763219088', date.today().strftime('%Y-%m-%d'), 'Phaltan', 'Shirur Gur Yard', 18.2, 3200, 2000, 'Partial', 'Delivered', 'Tata 407 Heavy'),
            ('MH-42-B-3312', 'Vikas Gaikwad', '9970112233', date.today().strftime('%Y-%m-%d'), 'Indapur', 'Ahmednagar Gaushala', 22.0, 4000, 4000, 'Paid', 'Delivered', 'Mahindra Blazo')
        ]
        cursor.executemany('''
            INSERT INTO transport (vehicle_no, driver_name, driver_phone, transport_date, from_location, to_location, quantity, freight_amount, paid_freight, freight_status, trip_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', transport_data)

    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        employees_data = [
            ('Santosh Kadam', '9890887766', 'Weighbridge & Field Supervisor', 'Monthly', 18000, 1, 15000, 3000),
            ('Datta Shinde', '9765112244', 'Cane Cutting & Loading Manager', 'Monthly', 16000, 0, 16000, 0),
            ('Rahul Shirsat', '9421998877', 'Accounts & Weighment Operator', 'Monthly', 15000, 2, 12000, 3000)
        ]
        cursor.executemany('''
            INSERT INTO employees (name, phone, designation, salary_type, daily_wage_or_salary, total_leaves, total_paid, pending_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', employees_data)

    cursor.execute("SELECT COUNT(*) FROM purchases")
    if cursor.fetchone()[0] == 0:
        today_str = date.today().strftime('%Y-%m-%d')
        purchases_data = [
            ('PUR-2026-001', 1, 'Shivaji Shinde', today_str, 'Co 86032', 25.5, 'Tons', 3150.0, 80325.0, 60000.0, 20325.0, 'Partial', 'MH-12-RN-4589', 'WB-8921', 'Fresh first cut ratoon'),
            ('PUR-2026-002', 2, 'Balasaheb Jadhav', today_str, 'Co 0238', 18.0, 'Tons', 3200.0, 57600.0, 57600.0, 0.0, 'Paid', 'MH-11-AX-9021', 'WB-8922', 'Plant cane high sucrose'),
            ('PUR-2026-003', 3, 'Anand Pawar', today_str, 'Co 0118', 22.0, 'Tons', 3100.0, 68200.0, 40000.0, 28200.0, 'Partial', 'MH-42-B-3312', 'WB-8923', 'Clean bundled cane')
        ]
        cursor.executemany('''
            INSERT INTO purchases (bill_no, supplier_id, supplier_name, purchase_date, variety, quantity, unit, rate_per_unit, total_amount, paid_amount, remaining_amount, payment_status, vehicle_no, weighbridge_slip_no, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', purchases_data)

    cursor.execute("SELECT COUNT(*) FROM sales")
    if cursor.fetchone()[0] == 0:
        today_str = date.today().strftime('%Y-%m-%d')
        sales_data = [
            ('INV-2026-001', 1, 'Gokul Dairy & Cattle Farm', today_str, 'Co 86032', 'Animal Feed', 24.5, 'Tons', 3550.0, 86975.0, 70000.0, 16975.0, 'Partial', 1, 'MH-12-RN-4589', 'Sold for dairy cattle green fodder'),
            ('INV-2026-002', 2, 'Shree Gur & Jaggery Udyog', today_str, 'Co 0238', 'Jaggery Making', 18.0, 'Tons', 3600.0, 64800.0, 64800.0, 0.0, 'Paid', 2, 'MH-11-AX-9021', 'Direct supply for organic jaggery plant'),
            ('INV-2026-003', 4, 'Kisan Gaushala & Dairy', today_str, 'Co 0118', 'Animal Feed', 15.0, 'Tons', 3500.0, 52500.0, 30000.0, 22500.0, 'Partial', 3, 'MH-42-B-3312', 'Chopped fodder cane tops for animal feed')
        ]
        cursor.executemany('''
            INSERT INTO sales (invoice_no, customer_id, customer_name, sale_date, variety, purpose, quantity, unit, rate_per_unit, total_amount, paid_amount, remaining_amount, payment_status, transport_id, vehicle_no, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sales_data)

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("CaneMart Database initialized successfully!")
