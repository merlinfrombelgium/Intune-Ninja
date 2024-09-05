import os
import time
import streamlit as st
from openai import OpenAI
from utils.oai_assistant import Assistant
from httpx import LocalProtocolError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_secret(key):
    if 'user_secrets' not in st.session_state:
        st.error("User secrets not initialized. Please refresh the page.")
        return None
    return st.session_state.user_secrets.get(key)

client = OpenAI(api_key=get_user_secret('LLM_API_KEY'))

def chat_with_ai(message, history, system_prompt):
    messages = [
        {"role": "system", "content": system_prompt['content']},
        {"role": "user", "content": message}
    ]
    
    response = client.chat.completions.create(
        model=get_user_secret('LLM_MODEL'),
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

def chat_with_assistant(message: str, history: list, thread_id: str = None):
    try:
        if not get_user_secret('LLM_API_KEY'):
            raise ValueError("OpenAI API key is missing or empty")

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

        with st.spinner("Preparing assistant..."):
            IntuneCopilotAssistant = Assistant(client).retrieve_assistant()
        if IntuneCopilotAssistant is None:
            raise ValueError("Failed to retrieve or create the Intune Copilot assistant")
        logger.info(f"Retrieved assistant. ID: {IntuneCopilotAssistant.id}")

        with st.spinner("Processing your request..."):
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=IntuneCopilotAssistant.id,
                instructions="Please provide a detailed response. You can use up to 4000 tokens if needed."
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

def interpret_graph_api_url(url, thread_id: str = None):
    prompt = f"""Interpret and explain the following Graph API URL: {url}

Provide a brief explanation of what this URL does and what kind of data it will retrieve.
If you think the URL could be improved or modified, suggest changes and explain why.
Format your response as follows:

Interpretation: [Your interpretation here]
Suggested Changes: [Your suggested changes here, or 'None' if no changes are needed]
Modified URL: [The modified URL if changes are suggested, or the original URL if no changes are needed]"""

    response = chat_with_assistant(prompt, [], thread_id)
    return {
        "interpretation": response.split("Interpretation:")[1].split("Suggested Changes:")[0].strip(),
        "suggested_changes": response.split("Suggested Changes:")[1].split("Modified URL:")[0].strip(),
        "modified_url": response.split("Modified URL:")[1].strip()
    }