import os
import streamlit as st
from utils.write_debug import write_debug, clear_debug_messages
from textwrap import dedent
from utils.graph_api import call_graph_api, get_access_token, test_graph_authentication
from utils.ai_chat import initialize_client, chat_with_assistant, check_client_status, update_client_status
import json
from urllib.parse import urlparse, parse_qs
import requests
import toml
from utils.graph_url_generator import generate_graph_api_url, format_graph_api_url

# At the beginning of the file, after other function definitions
def check_graph_auth():
    try:
        # Use a simple Graph API call to check authentication
        url = "https://graph.microsoft.com/v1.0/me"
        token = get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        return response.status_code == 200
    except Exception as e:
        write_debug(f"Error in check_graph_auth: {str(e)}")
        return False

# Add this new function to parse the pasted secrets
def parse_secrets(secrets_text):
    secrets = {}
    for line in secrets_text.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            secrets[key.strip()] = value.strip()
    return secrets

def save_secrets_to_file(secrets):
    secrets_path = os.path.join('.streamlit', 'secrets.toml')
    with open(secrets_path, 'w') as f:
        toml.dump(secrets, f)

def reset_state():
    keys_to_keep = ['user_secrets', 'LLM_MODEL', 'client_status']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    
    # Reset specific form fields
    st.session_state.query_input = ""
    st.session_state.graph_api_url = ""
    st.session_state.graph_api_json = {"version": "v1.0", "endpoint": "", "parameters": []}
    st.session_state.graph_api_response = ""
    st.session_state.graph_api_complete_url = ""
    st.session_state.examples_dropdown = ""
    st.session_state.messages = []
    
    # Clear debug messages
    clear_debug_messages()

def get_graph_api_url(query, system_prompt):
    try:
        url_data = generate_graph_api_url(query)
        if url_data:
            formatted_url = format_graph_api_url(url_data)
            write_debug(f"Generated URL (beta version): {formatted_url}")
            
            json_representation = {
                "base_url": url_data.base_url,
                "version": "beta",  # Ensure we're always using beta
                "endpoint": url_data.endpoint,
                "parameters": url_data.parameters or []
            }
            
            return {"url": formatted_url, "json": json_representation}
    except Exception as e:
        write_debug(f"Error in get_graph_api_url: {str(e)}")
    return None

# Streamlit UI setup
st.set_page_config(
    page_title=":ninja: Intune Ninja",
    layout="wide",
    page_icon=":ninja:",
    initial_sidebar_state="collapsed"
)  # This is how our app can be found through the Streamlit search engine

# Add this near the top of the file, after other imports
if 'secrets_saved' not in st.session_state:
    st.session_state.secrets_saved = False

