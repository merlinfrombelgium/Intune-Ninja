import streamlit as st
from openai import OpenAI
import re  # Make sure this import is at the top of the file

# Function to load or initialize secrets
def load_or_init_secrets():
    if 'user_secrets' not in st.session_state:
        st.session_state.user_secrets = {
            'LLM_API_KEY': st.secrets.get("LLM_API_KEY", ""),
            'LLM_MODEL': st.secrets.get("LLM_MODEL", "gpt-4o-mini"),
            'MS_GRAPH_TENANT_ID': st.secrets.get("MS_GRAPH_TENANT_ID", ""),
            'MS_GRAPH_CLIENT_ID': st.secrets.get("MS_GRAPH_CLIENT_ID", ""),
            'MS_GRAPH_CLIENT_SECRET': st.secrets.get("MS_GRAPH_CLIENT_SECRET", ""),
        }

# Load or initialize secrets
load_or_init_secrets()

# Initialize OpenAI client
client = OpenAI(api_key=st.session_state.user_secrets['LLM_API_KEY'])

# Now import other modules
import os, sys
from utils.ms_graph_api import MSGraphAPI
from utils.oai_assistant import Assistant
from utils.ai_chat import chat_with_ai, chat_with_assistant, interpret_graph_api_url
from utils.database import init_db, load_conversation_history, save_new_conversation, load_conversation, delete_conversation
from utils.graph_api import call_graph_api, get_graph_api_url
from utils.ui_helpers import generate_placeholder_title

# Function to mask sensitive information
def mask_string(s):
    if len(s) <= 15:
        return "*" * len(s)
    return s[:15] + "*" * (len(s) - 15)

# Function to validate OpenAI API key format
def is_valid_openai_api_key(api_key):
    return api_key.startswith('sk-') or api_key.startswith('sk-proj-')

# Initialize database and load conversation history
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = load_conversation_history()

# Streamlit UI setup
st.set_page_config(page_title="Copilot for Intune", layout="wide")

# Remove the custom CSS for the labeled expander
st.markdown("""
<style>
    /* Remove the labeled-expander styles */
</style>
""", unsafe_allow_html=True)

st.title("Copilot for Intune")

# Configuration expander
with st.sidebar.expander("App configuration", expanded=True):
    
    # OpenAI API Key
    new_api_key = st.text_input("OpenAI API Key", 
                                value=mask_string(st.session_state.user_secrets['LLM_API_KEY']), 
                                type="password")
    if new_api_key and new_api_key != mask_string(st.session_state.user_secrets['LLM_API_KEY']):
        if is_valid_openai_api_key(new_api_key):
            st.session_state.user_secrets['LLM_API_KEY'] = new_api_key
            # Update the global client
            client = OpenAI(api_key=new_api_key)
            # Update the client in utils/ai_chat.py
            import utils.ai_chat
            utils.ai_chat.client = OpenAI(api_key=new_api_key)
            st.success("API key updated successfully!")
        else:
            st.error("Invalid OpenAI API key format. The key should start with 'sk-' or 'sk-proj-'.")
    
    # OpenAI Model
    new_model = st.selectbox("OpenAI Model", 
                             ["gpt-4o-mini", "gpt-4o"], 
                             index=0 if st.session_state.user_secrets['LLM_MODEL'] == "gpt-4o-mini" else 1)
    if new_model != st.session_state.user_secrets['LLM_MODEL']:
        st.session_state.user_secrets['LLM_MODEL'] = new_model

    # Microsoft Graph API Credentials
    new_tenant_id = st.text_input("MS Graph Tenant ID", 
                                  value=mask_string(st.session_state.user_secrets['MS_GRAPH_TENANT_ID']), 
                                  type="password")
    if new_tenant_id and new_tenant_id != mask_string(st.session_state.user_secrets['MS_GRAPH_TENANT_ID']):
        st.session_state.user_secrets['MS_GRAPH_TENANT_ID'] = new_tenant_id

    new_client_id = st.text_input("MS Graph Client ID", 
                                  value=mask_string(st.session_state.user_secrets['MS_GRAPH_CLIENT_ID']), 
                                  type="password")
    if new_client_id and new_client_id != mask_string(st.session_state.user_secrets['MS_GRAPH_CLIENT_ID']):
        st.session_state.user_secrets['MS_GRAPH_CLIENT_ID'] = new_client_id

    new_client_secret = st.text_input("MS Graph Client Secret", 
                                      value=mask_string(st.session_state.user_secrets['MS_GRAPH_CLIENT_SECRET']), 
                                      type="password")
    if new_client_secret and new_client_secret != mask_string(st.session_state.user_secrets['MS_GRAPH_CLIENT_SECRET']):
        st.session_state.user_secrets['MS_GRAPH_CLIENT_SECRET'] = new_client_secret

    # Update OpenAI client if API key changes
    if st.session_state.user_secrets['LLM_API_KEY'] != st.secrets.get("LLM_API_KEY", ""):
        client = OpenAI(api_key=st.session_state.user_secrets['LLM_API_KEY'])

