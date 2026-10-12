import os
import socket
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from database import init_db, get_connection
import excel_export

app = Flask(__name__)
app.secret_key = 'canemart-secret-key-2026'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# Context processor to make local IP and current year available to all templates
@app.context_processor
def inject_global_data():
    return {
        'local_ip': get_local_ip(),
        'port': 5000,
        'current_year': datetime.now().year,
        'today_date': date.today().strftime('%Y-%m-%d')
    }

# ----------------- DASHBOARD -----------------
@app.route('/')
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    # Total Purchases
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(total_amount), 0) AS total_amt,
            COALESCE(SUM(paid_amount), 0) AS paid_amt,
            COALESCE(SUM(remaining_amount), 0) AS rem_amt,
            COUNT(*) AS total_count
        FROM purchases
    ''')
    pur_stat = cursor.fetchone()

    # Total Sales
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(total_amount), 0) AS total_amt,
            COALESCE(SUM(paid_amount), 0) AS paid_amt,
            COALESCE(SUM(remaining_amount), 0) AS rem_amt,
            COUNT(*) AS total_count
        FROM sales
    ''')
    sale_stat = cursor.fetchone()

    # Counts
    cursor.execute('SELECT COUNT(*) FROM suppliers')
    supplier_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM customers')
    customer_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM transport')
    transport_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM employees')
    employee_count = cursor.fetchone()[0]

    # Current Stock in Hand (Purchased - Sold)
    current_stock = max(0.0, round(float(pur_stat['total_qty']) - float(sale_stat['total_qty']), 2))
    gross_margin = round(float(sale_stat['total_amt']) - float(pur_stat['total_amt']), 2)

    # Recent Purchases
    cursor.execute('''
        SELECT id, bill_no, supplier_name, purchase_date, variety, quantity, unit, total_amount, paid_amount, remaining_amount, payment_status
        FROM purchases
        ORDER BY purchase_date DESC, id DESC LIMIT 5
    ''')
    recent_purchases = cursor.fetchall()

    # Recent Sales
    cursor.execute('''
        SELECT id, invoice_no, customer_name, sale_date, variety, purpose, quantity, unit, total_amount, paid_amount, remaining_amount, payment_status
        FROM sales
        ORDER BY sale_date DESC, id DESC LIMIT 5
    ''')
    recent_sales = cursor.fetchall()

    # Variety breakdown
    cursor.execute('''
        SELECT variety, COALESCE(SUM(quantity), 0) as total_qty
        FROM purchases
        GROUP BY variety
        ORDER BY total_qty DESC LIMIT 5
    ''')
    variety_breakdown = cursor.fetchall()

    conn.close()

    return render_template('index.html',
        pur_stat=pur_stat,
        sale_stat=sale_stat,
        current_stock=current_stock,
        gross_margin=gross_margin,
        supplier_count=supplier_count,
        customer_count=customer_count,
        transport_count=transport_count,
        employee_count=employee_count,
        recent_purchases=recent_purchases,
        recent_sales=recent_sales,
        variety_breakdown=variety_breakdown
    )

