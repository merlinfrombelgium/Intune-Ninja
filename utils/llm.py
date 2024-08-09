# Chat with an intelligent assistant in your terminal
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

history = [
    {"role": "system", "content": open("../prompts/system_prompt.md").read().strip()},
]

def chat():
    global history
    
    while True:  # Enter chat mode
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:  # Allow exit from chat
            break
        
        history.append({"role": "user", "content": user_input})
        completion = client.chat.completions.create(
            model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
            messages=history,
            temperature=0.7,
            stream=True,
        )

        new_message = {"role": "assistant", "content": ""}  # Moved inside the loop

        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                new_message["content"] += chunk.choices[0].delta.content

        # Append new_message to history after it has content
        history.append(new_message)  
        print()

def assistant(instruction):
    import json
    import re

    # Read the content of the intune_examples.md file
    with open("../prompts/intune_examples.md", "r") as file:
        lines = file.readlines()

    # Transform each line into the desired JSON format using regex
    pattern = r'^(?P<role>[^:]+):\s*(?P<content>.+)$'  # Match any word(s) before the colon

    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            role = match.group("role").strip().upper()  # Convert role to uppercase
            content = match.group("content").strip()
            # print(f'{{"role": "{role}", "content": "{content}"}}') # Uncomment to see the JSON output in the console

    response = client.chat.completions.create(
        model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
        messages=[
            {"role": "system", "content": history[0]["content"]},
            {"role": "user", "content": instruction}
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content

def get_embedding(text, model="nomic-ai/nomic-embed-text-v1.5-GGUF"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

def print_history():
    import json
    gray_color = "\033[90m"
    reset_color = "\033[0m"
    print(f"{gray_color}\n{'-'*20} History dump {'-'*20}\n")
    print(json.dumps(history, indent=2))
    print(f"\n{'-'*55}\n{reset_color}")

# Main chat loop
if __name__ == "__main__":
    while True:
        chat()
        # Uncomment the next line to see chat history
        # print_history()
        history.append({"role": "user", "content": input("> ")})

# Example usage of get_embedding
# print(get_embedding("Once upon a time, there was a cat."))