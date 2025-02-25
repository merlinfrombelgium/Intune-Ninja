import time
import streamlit as st
from openai import OpenAI
from utils.oai_assistant import Assistant
import logging
from textwrap import dedent
from utils.write_debug import write_debug
import openai
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# client = OpenAI(api_key=st.session_state.user_secrets['LLM_API_KEY'])
# if not client:
#     write_debug("OpenAI client not initialized. Please refresh the page.")
#     st.stop()

def get_user_secret(key):
    if key == 'LLM_MODEL':
        model = st.session_state.LLM_MODEL
        print(f"get_user_secret returning LLM_MODEL: {model}")
        return model
    if 'user_secrets' not in st.session_state:
        st.error("User secrets not initialized. Please refresh the page.")
        write_debug(f"User secrets not found in session state. Available keys: {st.session_state.keys()}")
        return None
    
    # Handle 'Graph proxy' prefix
    if key.startswith('Graph_proxy_'):
        key = 'Graph proxy ' + key[12:]
    
    value = st.session_state.user_secrets.get(key)
    write_debug(f"get_user_secret for {key}: {'Found' if value else 'Not found'}")
    return value

def initialize_client():
    api_key = get_user_secret('OpenAI API key')
    if not api_key:
        write_debug("OpenAI API key is not set.")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        write_debug("OpenAI client initialized successfully.")
        return client
    except Exception as e:
        write_debug(f"Error initializing OpenAI client: {str(e)}")
        return None

def get_openai_client():
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = initialize_client()
    return st.session_state.openai_client

def chat_with_ai(message, history, system_prompt):
    client = get_openai_client()
    if not client:
        st.error("OpenAI client is not initialized. Please check your configuration.")
        return [(message, "Error: OpenAI client is not initialized")]
    
    # Ensure system_prompt is in the correct format
    if isinstance(system_prompt, dict) and 'content' in system_prompt:
        system_content = system_prompt['content']
    elif isinstance(system_prompt, str):
        system_content = system_prompt
    else:
        st.error("Invalid system_prompt format.")
        return [(message, "Error: Invalid system_prompt format")]
    
    messages = [
        {"role": "developer", "content": system_content},
        {"role": "user", "content": message}
    ]
    
    model = st.session_state.get('LLM_MODEL', 'o3-mini')
    print(f"Using model in chat_with_ai: {model}")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            stream=True,
            max_tokens=1000,
        )

        partial_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                partial_response += chunk.choices[0].delta.content
                yield [(message, partial_response)]

        return [(message, partial_response)]
    except openai.APIError as e:
        error_message = f"OpenAI API Error: {str(e)}"
        st.error(error_message)
        write_debug(error_message)
        return [(message, f"Error: {str(e)}")]
    except Exception as e:
        error_message = f"Error in chat_with_ai: {str(e)}"
        st.error(error_message)
        write_debug(error_message)
        return [(message, f"Error: {str(e)}")]

