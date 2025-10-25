# app.py
from flask import Flask, render_template, request, redirect, url_for
import sqlite3, string, random, datetime

app = Flask(__name__)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('vouchers.db')
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

# --- Helper: Generate Random Code ---
def generate_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/')
def index():
    conn = sqlite3.connect('vouchers.db')
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
    conn = sqlite3.connect('vouchers.db')
    c = conn.cursor()
    c.execute("INSERT INTO vouchers (code, issued_to, status, expiry_date) VALUES (?, ?, ?, ?)",
              (code, name, "Active", expiry))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/redeem/<code>')
def redeem(code):
    conn = sqlite3.connect('vouchers.db')
    c = conn.cursor()
    c.execute("UPDATE vouchers SET status='Redeemed' WHERE code=?", (code,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
