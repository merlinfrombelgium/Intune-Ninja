import os
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
import json
from openai import OpenAI
import gradio as gr
#from pydantic import BaseModel, ValidationError

#working_dir = os.path.dirname(os.path.abspath(__file__))  # Define the root directory of the script as the working directory

def call_graph_api(api_url):
    """Call the Graph API and return the response."""
    ms_graph_api = MSGraphAPI()  # Instantiate MSGraphAPI
    try:
        api_response = ms_graph_api.call_api(api_url)
        return json.dumps(api_response, indent=2)  # Format the response as a JSON string
    except Exception as e:
        return f"Error calling API: {str(e)}"

def initialize():
    load_dotenv()  # Load environment variables from .env file

    client = OpenAI(api_key=os.getenv('LLM_API_KEY'))
    #global graph_api_request_url  # Declare the variable as global
    graph_api_request_url = ""  # Initialize the variable
    
    system_prompt_file = os.sep.join([os.curdir, "prompts", "system_prompt.md"])
    print("system prompt file :", system_prompt_file)
    system_prompt = {"role": "system", "content": open(system_prompt_file).read().strip()}
    print("system prompt :", system_prompt)

    def chat_with_ai(message, history):
        # Instantiate MSGraphAPI
        ms_graph_api = MSGraphAPI()
        #functions = open(os.path.join(working_dir, "prompts", "functions.md")).read().strip()
        
        messages = [
            {"role": "system", "content": f"{system_prompt['content']}"},
            {"role": "user", "content": message}
        ]
        
        response = client.chat.completions.create(
            model=os.getenv('LLM_MODEL'),
            #functions=functions,
            messages=messages,
            temperature=0.8,
            stream=True,
            max_tokens=1000,
        )

        # Process the streaming response
        partial_response = ""
        for stream_response in response:
            if stream_response.choices[0].delta.content is not None:
                partial_response += stream_response.choices[0].delta.content
                yield [(message, partial_response)]  # Yield as a list of tuples

        # Extract the Graph API URL from the AI response
        #graph_api_request_url = partial_response.split('\n')[0].strip('*')  # Assuming the URL is the first line
        #print("Graph API Request URL: " + graph_api_request_url)

        # Call the Graph API using the extracted URL
        #api_response_text = call_graph_api(graph_api_request_url)  # Use the new function

        # Return the output in the expected format
        return [(message, partial_response)]  # Ensure this is a list of tuples

    def get_graph_api_url(message):
        # class GraphAPIURL(BaseModel):
        #     base_url: str
        #     endpoint: str
        #     parameters: list[str]

        #functions = open(os.path.join(working_dir, "prompts", "functions.md")).read().strip()
        messages = [
            {"role": "system", "content": system_prompt["content"]},
            {"role": "user", "content": message}
        ]

        try:
            # response = client.beta.chat.completions.parse(  # The pydantic method
            response = client.chat.completions.create(
                model=os.getenv('LLM_MODEL'),
                #functions=functions,
                messages=messages,
                #temperature=os.getenv('LLM_TEMPERATURE'),
                #temperature=0.01,
                #stream=False,
                #max_tokens=150,
                # response_format=GraphAPIURL  # passing the pydantic format
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "GraphAPIURL",
                        "description": "A URL for the Microsoft Graph API",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "base_url": {"type": "string"},
                                "endpoint": {"type": "string"},
                                "parameters": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["base_url", "endpoint", "parameters"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )

            # Parse the response content as JSON
            content = response.choices[0].message.content
            print(content)  # Debugging line to check the response structure

            # Convert the string to a dictionary
            content_dict = json.loads(content)  # Parse the JSON string to a dictionary

            return f"{content_dict['base_url']}{content_dict['endpoint']}{'&'.join(content_dict['parameters'])}"
        # except ValidationError as e:  # only for pydantic validation errors
            print(e.json())
        except Exception as e:
            # Handle validation errors
            print(e)
    
    def reset_chat():
        return [], []  # Reset the chat history and return an empty list of tuples

    # Define components outside of gr.Blocks()
    user_input = gr.Textbox(label="Query", placeholder="Enter your query here...")
    graph_api_url = gr.Textbox(label="Graph API Request URL", placeholder="https://graph.microsoft.com/v1.0/...", interactive=True)
    graph_api_response = gr.Textbox(label="Graph API Response", placeholder="Graph API Response will be displayed here...", interactive=False)
    system_prompt_override = gr.Textbox(label="System Prompt", value=system_prompt["content"], interactive=True, lines=10, inputs=system_prompt["content"])
    chatbot = gr.Chatbot(scale=2, container=True, avatar_images=[None, os.path.join(os.curdir, "res", "img", "ninja_info.png")], layout="bubble")  # Define chatbot here
    chatwindow = gr.ChatInterface(fn=chat_with_ai, chatbot=chatbot, title="Chat with Workplace Ninja AI")
    chat_interface = gr.TabbedInterface([chatwindow, system_prompt_override], ["Chat", "System Prompt"])

    with gr.Blocks() as demo:
        gr.Markdown("""
        # Copilot for Intune
        ## Use AI to get insights on Intune data
        """)
        
        # Create a row for the two columns
        with gr.Row():
            # Left column for user input and Graph API URL
            with gr.Column():
                gr.Examples(["List all Windows 11 devices", "Show me users sorted by name", "Generate a report on non-compliant devices"], inputs=user_input, fn=get_graph_api_url, outputs=graph_api_url, run_on_click=True)  # Example usage
                user_input.render()  # Render user input
                graph_api_url.render()  # Render Graph API URL
                graph_api_response.render()  # Render Graph API Response
                btn_call_graph_api = gr.Button("Call Graph API")
                btn_clear_all = gr.ClearButton(components=[user_input, graph_api_url, graph_api_response, chatbot], value="Clear", variant="stop")
                
                user_input.submit(get_graph_api_url, user_input, [graph_api_url, chatbot])
                #user_input.submit(chat_with_ai, [user_input, chatbot], [chatbot])  # Reference chatbot after defining it
                graph_api_url.change(chat_with_ai, [graph_api_url, chatbot], [chatbot])
                btn_call_graph_api.click(call_graph_api, [graph_api_url], [graph_api_response])
                graph_api_response.change(chat_with_ai, [graph_api_response, chatbot], [chatbot])

            # Right column for the chatbot
            with gr.Column():
                chat_interface.render()

    demo.queue()
    demo.launch(debug=True)

if __name__ == "__main__":
    initialize()