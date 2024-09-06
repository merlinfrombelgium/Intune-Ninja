import os
import streamlit as st
from utils.write_debug import write_debug, clear_debug_messages
from textwrap import dedent

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
from utils.graph_api import call_graph_api, get_graph_api_url
from utils.ai_chat import client, chat_with_assistant

# Function to mask sensitive information and return the last 5 characters
def mask_string(s):
    if len(s) <= 15:
        return "*" * len(s), s[-5:] if s else ""
    return s[:15] + "*" * (len(s) - 15), s[-5:]

# Modify the return statement to format the output without quotes
def mask_string(s):
    if len(s) <= 15:
        return f"{'*' * len(s)} {s[-5:]}" if s else ""
    return f"{s[:15]}{'*' * (len(s) - 15)} {s[-5:]}"

# Function to validate OpenAI API key format
def is_valid_openai_api_key(api_key):
    return api_key.startswith('sk-') or api_key.startswith('sk-proj-')

# # Remove the custom CSS for the labeled expander
# st.markdown("""
# <style>
#     /* Remove the labeled-expander styles */
# </style>
# """, unsafe_allow_html=True)

st.title(":ninja: Copilot for Intune", help="*a ninja tool for crafting Graph API calls and interpreting the results with AI*")

# Configuration section
with st.sidebar:	
    st.title("App Configuration")
    
    with st.status("Configuring...", expanded=True) as status:
        st.write("Paste all your secrets here (one per line, in the format KEY=VALUE):")
        
        # Check if we need to clear the input
        if st.session_state.get('clear_secrets_input', False):
            st.session_state.secrets_input = ""
            st.session_state.clear_secrets_input = False
        
        secrets_input = st.text_area(label="Secrets", value="", height=150, key="secrets_input",
                                     help="Example format:\nLLM_API_KEY=sk-...\nMS_GRAPH_TENANT_ID=...\nMS_GRAPH_CLIENT_ID=...\nMS_GRAPH_CLIENT_SECRET=...")
        
        if st.button("Update Secrets"):
            new_secrets = parse_secrets(secrets_input)
            if new_secrets:
                for key, value in new_secrets.items():
                    if key in st.session_state.user_secrets and value:
                        st.session_state.user_secrets[key] = value
                
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
            st.text_input(label=key, value=mask_string(value), type="password", disabled=True)
        
        # OpenAI Model selection
        new_model = st.selectbox(label="OpenAI Model", 
                                 options=["gpt-4o-2024-08-06", "gpt-4o-mini"], 
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
    # st.header("Get a well formed Graph API request URL")
    # st.subheader("(Structured Output)")
    
    with st.form(key='query_form'):
        user_input = st.text_input(
            label="Query",
            placeholder="Enter your query here...",
            key="user_query"
        )
        examples = ["List all Windows 11 devices", "Show me users sorted by name", "Generate a report on non-compliant devices"]
        selected_example = st.selectbox(label="Examples", options=[""] + examples)
        
        submit_button = st.form_submit_button(label='Get Graph API URL')

    with st.popover("Prompt", use_container_width=True, help="This is the prompt for the AI to generate the Graph API URL"):
        def update_system_prompt():
            system_prompt["content"]=st.session_state.graph_api_prompt
            print(system_prompt["content"])
        st.text_area(label="Prompt", label_visibility="hidden", key="graph_api_prompt", value=f"{system_prompt['content']}", height=300, on_change=update_system_prompt)
    
    if selected_example:
        user_input = selected_example
    
    if submit_button or (user_input and user_input != st.session_state.get("last_query", "")):
        st.session_state.last_query = user_input
        with st.spinner("Generating Graph API URL..."):
            graph_api_url = get_graph_api_url(client, user_input, system_prompt)
        
        if graph_api_url:
            st.session_state.graph_api_url = graph_api_url
            # Call Graph API immediately
            with st.spinner("Calling Graph API..."):
                st.session_state.graph_api_response = call_graph_api(st.session_state.graph_api_url)
        else:
            st.error("Failed to generate Graph API URL. Please try again.")

    # Add back the Graph API URL form
    def update_url():
        if st.session_state.graph_api_complete_url != st.session_state.graph_api_url:
            st.session_state.graph_api_url = st.session_state.graph_api_complete_url
        else:
            st.session_state.graph_api_url = st.session_state.graph_api_base_url + st.session_state.graph_api_choice + "/" + st.session_state.graph_api_endpoint + "?" + st.session_state.graph_api_parameters
    
    if "graph_api_url" in st.session_state:
        with st.form(key='graph_api_form'):
            st.text_input(
                label="Base URL",
                value="https://graph.microsoft.com/",
                key="graph_api_base_url",
                disabled=True
            )
            API_version = st.radio(
                label="API version",
                options=["v1.0", "beta"],
                horizontal=True,
                key="graph_api_choice",
                # on_change=update_url
            )
            # if API_version == "beta":
            #     st.session_state.graph_api_version = "beta"
            # else:
            #     st.session_state.graph_api_version = "v1.0"

            st.text_input(
                label="endpoint",
                value=st.session_state.graph_api_url.split("/")[4].split("?")[0],
                key="graph_api_endpoint",
                # on_change=update_url
            )
            st.text_input(
                label="parameters",
                value=st.session_state.graph_api_url.split("?")[1] if "?" in st.session_state.graph_api_url else "",
                key="graph_api_parameters",
                # on_change=update_url
            )
            update_url_button = st.form_submit_button(label="Update URL")
            st.text_input(
                label="Complete URL",
                value=st.session_state.graph_api_url,
                key="graph_api_complete_url",
                disabled=False
            )
            submit_api_call = st.form_submit_button(label="Call Graph API")
        
        if update_url_button:
            update_url()
            st.rerun()

        if submit_api_call:
            with st.spinner("Calling Graph API..."):
                # Update the session state with the potentially modified URL
                # st.session_state.graph_api_url = updated_url
                st.session_state.graph_api_response = call_graph_api(st.session_state.graph_api_url)

    # Display the Graph API response in a scrollable window and add an interpret button
    if st.session_state.get("graph_api_response"):
        st.subheader("Graph API Response")
        with st.form(key='graph_api_response_form'):
            st.text_area(
                label="Graph API Response",
                label_visibility="collapsed",
                value=st.session_state.graph_api_response,
                height=300,
                key="graph_api_response_col1"
            )
            interpret_button = st.form_submit_button(label="Interpret Response")
        
        if interpret_button:
            st.session_state.interpret_url = True
            st.rerun()

with col2:
    # st.header("Have a conversation with an advanced AI")
    # st.subheader("(Threads, Reasoning, Tools, Functions)")
    
    # Add a Clear button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = client.beta.threads.create().id  # Create a new thread
        clear_debug_messages()  # Clear debug messages
        st.rerun()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat input at the top
    prompt = st.chat_input("Type something here...")

    # Create a container for the conversation
    conversation_container = st.container(height=None, border= True)  # Dynamically set height based on available space

    # Handle interpretation of API result
    if st.session_state.get("interpret_url", False):
        with st.spinner("Interpreting Graph API Response..."):
            graph_api_url = st.session_state.get("graph_api_url", "")
            graph_api_response = st.session_state.get("graph_api_response", "")
            thread_id = get_or_create_thread_id()
            
            interpretation_prompt = f"""\
            Interpret the following Graph API call:

            This was my request:
            {user_input}

            This was the Graph API call you provided:
            URL: {graph_api_url}
            Response: {graph_api_response}

            Please provide a clear and concise interpretation of this data.
            """
            
            ai_interpretation = chat_with_assistant(dedent(interpretation_prompt), [], thread_id)
            
            st.session_state.messages.append({"role": "assistant", "content": ai_interpretation})
        
        # Reset the flag
        st.session_state.interpret_url = False
        st.rerun()

    # Display the conversation history in reverse order
    with conversation_container:
        for message in reversed(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Handle new user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                thread_id = get_or_create_thread_id()
                full_response = chat_with_assistant(prompt, st.session_state.messages, thread_id)
            full_response
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

# At the end of the file, add this to ensure debug info is always displayed
write_debug("")