# ----------------- SUPPLIERS (FARMERS) -----------------
@app.route('/suppliers')
def suppliers_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, 
               COALESCE(SUM(p.quantity), 0) AS total_supplied_qty,
               COALESCE(SUM(p.total_amount), 0) AS total_bill_amt,
               COALESCE(SUM(p.paid_amount), 0) AS total_paid_amt,
               COALESCE(SUM(p.remaining_amount), 0) AS total_balance_due
        FROM suppliers s
        LEFT JOIN purchases p ON s.id = p.supplier_id
        GROUP BY s.id
        ORDER BY s.id DESC
    ''')
    suppliers = cursor.fetchall()
    conn.close()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile', '').strip()
    village = request.form.get('village', '').strip()
    farm_area = float(request.form.get('farm_area_acres') or 0)
    cane_variety = request.form.get('cane_variety', '').strip()
    bank_details = request.form.get('bank_details', '').strip()

    if not name:
        flash('Farmer / Supplier name is required.', 'danger')
        return redirect(url_for('suppliers_list'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO suppliers (name, mobile, village, farm_area_acres, cane_variety, bank_details)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, mobile, village, farm_area, cane_variety, bank_details))
    conn.commit()
    conn.close()

    flash(f'Farmer "{name}" registered successfully!', 'success')
    return redirect(url_for('suppliers_list'))

@app.route('/suppliers/<int:supplier_id>')
def supplier_detail(supplier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM suppliers WHERE id = ?', (supplier_id,))
    supplier = cursor.fetchone()
    if not supplier:
        conn.close()
        flash('Farmer not found.', 'danger')
        return redirect(url_for('suppliers_list'))

    # Purchases ledger for this supplier
    cursor.execute('''
        SELECT * FROM purchases
        WHERE supplier_id = ?
        ORDER BY purchase_date DESC, id DESC
    ''', (supplier_id,))
    purchases = cursor.fetchall()

    # Payments ledger
    cursor.execute('''
        SELECT * FROM payments
        WHERE party_type = 'supplier' AND party_id = ?
        ORDER BY payment_date DESC, id DESC
    ''', (supplier_id,))
    payments = cursor.fetchall()

    # Summary
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(total_amount), 0) AS total_amt,
            COALESCE(SUM(paid_amount), 0) AS total_paid,
            COALESCE(SUM(remaining_amount), 0) AS total_pending
        FROM purchases
        WHERE supplier_id = ?
    ''', (supplier_id,))
    summary = cursor.fetchone()

    conn.close()
    return render_template('supplier_detail.html', supplier=supplier, purchases=purchases, payments=payments, summary=summary)

@app.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM suppliers WHERE id = ?', (supplier_id,))
    conn.commit()
    conn.close()
    flash('Farmer record deleted.', 'info')
    return redirect(url_for('suppliers_list'))

# ----------------- CUSTOMERS (BUYERS / ANIMAL FEED) -----------------
@app.route('/customers')
def customers_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*,
               COALESCE(SUM(s.quantity), 0) AS total_bought_qty,
               COALESCE(SUM(s.total_amount), 0) AS total_bill_amt,
               COALESCE(SUM(s.paid_amount), 0) AS total_paid_amt,
               COALESCE(SUM(s.remaining_amount), 0) AS total_balance_due
        FROM customers c
        LEFT JOIN sales s ON c.id = s.customer_id
        GROUP BY c.id
        ORDER BY c.id DESC
    ''')
    customers = cursor.fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['POST'])
def add_customer():
    name = request.form.get('name', '').strip()
    mobile = request.form.get('mobile', '').strip()
    location = request.form.get('location', '').strip()
    customer_type = request.form.get('customer_type', 'Animal Feed / Dairy').strip()
    notes = request.form.get('notes', '').strip()

    if not name:
        flash('Customer name is required.', 'danger')
        return redirect(url_for('customers_list'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO customers (name, mobile, location, customer_type, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, mobile, location, customer_type, notes))
    conn.commit()
    conn.close()

    flash(f'Customer "{name}" added successfully!', 'success')
    return redirect(url_for('customers_list'))

@app.route('/customers/<int:customer_id>')
def customer_detail(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        conn.close()
        flash('Customer not found.', 'danger')
        return redirect(url_for('customers_list'))

    # Sales ledger
    cursor.execute('''
        SELECT * FROM sales
        WHERE customer_id = ?
        ORDER BY sale_date DESC, id DESC
    ''', (customer_id,))
    sales = cursor.fetchall()

    # Payments ledger
    cursor.execute('''
        SELECT * FROM payments
        WHERE party_type = 'customer' AND party_id = ?
        ORDER BY payment_date DESC, id DESC
    ''', (customer_id,))
    payments = cursor.fetchall()

    # Summary
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(total_amount), 0) AS total_amt,
            COALESCE(SUM(paid_amount), 0) AS total_paid,
            COALESCE(SUM(remaining_amount), 0) AS total_pending
        FROM sales
        WHERE customer_id = ?
    ''', (customer_id,))
    summary = cursor.fetchone()

    conn.close()
    return render_template('customer_detail.html', customer=customer, sales=sales, payments=payments, summary=summary)

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()
    flash('Customer record deleted.', 'info')
    return redirect(url_for('customers_list'))

