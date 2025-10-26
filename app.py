from flask import Flask, render_template, request, jsonify
import gspread, datetime, random, string, os
from oauth2client.service_account import ServiceAccountCredentials
import ast
app = Flask(__name__, template_folder='templates')

# Google Sheets setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open_by_key("1V0daaI3OgxJJ5lifrGeYbTH3qrG1AO_LX0Q6J7JR5C4").sheet1

def generate_code(prefix="NAT"):
    ym = datetime.datetime.now().strftime("%y%m")
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{ym}-{rand}"

@app.route('/')
def home():
    return render_template('voucher_console_basic_html.html')

@app.route('/issue', methods=['GET', 'POST'])
def issue():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        outlet = request.form.get('outlet')
        discount = request.form.get('discount')

        if not name or not mobile or not outlet:
            return jsonify({"status": "error", "message": "Missing fields"})

        code = generate_code(outlet.split('-')[0])
        created_at = datetime.datetime.now().isoformat()

        SHEET.append_row([name, mobile, outlet, code, created_at, "No", "",discount])

        return jsonify({
            "status": "success",
            "code": code,
            "name": name,
            "mobile": mobile,
            "outlet": outlet,
            "discount": discount,
            "redirect_url": f"/issued/{code}"
        })

    # If method == GET, render the form
    return render_template('issue_voucher_customer_form_basic_html.html')


@app.route("/redeem", methods=["GET", "POST"])
def redeem():
    if request.method == "GET":
        return render_template("redeem_voucher_basic_html.html")

    code = request.form.get("code", "").strip().upper()
    if not code:
        return jsonify({"status": "error", "message": "No code provided"})

    try:
        records = SHEET.get_all_records()
    except Exception as e:
        print("Google Sheet fetch error:", e)
        return jsonify({"status": "error", "message": "Cannot access Google Sheet."})

    for i, row in enumerate(records, start=2):  # header is row 1
        if str(row.get("Code", "")).upper() == code:
            if str(row.get("Redeemed", "")).lower() == "yes":
                return jsonify({"status": "error", "message": "Already redeemed."})
            try:
                SHEET.update([["Yes"]],f"F{i}")
                SHEET.update([[datetime.datetime.now().isoformat()]],f"G{i}" )
                
                return jsonify({"status": "success", "code":code,"message": "Voucher redeemed successfully."})
            except Exception as e:
                print("Sheet update error:", e)
                return jsonify({"status": "error", "message": "Could not update Google Sheet."})
    return jsonify({"status": "error", "message": "Invalid voucher code."})

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import send_file
import qrcode

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import send_file
import datetime, qrcode, os

@app.route('/voucher_download/<code>/<discount>/<partner_name>/234')
def generate_voucher_image(code: str, discount: int, partner_name: str, validity_days: int = 30) -> BytesIO:
    """Generate voucher image using Canva template with perfect text placement."""
    template_path = os.path.join("static", "voucher_template.jpeg")  # your Canva base
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Fonts
    try:
        font_name = ImageFont.truetype("arialbd.ttf", 95)   # large customer name
        font_value = ImageFont.truetype("arialbd.ttf", 33)
    except:
        font_name = font_value = ImageFont.load_default()

    # Validity date
    validity_date = (datetime.datetime.now() + datetime.timedelta(days=validity_days)).strftime("%d-%b-%Y")

    # --- 1️⃣ Customer name (replaces “35%”) ---
    # Shifted slightly right and down to fit the "35%" area perfectly
    name_x = int(width * 0.24)
    name_y = int(height * 0.43)
    # draw.text((name_x, name_y), partner_name, font=font_name, fill=(230, 141, 14))

    # --- 2️⃣ Voucher details (aligned beside labels) ---
    # Adjusted coordinates for Canva template (1366×768 approx)
    details_color = (0, 0, 0)
    draw.text((960, 585), partner_name, font=font_value, fill=details_color)  # partner name
    draw.text((920, 660), code, font=font_value, fill=details_color)          # voucher id
    draw.text((860, 735), validity_date, font=font_value, fill=details_color) # validity


    # Save image to buffer
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    return send_file(
    buf,
    mimetype="image/jpeg",
    as_attachment=True,          # ✅ This makes it download
    download_name=f"{code}.jpg"  # Sets the filename
    )







if __name__ == '__main__':
    app.run(debug=True)