# Function to load or initialize secrets
def load_or_init_secrets():
    # Comment out or remove some write_debug calls, for example:
    # write_debug("Starting load_or_init_secrets function")
    if 'user_secrets' not in st.session_state:
        # write_debug("Initializing user_secrets in session state")
        st.session_state.user_secrets = {
            'OpenAI API key': st.secrets.get("OpenAI_API_key", ""),
            'Graph proxy TENANT ID': st.secrets.get("Graph_proxy_TENANT_ID", ""),
            'Graph proxy CLIENT ID': st.secrets.get("Graph_proxy_CLIENT_ID", ""),
            'Graph proxy CLIENT SECRET': st.secrets.get("Graph_proxy_CLIENT_SECRET", ""),
        }
    else:
        # write_debug("user_secrets already in session state")
        pass

    # Initialize LLM_MODEL
    if 'LLM_MODEL' not in st.session_state:
        st.session_state.LLM_MODEL = st.secrets.get("LLM_MODEL", "o3-mini")
        write_debug(f"Initialized LLM_MODEL: {st.session_state.LLM_MODEL}")

    # Initialize client status
    if 'client_status' not in st.session_state:
        st.session_state.client_status = "unknown"
        write_debug("Initialized client_status to unknown")

    # Log the keys in user_secrets
    # write_debug(f"Keys in user_secrets: {list(st.session_state.user_secrets.keys())}")

    # Initialize query_input
    if 'query_input' not in st.session_state:
        st.session_state.query_input = ""

    # Initialize system prompt
    if 'system_prompt' not in st.session_state:
        try:
            with open(os.sep.join([os.curdir, "prompts", "system_prompt.md"]), 'r') as file:
                st.session_state.system_prompt = file.read().strip()
        except FileNotFoundError:
            st.session_state.system_prompt = "Default system prompt if file not found."

    # Initialize interpretation prompt
    if 'interpretation_prompt' not in st.session_state:
        st.session_state.interpretation_prompt = """
        Analyze the given Graph API response and provide a clear, concise interpretation. 
        Explain what the data represents and any notable insights. 
        If there are any errors or issues with the response, explain what they mean and suggest potential solutions.
        """

    # Initialize run_instructions
    if 'run_instructions' not in st.session_state:
        st.session_state.run_instructions = "Default instructions for the AI assistant."

    # Initialize other potentially used session state variables
    if 'secrets_saved' not in st.session_state:
        st.session_state.secrets_saved = False

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'graph_api_url' not in st.session_state:
        st.session_state.graph_api_url = ""

    if 'graph_api_json' not in st.session_state:
        st.session_state.graph_api_json = {"version": "v1.0", "endpoint": "", "parameters": []}

    if 'graph_api_response' not in st.session_state:
        st.session_state.graph_api_response = ""

    if 'new_url' not in st.session_state:
        st.session_state.new_url = None

    # write_debug("Finished load_or_init_secrets function")

# Ensure this function is called at the start of the application
load_or_init_secrets()
update_client_status()

def get_openai_client():
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = initialize_client()
        if st.session_state.openai_client:
            write_debug("OpenAI client initialized successfully.")
        else:
            write_debug("Failed to initialize OpenAI client.")
    return st.session_state.openai_client

# Function to check if secrets are set
def are_secrets_set():
    return all(st.session_state.user_secrets.values()) and st.session_state.secrets_saved

def update_client_and_status():
    client = get_openai_client()
    update_client_status()

# Check if it's the first run and secrets are not set
if 'first_run' not in st.session_state:
    st.session_state.first_run = True

# Welcome message using st.toast
if st.session_state.first_run and not are_secrets_set():
    st.toast("Intune Ninja says hi!", icon="🥷")
    st.session_state.first_run = False
    if 'bad_request' not in st.session_state:
        st.session_state.bad_request = False
# if not client:
#     client = initialize_client()
#     st.success("OpenAI client initialized successfully!")

# Modify the mask_string function to handle different types of secrets
def mask_string(s, key):
    if not s:
        return ""
    if key == 'Graph proxy CLIENT ID' or key == 'Graph proxy TENANT ID':
        return f"{s[:8]}{'*' * 16}{s[-12:]}"
    elif key == 'Graph proxy CLIENT SECRET':
        return f"{s[:6]}{'*' * 10}{s[-4:]}"
    elif key == 'OpenAI API key':
        return f"{s[:10]}{'*' * (len(s) - 14)}{s[-4:]}"
    else:
        return f"{'*' * (len(s) - 4)}{s[-4:]}"

# Function to validate OpenAI API key format
def is_valid_openai_api_key(api_key):
    return api_key.startswith('sk-') or api_key.startswith('sk-proj-')

def invoke_graph_api(url):
    response = call_graph_api(st.session_state.graph_api_url)
    if "Error 400" in response:
        write_debug(":negative_squared_cross_mark: Bad Request. Trying to get metadata instead.")
        #st.warning("Bad Request. Trying to get metadata instead.")
        st.session_state.bad_request = True
        try:
            st.session_state.metadata = call_graph_api(st.session_state.graph_api_json["base_url"] + st.session_state.graph_api_json["version"] + "/" + st.session_state.graph_api_json["endpoint"] + "?$top=1")
        except:
            st.session_state.metadata = call_graph_api("https://graph.microsoft.com/" + st.session_state.graph_api_json["version"] + "/" + st.session_state.graph_api_json["endpoint"] + "?$top=1")
    return response

