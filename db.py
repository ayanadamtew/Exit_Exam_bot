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
    
    # Create saved_quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quiz_name TEXT,
            questions_json TEXT,
            question_count INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

# ── Saved Quiz File Functions ────────────────────────────────────────────────

def save_quiz_file(user_id, quiz_name, questions_list):
    """Saves or replaces a quiz file for a user (keyed by quiz_name)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    questions_json = json.dumps(questions_list)
    question_count = len(questions_list)
    # If a quiz with the same name already exists for this user, replace it
    cursor.execute("""
        SELECT id FROM saved_quizzes WHERE user_id = ? AND quiz_name = ?
    """, (user_id, quiz_name))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE saved_quizzes
            SET questions_json = ?, question_count = ?, uploaded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (questions_json, question_count, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO saved_quizzes (user_id, quiz_name, questions_json, question_count)
            VALUES (?, ?, ?, ?)
        """, (user_id, quiz_name, questions_json, question_count))
    conn.commit()
    conn.close()

def get_saved_quizzes(user_id):
    """Returns list of saved quizzes for a user (id, quiz_name, question_count, uploaded_at)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, quiz_name, question_count, uploaded_at
        FROM saved_quizzes
        WHERE user_id = ?
        ORDER BY uploaded_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "quiz_name": r[1], "question_count": r[2], "uploaded_at": r[3]}
        for r in rows
    ]

def get_saved_quiz_by_id(quiz_id, user_id):
    """Returns the questions list for a saved quiz, or None if not found."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT questions_json, quiz_name FROM saved_quizzes
        WHERE id = ? AND user_id = ?
    """, (quiz_id, user_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {"questions": json.loads(row[0]), "quiz_name": row[1]}

def delete_saved_quiz(quiz_id, user_id):
    """Deletes a saved quiz for a user."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM saved_quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_id))
    conn.commit()
    conn.close()
