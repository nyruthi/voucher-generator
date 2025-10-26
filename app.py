from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import gspread, datetime, random, string, os
from oauth2client.service_account import ServiceAccountCredentials
import ast
app = Flask(__name__, template_folder='templates')

# Google Sheets setup
from google.oauth2.service_account import Credentials


SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDS = Credentials.from_service_account_file(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"), scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open_by_key("1V0daaI3OgxJJ5lifrGeYbTH3qrG1AO_LX0Q6J7JR5C4").sheet1
app.secret_key = "super_secret_key"  # change this to a random string

def get_user_from_sheet(username):
    """Fetch user record from Users sheet."""
    try:
        users_sheet = CLIENT.open_by_key("1V0daaI3OgxJJ5lifrGeYbTH3qrG1AO_LX0Q6J7JR5C4").worksheet("Users")
        records = users_sheet.get_all_records()
        for user in records:
            if user["Username"].strip().lower() == username.strip().lower():
                return user
    except Exception as e:
        print("Error reading Users sheet:", e)
    return None

def generate_code(prefix="NAT"):
    ym = datetime.datetime.now().strftime("%y%m")
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{ym}-{rand}"
from functools import wraps

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper
@app.route("/")
@app.route("/index")
@login_required
def index():
    return render_template("voucher_console_basic_html.html", outlet=session["outlet"])

@app.route('/')
def home():
    return render_template('voucher_console_basic_html.html')

@app.route('/issue', methods=['GET', 'POST'])
@login_required
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
    return render_template("issue_voucher_customer_form_basic_html.html", outlet=session["outlet"])


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
import os

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
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "arialbd.ttf")
        font_name = ImageFont.truetype(font_path, 95)
        font_value = ImageFont.truetype(font_path, 33)
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
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user_from_sheet(username)
        if not user:
            return render_template("login.html", error="User not found")

        if str(user["Password"]).strip() != password.strip():
            return render_template("login.html", error="Invalid password")

        # ✅ store user info in session
        session["username"] = user["Username"]
        session["outlet"] = user["Outlet"]
        session["role"] = user.get("Role", "staff")

        return redirect(url_for("index"))  # or /issue if that’s your main page
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))







if __name__ == '__main__':
    app.run(debug=True)