# Main layout
if not are_secrets_set():
    st.title("🥷 Intune Ninja")
    st.markdown("""
    Intune Ninja is an AI-powered tool that helps you craft Microsoft Graph API calls for Intune and interpret the results.
    It leverages OpenAI's language models to understand your queries and generate accurate API requests.
    
    To get started, please enter your API keys and secrets below.
    """)

    with st.container():
        st.subheader("API Keys and Secrets")
        st.info("Enter all your secrets below, then click 'Save Secrets' when done.")
        
        # Instructions for getting API keys
        with st.expander("Where to get API keys", expanded=False):
            st.markdown("""
            1. **OpenAI API key**: Get it from [OpenAI's website](https://platform.openai.com/account/api-keys)
            2. **Graph proxy TENANT ID**: Find it in your Entra ID (formerly Azure AD) overview
            3. **Graph proxy CLIENT ID**: Create a new app registration in Entra ID and use its Application (client) ID
            4. **Graph proxy CLIENT SECRET**: Generate a new client secret in your app registration
            
            For detailed instructions on setting up a Graph proxy app, please refer to our [Graph Proxy Setup Guide](https://docs.microsoft.com/en-us/graph/auth-v2-service).
            """)

        # Create separate input fields for each secret
        for key in st.session_state.user_secrets.keys():
            if key == 'OpenAI API key':
                new_value = st.text_input(
                    label=key,
                    value=mask_string(st.session_state.user_secrets[key], key),
                    type="password",
                    key=f"input_{key}",
                    help="Required. Must start with 'sk-' or 'sk-proj-'",
                    placeholder="Enter your OpenAI API key here" if not st.session_state.user_secrets[key] else ""
                )
                if new_value and new_value != mask_string(st.session_state.user_secrets[key], key):
                    if is_valid_openai_api_key(new_value):
                        st.session_state.user_secrets[key] = new_value
                    else:
                        st.error("Invalid OpenAI API key format. It should start with 'sk-' or 'sk-proj-'.")
            else:
                new_value = st.text_input(
                    label=key,
                    value=mask_string(st.session_state.user_secrets[key], key),
                    type="password",
                    key=f"input_{key}",
                    help="Required",
                    placeholder=f"Enter your {key} here" if not st.session_state.user_secrets[key] else ""
                )
                # Only update if the value has changed (ignoring masking)
                if new_value != mask_string(st.session_state.user_secrets[key], key):
                    st.session_state.user_secrets[key] = new_value

        if st.button("Save Secrets", type="primary"):
            with st.spinner("Saving secrets and initializing client..."):
                try:
                    # Update the secrets dictionary
                    new_secrets = {
                        'Graph_proxy_CLIENT_ID': st.session_state.user_secrets['Graph proxy CLIENT ID'],
                        'Graph_proxy_CLIENT_SECRET': st.session_state.user_secrets['Graph proxy CLIENT SECRET'],
                        'Graph_proxy_TENANT_ID': st.session_state.user_secrets['Graph proxy TENANT ID'],
                        'OpenAI_API_key': st.session_state.user_secrets['OpenAI API key'],
                        'LLM_MODEL': st.session_state.LLM_MODEL
                    }
                    
                    # Check if we're in a local environment
                    if os.path.exists('.streamlit/secrets.toml'):
                        save_secrets_to_file(new_secrets)
                        st.success("Secrets updated and saved successfully in .streamlit/secrets.toml!")
                    else:
                        st.warning("This appears to be a deployed environment. Secrets cannot be updated at runtime. Please use your deployment platform's secrets management system.")
                    
                    st.session_state.secrets_saved = True
                    update_client_and_status()
                    st.session_state.show_test_graph = True
                except Exception as e:
                    st.error(f"An error occurred while saving secrets: {str(e)}")
                    st.session_state.secrets_saved = False
                    write_debug(f"Error saving secrets: {str(e)}")
            st.rerun()

        if st.session_state.get('show_test_graph', False):
            if st.button("Test Graph Authentication"):
                with st.spinner("Testing Graph authentication..."):
                    success, message = test_graph_authentication()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

