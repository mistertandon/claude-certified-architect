# Sample source files to be reviewed by the multi-pass reviewer.
# Each dict simulates a file in a codebase — keeps the POC self-contained
# without requiring actual filesystem reads.

SAMPLE_FILES = {
    "auth/login.py": """
import hashlib
import os

PASSWORD_SALT = "static_salt_123"

def authenticate(username, password):
    hashed = hashlib.md5((password + PASSWORD_SALT).encode()).hexdigest()
    db_hash = lookup_user_hash(username)
    if hashed == db_hash:
        session_token = os.urandom(16).hex()
        return {"token": session_token, "role": "admin"}
    return None

def lookup_user_hash(username):
    # Simulated DB lookup
    return "fake_hash"
""",
    "auth/permissions.py": """
from auth.login import authenticate

ROLE_PERMISSIONS = {
    "admin": ["read", "write", "delete", "manage_users"],
    "user": ["read", "write"],
}

def check_permission(token_data, action):
    if token_data is None:
        return False
    role = token_data.get("role", "user")
    return action in ROLE_PERMISSIONS.get(role, [])

def escalate_role(token_data, new_role):
    token_data["role"] = new_role
    return token_data
""",
    "api/endpoints.py": """
from auth.login import authenticate
from auth.permissions import check_permission, escalate_role
from data.store import save_record, get_record

def handle_login(request):
    result = authenticate(request["username"], request["password"])
    return {"status": 200, "body": result}

def handle_get_record(request):
    record = get_record(request["record_id"])
    return {"status": 200, "body": record}

def handle_delete_record(request):
    token = request.get("token_data")
    if check_permission(token, "delete"):
        return {"status": 200, "body": "deleted"}
    return {"status": 403, "body": "forbidden"}

def handle_admin_escalation(request):
    token = request.get("token_data")
    escalated = escalate_role(token, "admin")
    return {"status": 200, "body": escalated}
""",
    "data/store.py": """
import sqlite3

DB_PATH = "app.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_record(record_id, data):
    conn = get_connection()
    query = f"INSERT INTO records (id, data) VALUES ('{record_id}', '{data}')"
    conn.execute(query)
    conn.commit()
    conn.close()

def get_record(record_id):
    conn = get_connection()
    query = f"SELECT * FROM records WHERE id = '{record_id}'"
    result = conn.execute(query).fetchone()
    conn.close()
    return result

def delete_record(record_id):
    conn = get_connection()
    query = f"DELETE FROM records WHERE id = '{record_id}'"
    conn.execute(query)
    conn.commit()
    conn.close()
"""
}
