from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os, uuid, json
import qrcode
from PIL import Image
import io

# Optional: OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

app = Flask(__name__)
app.secret_key = "dev-secret"  # for flash messages in demo
DATA_FILE = "data.json"
QR_DIR = os.path.join("static", "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)

# load/save helpers
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# optional: AI describe (requires OPENAI_API_KEY env var)
def ai_improve_description(text):
    if not OPENAI_AVAILABLE:
        return text
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return text
    openai.api_key = key
    prompt = f"Make this lost item description short, clear and helpful for reuniting with owner:\n\n{ text }"
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=80
        )
        out = resp.choices[0].message.content.strip()
        return out
    except Exception as e:
        print("OpenAI error:", e)
        return text

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    data = load_data()
    name = request.form.get("name","").strip()
    contact = request.form.get("contact","").strip()
    desc = request.form.get("description","").strip()
    # optionally improve via AI
    improved = ai_improve_description(desc) if desc else desc

    item_id = str(uuid.uuid4())[:8]
    item = {
        "id": item_id,
        "name": name,
        "contact": contact,
        "description": improved,
        "messages": []
    }
    data[item_id] = item
    save_data(data)

    # generate QR linking to item page
    link = request.url_root.rstrip("/") + url_for("item", item_id=item_id)
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_path = os.path.join(QR_DIR, f"{item_id}.png")
    img.save(qr_path)

    return render_template("register.html", item=item, qr_file=qr_path)

@app.route("/item/<item_id>")
def item(item_id):
    data = load_data()
    item = data.get(item_id)
    if not item:
        flash("Item not found.")
        return redirect(url_for("index"))
    return render_template("item.html", item=item)

@app.route("/contact/<item_id>", methods=["POST"])
def contact_owner(item_id):
    data = load_data()
    item = data.get(item_id)
    if not item:
        return "Item not found", 404

    finder_name = request.form.get("finder_name","").strip()
    finder_contact = request.form.get("finder_contact","").strip()
    found_where = request.form.get("found_where","").strip()
    message_text = request.form.get("message","").strip()

    message_record = {
        "finder_name": finder_name,
        "finder_contact": finder_contact,
        "found_where": found_where,
        "message": message_text
    }
    # store message
    item["messages"].append(message_record)
    data[item_id] = item
    save_data(data)

    # for demo: print to server console (simulate sending to owner)
    print(f"--- Found message for item {item_id} ---")
    print("Owner contact:", item.get("contact"))
    print("Finder:", finder_name, finder_contact)
    print("Found where:", found_where)
    print("Message:", message_text)
    print("------------------------------")

    flash("Message recorded and (simulated) sent to owner. Thank you!")
    return redirect(url_for("item", item_id=item_id))

# for convenience: serve qrcodes via static (Flask static already serves static/)
@app.route("/static/qrcodes/<path:filename>")
def qrcode_file(filename):
    return send_from_directory(QR_DIR, filename)

if __name__ == "__main__":
    # auto-create data file if missing
    if not os.path.exists(DATA_FILE):
        save_data({})
    app.run(host="0.0.0.0", port=5000, debug=True)
