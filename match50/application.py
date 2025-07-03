import os
from cs50 import SQL
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_session import Session
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# OpenAI client initialization
client = OpenAI(api_key="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")  # Use environment variable in production

db = SQL("sqlite:///match50.db")

# Create table if not exists
db.execute("""
CREATE TABLE IF NOT EXISTS registrants (
    rname TEXT PRIMARY KEY,
    rpassword TEXT,
    email TEXT,
    date INT,
    month TEXT,
    year INT,
    gender TEXT,
    profile_img TEXT DEFAULT '',
    q1 INT DEFAULT -1, q2 INT DEFAULT -1, q3 INT DEFAULT -1, q4 INT DEFAULT -1, q5 INT DEFAULT -1,
    q6 INT DEFAULT -1, q7 INT DEFAULT -1, q8 INT DEFAULT -1, q9 INT DEFAULT -1, q10 INT DEFAULT -1,
    q11 INT DEFAULT -1, q12 INT DEFAULT -1, q13 INT DEFAULT -1, q14 INT DEFAULT -1, q15 INT DEFAULT -1,
    q16 INT DEFAULT -1, q17 INT DEFAULT -1, q18 INT DEFAULT -1, q19 INT DEFAULT -1, q20 INT DEFAULT -1,
    p1 TEXT, p2 TEXT, p3 TEXT, p4 TEXT, perd TEXT,
    test_time TEXT DEFAULT ''
)
""")

@app.route("/")
def index():
    return render_template("homepage.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    rname = request.form.get("rname")
    rpassword = request.form.get("rpassword")
    cpassword = request.form.get("cpassword")
    email = request.form.get("email")
    date = request.form.get("date")
    month = request.form.get("month")
    year = request.form.get("year")
    gender = request.form.get("gender")

    if not all([rname, rpassword, cpassword, email, date, month, year, gender]):
        return render_template("failure.html")
    if rpassword != cpassword:
        return render_template("passworderror.html")
    if ".com" not in email:
        return render_template("iderror.html")
    if db.execute("SELECT * FROM registrants WHERE rname = ?", rname):
        return render_template("already.html")

    db.execute(
        "INSERT INTO registrants (rname, rpassword, email, date, month, year, gender) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rname, rpassword, email, date, month, year, gender
    )

    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    rname = request.form.get("lname")
    rpassword = request.form.get("lpassword")
    user = db.execute("SELECT * FROM registrants WHERE rname = ? AND rpassword = ?", rname, rpassword)

    if not user:
        return render_template("fault.html")

    session["user"] = rname
    return redirect("/user")

@app.route("/user")
def user():
    user = session.get("user")
    if not user:
        return redirect("/")
    return render_template("user.html", name=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/test")
def test():
    user = session.get("user")
    if not user:
        return redirect("/")

    answered = db.execute("SELECT q1 FROM registrants WHERE rname = ?", user)
    if answered and answered[0]["q1"] != -1:
        return render_template("retest.html")
    return render_template("test.html")

@app.route("/submit", methods=["POST"])
def submit():
    user = session.get("user")
    if not user:
        return redirect("/")

    answers = {}
    for i in range(1, 21):
        ans = request.form.get(f"q{i}")
        if not ans:
            return render_template("failure.html")
        answers[f"q{i}"] = int(ans)

    for i in range(1, 21):
        db.execute(f"UPDATE registrants SET q{i} = ? WHERE rname = ?", answers[f"q{i}"], user)

    p1 = "E" if sum(answers[f"q{i}"] for i in range(1, 6)) > 3 else "I"
    p2 = "S" if sum(answers[f"q{i}"] for i in range(6, 11)) > 3 else "N"
    p3 = "T" if sum(answers[f"q{i}"] for i in range(11, 16)) > 3 else "F"
    p4 = "J" if sum(answers[f"q{i}"] for i in range(16, 21)) > 3 else "P"
    personality = p1 + p2 + p3 + p4

    db.execute("UPDATE registrants SET p1 = ?, p2 = ?, p3 = ?, p4 = ?, perd = ?, test_time = ? WHERE rname = ?",
               p1, p2, p3, p4, personality, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user)

    return redirect("/user")

@app.route("/match")
def match():
    user = session.get("user")
    if not user:
        return redirect("/")
    user_type = db.execute("SELECT perd FROM registrants WHERE rname = ?", user)[0]["perd"]
    matches = db.execute("SELECT rname, email FROM registrants WHERE perd = ? AND rname != ?", user_type, user)
    return render_template("match.html", type=user_type, matches=matches)

@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return redirect("/")
    info = db.execute("SELECT * FROM registrants WHERE rname = ?", user)[0]
    return render_template("profile.html", user=info)

@app.route("/history")
def history():
    user = session.get("user")
    if not user:
        return redirect("/")
    row = db.execute("SELECT * FROM registrants WHERE rname = ?", user)[0]
    return render_template("history.html", user=row)

@app.route("/admin")
def admin():
    users = db.execute("SELECT * FROM registrants")
    return render_template("admin.html", users=users)

@app.route("/ask-ai", methods=["POST"])
def ask_ai():
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 403

    msg = request.json.get("prompt")
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a psychologist chatbot giving personality insights based on MBTI."},
                {"role": "user", "content": msg}
            ]
        )
        return jsonify({"response": res.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ai-summary")
def ai_summary_page():
    user = session.get("user")
    if not user:
        return redirect("/login")
    return render_template("insights.html")
