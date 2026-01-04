# app.py
from flask import Flask, render_template, request, jsonify, session
import sqlite3
from datetime import datetime
import hashlib
import re
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# =========================
# VALIDATION FUNCTIONS
# =========================

def is_valid_username(username):
    # only alphabets allowed
    return re.fullmatch(r"[A-Za-z]+", username) is not None


def is_valid_password(password):
    password = password.strip()

    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False

    special_chars = "!@#$%^&*()_+-="
    if not any(c in special_chars for c in password):
        return False

    return True


# =========================
# GEMINI CONFIG
# =========================
GEMINI_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)


class VotingSystem:
    def __init__(self):
        self.conn = sqlite3.connect('voting.db', check_same_thread=False)
        self.setup_database()

    def setup_database(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password_hash TEXT UNIQUE,
                has_voted BOOLEAN DEFAULT FALSE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                candidate_id INTEGER,
                voted_at DATETIME
            )
        """)

        self.conn.commit()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()


voting_system = VotingSystem()

# =========================
# GEMINI RESPONSE
# =========================
def get_gemini_response(user_message, context=""):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(user_message)
        return response.text
    except Exception:
        return "🤖 AI is currently unavailable. Please use voting commands."


# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template('chatbot.html')


@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json['message']
    response = process_message(user_message.strip())
    return jsonify({'response': response})


# =========================
# CHATBOT LOGIC
# =========================
def process_message(message):
    cursor = voting_system.conn.cursor()

    # ---------- REGISTRATION ----------
    if session.get('state') == 'registering':

        parts = message.split()
        if len(parts) < 2:
            return "❌ Use format: username password"

        username = parts[0]
        password = ' '.join(parts[1:])

        if not is_valid_username(username):
            session.pop('state', None)
            return "❌ Username must contain ONLY alphabets."

        if not is_valid_password(password):
            session.pop('state', None)
            return (
                "❌ Weak password.\n"
                "Must contain:\n"
                "• 8+ characters\n"
                "• Uppercase\n"
                "• Lowercase\n"
                "• Number\n"
                "• Special symbol"
            )

        password_hash = voting_system.hash_password(password)

        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            voting_system.conn.commit()
            session.pop('state', None)
            return f"✅ Registered successfully! Login using `{username}`"

        except sqlite3.IntegrityError:
            session.pop('state', None)
            return "❌ Password already exists. Choose a different password."

    # ---------- LOGIN ----------
    if session.get('state') == 'logging_in':

        parts = message.split()
        if len(parts) < 2:
            return "❌ Use format: username password"

        username = parts[0]
        password_hash = voting_system.hash_password(' '.join(parts[1:]))

        cursor.execute(
            "SELECT id FROM users WHERE username=? AND password_hash=?",
            (username, password_hash)
        )
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            session.pop('state', None)
            return f"✅ Welcome {username}! Type `vote` to continue."
        else:
            session.pop('state', None)
            return "❌ Invalid login details."

    # ---------- COMMANDS ----------
    if message.lower() == 'register':
        session['state'] = 'registering'
        return (
            "📝 Registration Rules:\n"
            "• Username: only alphabets\n"
            "• Password must have:\n"
            "  - 8+ characters\n"
            "  - Uppercase\n"
            "  - Lowercase\n"
            "  - Number\n"
            "  - Special character\n\n"
            "👉 Enter: username password"
        )

    if message.lower() == 'login':
        session['state'] = 'logging_in'
        return "🔐 Enter: username password"

    if message.lower() == 'vote':
        if 'user_id' not in session:
            return "❌ Login first."

        cursor.execute("SELECT has_voted FROM users WHERE id=?", (session['user_id'],))
        if cursor.fetchone()[0]:
            return "❌ You have already voted."

        session['state'] = 'voting'
        return "🗳️ Vote:\n1. Alice\n2. Bob\n3. Carol\nType candidate number."

    if session.get('state') == 'voting':
        if message not in ['1', '2', '3']:
            return "❌ Invalid choice."

        cursor.execute(
            "INSERT INTO votes (user_id, candidate_id, voted_at) VALUES (?, ?, ?)",
            (session['user_id'], int(message), datetime.now())
        )
        cursor.execute(
            "UPDATE users SET has_voted=TRUE WHERE id=?",
            (session['user_id'],)
        )
        voting_system.conn.commit()
        session.pop('state', None)
        return "✅ Vote recorded successfully!"

    if message.lower() == 'results':
        cursor.execute("SELECT candidate_id, COUNT(*) FROM votes GROUP BY candidate_id")
        results = cursor.fetchall()
        if not results:
            return "📊 No votes yet."
        return "\n".join([f"Candidate {r[0]}: {r[1]} votes" for r in results])

    if message.lower() == 'logout':
        session.clear()
        return "✅ Logged out."

    if message.lower() == 'help':
        return "📖 Commands: register, login, vote, results, logout"

    return get_gemini_response(message)


# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    app.run(debug=True)
