from cs50 import SQL
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///match50/match50.db")

# Ensure table exists
db.execute("""
CREATE TABLE IF NOT EXISTS registrants (
    rname TEXT PRIMARY KEY,
    rpassword TEXT,
    email TEXT,
    date INT,
    month TEXT,
    year INT,
    q1 INT DEFAULT -1, q2 INT DEFAULT -1, q3 INT DEFAULT -1, q4 INT DEFAULT -1, q5 INT DEFAULT -1,
    q6 INT DEFAULT -1, q7 INT DEFAULT -1, q8 INT DEFAULT -1, q9 INT DEFAULT -1, q10 INT DEFAULT -1,
    q11 INT DEFAULT -1, q12 INT DEFAULT -1, q13 INT DEFAULT -1, q14 INT DEFAULT -1, q15 INT DEFAULT -1,
    q16 INT DEFAULT -1, q17 INT DEFAULT -1, q18 INT DEFAULT -1, q19 INT DEFAULT -1, q20 INT DEFAULT -1,
    p1 TEXT, p2 TEXT, p3 TEXT, p4 TEXT, perd TEXT
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

    exists = db.execute("SELECT * FROM registrants WHERE rname = ?", rname)
    if exists:
        return render_template("already.html")

    db.execute(
        """
        INSERT INTO registrants (
            rname, rpassword, email, date, month, year,
            q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
            q11, q12, q13, q14, q15, q16, q17, q18, q19, q20
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rname, rpassword, email, date, month, year,
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1
    )
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    rname = request.form.get("lname")
    rpassword = request.form.get("lpassword")

    result = db.execute("SELECT * FROM registrants WHERE rname = ? AND rpassword = ?", rname, rpassword)
    if not result:
        return render_template("fault.html")

    session["user"] = rname
    return render_template("user.html", name=rname)


@app.route("/test")
def test():
    user = session.get("user")
    if not user:
        return redirect("/")

    # Get all q1 to q20
    data = db.execute("SELECT " + ", ".join([f"q{i}" for i in range(1, 21)]) + " FROM registrants WHERE rname = ?", user)
    if not data:
        return redirect("/")

    user_answers = data[0]
    already_taken = any(user_answers[f"q{i}"] != -1 for i in range(1, 21))
    if already_taken:
        return render_template("retest.html")
    return render_template("test.html")

@app.route("/retest")
def retest():
    return render_template("test.html")

@app.route("/hpage")
def hpage():
    user = session.get("user")
    if not user:
        return redirect("/")
    return render_template("user.html", name=user)

@app.route("/submit", methods=["POST"])
def submit():
    user = session.get("user")
    if not user:
        return redirect("/")

    answers = {}
    for i in range(1, 21):
        val = request.form.get(f"q{i}")
        if val is None:
            return render_template("failure.html")
        answers[f"q{i}"] = int(val)

    for i in range(1, 21):
        db.execute(f"UPDATE registrants SET q{i} = ? WHERE rname = ?", answers[f"q{i}"], user)

    p1 = "E" if sum(answers[f"q{i}"] for i in range(1, 6)) > 3 else "I"
    p2 = "S" if sum(answers[f"q{i}"] for i in range(6, 11)) > 3 else "N"
    p3 = "T" if sum(answers[f"q{i}"] for i in range(11, 16)) > 3 else "F"
    p4 = "J" if sum(answers[f"q{i}"] for i in range(16, 21)) > 3 else "P"

    personality = p1 + p2 + p3 + p4

    db.execute("UPDATE registrants SET p1 = ?, p2 = ?, p3 = ?, p4 = ?, perd = ? WHERE rname = ?",
               p1, p2, p3, p4, personality, user)

    return render_template("user.html", name=user)

@app.route("/match")
def match():
    user = session.get("user")
    if not user:
        return redirect("/")

    user_type = db.execute("SELECT perd FROM registrants WHERE rname = ?", user)[0]["perd"]
    results = db.execute("SELECT email FROM registrants WHERE perd = ? AND rname != ?", user_type, user)
    emails = [row["email"] for row in results]

    return render_template("match.html", type=user_type, matches=emails)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
