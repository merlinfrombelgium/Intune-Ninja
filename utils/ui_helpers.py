from utils.ai_chat import chat_with_ai

def generate_placeholder_title(message, system_prompt):
    prompt = f"Generate a short, concise title (max 5 words) for this conversation based on the following message: '{message}'"
    for response in chat_with_ai(prompt, [], system_prompt):
        title = response[0][1].strip('"').capitalize()
    return title