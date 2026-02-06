import sqlite3
import os

db_path = r'c:\Users\h\Desktop\zuoye1\new-api\data\one-api.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, role FROM users")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}, User: {row[1]}, Role: {row[3]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
