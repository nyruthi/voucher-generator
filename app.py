from flask import Flask, render_template, request, redirect, url_for
import sqlite3, string, random, os

app = Flask(__name__)
DB_FILE = "vouchers.db"

# --- Database Setup ---
def init_db():
    """Create DB and table if missing."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    issued_to TEXT,
                    status TEXT,
                    expiry_date TEXT
                )''')
    conn.commit()
    conn.close()

# --- Run init_db() once when the app starts ---
with app.app_context():
    init_db()

# --- Helper: Generate Random Code ---
def generate_code(length=8):
    import random, string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/')
def index():
    init_db()  # <- ensures table exists even on first request
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM vouchers")
    vouchers = c.fetchall()
    conn.close()
    return render_template('index.html', vouchers=vouchers)

@app.route('/create', methods=['POST'])
def create_voucher():
    name = request.form['issued_to']
    expiry = request.form['expiry_date']
    code = generate_code()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO vouchers (code, issued_to, status, expiry_date) VALUES (?, ?, ?, ?)",
              (code, name, "Active", expiry))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/redeem/<code>')
def redeem(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE vouchers SET status='Redeemed' WHERE code=?", (code,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
