from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3, os, datetime, random, string

app = Flask(__name__, template_folder='templates')

DB_PATH = "voucher.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    mobile TEXT,
                    outlet TEXT,
                    code TEXT UNIQUE,
                    created_at TEXT,
                    redeemed INTEGER DEFAULT 0,
                    redeemed_at TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

def generate_code(prefix):
    now = datetime.datetime.now()
    ym = now.strftime("%y%m")
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{ym}-{rand}"

@app.route('/')
def home():
    return render_template('voucher_console_basic_html.html')

@app.route('/issue', methods=['GET', 'POST'])
def issue_voucher():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        outlet = request.form.get('outlet')
        prefix = outlet.split('-')[0].upper()
        code = generate_code(prefix)
        created_at = datetime.datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO vouchers (name, mobile, outlet, code, created_at) VALUES (?, ?, ?, ?, ?)",
                  (name, mobile, outlet, code, created_at))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Voucher issued successfully",
            "code": code,
            "name": name,
            "mobile": mobile,
            "outlet": outlet
        })
    return render_template('issue_voucher_customer_form_basic_html.html')

@app.route('/redeem', methods=['GET', 'POST'])
def redeem_voucher():
    if request.method == 'POST':
        code = request.form.get('code').strip().upper()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, redeemed FROM vouchers WHERE code = ?", (code,))
        row = c.fetchone()

        if not row:
            conn.close()
            return jsonify({"status": "error", "message": "Invalid voucher code"})

        if row[1] == 1:
            conn.close()
            return jsonify({"status": "error", "message": "Voucher already redeemed"})

        redeemed_at = datetime.datetime.now().isoformat()
        c.execute("UPDATE vouchers SET redeemed = 1, redeemed_at = ? WHERE id = ?", (redeemed_at, row[0]))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Voucher redeemed", "code": code, "redeemed_at": redeemed_at})

    return render_template('redeem_voucher_basic_html.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
