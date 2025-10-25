from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3, os, datetime, random, string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import send_file
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

@app.route('/redeem', methods=['GET', 'POST'])
def redeem_voucher():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()

        import re
        # Validate format like HYD-2510-7K9Q (3–4 letters, dash, YYMM, dash, 4 alphanumeric)
        if not re.match(r'^[A-Z]{3,4}-\d{4}-[A-Z0-9]{4}$', code):
            return jsonify({
                "status": "error",
                "message": "Invalid voucher format. Use format: ABC-YYMM-XXXX"
            })

        # Open DB connection
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, redeemed, redeemed_at FROM vouchers WHERE code = ?", (code,))
        record = c.fetchone()

        if not record:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "Voucher code not found in system."
            })

        voucher_id, name, redeemed, redeemed_at = record

        if redeemed == 1:
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Voucher already redeemed on {redeemed_at}"
            })

        # Mark as redeemed
        redeemed_at = datetime.datetime.now().isoformat()
        c.execute(
            "UPDATE vouchers SET redeemed = 1, redeemed_at = ? WHERE id = ?",
            (redeemed_at, voucher_id)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Voucher redeemed successfully for {name}",
            "code": code,
            "redeemed_at": redeemed_at
        })

    return render_template('redeem_voucher_basic_html.html')



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



@app.route('/voucher_image/<code>/<discount>')
def voucher_image(code, discount):
    # Create base image
    img = Image.new("RGB", (600, 300), color="#f9fafb")
    draw = ImageDraw.Draw(img)

    # Load fonts (use default if no font files)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 40)
        font_sub = ImageFont.truetype("arial.ttf", 24)
        font_code = ImageFont.truetype("arialbd.ttf", 28)
    except:
        font_title = font_sub = font_code = ImageFont.load_default()

    # Header
    draw.text((30, 30), "Naturals", fill="#8b5cf6", font=font_title)

    # Discount text
    draw.text((30, 100), f"Enjoy {discount}% OFF on your next visit!", fill="#111827", font=font_sub)

    # Voucher code
    draw.text((30, 170), f"Voucher Code: {code}", fill="#2563eb", font=font_code)

    # Footer
    draw.text((30, 240), "Valid at participating outlets only", fill="#6b7280", font=font_sub)

    # Output as PNG
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