elif are_secrets_set():
    st.title("🥷 Intune Ninja", help="*a ninja tool for crafting Graph API calls and interpreting the results with AI*")

    # Move configuration to sidebar
    with st.sidebar:
        st.subheader("Configuration")
        
        # Display masked secrets
        for key, value in st.session_state.user_secrets.items():
            st.text_input(
                label=key,
                value=mask_string(value, key),
                type="password",
                disabled=True
            )
        
        if st.button("Edit Secrets"):
            st.session_state.secrets_saved = False
            st.rerun()

        # OpenAI Model selection
        AVAILABLE_MODELS = ["o3-mini", "gpt-4o-2024-08-06", "gpt-4o-mini"]
        current_model = st.session_state.LLM_MODEL
        if current_model not in AVAILABLE_MODELS:
            st.warning(f"The currently saved model '{current_model}' is not in the list of available models. Defaulting to 'o3-mini'.")
            current_model = "o3-mini"
        
        new_model = st.selectbox(
            label="OpenAI Model", 
            options=AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(current_model)
        )
        if new_model != st.session_state.LLM_MODEL:
            with st.spinner("Updating model selection..."):
                try:
                    st.session_state.LLM_MODEL = new_model
                    # Update the secrets file with the new model
                    save_secrets_to_file({**st.secrets, "LLM_MODEL": new_model})
                    update_client_and_status()
                    st.success("Model selection updated successfully!")
                except Exception as e:
                    st.error(f"An error occurred while updating the model: {str(e)}")
                    write_debug(f"Error updating model: {str(e)}")

        # Add reasoning effort selection only for o3 models
        if st.session_state.LLM_MODEL.startswith("o3"):
            REASONING_EFFORTS = ["low", "medium", "high"]
            current_effort = st.session_state.get('REASONING_EFFORT', 'medium')
            reasoning_effort_tooltip = "Reasoning effort controls the depth and complexity of the model's reasoning. Higher values may result in more thorough but slower responses. [Learn more](https://platform.openai.com/docs/api-reference/chat/create#chat-create-reasoning_effort)"
            new_effort = st.selectbox(
                label="Reasoning Effort for Interpretation", 
                options=REASONING_EFFORTS,
                index=REASONING_EFFORTS.index(current_effort),
                help=reasoning_effort_tooltip
            )
            if new_effort != current_effort:
                st.session_state.REASONING_EFFORT = new_effort
                st.success("Reasoning effort updated successfully!")
        else:
            # Remove REASONING_EFFORT from session state if not using o3 model
            st.session_state.pop('REASONING_EFFORT', None)

        # Add Graph API authentication test button
        if st.button("Test Graph API Authentication"):
            with st.spinner("Testing Graph API authentication..."):
                success, message = test_graph_authentication()
                if success:
                    st.success(message)
                else:
                    st.error(message)

        # OpenAI Client Status
        st.subheader("OpenAI Client Status")
        client = get_openai_client()
        if client:
            st.success("OpenAI Client: :white_check_mark: Ready")
        else:
            st.error("OpenAI Client: :x: Error")
            st.error("There was an error initializing the OpenAI client. Please check your configuration and try again.")

        if st.button("Refresh Client Status"):
            with st.spinner("Refreshing client status..."):
                update_client_status()

    # Main content area
    left_column, right_column = st.columns([1, 2])

    with left_column:
        st.subheader("Query Input")
        # Create the examples dropdown
        examples = st.selectbox(
            "Examples",
            ["", "Show me users sorted by name", "List all Windows 11 devices", "Get all iOS devices"],
            key="examples_dropdown"
        )

        # Handle example selection
        if examples and examples != st.session_state.get("last_example", ""):
            st.session_state.last_example = examples
            st.session_state.query_input = examples

        # Create the query input
        query = st.text_input(
            "Open Query", 
            key="query_input",
            value=st.session_state.query_input
        )

        # Suggest Graph API URL button
        suggest_button = st.button('Suggest Graph API URL')

        # Move Graph API Request section here when interpretation is shown
        if 'show_interpretation' in st.session_state and st.session_state.show_interpretation:
            st.subheader("Graph API Request")
            if "graph_api_url" in st.session_state:
                with st.form(key='graph_api_form'):
                    original_values = {
                        'url': st.session_state.graph_api_url,
                        'version': st.session_state.graph_api_json.get("version", "beta"),
                        'endpoint': st.session_state.graph_api_json.get("endpoint", ""),
                        'parameters': "\n&".join(st.session_state.graph_api_json.get("parameters", []))
                    }

                    st.text_input(
                        label="Complete URL",
                        value=original_values['url'],
                        key="graph_api_complete_url",
                        disabled=False,
                    )
                    col_graph_left, col_graph_right = st.columns([0.2, 0.8])
                    with col_graph_left:
                        API_version = st.radio(
                            label="API version",
                            options=["v1.0", "beta"],
                            index=0 if original_values['version'] == "v1.0" else 1,
                            horizontal=True,
                            key="graph_api_choice",
                        )
                    with col_graph_right:
                        st.text_input(
                            label="endpoint",
                            value=original_values['endpoint'],
                            key="graph_api_endpoint",
                        )
                    st.text_area(
                        label="parameters",
                        value=original_values['parameters'],
                        key="graph_api_parameters",
                    )
                    
                    # Check if any values have changed
                    values_changed = (
                        st.session_state.graph_api_complete_url != original_values['url'] or
                        st.session_state.graph_api_choice != original_values['version'] or
                        st.session_state.graph_api_endpoint != original_values['endpoint'] or
                        st.session_state.graph_api_parameters != original_values['parameters']
                    )

                    col_graph_submit_left, col_graph_submit_right = st.columns(2)
                    with col_graph_submit_left:
                        submit_api_call = st.form_submit_button(label="🤞 :green[Try Graph API request]")
                    with col_graph_submit_right:
                        update_url_button = st.form_submit_button(label="♻️ Update Graph API URL", disabled=not values_changed)

                if update_url_button:
                    update_url()
                    st.rerun()

                if submit_api_call:
                    with st.spinner("Calling Graph API..."):
                        st.session_state.graph_api_response = invoke_graph_api(st.session_state.graph_api_url)
                        st.rerun()

        # Display the Graph API response
        if st.session_state.get("graph_api_response"):
            st.subheader("Graph API Response")
            st.text_area(
                label="Graph API Response",
                value=st.session_state.graph_api_response,
                height=250,
                key="graph_api_response_left_column"
            )

