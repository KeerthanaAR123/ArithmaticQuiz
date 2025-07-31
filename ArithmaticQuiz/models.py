import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DATABASE = 'quiz.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with proper schema handling"""
    conn = get_db_connection()
    
    try:
        # Check if tables exist and have correct schema
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_results'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Check if user_id column exists
            cursor = conn.execute("PRAGMA table_info(quiz_results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'user_id' not in columns:
                # Drop and recreate table with correct schema
                conn.execute('DROP TABLE IF EXISTS quiz_results')
                print("Dropped old quiz_results table with incorrect schema")
        
        # Create users table if not exists
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create questions table if not exists
        conn.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                option1 TEXT NOT NULL,
                option2 TEXT NOT NULL,
                option3 TEXT NOT NULL,
                option4 TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                difficulty TEXT DEFAULT 'medium'
            )
        ''')
        
        # Create quiz_results table with correct schema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                time_taken INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create admin user if not exists
        admin_exists = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not admin_exists:
            admin_password = generate_password_hash('admin123')
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                        ('admin', 'admin@apquiz.com', admin_password))
            print("Admin user created")
        
        # Insert sample questions if table is empty
        question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        if question_count == 0:
            sample_questions = [
                ("What is the 10th term of the AP: 3, 8, 13, 18...?", "48", "53", "58", "63", 2, "easy"),
                ("Find the sum of first 10 terms of AP: 2, 5, 8, 11...", "155", "165", "175", "185", 2, "medium"),
                ("Which of the following is NOT an arithmetic progression?", "2, 4, 6, 8", "1, 4, 9, 16", "5, 10, 15, 20", "3, 7, 11, 15", 2, "easy"),
                ("In AP: 7, _, 19, _, 31 - find the first missing term", "13", "15", "11", "12", 1, "medium"),
                ("The common difference of AP: -5, -1, 3, 7... is", "4", "-4", "6", "-6", 1, "easy"),
                ("Sum of first n natural numbers is given by", "n(n+1)", "n(n+1)/2", "n(n-1)/2", "2n+1", 2, "medium"),
                ("If 5th term of AP is 18 and 10th term is 38, find common difference", "4", "5", "6", "3", 1, "hard"),
                ("The 20th term of sequence 100, 95, 90, 85... is", "0", "5", "10", "15", 2, "medium"),
                ("How many terms of AP: 3, 7, 11... make sum 300?", "10", "12", "15", "18", 2, "hard"),
                ("If first term is 'a' and common difference is 'd', nth term is", "a + nd", "a + (n-1)d", "a + (n+1)d", "nd - a", 2, "easy"),
                ("Find the sum of first 15 terms of AP: 4, 9, 14, 19...", "525", "545", "565", "585", 3, "medium"),
                ("Which term of AP: 21, 18, 15, 12... is the first negative term?", "7th", "8th", "9th", "10th", 2, "hard"),
                ("The arithmetic mean of first n odd numbers is", "n", "(n+1)/2", "n/2", "2n-1", 1, "medium"),
                ("In an AP, if a = 5, d = 3, then S₁₀ = ?", "185", "195", "175", "165", 1, "easy"),
                ("The middle term of AP: 1, 4, 7, ..., 97 is", "49", "51", "47", "53", 1, "medium")
            ]
            
            conn.executemany('''
                INSERT INTO questions (question, option1, option2, option3, option4, correct_answer, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', sample_questions)
            print(f"Inserted {len(sample_questions)} sample questions")
        
        conn.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_user(username, email, password):
    conn = get_db_connection()
    hashed_password = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password))
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_questions():
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions').fetchall()
    conn.close()
    return [dict(q) for q in questions]

def add_question(question, option1, option2, option3, option4, correct_answer, difficulty):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO questions (question, option1, option2, option3, option4, correct_answer, difficulty)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (question, option1, option2, option3, option4, correct_answer, difficulty))
    conn.commit()
    conn.close()

def save_result(user_id, score, total, time_taken, percentage):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO quiz_results (user_id, score, total_questions, percentage, time_taken)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, score, total, percentage, time_taken))
    conn.commit()
    conn.close()

def get_user_results(user_id):
    conn = get_db_connection()
    results = conn.execute('''
        SELECT * FROM quiz_results 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in results]

def get_all_results():
    conn = get_db_connection()
    results = conn.execute('''
        SELECT qr.*, u.username, u.email 
        FROM quiz_results qr 
        JOIN users u ON qr.user_id = u.id 
        ORDER BY qr.timestamp DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in results]
