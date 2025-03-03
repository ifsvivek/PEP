from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from config import Config
from utils.content_generator import generate_content, generate_quiz
from utils.json_handler import read_json, write_json, user_exists

app = Flask(__name__)
app.config.from_object(Config)

# Ensure data directories exist
os.makedirs('data/users', exist_ok=True)
os.makedirs('data/content', exist_ok=True)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if user_exists(username):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Create user profile
        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'joined_date': datetime.now().strftime("%Y-%m-%d"),
            'topics': [],
            'progress': {},
            'quiz_scores': {}
        }
        
        write_json(f'data/users/{username}.json', user_data)
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not user_exists(username):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        user_data = read_json(f'data/users/{username}.json')
        if check_password_hash(user_data['password'], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_data = read_json(f'data/users/{username}.json')
    return render_template('dashboard.html', user=user_data)

@app.route('/topics')
def topics():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    categories = read_json('data/topics.json')
    return render_template('topics.html', categories=categories)

@app.route('/select_topic', methods=['POST'])
def select_topic():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    topic = request.form['topic']
    category = request.form['category']
    
    # Update user's selected topics
    user_data = read_json(f'data/users/{username}.json')
    if topic not in user_data['topics']:
        user_data['topics'].append(topic)
        user_data['progress'][topic] = 0
    write_json(f'data/users/{username}.json', user_data)
    
    # Check if content is already generated
    content_file = f'data/content/{username}_{topic.replace(" ", "_")}.json'
    if not os.path.exists(content_file):
        # Generate content
        content = generate_content(topic)
        write_json(content_file, content)
    
    return redirect(url_for('learn', topic=topic.replace(" ", "_")))

@app.route('/learn/<topic>')
def learn(topic):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    topic_name = topic.replace("_", " ")
    content_file = f'data/content/{username}_{topic}.json'
    
    # Check if content file exists and regenerate if needed
    if not os.path.exists(content_file):
        content = generate_content(topic_name)
        write_json(content_file, content)
    else:
        content = read_json(content_file)
        # Regenerate if content is minimal (likely fallback content)
        if len(content.get("introduction", "")) < 50 or len(content.get("sections", [])) < 2:
            content = generate_content(topic_name)
            write_json(content_file, content)
    
    # Update progress
    user_data = read_json(f'data/users/{username}.json')
    user_data['progress'][topic_name] = 100  # Mark as completed when viewed
    write_json(f'data/users/{username}.json', user_data)
    
    return render_template('learn.html', content=content, topic=topic_name)

@app.route('/quiz/<topic>', methods=['GET'])
def quiz(topic):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    topic_name = topic.replace("_", " ")
    quiz_file = f'data/content/{username}_{topic}_quiz.json'
    
    # Check if quiz content exists, if not generate it
    if not os.path.exists(quiz_file):
        # Get the learning content to base the quiz on
        content_file = f'data/content/{username}_{topic}.json'
        if not os.path.exists(content_file):
            # If no content exists, generate it first
            content = generate_content(topic_name)
            write_json(content_file, content)
        else:
            content = read_json(content_file)
        
        # Generate quiz based on content
        quiz_data = generate_quiz(content)
        write_json(quiz_file, quiz_data)
    else:
        quiz_data = read_json(quiz_file)
    
    return render_template('quiz.html', quiz=quiz_data, topic=topic_name)

@app.route('/submit_quiz/<topic>', methods=['POST'])
def submit_quiz(topic):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    topic_name = topic.replace("_", " ")
    
    quiz_file = f'data/content/{username}_{topic}_quiz.json'
    quiz_data = read_json(quiz_file)
    
    score = 0
    total = len(quiz_data['questions'])
    
    # Check answers using q0, q1, q2, etc. as form field names
    for i, question in enumerate(quiz_data['questions']):
        user_answer = request.form.get(f'q{i}')
        if user_answer == question['correct']:
            score += 1
    
    # Update user score
    user_data = read_json(f'data/users/{username}.json')
    user_data['quiz_scores'][topic_name] = {
        'score': score,
        'total': total,
        'percentage': (score / total) * 100,
        'date': datetime.now().strftime("%Y-%m-%d")
    }
    write_json(f'data/users/{username}.json', user_data)
    
    return render_template('quiz_result.html', score=score, total=total, topic=topic_name)

if __name__ == '__main__':
    app.run(debug=True)
