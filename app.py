import os
from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# Hugging Face setup
API_URL = "https://api-inference.huggingface.co/models/falconsai/text_summarization"
API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# Upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "heic", "heif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_image(path):
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img)
    except Exception as e:
        return f"Image extraction error: {e}"


def extract_text_from_pdf(path):
    try:
        text = ""
        with fitz.open(path) as doc:
            for page in doc:
                text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"PDF extraction error: {e}"


def query_huggingface(text):
    try:
        response = requests.post(API_URL, headers=HEADERS, json={"inputs": text}, timeout=15)
        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        return "Unexpected AI response"
    except Exception as e:
        return f"AI request failed: {e}"


@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    input_text = ""

    if request.method == "POST":
        if "bill_text" in request.form:
            input_text = request.form.get("bill_text", "").strip()
        elif "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                ext = filename.rsplit(".", 1)[1].lower()
                if ext == "pdf":
                    input_text = extract_text_from_pdf(file_path)
                else:
                    input_text = extract_text_from_image(file_path)
            else:
                flash("Unsupported or missing file.", "danger")

        if input_text:
            result = query_huggingface(input_text)
        else:
            flash("No valid input found.", "warning")

    return render_template("index.html", result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)