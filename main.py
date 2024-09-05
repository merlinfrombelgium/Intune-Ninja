import os
import streamlit as st
from openai import OpenAI
from utils.write_debug import write_debug

# Add this new function to parse the pasted secrets
def parse_secrets(secrets_text):
    secrets = {}
    for line in secrets_text.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            secrets[key.strip()] = value.strip()
    return secrets

# Streamlit UI setup
st.set_page_config(page_title="Copilot for Intune", layout="wide")

# Function to load or initialize secrets
def load_or_init_secrets():
    if 'user_secrets' not in st.session_state:
        st.session_state.user_secrets = {
            'LLM_API_KEY': "",
            'MS_GRAPH_TENANT_ID': "",
            'MS_GRAPH_CLIENT_ID': "",
            'MS_GRAPH_CLIENT_SECRET': "",
        }
        # Try to load from st.secrets if available
        try:
            for key in st.session_state.user_secrets.keys():
                st.session_state.user_secrets[key] = st.secrets.get(key, st.session_state.user_secrets[key])
        except FileNotFoundError:
            st.warning("Please enter your secrets in the configuration section.")

    # Initialize LLM_MODEL separately
    if 'LLM_MODEL' not in st.session_state:
        st.session_state.LLM_MODEL = "gpt-4o-2024-08-06"  # Updated default model
    # print(f"Current LLM_MODEL: {st.session_state.LLM_MODEL}")  # Add this line

def clear_secrets_input():
    st.session_state.secrets_input = ""
    
# Load or initialize secrets
load_or_init_secrets()

# Function to check if secrets are set
def are_secrets_set():
    return all([
        st.session_state.user_secrets['LLM_API_KEY'],
        st.session_state.user_secrets['MS_GRAPH_TENANT_ID'],
        st.session_state.user_secrets['MS_GRAPH_CLIENT_ID'],
        st.session_state.user_secrets['MS_GRAPH_CLIENT_SECRET']
    ])

# Check if it's the first run and secrets are not set
if 'first_run' not in st.session_state:
    st.session_state.first_run = True

# Welcome message using st.toast
if st.session_state.first_run and not are_secrets_set():
    st.toast("Welcome to Copilot for Intune!", icon="🥷")
    st.session_state.first_run = False

# Load modules depending on secrets
from utils.ai_chat import chat_with_assistant, client
from utils.graph_api import call_graph_api, get_graph_api_url

# Function to mask sensitive information
def mask_string(s):
    if len(s) <= 15:
        return "*" * len(s)
    return s[:15] + "*" * (len(s) - 15)

# Function to validate OpenAI API key format
def is_valid_openai_api_key(api_key):
    return api_key.startswith('sk-') or api_key.startswith('sk-proj-')

# Remove the custom CSS for the labeled expander
st.markdown("""
<style>
    /* Remove the labeled-expander styles */
</style>
""", unsafe_allow_html=True)

st.title("Copilot for Intune")

# Configuration section
with st.sidebar:	
    st.title("App Configuration")
    
    with st.status("Configuring...", expanded=True) as status:
        st.write("Paste all your secrets here (one per line, in the format KEY=VALUE):")
        
        # Check if we need to clear the input
        if st.session_state.get('clear_secrets_input', False):
            st.session_state.secrets_input = ""
            st.session_state.clear_secrets_input = False
        
        secrets_input = st.text_area("Secrets", height=150, key="secrets_input",
                                     help="Example format:\nLLM_API_KEY=sk-...\nMS_GRAPH_TENANT_ID=...\nMS_GRAPH_CLIENT_ID=...\nMS_GRAPH_CLIENT_SECRET=...")
        
        if st.button("Update Secrets"):
            new_secrets = parse_secrets(secrets_input)
            if new_secrets:
                for key, value in new_secrets.items():
                    if key in st.session_state.user_secrets and value:
                        st.session_state.user_secrets[key] = value
                
                # Update OpenAI client if API key changes
                if 'LLM_API_KEY' in new_secrets and is_valid_openai_api_key(new_secrets['LLM_API_KEY']):
                    client = OpenAI(api_key=new_secrets['LLM_API_KEY'])
                
                st.success("Secrets updated successfully!")
                # Set the flag to clear the input field on the next run
                st.session_state.clear_secrets_input = True
                # Collapse the configuration pane
                status.update(label="Configuration complete!", state="complete", expanded=False)
                st.rerun()  # Rerun the app to apply changes
            else:
                st.error("No valid secrets found. Please check the format and try again.")
        
        # Display current secret values (masked)
        st.write("Current Secret Values:")
        for key, value in st.session_state.user_secrets.items():
            st.text_input(key, value=mask_string(value), type="password", disabled=True)
        
        # OpenAI Model selection
        new_model = st.selectbox("OpenAI Model", 
                                 ["gpt-4o-2024-08-06", "gpt-4o-mini"], 
                                 index=0 if st.session_state.LLM_MODEL == "gpt-4o-2024-08-06" else 1)
        if new_model != st.session_state.LLM_MODEL:
            st.session_state.LLM_MODEL = new_model
            print(f"Updated LLM_MODEL: {st.session_state.LLM_MODEL}")  # Add this line
        
        if are_secrets_set():
            status.update(label="Configuration complete!", state="complete", expanded=False)
        else:
            status.update(label="Please complete the configuration", state="running")

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
