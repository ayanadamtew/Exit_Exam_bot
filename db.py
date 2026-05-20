import sqlite3
import json
from datetime import datetime

DB_FILE = "quiz_bot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)
    
    # Create active_quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_quizzes (
            user_id INTEGER PRIMARY KEY,
            questions_json TEXT,
            current_index INTEGER,
            score INTEGER,
            total_questions INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    # Create quiz_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            total_questions INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()

def start_quiz(user_id, questions_list):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    questions_json = json.dumps(questions_list)
    total_questions = len(questions_list)
    cursor.execute("""
        INSERT INTO active_quizzes (user_id, questions_json, current_index, score, total_questions)
        VALUES (?, ?, 0, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            questions_json = excluded.questions_json,
            current_index = 0,
            score = 0,
            total_questions = excluded.total_questions
    """, (user_id, questions_json, total_questions))
    conn.commit()
    conn.close()

def get_active_quiz(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT questions_json, current_index, score, total_questions
        FROM active_quizzes
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    return {
        "questions": json.loads(row[0]),
        "current_index": row[1],
        "score": row[2],
        "total_questions": row[3]
    }

def update_quiz_progress(user_id, current_index, score):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE active_quizzes
        SET current_index = ?, score = ?
        WHERE user_id = ?
    """, (current_index, score, user_id))
    conn.commit()
    conn.close()

def delete_active_quiz(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_quizzes WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def record_quiz_history(user_id, score, total_questions):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quiz_history (user_id, score, total_questions)
        VALUES (?, ?, ?)
    """, (user_id, score, total_questions))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*), AVG(CAST(score AS REAL) / total_questions * 100), MAX(score)
        FROM quiz_history
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or row[0] == 0:
        return None
        
    return {
        "total_quizzes": row[0],
        "average_score_pct": round(row[1], 1) if row[1] is not None else 0.0,
        "high_score": row[2] if row[2] is not None else 0
    }
