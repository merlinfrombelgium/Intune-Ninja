import sqlite3
import json

def init_db():
    conn = sqlite3.connect('conversation_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY, title TEXT UNIQUE, messages TEXT)''')
    conn.commit()
    conn.close()

def load_conversation_history():
    conn = sqlite3.connect('conversation_history.db')
    c = conn.cursor()
    c.execute("SELECT title FROM conversations")
    conversations = c.fetchall()
    conn.close()
    return [conv[0] for conv in conversations]

def save_new_conversation(title, messages):
    conn = sqlite3.connect('conversation_history.db')
    c = conn.cursor()
    messages_json = json.dumps(messages)
    try:
        c.execute("INSERT OR REPLACE INTO conversations (title, messages) VALUES (?, ?)",
                  (title, messages_json))
        conn.commit()
        return True, "Conversation saved successfully"
    except sqlite3.IntegrityError:
        return False, f"Error: Conversation title '{title}' already exists"
    except Exception as e:
        return False, f"Error saving conversation: {str(e)}"
    finally:
        conn.close()

def load_conversation(title):
    conn = sqlite3.connect('conversation_history.db')
    c = conn.cursor()
    c.execute("SELECT messages FROM conversations WHERE title = ?", (title,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else []

def delete_conversation(title):
    conn = sqlite3.connect('conversation_history.db')
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE title = ?", (title,))
    conn.commit()
    conn.close()