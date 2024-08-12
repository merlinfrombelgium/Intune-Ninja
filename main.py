import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json

def main():
    load_dotenv()  # Load environment variables from .env file
    import gradio as gr

    def chat_with_ai(message, history):  # Use a mutable default argument
        history_openai_format = []
        for human, ai_assistant in history:
            history_openai_format.append({"role": "user", "content": human })
            history_openai_format.append({"role": "assistant", "content": ai_assistant})
        history_openai_format.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
            messages=history_openai_format,
            temperature=0.4,
            stream=True,  # Enable streaming
        )

        partial_message = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                partial_message = partial_message + chunk.choices[0].delta.content
                yield partial_message

    iface = gr.ChatInterface(fn=chat_with_ai, title="Copilot for Intune", description="Use AI to get insights on Intune managed devices")  # Changed to ChatInterface
    iface.launch()
     
if __name__ == "__main__":
    main()