# ----------------- PURCHASES (FARMER PROCUREMENT) -----------------
@app.route('/purchases')
def purchases_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, s.mobile as supplier_mobile, s.village as supplier_village
        FROM purchases p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        ORDER BY p.purchase_date DESC, p.id DESC
    ''')
    purchases = cursor.fetchall()

    cursor.execute('SELECT id, name, village FROM suppliers ORDER BY name ASC')
    suppliers = cursor.fetchall()

    # Totals
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) as total_qty,
            COALESCE(SUM(total_amount), 0) as total_amt,
            COALESCE(SUM(paid_amount), 0) as total_paid,
            COALESCE(SUM(remaining_amount), 0) as total_rem
        FROM purchases
    ''')
    stats = cursor.fetchone()

    conn.close()
    return render_template('purchases.html', purchases=purchases, suppliers=suppliers, stats=stats)

@app.route('/purchases/add', methods=['POST'])
def add_purchase():
    supplier_id_raw = request.form.get('supplier_id')
    new_farmer_name = request.form.get('new_farmer_name', '').strip()
    purchase_date = request.form.get('purchase_date') or date.today().strftime('%Y-%m-%d')
    variety = request.form.get('variety', 'Co 86032').strip()
    quantity = float(request.form.get('quantity') or 0)
    unit = request.form.get('unit', 'Tons').strip()
    rate_per_unit = float(request.form.get('rate_per_unit') or 0)
    paid_amount = float(request.form.get('paid_amount') or 0)
    vehicle_no = request.form.get('vehicle_no', '').strip()
    weighbridge_slip_no = request.form.get('weighbridge_slip_no', '').strip()
    notes = request.form.get('notes', '').strip()

    total_amount = round(quantity * rate_per_unit, 2)
    remaining_amount = max(0.0, round(total_amount - paid_amount, 2))

    if remaining_amount == 0 and total_amount > 0:
        payment_status = 'Paid'
    elif paid_amount > 0:
        payment_status = 'Partial'
    else:
        payment_status = 'Unpaid'

    conn = get_connection()
    cursor = conn.cursor()

    # Determine supplier
    supplier_id = None
    supplier_name = ''
    if supplier_id_raw and supplier_id_raw != 'new':
        supplier_id = int(supplier_id_raw)
        cursor.execute('SELECT name FROM suppliers WHERE id = ?', (supplier_id,))
        row = cursor.fetchone()
        if row:
            supplier_name = row['name']
    elif new_farmer_name:
        farmer_mobile = request.form.get('new_farmer_mobile', '').strip()
        farmer_village = request.form.get('new_farmer_village', '').strip()
        cursor.execute('''
            INSERT INTO suppliers (name, mobile, village, cane_variety)
            VALUES (?, ?, ?, ?)
        ''', (new_farmer_name, farmer_mobile, farmer_village, variety))
        supplier_id = cursor.lastrowid
        supplier_name = new_farmer_name

    if not supplier_name:
        conn.close()
        flash('Please select or enter a farmer name.', 'danger')
        return redirect(url_for('purchases_list'))

    # Generate Bill No
    cursor.execute('SELECT COUNT(*) FROM purchases')
    p_count = cursor.fetchone()[0] + 1
    bill_no = f"PUR-{datetime.now().strftime('%Y%m')}-{p_count:04d}"

    cursor.execute('''
        INSERT INTO purchases (
            bill_no, supplier_id, supplier_name, purchase_date, variety,
            quantity, unit, rate_per_unit, total_amount, paid_amount,
            remaining_amount, payment_status, vehicle_no, weighbridge_slip_no, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        bill_no, supplier_id, supplier_name, purchase_date, variety,
        quantity, unit, rate_per_unit, total_amount, paid_amount,
        remaining_amount, payment_status, vehicle_no, weighbridge_slip_no, notes
    ))
    purchase_id = cursor.lastrowid

    # If paid amount > 0, log in payments table
    if paid_amount > 0:
        payment_mode = request.form.get('payment_mode', 'Cash')
        cursor.execute('''
            INSERT INTO payments (
                payment_type, party_type, party_id, party_name,
                purchase_id, payment_date, amount, payment_mode, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'supplier_payment', 'supplier', supplier_id or 0, supplier_name,
            purchase_id, purchase_date, paid_amount, payment_mode, f"Initial payment for {bill_no}"
        ))

    conn.commit()
    conn.close()

    flash(f'Sugarcane purchase bill {bill_no} recorded successfully!', 'success')
    return redirect(url_for('purchases_list'))

