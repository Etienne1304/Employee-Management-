
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date

from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

# Store the database beside this app.py file.
DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "employees.db"
)


# -----------------------------
# Database connection
# -----------------------------

@contextmanager
def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create the employees table if it does not exist."""
    with db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                middle_name TEXT,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                date_of_birth TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1))
            )
        """)


def employee_to_dict(row):
    """Convert a SQLite row to a JSON-friendly dictionary."""
    employee = dict(row)
    employee["is_active"] = bool(employee["is_active"])
    return employee


# -----------------------------
# Input validation
# -----------------------------

def normalize_employee(data, existing=None):
    """
    Validate and normalize employee data.

    For PUT, existing values are used when a field is omitted.
    Returns (cleaned_data, errors).
    """
    if not isinstance(data, dict):
        return None, {"body": "Request body must be a JSON object."}

    existing = existing or {}

    def get_value(field, default=""):
        value = data.get(field, existing.get(field, default))
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        return value.strip()

    first_name = get_value("first_name")
    middle_name = get_value("middle_name")
    last_name = get_value("last_name")
    email = get_value("email")
    dob = get_value("date_of_birth")

    errors = {}

    # Name validation
    if not isinstance(first_name, str) or not first_name:
        errors["first_name"] = "First name is required."
    elif len(first_name) > 100:
        errors["first_name"] = "First name must be 100 characters or fewer."

    if not isinstance(middle_name, str):
        errors["middle_name"] = "Middle name must be text."
    elif len(middle_name) > 100:
        errors["middle_name"] = "Middle name must be 100 characters or fewer."

    if not isinstance(last_name, str) or not last_name:
        errors["last_name"] = "Last name is required."
    elif len(last_name) > 100:
        errors["last_name"] = "Last name must be 100 characters or fewer."

    # Email validation
    if not isinstance(email, str) or not email:
        errors["email"] = "Email is required."
    elif len(email) > 150 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        errors["email"] = "Enter a valid email address."

    # Date of birth validation
    if not isinstance(dob, str) or not dob:
        errors["date_of_birth"] = "Date of birth is required."
    else:
        try:
            parsed_date = date.fromisoformat(dob)
            if parsed_date.isoformat() != dob:
                raise ValueError
            if parsed_date > date.today():
                errors["date_of_birth"] = "Date of birth cannot be in the future."
        except ValueError:
            errors["date_of_birth"] = "Use a valid date in YYYY-MM-DD format."

    # Active status validation
    active_value = data.get("is_active", existing.get("is_active", True))

    if isinstance(active_value, bool):
        is_active = active_value
    elif isinstance(active_value, int) and active_value in (0, 1):
        is_active = bool(active_value)
    elif isinstance(active_value, str) and active_value.lower() in (
        "true", "false", "1", "0"
    ):
        is_active = active_value.lower() in ("true", "1")
    else:
        is_active = True
        errors["is_active"] = "Active status must be true or false."

    if errors:
        return None, errors

    return {
        "first_name": first_name,
        "middle_name": middle_name or None,
        "last_name": last_name,
        "email": email.lower(),
        "date_of_birth": dob,
        "is_active": int(is_active),
    }, {}


# -----------------------------
# Home and health routes
# -----------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Employee Management System API is running"
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


# -----------------------------
# GET all employees
# Supports search and status filters
# -----------------------------

@app.route("/api/employees", methods=["GET"])
def get_employees():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip().lower()

    if status not in ("", "active", "inactive"):
        return jsonify({
            "error": "Status must be active or inactive."
        }), 400

    sql = """
        SELECT id, first_name, middle_name, last_name,
               email, date_of_birth, is_active
        FROM employees
        WHERE 1 = 1
    """
    params = []

    if search:
        pattern = f"%{search}%"
        sql += """
            AND (
                first_name LIKE ?
                OR middle_name LIKE ?
                OR last_name LIKE ?
                OR email LIKE ?
            )
        """
        params.extend([pattern, pattern, pattern, pattern])

    if status == "active":
        sql += " AND is_active = 1"
    elif status == "inactive":
        sql += " AND is_active = 0"

    sql += " ORDER BY id DESC"

    with db_connection() as connection:
        rows = connection.execute(sql, params).fetchall()

    return jsonify([employee_to_dict(row) for row in rows])


# -----------------------------
# GET one employee
# -----------------------------

@app.route("/api/employees/<int:employee_id>", methods=["GET"])
def get_employee(employee_id):
    with db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

    if row is None:
        return jsonify({"error": "Employee not found."}), 404

    return jsonify(employee_to_dict(row))


# -----------------------------
# POST: Create an employee
# -----------------------------

@app.route("/api/employees", methods=["POST"])
def create_employee():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "A JSON request body is required."}), 400

    employee, errors = normalize_employee(data)

    if errors:
        return jsonify({
            "error": "Validation failed.",
            "errors": errors
        }), 400

    try:
        with db_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO employees (
                    first_name, middle_name, last_name,
                    email, date_of_birth, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                employee["first_name"],
                employee["middle_name"],
                employee["last_name"],
                employee["email"],
                employee["date_of_birth"],
                employee["is_active"],
            ))

            employee_id = cursor.lastrowid

            row = connection.execute(
                "SELECT * FROM employees WHERE id = ?",
                (employee_id,)
            ).fetchone()

        return jsonify(employee_to_dict(row)), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "An employee with this email already exists."
        }), 409


# -----------------------------
# PUT: Update an employee
# -----------------------------

@app.route("/api/employees/<int:employee_id>", methods=["PUT"])
def update_employee(employee_id):
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "A JSON request body is required."}), 400

    with db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        ).fetchone()

    if row is None:
        return jsonify({"error": "Employee not found."}), 404

    employee, errors = normalize_employee(data, dict(row))

    if errors:
        return jsonify({
            "error": "Validation failed.",
            "errors": errors
        }), 400

    try:
        with db_connection() as connection:
            connection.execute("""
                UPDATE employees
                SET first_name = ?,
                    middle_name = ?,
                    last_name = ?,
                    email = ?,
                    date_of_birth = ?,
                    is_active = ?
                WHERE id = ?
            """, (
                employee["first_name"],
                employee["middle_name"],
                employee["last_name"],
                employee["email"],
                employee["date_of_birth"],
                employee["is_active"],
                employee_id,
            ))

            updated_row = connection.execute(
                "SELECT * FROM employees WHERE id = ?",
                (employee_id,)
            ).fetchone()

        return jsonify(employee_to_dict(updated_row))

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "An employee with this email already exists."
        }), 409


# -----------------------------
# DELETE: Remove an employee
# -----------------------------

@app.route("/api/employees/<int:employee_id>", methods=["DELETE"])
def delete_employee(employee_id):
    with db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM employees WHERE id = ?",
            (employee_id,)
        )

        deleted = cursor.rowcount

    if deleted == 0:
        return jsonify({"error": "Employee not found."}), 404

    return jsonify({
        "message": "Employee deleted successfully."
    })


# -----------------------------
# Start the application
# -----------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
