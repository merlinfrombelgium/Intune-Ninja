import os, sys
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
from textwrap import dedent
from utils.ms_graph_api import MSGraphAPI
from utils.oai_assistant import Assistant
from utils.ai_chat import chat_with_ai, chat_with_assistant, interpret_graph_api_url
from utils.database import init_db, load_conversation_history, save_new_conversation, load_conversation, delete_conversation
from utils.graph_api import call_graph_api, get_graph_api_url
from utils.ui_helpers import generate_placeholder_title

def initialize_assistant():
    assistant = Assistant(client)
    try:
        assistant.retrieve_assistant()
        return assistant
    except Exception as e:
        return f"Error initializing assistant: {str(e)}"

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv('LLM_API_KEY'))
threads = {}

system_prompt_file = os.sep.join([os.curdir, "prompts", "system_prompt.md"])
system_prompt = {"role": "system", "content": open(system_prompt_file).read().strip()}

# Initialize database and load conversation history
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = load_conversation_history()

# Streamlit UI setup
st.set_page_config(page_title="Copilot for Intune", layout="wide")
st.title("Copilot for Intune")

def get_or_create_thread_id():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = client.beta.threads.create().id
    return st.session_state.thread_id

# Add this CSS to create a vertical separator
st.markdown("""
<style>
.vertical-separator {
    border-left: 2px solid #e0e0e0;
    height: 100vh;
    position: absolute;
    left: 50%;
    top: 0;
}
</style>
""", unsafe_allow_html=True)

# Create the columns
col1, separator, col2 = st.columns([0.495, 0.01, 0.495])

# Add the vertical separator
with separator:
    st.markdown('<div class="vertical-separator"></div>', unsafe_allow_html=True)

with col1:
    st.header("Get a well formed Graph API request URL")
    st.subheader("(Structured Output)")
    
    # Modify the text input to capture the enter key press
    user_input = st.text_input("Query", placeholder="Enter your query here...", key="user_query")
    examples = ["List all Windows 11 devices", "Show me users sorted by name", "Generate a report on non-compliant devices"]
    selected_example = st.selectbox("Examples", [""] + examples)
    
    if selected_example:
        user_input = selected_example
    
    # Function to handle URL generation
    def generate_graph_api_url():
        with st.spinner("Generating Graph API URL..."):
            graph_api_url = get_graph_api_url(user_input, system_prompt)
        
        if graph_api_url:
            st.session_state.graph_api_url = graph_api_url
            st.text_input("Graph API Request URL", value=graph_api_url, key="graph_api_url")
            
            # Trigger interpretation in col2
            st.session_state.interpret_url = True
        else:
            st.error("Failed to generate Graph API URL. Please try again.")
        
        st.rerun()
    
    # Check if the user has pressed enter or clicked the button
    if st.button("Get Graph API URL") or (user_input and user_input != st.session_state.get("last_query", "")):
        st.session_state.last_query = user_input
        generate_graph_api_url()
    
    # Display the Graph API URL
    graph_api_url = st.session_state.get("graph_api_url", "")
    if graph_api_url:
        st.text_input("Graph API Request URL", value=graph_api_url, key="graph_api_url")
    
    if st.button("Call Graph API"):
        graph_api_url = st.session_state.get("graph_api_url", "")
        if graph_api_url:
            graph_api_response = call_graph_api(graph_api_url)
            
            # Limit the response to 20 lines for display
            response_lines = graph_api_response.split('\n')
            if len(response_lines) > 20:
                limited_response = '\n'.join(response_lines[:20]) + '\n...'
            else:
                limited_response = graph_api_response
            
            # Display the limited response in a scrollable text area
            st.text_area("Graph API Response (first 20 lines)", value=limited_response, height=300)
            
            # Add a download button for the full response
            st.download_button(
                label="Download Full Response",
                data=graph_api_response,
                file_name="graph_api_response.json",
                mime="application/json"
            )
            
            # Send the API response to the AI assistant for interpretation
            interpretation_prompt = f"""Inspect the response from the earlier Graph request:

{graph_api_response}

If it doesn't show valid data or there's an error, suggest changes to the API URL so it can be called again for better results. If data in the response is as expected, present it in a useful way using all available format functions in markdown.

Please structure your response as follows:
1. Data Validity: [Valid/Invalid/Error]
2. Interpretation: [Your interpretation of the data]
3. Suggested Changes (if any): [Changes to the API URL, if needed]
4. Formatted Data Presentation: [Present the data in a useful way using markdown]
"""
            
            thread_id = get_or_create_thread_id()
            ai_interpretation = chat_with_assistant(interpretation_prompt, [], thread_id)
            
            # Display the AI interpretation
            st.markdown("## AI Interpretation of API Response")
            st.markdown(ai_interpretation)
            
            # Add the API response and interpretation to the conversation
            st.session_state.messages.append({"role": "assistant", "content": f"Graph API Response:\n```json\n{graph_api_response}\n```\n\nAI Interpretation:\n{ai_interpretation}"})
            st.rerun()
        else:
            st.warning("Please generate a Graph API URL first.")

with col2:
    st.header("Have a conversation with an advanced AI")
    st.subheader("(Threads, Reasoning, Tools, Functions)")
    
    # Add a Clear button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = client.beta.threads.create().id  # Create a new thread
        st.rerun()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat input at the top
    prompt = st.chat_input("What is your question?")

    # Create a container for the conversation
    conversation_container = st.container()

    # Handle new user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                thread_id = get_or_create_thread_id()
                full_response = chat_with_assistant(prompt, st.session_state.messages, thread_id)
            st.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

    # Display the conversation history in reverse order
    with conversation_container:
        for message in reversed(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Handle URL interpretation here
    if st.session_state.get("interpret_url", False):
        with st.spinner("Interpreting Graph API URL..."):
            graph_api_url = st.session_state.get("graph_api_url", "")
            thread_id = get_or_create_thread_id()
            interpretation = interpret_graph_api_url(graph_api_url, thread_id)
            
            interpretation_message = f"""Graph API URL Interpretation:
Interpretation: {interpretation['interpretation']}
Suggested Changes: {interpretation['suggested_changes']}
Modified URL: {interpretation['modified_url']}"""
            st.session_state.messages.append({"role": "assistant", "content": interpretation_message})
            
            # Update the URL if changes were suggested
            if interpretation['modified_url'] != graph_api_url:
                st.session_state.modified_graph_api_url = interpretation['modified_url']
                st.text_input("Modified Graph API Request URL", value=st.session_state.modified_graph_api_url, key="modified_graph_api_url_input")
                
                # Add a button to apply the modified URL
                if st.button("Apply Modified URL"):
                    st.session_state.graph_api_url = st.session_state.modified_graph_api_url
                    st.success("Graph API URL updated successfully!")
                    st.rerun()
        
        # Reset the flag
        st.session_state.interpret_url = False

# Move the System Prompt Override outside of the columns
with st.expander("System Prompt"):
    new_system_prompt = st.text_area("Override System Prompt", value=system_prompt["content"], height=200)
    if st.button("Update System Prompt"):
        system_prompt["content"] = new_system_prompt
        st.success("System prompt updated successfully!")

if __name__ == "__main__":
    pass