@app.route('/purchases/delete/<int:purchase_id>', methods=['POST'])
def delete_purchase(purchase_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM purchases WHERE id = ?', (purchase_id,))
    conn.commit()
    conn.close()
    flash('Purchase record removed.', 'info')
    return redirect(url_for('purchases_list'))

# ----------------- SALES (ANIMAL FEED / MILLS / CUSTOMERS) -----------------
@app.route('/sales')
def sales_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, c.mobile as customer_mobile, c.location as customer_location, c.customer_type
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        ORDER BY s.sale_date DESC, s.id DESC
    ''')
    sales = cursor.fetchall()

    cursor.execute('SELECT id, name, customer_type, location FROM customers ORDER BY name ASC')
    customers = cursor.fetchall()

    cursor.execute('SELECT id, vehicle_no, driver_name FROM transport ORDER BY id DESC')
    transporters = cursor.fetchall()

    # Totals
    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) as total_qty,
            COALESCE(SUM(total_amount), 0) as total_amt,
            COALESCE(SUM(paid_amount), 0) as total_paid,
            COALESCE(SUM(remaining_amount), 0) as total_rem
        FROM sales
    ''')
    stats = cursor.fetchone()

    conn.close()
    return render_template('sales.html', sales=sales, customers=customers, transporters=transporters, stats=stats)

@app.route('/sales/add', methods=['POST'])
def add_sale():
    customer_id_raw = request.form.get('customer_id')
    new_customer_name = request.form.get('new_customer_name', '').strip()
    sale_date = request.form.get('sale_date') or date.today().strftime('%Y-%m-%d')
    variety = request.form.get('variety', 'Co 86032').strip()
    purpose = request.form.get('purpose', 'Animal Feed').strip()
    quantity = float(request.form.get('quantity') or 0)
    unit = request.form.get('unit', 'Tons').strip()
    rate_per_unit = float(request.form.get('rate_per_unit') or 0)
    paid_amount = float(request.form.get('paid_amount') or 0)
    transport_id = int(request.form.get('transport_id')) if request.form.get('transport_id') else None
    vehicle_no = request.form.get('vehicle_no', '').strip()
    notes = request.form.get('notes', '').strip()

    total_amount = round(quantity * rate_per_unit, 2)
    remaining_amount = max(0.0, round(total_amount - paid_amount, 2))

    if remaining_amount == 0 and total_amount > 0:
        payment_status = 'Paid'
    elif paid_amount > 0:
        payment_status = 'Partial'
    else:
        payment_status = 'Unpaid'

    conn = get_connection()
    cursor = conn.cursor()

    # Determine customer
    customer_id = None
    customer_name = ''
    if customer_id_raw and customer_id_raw != 'new':
        customer_id = int(customer_id_raw)
        cursor.execute('SELECT name FROM customers WHERE id = ?', (customer_id,))
        row = cursor.fetchone()
        if row:
            customer_name = row['name']
    elif new_customer_name:
        cust_mobile = request.form.get('new_customer_mobile', '').strip()
        cust_location = request.form.get('new_customer_location', '').strip()
        cust_type = request.form.get('new_customer_type', 'Animal Feed / Dairy').strip()
        cursor.execute('''
            INSERT INTO customers (name, mobile, location, customer_type)
            VALUES (?, ?, ?, ?)
        ''', (new_customer_name, cust_mobile, cust_location, cust_type))
        customer_id = cursor.lastrowid
        customer_name = new_customer_name

    if not customer_name:
        conn.close()
        flash('Please select or specify customer name.', 'danger')
        return redirect(url_for('sales_list'))

    # Generate Invoice No
    cursor.execute('SELECT COUNT(*) FROM sales')
    s_count = cursor.fetchone()[0] + 1
    invoice_no = f"INV-{datetime.now().strftime('%Y%m')}-{s_count:04d}"

    cursor.execute('''
        INSERT INTO sales (
            invoice_no, customer_id, customer_name, sale_date, variety,
            purpose, quantity, unit, rate_per_unit, total_amount,
            paid_amount, remaining_amount, payment_status, transport_id, vehicle_no, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        invoice_no, customer_id, customer_name, sale_date, variety,
        purpose, quantity, unit, rate_per_unit, total_amount,
        paid_amount, remaining_amount, payment_status, transport_id, vehicle_no, notes
    ))
    sale_id = cursor.lastrowid

    # If initial payment received, log in payments ledger
    if paid_amount > 0:
        payment_mode = request.form.get('payment_mode', 'Cash')
        cursor.execute('''
            INSERT INTO payments (
                payment_type, party_type, party_id, party_name,
                sale_id, payment_date, amount, payment_mode, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'customer_receipt', 'customer', customer_id or 0, customer_name,
            sale_id, sale_date, paid_amount, payment_mode, f"Payment for {invoice_no}"
        ))

    conn.commit()
    conn.close()

    flash(f'Sugarcane sale invoice {invoice_no} created successfully!', 'success')
    return redirect(url_for('sales_list'))

