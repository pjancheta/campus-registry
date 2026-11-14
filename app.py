import os
from contextlib import contextmanager

import psycopg2
import psycopg2.errors
import psycopg2.extras
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")
DATABASE_URL = os.environ.get("DATABASE_URL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id         SERIAL PRIMARY KEY,
    student_no VARCHAR(20)  UNIQUE NOT NULL,
    first_name VARCHAR(50)  NOT NULL,
    last_name  VARCHAR(50)  NOT NULL,
    course     VARCHAR(100) NOT NULL,
    year_level INTEGER      NOT NULL CHECK (year_level BETWEEN 1 AND 6),
    email      VARCHAR(100),
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
)
"""


@contextmanager
def db_cursor():
    """Open a connection, yield a dict-like cursor, commit, then always close."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def read_form():
    f = request.form
    return {
        "student_no": f["student_no"].strip(),
        "first_name": f["first_name"].strip(),
        "last_name": f["last_name"].strip(),
        "course": f["course"].strip(),
        "year_level": int(f["year_level"]),
        "email": f.get("email", "").strip() or None,
    }


@app.route("/")
def students_list():
    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()

    sql = "SELECT * FROM students WHERE TRUE"
    params = []
    if q:
        sql += (" AND (student_no ILIKE %s OR first_name ILIKE %s"
                " OR last_name ILIKE %s OR course ILIKE %s)")
        params += [f"%{q}%"] * 4
    if year.isdigit():
        sql += " AND year_level = %s"
        params.append(int(year))
    sql += " ORDER BY last_name, first_name"

    with db_cursor() as cur:
        cur.execute(sql, params)
        students = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS n FROM students")
        total = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(DISTINCT course) AS n FROM students")
        courses = cur.fetchone()["n"]

    return render_template("students.html", students=students, q=q, year=year,
                           total=total, courses=courses)


@app.route("/students/new", methods=["GET", "POST"])
def student_new():
    if request.method == "POST":
        data = read_form()
        try:
            with db_cursor() as cur:
                cur.execute(
                    """INSERT INTO students
                       (student_no, first_name, last_name, course, year_level, email)
                       VALUES (%(student_no)s, %(first_name)s, %(last_name)s,
                               %(course)s, %(year_level)s, %(email)s)""", data)
            flash("Student added successfully.", "ok")
            return redirect(url_for("students_list"))
        except psycopg2.errors.UniqueViolation:
            flash("Student number already exists.", "error")
            return render_template("student_form.html", student=data, mode="new")
    return render_template("student_form.html", student=None, mode="new")


@app.route("/students/<int:sid>/edit", methods=["GET", "POST"])
def student_edit(sid):
    if request.method == "POST":
        data = read_form()
        data["id"] = sid
        try:
            with db_cursor() as cur:
                cur.execute(
                    """UPDATE students SET student_no=%(student_no)s,
                       first_name=%(first_name)s, last_name=%(last_name)s,
                       course=%(course)s, year_level=%(year_level)s,
                       email=%(email)s WHERE id=%(id)s""", data)
            flash("Student record updated.", "ok")
            return redirect(url_for("students_list"))
        except psycopg2.errors.UniqueViolation:
            flash("Student number already exists.", "error")
            return render_template("student_form.html", student=data, mode="edit")

    with db_cursor() as cur:
        cur.execute("SELECT * FROM students WHERE id = %s", (sid,))
        student = cur.fetchone()
    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_list"))
    return render_template("student_form.html", student=student, mode="edit")


@app.route("/students/<int:sid>/delete", methods=["POST"])
def student_delete(sid):
    with db_cursor() as cur:
        cur.execute("DELETE FROM students WHERE id = %s", (sid,))
    flash("Student record deleted.", "ok")
    return redirect(url_for("students_list"))


# Create the table automatically if it does not exist yet.
with db_cursor() as _cur:
    _cur.execute(SCHEMA)

if __name__ == "__main__":
    app.run(debug=True)
