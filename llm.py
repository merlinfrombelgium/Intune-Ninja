# Chat with an intelligent assistant in your terminal
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

history = [
    {"role": "system", "content": "You are an AI assistant specialized in interpreting Microsoft Graph API responses and explaining them in the context of Microsoft Intune management. Your task is to analyze the API response and provide a clear, concise explanation of what the data means and how it relates to the user's original query about Intune management."},
    {"role": "user", "content": "Show me all intune windows devices and only device name and os version"},
    {"role": "assistant", "content": "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=operatingSystem eq 'Windows'&$select=deviceName,osVersion"},
    {"role": "user", "content": "Show me all Entra ID windows devices"},
    {"role": "assistant", "content": "https://graph.microsoft.com/v1.0/Devices?$filter=operatingSystem eq 'Windows'"},
    {"role": "user", "content": "Show me all Entra ID windows devices and only device name and management type"},
    {"role": "assistant", "content": "https://graph.microsoft.com/v1.0/devices?$filter=operatingSystem eq 'Windows'&$select=displayName,managementType"},
    {"role": "user", "content": "Show me all co-managed windows devices"},
    {"role": "assistant", "content": "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=managementAgent eq 'configurationManagerClientMDM' and operatingSystem eq 'Windows'&$select=deviceName,managementAgent"},
    {"role": "user", "content": "Show me all intune only managed windows devices with only device name and management type"},
    {"role": "assistant", "content": "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=managementAgent eq 'MDM' and operatingSystem eq 'Windows'&$select=deviceName,managementAgent"},
    {"role": "user", "content": "Show me the configuration profile with the name \"Enable Remote desktop\""},
    {"role": "assistant", "content": "https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=name eq 'Enable Remote Desktop'"},
    {"role": "user", "content": "Show me all configuration profiles with the word: Enable"},
    {"role": "assistant", "content": "https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=contains(name,'Enable')"},
    {"role": "user", "content": "Show me the settings from the configuration profile \"Enable Remote desktop\""},
    {"role": "assistant", "content": "https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=name eq 'Enable Remote Desktop'&$select=id"},
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
    response = client.chat.completions.create(
        model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
        messages=[{"role": "user", "content": instruction}],
        temperature=0.4,
    )
    return response.choices[0].delta.content

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