@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
    conn.commit()
    conn.close()
    flash('Sale invoice deleted.', 'info')
    return redirect(url_for('sales_list'))

# ----------------- PAYMENTS LEDGER -----------------
@app.route('/payments')
def payments_ledger():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM payments ORDER BY payment_date DESC, id DESC')
    payments = cursor.fetchall()

    cursor.execute('SELECT id, name, village FROM suppliers ORDER BY name ASC')
    suppliers = cursor.fetchall()

    cursor.execute('SELECT id, name, location FROM customers ORDER BY name ASC')
    customers = cursor.fetchall()

    # Total collected vs total paid out
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_type = 'customer_receipt'")
    total_received = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_type = 'supplier_payment'")
    total_paid_out = cursor.fetchone()[0]

    conn.close()
    return render_template('payments.html', payments=payments, suppliers=suppliers, customers=customers, total_received=total_received, total_paid_out=total_paid_out)

@app.route('/payments/add', methods=['POST'])
def add_payment():
    payment_type = request.form.get('payment_type') # 'customer_receipt' or 'supplier_payment'
    amount = float(request.form.get('amount') or 0)
    payment_date = request.form.get('payment_date') or date.today().strftime('%Y-%m-%d')
    payment_mode = request.form.get('payment_mode', 'Cash')
    reference_no = request.form.get('reference_no', '').strip()
    notes = request.form.get('notes', '').strip()

    if amount <= 0:
        flash('Payment amount must be greater than 0.', 'danger')
        return redirect(url_for('payments_ledger'))

    conn = get_connection()
    cursor = conn.cursor()

    if payment_type == 'customer_receipt':
        customer_id = int(request.form.get('customer_id'))
        cursor.execute('SELECT name FROM customers WHERE id = ?', (customer_id,))
        c_row = cursor.fetchone()
        party_name = c_row['name'] if c_row else 'Customer'

        cursor.execute('''
            INSERT INTO payments (
                payment_type, party_type, party_id, party_name,
                payment_date, amount, payment_mode, reference_no, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'customer_receipt', 'customer', customer_id, party_name,
            payment_date, amount, payment_mode, reference_no, notes
        ))

        # Update remaining amounts of oldest unpaid sales for this customer
        rem_to_apply = amount
        cursor.execute('''
            SELECT id, remaining_amount, paid_amount, total_amount
            FROM sales
            WHERE customer_id = ? AND remaining_amount > 0
            ORDER BY sale_date ASC, id ASC
        ''', (customer_id,))
        unpaid_sales = cursor.fetchall()
        for s in unpaid_sales:
            if rem_to_apply <= 0:
                break
            pay_for_this = min(rem_to_apply, s['remaining_amount'])
            new_rem = round(s['remaining_amount'] - pay_for_this, 2)
            new_paid = round(s['paid_amount'] + pay_for_this, 2)
            status = 'Paid' if new_rem == 0 else 'Partial'
            cursor.execute('''
                UPDATE sales
                SET remaining_amount = ?, paid_amount = ?, payment_status = ?
                WHERE id = ?
            ''', (new_rem, new_paid, status, s['id']))
            rem_to_apply -= pay_for_this

    else: # supplier_payment
        supplier_id = int(request.form.get('supplier_id'))
        cursor.execute('SELECT name FROM suppliers WHERE id = ?', (supplier_id,))
        s_row = cursor.fetchone()
        party_name = s_row['name'] if s_row else 'Farmer'

        cursor.execute('''
            INSERT INTO payments (
                payment_type, party_type, party_id, party_name,
                payment_date, amount, payment_mode, reference_no, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'supplier_payment', 'supplier', supplier_id, party_name,
            payment_date, amount, payment_mode, reference_no, notes
        ))

        # Update remaining amounts of oldest unpaid purchases
        rem_to_apply = amount
        cursor.execute('''
            SELECT id, remaining_amount, paid_amount, total_amount
            FROM purchases
            WHERE supplier_id = ? AND remaining_amount > 0
            ORDER BY purchase_date ASC, id ASC
        ''', (supplier_id,))
        unpaid_purchases = cursor.fetchall()
        for p in unpaid_purchases:
            if rem_to_apply <= 0:
                break
            pay_for_this = min(rem_to_apply, p['remaining_amount'])
            new_rem = round(p['remaining_amount'] - pay_for_this, 2)
            new_paid = round(p['paid_amount'] + pay_for_this, 2)
            status = 'Paid' if new_rem == 0 else 'Partial'
            cursor.execute('''
                UPDATE purchases
                SET remaining_amount = ?, paid_amount = ?, payment_status = ?
                WHERE id = ?
            ''', (new_rem, new_paid, status, p['id']))
            rem_to_apply -= pay_for_this

    conn.commit()
    conn.close()

    flash(f'Payment of ₹{amount:,.2f} recorded and balance adjusted successfully!', 'success')
    return redirect(url_for('payments_ledger'))

