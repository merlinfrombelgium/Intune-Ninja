import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json

def main():
    load_dotenv()  # Load environment variables from .env file
    import gradio as gr
    from gradio import MessageDict

    #global graph_api_request_url  # Declare the variable as global
    graph_api_request_url = ""  # Initialize the variable
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to the prompts directory
    prompts_dir = os.path.join(current_dir, 'prompts')
    
    system_prompt = {"role": "system", "content": open(os.path.join(prompts_dir, "system_prompt.md")).read().strip()}

    def chat_with_ai(message, history):
        # Instantiate MSGraphAPI
        ms_graph_api = MSGraphAPI()
        
        messages = []
        #messages.append(system_prompt)
        
        # Filter out empty history entries
        filtered_history = [entry for entry in history if entry]  # Ensure no empty entries
        messages.extend(filtered_history)
        
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
            messages=messages,
            temperature=0.2,
            stream=True,
            max_tokens=1000,            
        )

        # Process the streaming response
        partial_response = ""
        for stream_response in response:
            if stream_response.choices[0].delta.content is not None:
                partial_response += stream_response.choices[0].delta.content
                yield [(message, partial_response)]

        # Update the graph_api_url value after processing the complete response
        #graph_api_request_url = partial_message.split('\n')[0].strip('*')  # Get the first line as the URL
        #print("Graph API Request URL: " + graph_api_request_url)
        
        # Return the output in the expected format
        #print([(message, partial_message)])
        return [(message, partial_response)] #, gr.update(value=graph_api_request_url)
    
    with gr.Blocks() as demo:
        gr.Markdown("## Copilot for Intune")
        gr.Markdown("Use AI to get insights on Intune managed devices")
        chatbot = gr.Chatbot()
        user_input = gr.Textbox(label="User Input", placeholder="Enter your query here...")
        user_input.submit(chat_with_ai, [user_input, chatbot], [chatbot])
        graph_api_url = gr.Textbox(label="Graph API Request URL", placeholder="https://graph.microsoft.com/v1.0/...")
        #graph_api_url.change(fn=chat_with_ai, inputs=user_input, outputs=graph_api_url)
        #graph_api_output = gr.Textbox(label="Graph API Response")
        #print("Graph API URL: " + graph_api_url.value)
        #iface.api_url = graph_api_url
        #iface.output_api = graph_api_output

    demo.queue()
    demo.launch(debug=True)
     
if __name__ == "__main__":
    main()