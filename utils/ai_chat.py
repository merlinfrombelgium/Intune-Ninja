import time
import streamlit as st
from openai import OpenAI
from utils.oai_assistant import Assistant
import logging
from textwrap import dedent
from utils.write_debug import write_debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# client = OpenAI(api_key=st.session_state.user_secrets['LLM_API_KEY'])
# if not client:
#     write_debug("OpenAI client not initialized. Please refresh the page.")
#     st.stop()

def get_user_secret(key):
    if key == 'LLM_MODEL':
        model = st.session_state.LLM_MODEL
        print(f"get_user_secret returning LLM_MODEL: {model}")  # Add this line
        return model
    if 'user_secrets' not in st.session_state:
        st.error("User secrets not initialized. Please refresh the page.")
        return None
    return st.session_state.user_secrets.get(key)

def initialize_client():
    global client
    client = OpenAI(api_key=st.session_state.user_secrets['LLM_API_KEY'])
    if not client:
        st.error("OpenAI client not initialized. Please refresh the page.")
        st.stop()
    else:
        return client

def chat_with_ai(message, history, system_prompt):
    # if not client:
    #     client = AI_client()
    
    messages = [
        {"role": "system", "content": system_prompt['content']},
        {"role": "user", "content": message}
    ]
    
    model = st.session_state.get('LLM_MODEL', 'gpt-4o-2024-08-06')
    print(f"Using model in chat_with_ai: {model}")  # Add this line
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            stream=True,
            max_tokens=1000,
        )

        partial_response = ""
        for stream_response in response:
            if stream_response.choices[0].delta.content is not None:
                partial_response += stream_response.choices[0].delta.content
                yield [(message, partial_response)]

        return [(message, partial_response)]
    except Exception as e:
        st.error(f"Error in chat_with_ai: {str(e)}")
        return [(message, f"Error: {str(e)}")]

def chat_with_assistant(message: str, run_instructions: str, history: list, thread_id: str = None):
    # if not client:
    #     client = AI_client()
    
    try:

        logger.info(f"Starting chat_with_assistant. Message: {message[:50]}...")

        # Try to use the existing thread_id, create a new one if it doesn't exist
        try:
            if thread_id:
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
            else:
                thread_id = client.beta.threads.create().id
                logger.info(f"Created new thread. ID: {thread_id}")
        except Exception as e:
            logger.warning(f"Error retrieving thread: {str(e)}. Creating a new one.")
            thread_id = client.beta.threads.create().id
            logger.info(f"Created new thread. ID: {thread_id}")

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
            content=message
        )
        logger.info("Added user message to thread")

        if 'IntuneCopilotAssistant' not in st.session_state:
            with st.spinner("Preparing assistant..."):
                st.session_state.IntuneCopilotAssistant = Assistant(client).retrieve_assistant()
            if st.session_state.IntuneCopilotAssistant is None:
                raise ValueError("Failed to retrieve or create the Intune Copilot assistant")
            logger.info(f"Retrieved assistant. ID: {st.session_state.IntuneCopilotAssistant.id}")

        # with st.spinner("Processing your request..."):
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=st.session_state.IntuneCopilotAssistant.id,
            tools=[{"type": "file_search"}],
            # instructions="Please be concise and to the point. Stick to the context of Intune and Graph API. Politely decline to answer out of scope questions. It's okay to use humor."
            instructions=run_instructions if run_instructions else 
            """
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
        )
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
            # Check if the first item has a 'text' attribute
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
    try:
        # Attempt a simple API call to check if the client is working
        client.models.list()
        return "ready" #, "Client is ready and connected."
    except Exception as e:
        return "error", f"Error: {str(e)}"

# Add this function to check and update client status
def update_client_status():
    status = check_client_status(client)
    st.session_state.client_status = status
    #st.session_state.client_status_message = message