with right_column:
    if 'show_interpretation' not in st.session_state or not st.session_state.show_interpretation:
        st.subheader("Graph API Request")
        if suggest_button:
            if not st.session_state.secrets_saved:
                st.warning("Please save your secrets in the configuration section before using this feature.")
            else:
                current_query = st.session_state.query_input
                with st.spinner("Suggesting Graph API URL..."):
                    graph_api_url = get_graph_api_url(current_query, st.session_state.system_prompt)
                    if graph_api_url:
                        st.session_state.graph_api_url = graph_api_url["url"]
                        st.session_state.graph_api_json = graph_api_url["json"]
                    else:
                        st.error("Failed to generate Graph API URL. Please try again.")

        # Add back the Graph API URL form
        if "graph_api_url" in st.session_state:
            with st.form(key='graph_api_form'):
                original_values = {
                    'url': st.session_state.graph_api_url,
                    'version': st.session_state.graph_api_json.get("version", "beta"),
                    'endpoint': st.session_state.graph_api_json.get("endpoint", ""),
                    'parameters': "\n&".join(st.session_state.graph_api_json.get("parameters", []))
                }

                st.text_input(
                    label="Complete URL",
                    value=original_values['url'],
                    key="graph_api_complete_url",
                    disabled=False,
                )
                col_graph_left, col_graph_right = st.columns([0.2, 0.8])
                with col_graph_left:
                    API_version = st.radio(
                        label="API version",
                        options=["v1.0", "beta"],
                        index=0 if original_values['version'] == "v1.0" else 1,
                        horizontal=True,
                        key="graph_api_choice",
                    )
                with col_graph_right:
                    st.text_input(
                        label="endpoint",
                        value=original_values['endpoint'],
                        key="graph_api_endpoint",
                    )
                st.text_area(
                    label="parameters",
                    value=original_values['parameters'],
                    key="graph_api_parameters",
                )
                
                # Check if any values have changed
                values_changed = (
                    st.session_state.graph_api_complete_url != original_values['url'] or
                    st.session_state.graph_api_choice != original_values['version'] or
                    st.session_state.graph_api_endpoint != original_values['endpoint'] or
                    st.session_state.graph_api_parameters != original_values['parameters']
                )

                col_graph_submit_left, col_graph_submit_right = st.columns(2)
                with col_graph_submit_left:
                    submit_api_call = st.form_submit_button(label="🤞 :green[Try Graph API request]")
                with col_graph_submit_right:
                    update_url_button = st.form_submit_button(label="♻️ Update Graph API URL", disabled=not values_changed)

            if update_url_button:
                update_url()
                st.rerun()

            if submit_api_call:
                with st.spinner("Calling Graph API..."):
                    st.session_state.graph_api_response = invoke_graph_api(st.session_state.graph_api_url)
                    st.rerun()

        # Display the Graph API response
        if st.session_state.get("graph_api_response"):
            st.subheader("Graph API Response")
            with st.form(key='graph_api_response_form'):
                interpret_button = st.form_submit_button(
                    label="❔Interpret Response" if not st.session_state.get('bad_request', False) else "🪄 Fix it!"
                )
                st.text_area(
                    label="Graph API Response",
                    value=st.session_state.graph_api_response,
                    height=250,
                    key="graph_api_response_right_column"
                )
            
            if interpret_button:
                st.session_state.show_interpretation = True
                st.rerun()

    if 'show_interpretation' in st.session_state and st.session_state.show_interpretation:
        st.subheader("Interpretation")
        with st.spinner("Interpreting response..."):
            interpretation = chat_with_assistant(
                f"Interpret this Graph API response: {st.session_state.graph_api_response}",
                st.session_state.interpretation_prompt,
                st.session_state.messages
            )
            st.write(interpretation)

