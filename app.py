import os
import uuid
import bcrypt
import psycopg2
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------- CONFIG ----------
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.pdf')

# ---------- DATABASE ----------
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            text TEXT,
            files TEXT,
            password TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route('/')
def index():
    return render_template("index.html")

# ---------- CREATE ----------
@app.route('/create', methods=['POST'])
def create():
    text = request.form.get("text")
    password = request.form.get("password")
    files = request.files.getlist("file")

    if (not text or text.strip() == "") and (not files or files[0].filename == ""):
        return "❌ Add text or upload file"

    if not password:
        return "❌ Password required"

    filenames = []
    total_size = 0

    # size check
    for file in files:
        if file:
            file.seek(0, os.SEEK_END)
            total_size += file.tell()
            file.seek(0)

    if total_size > 50 * 1024 * 1024:
        return "❌ Max total size 50MB"

    # save files
    for file in files:
        if file and file.filename != "":
            if file.filename.lower().endswith(ALLOWED_EXTENSIONS):

                filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                file.save(filepath)
                filenames.append(filename)

            else:
                return "❌ Only JPG, PNG, PDF allowed"

    files_string = ",".join(filenames)

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO posts (text, files, password) VALUES (%s, %s, %s)",
        (text, files_string, hashed_password)
    )

    conn.commit()
    cur.close()
    conn.close()

    return render_template("success.html")

# ---------- OPEN ----------
@app.route('/open', methods=['POST'])
def open_post():
    password = request.form.get("password")

    if not password:
        return "❌ Enter password"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT text, files, password FROM posts")
    posts = cur.fetchall()

    cur.close()
    conn.close()

    for post in posts:
        try:
            stored_hash = post[2].encode()

            if bcrypt.checkpw(password.encode(), stored_hash):
                files = post[1].split(",") if post[1] else []
                return render_template("view.html", text=post[0], files=files)

        except:
            continue

    return "❌ Wrong password"

# ---------- VIEW FILE ----------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------- DOWNLOAD ----------
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
