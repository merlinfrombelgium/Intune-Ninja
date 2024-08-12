import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json

def main():
    load_dotenv()  # Load environment variables from .env file
    import gradio as gr

    def chat_with_llm(user_input, state=None):  # Added state parameter
        response_text = ""  # Initialize an empty string to accumulate responses
        # Use a generator to stream responses
        for response in assistant(user_input):  # Assuming assistant can yield responses
            response_text += response  # Accumulate the response
            yield response_text  # Return the accumulated response as plain text

    iface = gr.ChatInterface(fn=chat_with_llm, title="Copilot for Intune", description="Use AI to get insights on Intune managed devices")  # Changed to ChatInterface
    iface.launch()
     
if __name__ == "__main__":
    main()