# ----------------- TRANSPORTERS & LOGISTICS (DFD D5) -----------------
@app.route('/transport')
def transport_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transport ORDER BY transport_date DESC, id DESC')
    transports = cursor.fetchall()

    cursor.execute('''
        SELECT 
            COUNT(*) as total_trips,
            COALESCE(SUM(freight_amount), 0) as total_freight,
            COALESCE(SUM(paid_freight), 0) as total_paid_freight
        FROM transport
    ''')
    stat = cursor.fetchone()

    conn.close()
    return render_template('transport.html', transports=transports, stat=stat)

@app.route('/transport/add', methods=['POST'])
def add_transport():
    vehicle_no = request.form.get('vehicle_no', '').strip().upper()
    driver_name = request.form.get('driver_name', '').strip()
    driver_phone = request.form.get('driver_phone', '').strip()
    transport_date = request.form.get('transport_date') or date.today().strftime('%Y-%m-%d')
    from_location = request.form.get('from_location', '').strip()
    to_location = request.form.get('to_location', '').strip()
    quantity = float(request.form.get('quantity') or 0)
    freight_amount = float(request.form.get('freight_amount') or 0)
    paid_freight = float(request.form.get('paid_freight') or 0)
    freight_status = 'Paid' if paid_freight >= freight_amount and freight_amount > 0 else ('Partial' if paid_freight > 0 else 'Pending')
    trip_status = request.form.get('trip_status', 'Delivered')
    notes = request.form.get('notes', '').strip()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transport (
            vehicle_no, driver_name, driver_phone, transport_date,
            from_location, to_location, quantity, freight_amount,
            paid_freight, freight_status, trip_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        vehicle_no, driver_name, driver_phone, transport_date,
        from_location, to_location, quantity, freight_amount,
        paid_freight, freight_status, trip_status, notes
    ))
    conn.commit()
    conn.close()

    flash(f'Vehicle {vehicle_no} trip registered successfully!', 'success')
    return redirect(url_for('transport_list'))

