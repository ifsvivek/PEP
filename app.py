from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from config import Config
from utils.content_generator import generate_content, generate_quiz
from utils.json_handler import read_json, write_json, user_exists
from utils.code_executor import CodeExecutor
import uuid
app = Flask(__name__)
app.config.from_object(Config)

# Ensure data directories exist
os.makedirs('data/users', exist_ok=True)
os.makedirs('data/content', exist_ok=True)

code_executor = CodeExecutor()

@app.after_request
def add_no_cache_headers(response):
    """Add headers to prevent browser caching during development"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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

def ensure_user_data_integrity(user_data):
    """Ensure user data has all required fields with proper types"""
    # Fix basic structure
    if 'topics' not in user_data:
        user_data['topics'] = []
    
    if 'progress' not in user_data:
        user_data['progress'] = {}
        
    if 'quiz_scores' not in user_data:
        user_data['quiz_scores'] = {}
    
    # Fix topics and progress relationship
    for topic in user_data['topics']:
        if topic not in user_data['progress']:
            user_data['progress'][topic] = 0
    
    # Fix quiz scores
    for topic, data in list(user_data.get('quiz_scores', {}).items()):
        if not isinstance(data, dict):
            # Remove invalid entries
            user_data['quiz_scores'].pop(topic, None)
            continue
            
        # Ensure percentage is a float
        if 'percentage' in data:
            try:
                data['percentage'] = float(data['percentage'])
            except (ValueError, TypeError):
                # Fix percentage based on score/total
                if 'score' in data and 'total' in data and data['total'] > 0:
                    data['percentage'] = float((data['score'] / data['total']) * 100)
                else:
                    # Default to 0 if we can't calculate
                    data['percentage'] = 0.0
    
    return user_data

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_file = f'data/users/{username}.json'
    
    if not os.path.exists(user_file):
        flash('User data not found. Please log in again.')
        return redirect(url_for('logout'))
    
    user_data = read_json(user_file)
    
    # Fix potential data structure issues
    user_data = ensure_user_data_integrity(user_data)
    
    # Save fixed data
    write_json(user_file, user_data)
    
    # Debug output
    app.logger.debug(f"User data for {username}: {json.dumps(user_data)}")
    
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



CODING_PROBLEMS = {
    'python': [
        {
            'id': 'py1',
            'title': 'Sum of Two Numbers',
            'description': 'Write a function that takes two numbers as input and returns their sum.',
            'example': 'Input: 5 3\nOutput: 8',
            'template': 'def sum_numbers(a, b):\n    # Your code here\n    pass\n\n# Read input\na, b = map(int, input().split())\nresult = sum_numbers(a, b)\nprint(result)',
            'test_cases': [
                {'input': '5 3', 'output': '8'},
                {'input': '10 20', 'output': '30'},
                {'input': '0 0', 'output': '0'}
            ]
        }
    ],
    'javascript': [
        {
            'id': 'js1',
            'title': 'String Reversal',
            'description': 'Write a function that reverses a string.',
            'example': 'Input: hello\nOutput: olleh',
            'template': 'function reverseString(str) {\n    // Your code here\n}\n\n// Read input\nconst input = require("readline").createInterface({\n    input: process.stdin,\n    output: process.stdout\n});\n\ninput.on("line", (line) => {\n    console.log(reverseString(line));\n    input.close();\n});',
            'test_cases': [
                {'input': 'hello', 'output': 'olleh'},
                {'input': 'javascript', 'output': 'tpircsavaj'},
                {'input': 'racecar', 'output': 'racecar'}
            ]
        }
    ],
    'c': [
        {
            'id': 'c1',
            'title': 'Factorial Calculator',
            'description': 'Write a program that calculates the factorial of a number.',
            'example': 'Input: 5\nOutput: 120',
            'template': '#include <stdio.h>\n\nint factorial(int n) {\n    // Your code here\n    return 0;\n}\n\nint main() {\n    int n;\n    scanf("%d", &n);\n    printf("%d\\n", factorial(n));\n    return 0;\n}',
            'test_cases': [
                {'input': '5', 'output': '120'},
                {'input': '3', 'output': '6'},
                {'input': '0', 'output': '1'}
            ]
        }
    ]
}

@app.route('/code/<language>')
def code_editor(language):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if language not in code_executor.supported_languages:
        return redirect(url_for('code_editor', language='python'))
    
    # Get the first problem for the language (you can add problem selection later)
    problem = CODING_PROBLEMS[language][0]
    
    return render_template('code_editor.html', language=language, problem=problem)

@app.route('/execute_code', methods=['POST'])
def execute_code():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'})
    
    data = request.json
    code = data.get('code')
    language = data.get('language')
    problem_id = data.get('problem_id')
    
    # Find the problem and its test cases
    problem = next((p for problems in CODING_PROBLEMS.values() 
                   for p in problems if p['id'] == problem_id), None)
    
    if not problem:
        return jsonify({'error': 'Problem not found'})
    
    result = code_executor.execute_code(code, language, problem['test_cases'])
    
    if result.get('success'):
        output = "Test Results:\n"
        for i, test_result in enumerate(result['results'], 1):
            output += f"\nTest {i}:\n"
            output += f"Input: {test_result['input']}\n"
            output += f"Expected: {test_result['expected']}\n"
            output += f"Actual: {test_result['actual']}\n"
            output += "Status: " + ("✓ Passed" if test_result['expected'] == test_result['actual'] 
                                  else "✗ Failed")
        
        if result['all_passed']:
            output += "\n\nCongratulations! All tests passed! 🎉"
    else:
        output = f"Error:\n{result['error']}"
    
    return jsonify({'output': output})

@app.route('/get_hint', methods=['POST'])
def get_hint():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'})
    
    data = request.json
    code = data.get('code')
    language = data.get('language')
    problem_id = data.get('problem_id')
    
    # Find the problem
    problem = next((p for problems in CODING_PROBLEMS.values() 
                   for p in problems if p['id'] == problem_id), None)
    
    if not problem:
        return jsonify({'error': 'Problem not found'})
    
    hint = code_executor.generate_hint(code, problem['description'], language)
    return jsonify({'hint': hint})

@app.route('/coding')
def coding():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('coding.html')

if __name__ == '__main__':
    app.run(debug=True)
