import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json

def main():
    load_dotenv()  # Load environment variables from .env file
    import gradio as gr

    def chat_with_llm(user_input):
        response = assistant(user_input)  # Using the assistant function from llm.py
        return json.dumps({"response": response})

    iface = gr.Interface(fn=chat_with_llm, inputs="text", outputs="json", title="Copilot for Intune", description="Interact with the LLM to get insights on Intune managed devices")
    iface.launch()

if __name__ == "__main__":
    main()