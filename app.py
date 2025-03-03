from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from config import Config
from utils.content_generator import generate_content, generate_quiz
from utils.json_handler import read_json, write_json, user_exists
from utils.code_executor import CodeExecutor
from utils.question_generator import QuestionGenerator
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# Ensure data directories exist
os.makedirs("data/users", exist_ok=True)
os.makedirs("data/content", exist_ok=True)

code_executor = CodeExecutor()
question_generator = QuestionGenerator()


@app.after_request
def add_no_cache_headers(response):
    """Add headers to prevent browser caching during development"""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if user_exists(username):
            flash("Username already exists")
            return redirect(url_for("register"))

        # Create user profile
        user_data = {
            "username": username,
            "email": email,
            "password": generate_password_hash(password),
            "joined_date": datetime.now().strftime("%Y-%m-%d"),
            "topics": [],
            "progress": {},
            "quiz_scores": {},
        }

        write_json(f"data/users/{username}.json", user_data)
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not user_exists(username):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        user_data = read_json(f"data/users/{username}.json")
        if check_password_hash(user_data["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))


def ensure_user_data_integrity(user_data):
    """Ensure user data has all required fields with proper types"""
    # Fix basic structure
    if "topics" not in user_data:
        user_data["topics"] = []

    if "progress" not in user_data:
        user_data["progress"] = {}

    if "quiz_scores" not in user_data:
        user_data["quiz_scores"] = {}

    # Fix topics and progress relationship
    for topic in user_data["topics"]:
        if topic not in user_data["progress"]:
            user_data["progress"][topic] = 0

    # Fix quiz scores
    for topic, data in list(user_data.get("quiz_scores", {}).items()):
        if not isinstance(data, dict):
            # Remove invalid entries
            user_data["quiz_scores"].pop(topic, None)
            continue

        # Ensure percentage is a float
        if "percentage" in data:
            try:
                data["percentage"] = float(data["percentage"])
            except (ValueError, TypeError):
                # Fix percentage based on score/total
                if "score" in data and "total" in data and data["total"] > 0:
                    data["percentage"] = float((data["score"] / data["total"]) * 100)
                else:
                    # Default to 0 if we can't calculate
                    data["percentage"] = 0.0

    return user_data


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_file = f"data/users/{username}.json"

    if not os.path.exists(user_file):
        flash("User data not found. Please log in again.")
        return redirect(url_for("logout"))

    user_data = read_json(user_file)

    # Fix potential data structure issues
    user_data = ensure_user_data_integrity(user_data)

    # Save fixed data
    write_json(user_file, user_data)

    # Debug output
    app.logger.debug(f"User data for {username}: {json.dumps(user_data)}")

    return render_template("dashboard.html", user=user_data)


@app.route("/topics")
def topics():
    if "username" not in session:
        return redirect(url_for("login"))

    categories = read_json("data/topics.json")
    return render_template("topics.html", categories=categories)


@app.route("/select_topic", methods=["POST"])
def select_topic():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    topic = request.form["topic"]
    category = request.form["category"]

    # Update user's selected topics
    user_data = read_json(f"data/users/{username}.json")
    if topic not in user_data["topics"]:
        user_data["topics"].append(topic)
        user_data["progress"][topic] = 0
    write_json(f"data/users/{username}.json", user_data)

    # Check if content is already generated
    content_file = f'data/content/{username}_{topic.replace(" ", "_")}.json'
    if not os.path.exists(content_file):
        # Generate content
        content = generate_content(topic)
        write_json(content_file, content)

    return redirect(url_for("learn", topic=topic.replace(" ", "_")))


@app.route("/learn/<topic>")
def learn(topic):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    topic_name = topic.replace("_", " ")
    content_file = f"data/content/{username}_{topic}.json"

    # Check if content file exists and regenerate if needed
    if not os.path.exists(content_file):
        content = generate_content(topic_name)
        write_json(content_file, content)
    else:
        content = read_json(content_file)
        # Regenerate if content is minimal (likely fallback content)
        if (
            len(content.get("introduction", "")) < 50
            or len(content.get("sections", [])) < 2
        ):
            content = generate_content(topic_name)
            write_json(content_file, content)

    # Update progress
    user_data = read_json(f"data/users/{username}.json")
    user_data["progress"][topic_name] = 100  # Mark as completed when viewed
    write_json(f"data/users/{username}.json", user_data)

    return render_template("learn.html", content=content, topic=topic_name)


@app.route("/quiz/<topic>", methods=["GET"])
def quiz(topic):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    topic_name = topic.replace("_", " ")
    quiz_file = f"data/content/{username}_{topic}_quiz.json"

    # Check if quiz content exists, if not generate it
    if not os.path.exists(quiz_file):
        # Get the learning content to base the quiz on
        content_file = f"data/content/{username}_{topic}.json"
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

    return render_template("quiz.html", quiz=quiz_data, topic=topic_name)


@app.route("/submit_quiz/<topic>", methods=["POST"])
def submit_quiz(topic):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    topic_name = topic.replace("_", " ")

    quiz_file = f"data/content/{username}_{topic}_quiz.json"
    quiz_data = read_json(quiz_file)

    score = 0
    total = len(quiz_data["questions"])

    # Check answers using q0, q1, q2, etc. as form field names
    for i, question in enumerate(quiz_data["questions"]):
        user_answer = request.form.get(f"q{i}")
        if user_answer == question["correct"]:
            score += 1

    # Update user score
    user_data = read_json(f"data/users/{username}.json")
    user_data["quiz_scores"][topic_name] = {
        "score": score,
        "total": total,
        "percentage": (score / total) * 100,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    write_json(f"data/users/{username}.json", user_data)

    return render_template(
        "quiz_result.html", score=score, total=total, topic=topic_name
    )


@app.route("/coding")
def coding():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("coding.html")


@app.route("/code/<language>")
def code_editor(language):
    if "username" not in session:
        return redirect(url_for("login"))

    if language not in code_executor.supported_languages:
        return redirect(url_for("code_editor", language="python"))

    # Generate a new question for each visit
    problem = question_generator.generate_question(language)

    return render_template("code_editor.html", language=language, problem=problem)


# Update the execute_code route to handle dynamic problems
@app.route("/execute_code", methods=["POST"])
def execute_code():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"})

    data = request.json
    code = data.get("code")
    language = data.get("language")

    # Generate the same problem to get test cases
    problem = question_generator.generate_question(language)

    result = code_executor.execute_code(code, language, problem["test_cases"])

    if result.get("success"):
        output = "Test Results:\n"
        for i, test_result in enumerate(result["results"], 1):
            output += f"\nTest {i}:\n"
            output += f"Input: {test_result['input']}\n"
            output += f"Expected: {test_result['expected']}\n"
            output += f"Actual: {test_result['actual']}\n"
            output += "Status: " + (
                "✓ Passed"
                if test_result["expected"] == test_result["actual"]
                else "✗ Failed"
            )

        if result["all_passed"]:
            output += "\n\nCongratulations! All tests passed! 🎉"
    else:
        output = f"Error:\n{result['error']}"

    return jsonify({"output": output})


@app.route("/get_hint", methods=["POST"])
def get_hint():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"})

    data = request.json
    code = data.get("code")
    language = data.get("language")

    # Generate the same problem to get description
    problem = question_generator.generate_question(language)

    hint = code_executor.generate_hint(code, problem["description"], language)
    return jsonify({"hint": hint})


@app.route("/step-topics")
def step_topics():
    if "username" not in session:
        return redirect(url_for("login"))

    # Get available step-based topics from steps directory
    step_topics = []
    steps_dir = os.path.join("data", "steps")

    for file in os.listdir(steps_dir):
        if file.endswith(".json"):
            topic_content = read_json(os.path.join(steps_dir, file))
            topic_name = list(topic_content.keys())[0]  # Get first key as topic name
            step_topics.append(
                {
                    "name": topic_name,
                    "description": topic_content[topic_name]
                    .get("Introduction", {})
                    .get("Definition", ""),
                }
            )

    return render_template("step_topics.html", topics=step_topics)


@app.route("/steps/<topic>/<int:step>")
def steps(topic, step):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    topic_name = topic.replace("_", " ")

    try:
        content = read_json(f"data/steps/{topic.lower()}.json")
    except:
        flash("Topic content not found")
        return redirect(url_for("step_topics"))

    topic_content = content[topic_name]
    learning_path = list(topic_content.keys())
    total_steps = len(learning_path)

    if step < 0 or step >= total_steps:
        return redirect(url_for("steps", topic=topic, step=0))

    current_section = learning_path[step]
    section_content = topic_content[current_section]

    # Format content structure
    formatted_content = []
    for key, value in section_content.items():
        item = {"title": key, "content": value, "type": "text"}  # default type

        if isinstance(value, list):
            item["type"] = "list"
        elif isinstance(value, dict):
            item["type"] = "dict"
            # Convert nested dict to list of items for easier template handling
            item["dict_items"] = [{"key": k, "value": v} for k, v in value.items()]
        elif key.lower() == "example":
            item["type"] = "code"

        formatted_content.append(item)

    # Update user progress
    user_data = read_json(f"data/users/{username}.json")
    if "step_progress" not in user_data:
        user_data["step_progress"] = {}

    if topic_name not in user_data["step_progress"]:
        user_data["step_progress"][topic_name] = {
            "current_step": 0,
            "total_steps": total_steps,
            "completed": False,
            "progress": 0.0,
        }

    if step > user_data["step_progress"][topic_name]["current_step"]:
        user_data["step_progress"][topic_name]["current_step"] = step
        user_data["step_progress"][topic_name]["progress"] = (step / total_steps) * 100

        if step >= total_steps - 1:
            user_data["step_progress"][topic_name]["completed"] = True
            user_data["step_progress"][topic_name]["progress"] = 100.0

    write_json(f"data/users/{username}.json", user_data)

    return render_template(
        "steps.html",
        topic=topic_name,
        current_step=step,
        total_steps=total_steps,
        progress=user_data["step_progress"][topic_name]["progress"],
        learning_path=learning_path,
        section_name=current_section,
        content=formatted_content,
    )


if __name__ == "__main__":
    app.run(debug=True)
