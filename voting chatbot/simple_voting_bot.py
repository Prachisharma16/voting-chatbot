# simple_voting_bot
import sqlite3
import hashlib
from datetime import datetime
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyAkPNxvn5N1Du8_ApRDviI_5b7XnrU6kQk" # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_response(user_message, context=""):
    """Get AI response from Gemini"""
    try:
        # Create the model
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]

        model = genai.GenerativeModel(model_name="gemini-2.5-flash", 
                                    generation_config=generation_config,
                                    safety_settings=safety_settings)
        
        # Create context-aware prompt
        prompt = f"""
        You are an AI assistant for a voting system chatbot. Your role is to help users with voting-related queries and provide friendly, helpful responses.

        Context: {context}
        
        User Message: {user_message}
        
        Available voting system commands:
        - register: Create new account
        - login: Sign in to account
        - vote: Cast vote
        - results: View election results
        - logout: Sign out
        - help: Show help
        - quit: Exit program
        
        Please respond in a helpful, conversational manner. If the user asks about voting procedures, candidates, or election information, provide helpful information. For technical commands like registration, voting, etc., guide them to use the specific commands.
        
        Keep responses concise and friendly. If the query is not related to voting, politely redirect to voting topics.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🤖 I'm having trouble connecting to AI right now. Please use the voting commands directly."

class SimpleVotingChatbot:
    def __init__(self):
        self.setup_database()
        self.current_user = None
        
    def setup_database(self):
        self.conn = sqlite3.connect('simple_voting.db')
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                has_voted BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                candidate_name TEXT,
                voted_at DATETIME
            )
        ''')
        self.conn.commit()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def is_conversational_query(self, message):
        """Check if the message is a conversational query for Gemini"""
        conversational_phrases = [
            'what', 'how', 'why', 'when', 'where', 'who', 'can you', 'could you',
            'would you', 'tell me', 'explain', 'help me', 'i need', 'i want',
            'question', 'advice', 'suggest', 'recommend', '?'
        ]
        
        # Check if message is conversational (not a direct command)
        if (not message in ['register', 'login', 'vote', 'results', 'logout', 'help', 'quit', 'exit'] and
            any(phrase in message for phrase in conversational_phrases)):
            return True
        
        # Also use Gemini for general greetings
        if message in ['hello', 'hi', 'hey', 'greetings']:
            return True
            
        return False
    
    def start_chat(self):
        print("🤖 Welcome to Simple Voting Chatbot with AI Assistant!")
        print("Type 'help' for commands or 'quit' to exit\n")
        print("💡 You can also ask me questions about voting, candidates, or election procedures!\n")
        
        while True:
            if self.current_user:
                prompt = f"[{self.current_user}]> "
            else:
                prompt = "> "
            
            message = input(prompt).strip().lower()
            
            if message in ['quit', 'exit']:
                print("Goodbye! 👋")
                break
            
            # Check if this is a conversational query
            if self.is_conversational_query(message):
                context = "User is interacting with terminal voting system."
                if self.current_user:
                    context += f" Current user: {self.current_user}"
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT has_voted FROM users WHERE username = ?", (self.current_user,))
                    user = cursor.fetchone()
                    if user and user[0]:
                        context += " - User has already voted."
                    else:
                        context += " - User has not voted yet."
                
                ai_response = get_gemini_response(message, context)
                print(f"🤖 AI: {ai_response}\n")
                continue
            
            # Process commands
            if message == 'help':
                self.show_help()
            elif message == 'register':
                self.register()
            elif message == 'login':
                self.login()
            elif message == 'vote':
                self.vote()
            elif message == 'results':
                self.show_results()
            elif message == 'logout':
                self.logout()
            else:
                print("❌ Unknown command. Type 'help' for available commands or ask me a question.")
    
    def show_help(self):
        print("\n📖 Available Commands:")
        print("register - Create new account")
        print("login    - Sign in to your account")
        print("vote     - Cast your vote")
        print("results  - View current results")
        print("logout   - Sign out")
        print("help     - Show this help")
        print("quit     - Exit the program")
        print("\n💡 AI Features:")
        print("Ask questions about voting, candidates, or election procedures!")
        print("Examples:")
        print("- How does voting work?")
        print("- Tell me about the candidates")
        print("- What is election security?")
        print("- Explain the voting process\n")
    
    def register(self):
        username = input("Choose username: ").strip()
        password = input("Choose password: ").strip()
        
        if not username or not password:
            print("❌ Username and password cannot be empty")
            return
        
        password_hash = self.hash_password(password)
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            self.conn.commit()
            print("✅ Registration successful! You can now login.")
        except sqlite3.IntegrityError:
            print("❌ Username already exists. Please choose another one.")
    
    def login(self):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        password_hash = self.hash_password(password)
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT id, username, has_voted FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        user = cursor.fetchone()
        
        if user:
            self.current_user = user[1]
            print(f"✅ Welcome {self.current_user}!")
        else:
            print("❌ Invalid credentials.")
    
    def vote(self):
        if not self.current_user:
            print("❌ Please login first.")
            return
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT has_voted FROM users WHERE username = ?", (self.current_user,))
        user = cursor.fetchone()
        
        if user and user[0]:
            print("❌ You have already voted!")
            return
        
        print("\n🗳️ Student Council Election 2024")
        print("\nAvailable Candidates:")
        print("1. Alice Johnson - Progress Party (Focused on student welfare)")
        print("2. Bob Smith - Unity Alliance (Advocating for better facilities)")
        print("3. Carol Davis - Future Forward (Technology and innovation)")
        
        choice = input("\nEnter candidate number (1-3): ").strip()
        
        if choice in ['1', '2', '3']:
            candidates = {'1': 'Alice Johnson', '2': 'Bob Smith', '3': 'Carol Davis'}
            candidate_name = candidates[choice]
            
            # Get user ID
            cursor.execute("SELECT id FROM users WHERE username = ?", (self.current_user,))
            user_id = cursor.fetchone()[0]
            
            # Record vote
            cursor.execute(
                "INSERT INTO votes (user_id, candidate_name, voted_at) VALUES (?, ?, ?)",
                (user_id, candidate_name, datetime.now())
            )
            cursor.execute(
                "UPDATE users SET has_voted = TRUE WHERE username = ?",
                (self.current_user,)
            )
            self.conn.commit()
            
            print(f"✅ Vote cast for {candidate_name}! Thank you for voting. 🗳️")
        else:
            print("❌ Invalid choice. Please select 1, 2, or 3.")
    
    def show_results(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT candidate_name, COUNT(*) as vote_count 
            FROM votes 
            GROUP BY candidate_name 
            ORDER BY vote_count DESC
        ''')
        results = cursor.fetchall()
        
        print("\n📊 Election Results:")
        total_votes = sum(result[1] for result in results)
        
        for candidate, votes in results:
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            print(f"• {candidate}: {votes} votes ({percentage:.1f}%)")
        
        print(f"\nTotal votes: {total_votes}")
        
        if total_votes == 0:
            print("No votes have been cast yet.")
    
    def logout(self):
        if self.current_user:
            print(f"✅ Goodbye {self.current_user}!")
            self.current_user = None
        else:
            print("❌ You are not logged in.")

if __name__ == "__main__":
    chatbot = SimpleVotingChatbot()
    chatbot.start_chat()