# At the end of the file, add this to ensure debug info is always displayed
# write_debug("")

# At the end of the file
if __name__ == "__main__":
    # Move any necessary initialization code here
    load_or_init_secrets()
    update_client_status()
    
    # Ensure there's always a last element in the Streamlit app
    st.empty()

def update_url():
    try:
        if "new_url" in st.session_state:
            st.session_state.graph_api_url = st.session_state.new_url
            del st.session_state["new_url"]
        elif st.session_state.graph_api_complete_url != st.session_state.graph_api_url:
            st.session_state.graph_api_url = st.session_state.graph_api_complete_url
            st.session_state.graph_api_json = {
                "version": st.session_state.graph_api_choice,
                "endpoint": st.session_state.graph_api_endpoint,
                "parameters": st.session_state.graph_api_parameters.split('\n')
            }
        else:
            base_url = "https://graph.microsoft.com/"
            parameters = st.session_state.graph_api_parameters.replace('\n', '&').strip('&')
            st.session_state.graph_api_url = f"{base_url}{st.session_state.graph_api_choice}/{st.session_state.graph_api_endpoint}{'?' + parameters if parameters else ''}"
        
        write_debug(f"Updated Graph API URL: {st.session_state.graph_api_url}")
    except Exception as e:
        st.error(f"Error updating URL: {e}")
        write_debug(f"Error in update_url: {str(e)}")