# ----------------- EMPLOYEES & ATTENDANCE (DFD D1) -----------------
@app.route('/employees')
def employees_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM employees ORDER BY id ASC')
    employees = cursor.fetchall()

    today_str = date.today().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT ea.*, e.name as employee_name
        FROM employee_attendance ea
        JOIN employees e ON ea.employee_id = e.id
        WHERE ea.attendance_date = ?
    ''', (today_str,))
    today_attendance = {row['employee_id']: row['status'] for row in cursor.fetchall()}

    conn.close()
    return render_template('employees.html', employees=employees, today_attendance=today_attendance)

@app.route('/employees/add', methods=['POST'])
def add_employee():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    designation = request.form.get('designation', 'Field Staff').strip()
    salary_type = request.form.get('salary_type', 'Monthly')
    daily_wage_or_salary = float(request.form.get('daily_wage_or_salary') or 0)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO employees (name, phone, designation, salary_type, daily_wage_or_salary, pending_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, phone, designation, salary_type, daily_wage_or_salary, daily_wage_or_salary))
    conn.commit()
    conn.close()

    flash(f'Employee "{name}" added successfully!', 'success')
    return redirect(url_for('employees_list'))

@app.route('/employees/attendance', methods=['POST'])
def mark_attendance():
    employee_id = int(request.form.get('employee_id'))
    status = request.form.get('status', 'Present')
    att_date = request.form.get('attendance_date') or date.today().strftime('%Y-%m-%d')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO employee_attendance (employee_id, attendance_date, status)
        VALUES (?, ?, ?)
        ON CONFLICT(employee_id, attendance_date) DO UPDATE SET status = excluded.status
    ''', (employee_id, att_date, status))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'status': status})

# ----------------- RECEIPT / INVOICE VIEW (PRINT / WHATSAPP SHARE) -----------------
@app.route('/receipt/purchase/<int:purchase_id>')
def purchase_receipt(purchase_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, s.mobile as supplier_mobile, s.village as supplier_village, s.bank_details
        FROM purchases p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = ?
    ''', (purchase_id,))
    item = cursor.fetchone()
    conn.close()
    if not item:
        flash('Bill not found', 'danger')
        return redirect(url_for('purchases_list'))
    return render_template('receipt.html', item=item, type='purchase')

@app.route('/receipt/sale/<int:sale_id>')
def sale_receipt(sale_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, c.mobile as customer_mobile, c.location as customer_location, c.customer_type
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.id = ?
    ''', (sale_id,))
    item = cursor.fetchone()
    conn.close()
    if not item:
        flash('Invoice not found', 'danger')
        return redirect(url_for('sales_list'))
    return render_template('receipt.html', item=item, type='sale')

# ----------------- EXCEL EXPORTS (DOWNLOAD DATA IN EXCEL) -----------------
@app.route('/export/purchases')
def export_purchases():
    excel_stream = excel_export.export_purchases_excel()
    filename = f"CaneMart_Purchases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export/sales')
def export_sales():
    excel_stream = excel_export.export_sales_excel()
    filename = f"CaneMart_Sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export/full-report')
def export_full_report():
    excel_stream = excel_export.export_full_canemart_report()
    filename = f"CaneMart_Master_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/reports')
def reports_page():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) as total_pur_qty,
            COALESCE(SUM(total_amount), 0) as total_pur_amt,
            COALESCE(SUM(paid_amount), 0) as total_pur_paid,
            COALESCE(SUM(remaining_amount), 0) as total_pur_rem
        FROM purchases
    ''')
    pur = cursor.fetchone()

    cursor.execute('''
        SELECT 
            COALESCE(SUM(quantity), 0) as total_sale_qty,
            COALESCE(SUM(total_amount), 0) as total_sale_amt,
            COALESCE(SUM(paid_amount), 0) as total_sale_paid,
            COALESCE(SUM(remaining_amount), 0) as total_sale_rem
        FROM sales
    ''')
    sale = cursor.fetchone()

    conn.close()
    return render_template('reports.html', pur=pur, sale=sale)

if __name__ == '__main__':
    import sys
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    init_db()
    ip = get_local_ip()
    print("=" * 60)
    print("[*] CaneMart Sugarcane Management System Running!")
    print(f"[*] Local Computer:  http://127.0.0.1:5000")
    print(f"[*] Mobile on Wi-Fi: http://{ip}:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
