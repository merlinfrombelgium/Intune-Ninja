import os
from openai import OpenAI

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the prompts directory
prompts_dir = os.path.join(current_dir, '..', 'prompts')

# Initialize the OpenAI client
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Load the system prompt from the relative path
history = [
    {"role": "system", "content": open(os.path.join(prompts_dir, "system_prompt.md")).read().strip()},
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
            temperature=0.5,
            stream=True,
            max_tokens=1000,
        )

        new_message = {"role": "assistant", "content": ""}  # Moved inside the loop

        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                new_message["content"] += chunk.choices[0].delta.content

        # Append new_message to history after it has content
        history.append(new_message)  
        print()

def assistant(instruction, system_prompt=None):
    import json
    import re

    # Read the content of the intune_examples.md file
    with open(os.path.join(prompts_dir, "intune_examples.md"), "r") as file:
        lines = file.readlines()

    # Transform each line into the desired JSON format using regex
    pattern = r'^(?P<role>[^:]+):\s*(?P<content>.+)$'  # Match any word(s) before the colon

    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            role = match.group("role").strip().upper()  # Convert role to uppercase
            content = match.group("content").strip()

    # Use the provided system_prompt if available, otherwise use the default from history
    system_prompt_content = system_prompt if system_prompt else history[0]["content"]

    response = client.chat.completions.create(
        model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
        messages=[
            {"role": "system", "content": system_prompt_content},
            {"role": "user", "content": instruction}
        ],
        temperature=0.4,
        stream=True,  # Enable streaming
    )

    # Stream the response
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content  # Yield each chunk of the reasoning

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