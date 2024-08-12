import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json

def main():
    load_dotenv()  # Load environment variables from .env file
    import gradio as gr

    def chat_with_llm(user_input):
        response_text = ""  # Initialize an empty string to accumulate responses
        # Use a generator to stream responses
        for response in assistant(user_input):  # Assuming assistant can yield responses
            response_text += response  # Accumulate the response
            yield response_text  # Return the accumulated response as plain text

    iface = gr.Interface(fn=chat_with_llm, inputs="text", outputs="text", title="Copilot for Intune", description="Interact with the LLM to get insights on Intune managed devices", allow_flagging=False)
    iface.launch()
     
if __name__ == "__main__":
    main()