import os
import uuid
import sqlite3
import bcrypt
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------- PATH SETUP ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

ALLOWED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.pdf')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🔥 Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    text TEXT,
                    files TEXT,
                    password TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------- CREATE ----------------
@app.route('/create', methods=['POST'])
def create():
    text = request.form.get('text')
    password = request.form.get('password')
    files = request.files.getlist('file')

    if not password:
        return "❌ Password required"

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    all_posts = c.fetchall()

    # 🔒 Prevent duplicate password
    for post in all_posts:
        try:
            stored_hash = post[2].encode()
            if bcrypt.checkpw(password.encode(), stored_hash):
                conn.close()
                return "❌ Password already used. Try another."
        except:
            continue

    filenames = []

    for file in files:
        if file and file.filename != "":
            if file.filename.lower().endswith(ALLOWED_EXTENSIONS):

                filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)

                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # 🔥 Ensure folder exists again (safety)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

                print("Saving file to:", filepath)

                file.save(filepath)
                filenames.append(filename)

            else:
                return "❌ Only JPG, PNG, PDF allowed"

    files_string = ",".join(filenames)

    # 🔐 Hash password
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    c.execute("INSERT INTO posts VALUES (?, ?, ?)",
              (text, files_string, hashed_password))
    conn.commit()
    conn.close()

    return render_template("success.html")

# ---------------- OPEN ----------------
@app.route('/open', methods=['POST'])
def open_post():
    password = request.form.get('password')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    posts = c.fetchall()
    conn.close()

    for post in posts:
        try:
            stored_hash = post[2].encode()

            if bcrypt.checkpw(password.encode(), stored_hash):
                files = post[1].split(",") if post[1] else []
                return render_template('view.html', text=post[0], files=files)

        except:
            continue

    return "❌ Wrong Password"

# ---------------- VIEW FILE ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- DOWNLOAD ----------------
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