def chat_with_assistant(prompt, instructions, history, thread_id=None, force_new_thread=False):
    # Added an optional force_new_thread parameter to allow creation of a new thread on demand
    client = get_openai_client()
    if not client:
        st.error("OpenAI client is not initialized. Please check your configuration.")
        return "Error: OpenAI client is not initialized"
    
    if history is None:
        history = []
    
    # Ensure instructions is a string
    if instructions is None or not isinstance(instructions, str):
        instructions = """
            You are an AI assistant specialized in Microsoft Intune, Entra ID and Windows 10/11. Based on a user's natural language request, you are to provide guidance and advanced insights on the Graph request needed to provide an answer to the user's question. Use the knowledge base provided to you. (file_search)

            Instructions:
            - Only answer questions related to Microsoft Intune, Entra ID and Windows 10/11
            - Consider to use the /beta version of Graph if it would yield better and more accurate results. (refer to your knowledge base)
            - Always look at the available attributes of the objects in the Graph response and try to get better results and granularity by suggesting other filters.
            - For error 400 (bad request), look at the error message and suggest a new Graph request.
            - The answers **must** consist of at least three paragraphs that explain the user's request, a reference to the documents that relate to the topic the user is asking about, and further explanation for the answer. You may also provide further steps and guidance to explain the answer.
            - If you're unsure of an answer, please say so.
            - Please explain the answer you give and provide a link to the documentation if possible. Show also the time stamp of the documentation.
            - Windows 11 is listed as osVersion "10.0.22000" or higher. The correct query to get Windows 11 devices is `deviceManagement/managedDevices?$filter=operatingSystem eq 'Windows' and startsWith(osVersion, '10.0.22')`.
            """
    
    try:
        logger.info(f"Starting chat_with_assistant. Message: {prompt[:50]}...")

        # If force_new_thread is enabled or no thread_id is provided, always create a new thread.
        if force_new_thread or not thread_id:
            thread_id = client.beta.threads.create().id
            logger.info(f"Created new thread due to force_new_thread flag. ID: {thread_id}")
        else:
            try:
                # Check if the thread exists
                thread = client.beta.threads.retrieve(thread_id)
                logger.info(f"Using existing thread. ID: {thread_id}")
                
                # Check for any active runs on this thread
                runs = client.beta.threads.runs.list(thread_id=thread_id, limit=1)
                if runs.data and runs.data[0].status in ['queued', 'in_progress', 'requires_action']:
                    logger.info(f"Waiting for active run to complete. Run ID: {runs.data[0].id}")
                    while runs.data[0].status in ['queued', 'in_progress', 'requires_action']:
                        time.sleep(1)
                        runs.data[0] = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=runs.data[0].id)
                    logger.info(f"Active run completed. Status: {runs.data[0].status}")
            except Exception as e:
                logger.warning(f"Error retrieving thread: {str(e)}. Creating a new one.")
                thread_id = client.beta.threads.create().id
                logger.info(f"Created new thread. ID: {thread_id}")

        # For a new Graph API URL query, you might not need old history;
        # if so, you could also choose to skip adding history messages.
        for msg in history:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role=msg["role"],
                content=msg["content"]
            )
        logger.info(f"Added {len(history)} messages from history")

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=prompt
        )
        logger.info("Added user message to thread")

        # Initialize the assistant without showing info/debug messages in the UI
        if 'IntuneCopilotAssistant' not in st.session_state:
            with st.spinner("Preparing assistant..."):
                # Create a placeholder for potential UI messages
                with st.empty():
                    # Initialize the assistant
                    st.session_state.IntuneCopilotAssistant = Assistant(client).retrieve_assistant()
            if st.session_state.IntuneCopilotAssistant is None:
                raise ValueError("Failed to retrieve or create the Intune Copilot assistant")
            logger.info(f"Retrieved assistant. ID: {st.session_state.IntuneCopilotAssistant.id}")

        run_params = {
            "thread_id": thread_id,
            "assistant_id": st.session_state.IntuneCopilotAssistant.id,
            "tools": [{"type": "file_search"}],
            "instructions": instructions,
        }

        run = client.beta.threads.runs.create(**run_params)
        logger.info(f"Created run. ID: {run.id}")

        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            logger.info(f"Run status: {run.status}")
            if run.status == "failed":
                raise Exception(f"Run failed. Error: {run.last_error}")
            time.sleep(0.5)

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        logger.info(f"Retrieved messages. Count: {len(messages.data)}")

        if not messages.data:
            raise ValueError("No messages returned from the assistant")
        
        logger.info(f"First message content type: {type(messages.data[0].content)}")
        logger.info(f"First message content: {messages.data[0].content}")

        # Check if content is a list and has at least one item
        if isinstance(messages.data[0].content, list) and len(messages.data[0].content) > 0:
            if hasattr(messages.data[0].content[0], 'text'):
                return messages.data[0].content[0].text.value
            else:
                raise ValueError("Unexpected message content structure")
        else:
            raise ValueError("Unexpected message content structure")

    except Exception as e:
        logger.error(f"Error in chat_with_assistant: {str(e)}", exc_info=True)
        error_message = f"An error occurred: {str(e)}"
        st.error(error_message)
        return error_message

# def interpret_graph_api_url(url, thread_id: str = None):
#     prompt = f"""\
#     Interpret and explain the following Graph API URL: {url}

#     Provide a brief explanation of what this URL does and what kind of data it will retrieve.
#     If you think the URL could be improved or modified, suggest changes and explain why.
#     Format your response as follows:

#     Interpretation: [Your interpretation here]
#     Suggested Changes: [Your suggested changes here, or 'None' if no changes are needed]
#     Modified URL: [The modified URL if changes are suggested, or the original URL if no changes are needed]
#     """

#     response = chat_with_assistant(dedent(prompt), [], thread_id)
#     return {
#         "interpretation": response.split("Interpretation:")[1].split("Suggested Changes:")[0].strip(),
#         "suggested_changes": response.split("Suggested Changes:")[1].split("Modified URL:")[0].strip(),
#         "modified_url": response.split("Modified URL:")[1].strip()
#     }

def check_client_status(client):
    if not client:
        return "not_configured"
    try:
        # Instead of listing all models, we'll just check if we can access the API
        client.api_key
        return "ready"
    except Exception as e:
        return "error", f"Error: {str(e)}"

def update_client_status():
    client = get_openai_client()
    status = check_client_status(client)
    st.session_state.client_status = status

