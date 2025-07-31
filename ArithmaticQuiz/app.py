from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import random
import time
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'arithmetic_quiz_secret_key_2025'

DATABASE = 'quiz.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with proper schema handling"""
    try:
        conn = get_db_connection()
        
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
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        if get_user(username):
            flash('Username already exists!', 'error')
            return render_template('register.html')
        
        try:
            create_user(username, email, password)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            user = get_user(username)
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password!', 'error')
        except Exception as e:
            flash('Login failed. Please try again.', 'error')
            print(f"Login error: {e}")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user_results = get_user_results(session['user_id'])
        return render_template('dashboard.html', results=user_results)
    except Exception as e:
        flash('Error loading dashboard.', 'error')
        print(f"Dashboard error: {e}")
        return redirect(url_for('index'))

@app.route('/prerequisites')
def prerequisites():
    return render_template('prerequisites.html')

@app.route('/tutorials')
def tutorials():
    return render_template('tutorials.html')

@app.route('/quiz')
def quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        questions = get_questions()
        if not questions:
            flash('No questions available. Please contact administrator.', 'error')
            return redirect(url_for('dashboard'))
        
        # Shuffle questions and store in session
        random.shuffle(questions)
        session['questions'] = questions[:10]  # Limit to 10 questions
        session['current_question'] = 0
        session['score'] = 0
        session['start_time'] = time.time()
        session['answers'] = []
        
        return render_template('quiz.html', 
                             question=session['questions'][0], 
                             question_num=1, 
                             total=len(session['questions']))
    except Exception as e:
        flash('Error starting quiz. Please try again.', 'error')
        print(f"Quiz error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/answer', methods=['POST'])
def answer():
    if 'user_id' not in session or 'questions' not in session:
        return redirect(url_for('quiz'))
    
    try:
        current_q = session['current_question']
        selected_answer = int(request.form['answer'])
        correct_answer = session['questions'][current_q]['correct_answer']
        
        # Store answer
        session['answers'].append({
            'question': session['questions'][current_q]['question'],
            'selected': selected_answer,
            'correct': correct_answer,
            'is_correct': selected_answer == correct_answer,
            'options': [
                session['questions'][current_q]['option1'],
                session['questions'][current_q]['option2'],
                session['questions'][current_q]['option3'],
                session['questions'][current_q]['option4']
            ]
        })
        
        # Update score
        if selected_answer == correct_answer:
            session['score'] += 1
        
        session['current_question'] += 1
        
        # Check if quiz is complete
        if session['current_question'] >= len(session['questions']):
            return redirect(url_for('result'))
        
        # Next question
        next_question = session['questions'][session['current_question']]
        return render_template('quiz.html', 
                             question=next_question, 
                             question_num=session['current_question'] + 1, 
                             total=len(session['questions']))
    except Exception as e:
        flash('Error processing answer. Please try again.', 'error')
        print(f"Answer error: {e}")
        return redirect(url_for('quiz'))

@app.route('/result')
def result():
    if 'user_id' not in session or 'score' not in session:
        return redirect(url_for('quiz'))
    
    try:
        end_time = time.time()
        time_taken = int(end_time - session['start_time'])
        score = session['score']
        total = len(session['questions'])
        percentage = (score / total) * 100
        
        # Save result to database
        save_result(session['user_id'], score, total, time_taken, percentage)
        
        # Store for display
        answers = session.get('answers', [])
        
        # Clear quiz session data
        quiz_keys = ['questions', 'current_question', 'score', 'start_time', 'answers']
        for key in quiz_keys:
            session.pop(key, None)
        
        return render_template('result.html', 
                             score=score, 
                             total=total, 
                             percentage=percentage, 
                             time_taken=time_taken,
                             answers=answers)
    except Exception as e:
        flash('Error displaying results. Please try again.', 'error')
        print(f"Result error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Simple admin check
    if session['username'] != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        questions = get_questions()
        all_results = get_all_results()
        return render_template('admin.html', questions=questions, results=all_results)
    except Exception as e:
        flash('Error loading admin panel.', 'error')
        print(f"Admin error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/add_question', methods=['POST'])
def add_question_route():
    if 'user_id' not in session or session['username'] != 'admin':
        return redirect(url_for('dashboard'))
    
    try:
        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_answer = int(request.form['correct_answer'])
        difficulty = request.form['difficulty']
        
        add_question(question, option1, option2, option3, option4, correct_answer, difficulty)
        flash('Question added successfully!', 'success')
    except Exception as e:
        flash('Error adding question. Please try again.', 'error')
        print(f"Add question error: {e}")
    
    return redirect(url_for('admin'))

@app.route('/all_results')
def all_results():
    if 'user_id' not in session or session['username'] != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        results = get_all_results()
        return render_template('all_results.html', results=results)
    except Exception as e:
        flash('Error loading results.', 'error')
        print(f"All results error: {e}")
        return redirect(url_for('admin'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Initialize database and start application
if __name__ == '__main__':
    print("Starting Arithmetic Progression Quiz Application...")
    
    try:
        # Initialize database
        print("Initializing database...")
        init_db()
        
        # Start Flask server
        print("Starting Flask server...")
        print("Server will be available at: http://127.0.0.1:5000")
        app.run(host='127.0.0.1', port=5000, debug=True)
        
    except Exception as e:
        print(f"Error starting application: {e}")
        print("Please check if port 5000 is available or try a different port.")