# Remove the closing div tag
# st.sidebar.markdown("</div>", unsafe_allow_html=True)

# Add this to the top of the file, after other initializations
if 'graph_api_response' not in st.session_state:
    st.session_state.graph_api_response = ""

def get_or_create_thread_id():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = client.beta.threads.create().id
    return st.session_state.thread_id

# Load system prompt
system_prompt_file = os.sep.join([os.curdir, "prompts", "system_prompt.md"])
with open(system_prompt_file, 'r') as file:
    system_prompt = {"role": "system", "content": file.read().strip()}

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
    
    user_input = st.text_input("Query", placeholder="Enter your query here...", key="user_query")
    examples = ["List all Windows 11 devices", "Show me users sorted by name", "Generate a report on non-compliant devices"]
    selected_example = st.selectbox("Examples", [""] + examples)
    
    if selected_example:
        user_input = selected_example
    
    if st.button("Get Graph API URL") or (user_input and user_input != st.session_state.get("last_query", "")):
        st.session_state.last_query = user_input
        with st.spinner("Generating Graph API URL..."):
            graph_api_url = get_graph_api_url(user_input, system_prompt)
        
        if graph_api_url:
            st.session_state.graph_api_url = graph_api_url
            st.text_area("Graph API Request URL", value=graph_api_url, key="graph_api_url", height=100)
            
            # Call Graph API immediately
            with st.spinner("Calling Graph API..."):
                st.session_state.graph_api_response = call_graph_api(graph_api_url)
            
            # Trigger interpretation in col2
            st.session_state.interpret_url = True
        else:
            st.error("Failed to generate Graph API URL. Please try again.")
    
    # Always display the Graph API URL if it exists in session state
    elif "graph_api_url" in st.session_state:
        st.text_area("Graph API Request URL", value=st.session_state.graph_api_url, key="graph_api_url", height=100)

    # Display the Graph API response in a scrollable window
    if st.session_state.get("graph_api_response"):
        st.subheader("Graph API Response")
        st.text_area("", value=st.session_state.graph_api_response, height=300, key="graph_api_response_col1")

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
        with st.spinner("Interpreting Graph API URL and Response..."):
            graph_api_url = st.session_state.get("graph_api_url", "")
            graph_api_response = st.session_state.get("graph_api_response", "")
            thread_id = get_or_create_thread_id()
            
            interpretation_prompt = f"""Inspect the response from the Graph API request:

URL: {graph_api_url}
Response: {graph_api_response}

If it doesn't show valid data or there's an error, suggest changes to the API URL so it can be called again for better results. If data in the response is as expected, present it in a useful way using all available format functions in markdown.

Please structure your response as follows:
1. Data Validity: [Valid/Invalid/Error]
2. Interpretation: [Your interpretation of the data]
3. Suggested Changes (if any): [Changes to the API URL, if needed]
4. Formatted Data Presentation: [Present the data in a useful way using markdown]
"""
            
            try:
                ai_interpretation = chat_with_assistant(interpretation_prompt, [], thread_id)
                
                interpretation_message = f"""
Graph API URL: {graph_api_url}
Graph API Response:
```

AI Interpretation:
{ai_interpretation}
"""
                st.session_state.messages.append({"role": "assistant", "content": interpretation_message})
            except IndexError:
                st.error("An error occurred while processing the AI interpretation. Please try again.")
        
        # Reset the flag
        st.session_state.interpret_url = False
        st.rerun()