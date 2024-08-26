import os, sys
from dotenv import load_dotenv
from utils.ms_graph_api import MSGraphAPI
from utils.llm import *
from utils.oai_assistant import Assistant
import json
from openai import OpenAI, AssistantEventHandler
import gradio as gr
from gradio import ChatMessage, MessageDict
from textwrap import dedent
#from pydantic import BaseModel, ValidationError

sys.path.append(os.path.abspath("."))
#working_dir = os.path.dirname(os.path.abspath(__file__))  # Define the root directory of the script as the working directory

def call_graph_api(api_url):
    """Call the Graph API and return the response."""
    ms_graph_api = MSGraphAPI()  # Instantiate MSGraphAPI
    try:
        api_response = ms_graph_api.call_api(api_url)
        return json.dumps(api_response, indent=2)  # Format the response as a JSON string
    except Exception as e:
        return f"Error calling API: {str(e)}"

def initialize_assistant():
    assistant = Assistant(client)
    try:
        assistant.retrieve_assistant()
        return assistant
    except Exception as e:
        return f"Error initializing assistant: {str(e)}"


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
        {"role": "system", "content": dedent(system_prompt["content"])},
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
                                "type": ["array", "null"],
                                "description": "A list of optional parameters for the Microsoft Graph API",
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

def chat_with_assistant(message: str, history: MessageDict, request: gr.Request) -> MessageDict:
    history.append({"role": "user", "content": message})

    if request.session_hash in threads:
        thread = threads[request.session_hash]
    else:
        threads[request.session_hash] = thread = client.beta.threads.create()
    
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=message
    )

    # from typing_extensions import override
    
    # # First, we create a EventHandler class to define
    # # how we want to handle the events in the response stream.
    
    # class EventHandler(AssistantEventHandler):    
    #     @override
    #     def on_text_created(self, text) -> None:
    #         print(f"\nassistant > ", end="", flush=True)
            
    #     @override
    #     def on_text_delta(self, delta, snapshot):
    #         print(delta.value, end="", flush=True)
            
    #     def on_tool_call_created(self, tool_call):
    #         print(f"\nassistant > {tool_call.type}\n", flush=True)
        
    #     def on_tool_call_delta(self, delta, snapshot):
    #         if delta.type == 'code_interpreter':
    #             if delta.code_interpreter.input:
    #                 print(delta.code_interpreter.input, end="", flush=True)
    #             if delta.code_interpreter.outputs:
    #                 print(f"\n\noutput >", flush=True)
    #                 for output in delta.code_interpreter.outputs:
    #                     if output.type == "logs":
    #                         print(f"\n{output.logs}", flush=True)
    
    # Then, we use the `stream` SDK helper 
    # with the `EventHandler` class to create the Run 
    # and stream the response.
    
    IntuneCopilotAssistant = Assistant(client).retrieve_assistant()
    toolcall = ChatMessage(role="assistant", metadata = {"title": "🛠️ Used tool "}, content="")
    response = ChatMessage(role="assistant", content="")

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=IntuneCopilotAssistant.id,
        #instructions="Please address the user as Jane Doe. The user has a premium account.",
        #event_handler=EventHandler(),
    ) as stream:
        for event in stream:
            #print("event :", event)
            # if event.event == "thread.run.step.delta" and event.data.delta.step_details.type == "tool_calls":
            #     #toolcall.metadata["title"] += event.data.delta.step_details.tool_calls[0].type
            #     history.append({"role": "assistant", "metadata": {"title": f"🛠️ Used tool {event.data.delta.step_details.tool_calls[0].type}"}, "content": "nothing here"})
            #     print("history :", history)
            #     return history
            if event.event == "thread.message.delta" and event.data.delta.content:
                # history.append({"role": "assistant", "content": ""})
                # history[-1].content += event.data.delta.content[0].text.value
                # print("history :", history)
                # yield history
                response.content += event.data.delta.content[0].text.value
                yield response

    return history





load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv('LLM_API_KEY'))
#global graph_api_request_url  # Declare the variable as global
graph_api_request_url = ""  # Initialize the variable
threads = {}

system_prompt_file = os.sep.join([os.curdir, "prompts", "system_prompt.md"])
print("system prompt file :", system_prompt_file)
system_prompt = {"role": "system", "content": open(system_prompt_file).read().strip()}
print("system prompt :", system_prompt)

# Define components outside of gr.Blocks()
user_input = gr.Textbox(label="Query", placeholder="Enter your query here...")
graph_api_url = gr.Textbox(label="Graph API Request URL", placeholder="https://graph.microsoft.com/v1.0/...", interactive=True)
graph_api_response = gr.Textbox(label="Graph API Response", placeholder="Graph API Response will be displayed here...", interactive=False)
system_prompt_override = gr.Textbox(label="System Prompt", value=system_prompt["content"], interactive=True, lines=10, inputs=system_prompt["content"])
chatbot = gr.Chatbot(
            scale=2,
            container=False,
            layout="bubble",
            type="messages",
            value = [{"role": "assistant", "content": "Ask me about any data in Intune"}]
)
chatwindow = gr.ChatInterface(
            fn=chat_with_assistant,
            type="messages",
            chatbot=chatbot,
            title="Chat with Workplace Ninja AI",
            show_progress="full",
            fill_width=True
)
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
            #graph_api_url.change(chat_with_ai, [graph_api_url, chatbot], [chatbot])
            btn_call_graph_api.click(call_graph_api, [graph_api_url], [graph_api_response])
            #graph_api_response.change(chat_with_ai, [graph_api_response, chatbot], [chatbot])

        # Right column for the chatbot
        with gr.Column():
            chat_interface.render()

# demo.queue()
# demo.launch(debug=True)

if __name__ == "__main__":
    #initialize()
    demo.launch(debug=True)