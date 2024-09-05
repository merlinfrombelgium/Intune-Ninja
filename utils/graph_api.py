import streamlit as st
import requests
import json
from requests.exceptions import HTTPError
from utils.ai_chat import get_user_secret, client
from utils.write_debug import write_debug

class MSGraphAPI:
    def __init__(self):
        write_debug("Initializing MSGraphAPI...")
        self.client_id = get_user_secret('MS_GRAPH_CLIENT_ID')
        self.client_secret = get_user_secret('MS_GRAPH_CLIENT_SECRET')
        self.tenant_id = get_user_secret('MS_GRAPH_TENANT_ID')
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            st.error("One or more required secrets are missing. Please check your configuration.")
            return

        self.base_url = "https://graph.microsoft.com/v1.0"
        write_debug("Attempting to get access token...")
        self.token = self.get_access_token()

    def get_access_token(self):
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        try:
            write_debug(f"Sending request to {url}")
            response = requests.post(url, headers=headers, data=body)
            write_debug(f"Response status code: {response.status_code}")
            response.raise_for_status()
            token = response.json().get("access_token")
            write_debug("Successfully obtained access token")
            return token
        except HTTPError as e:
            st.error(f"HTTP Error: {e}")
            if e.response.status_code == 400:
                st.error("Error 400: Bad Request. Please check your MS_GRAPH_TENANT_ID and MS_GRAPH_CLIENT_ID in the user secrets.")
            elif e.response.status_code == 401:
                st.error("Error 401: Unauthorized. Please check your MS_GRAPH_CLIENT_SECRET in the user secrets.")
            raise ValueError(f"HTTP Error: {e}")
        except Exception as e:
            st.error(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")
            raise ValueError(f"Error initializing Microsoft Graph client: {str(e)}. Please check your Microsoft Graph credentials.")

    def call_api(self, endpoint, method='GET', data=None):
        url = f"{endpoint}" if endpoint.startswith(self.base_url) else f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError("Unsupported HTTP method")

            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            if e.response.status_code == 400:
                raise ValueError("Error 400: Bad Request. Please check your request parameters and try again.\n\nFull Error: " + str(e))
            raise ValueError(f"HTTP Error: {e}")
        except Exception as e:
            raise ValueError(f"Error calling Microsoft Graph API: {str(e)}")

def call_graph_api(api_url):
    ms_graph_api = MSGraphAPI()
    try:
        api_response = ms_graph_api.call_api(api_url)
        return json.dumps(api_response, indent=2)
    except Exception as e:
        return f"Error calling API: {str(e)}"

def get_graph_api_url(message, system_prompt):
    if not client:
        st.error("OpenAI client is not initialized.")
        return None

    messages = [
        {"role": "system", "content": system_prompt["content"]},
        {"role": "user", "content": message}
    ]

    try:
        model = get_user_secret('LLM_MODEL')
        print(f"Using model in get_graph_api_url: {model}")  # Debug print

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "GraphAPIURL",
                    "description": "A URL for the Microsoft Graph API.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "base_url": {"type": "string"},
                            "endpoint": {"type": "string"},
                            "parameters": {
                                "type": ["array", "null"],
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["base_url", "endpoint", "parameters"]
                    }
                }
            }
        )

        content = response.choices[0].message.content
        content_dict = json.loads(content)

        if content_dict['parameters']:
            parameters = [param.lstrip('?') for param in content_dict['parameters']]
            url = f"{content_dict['base_url']}{content_dict['endpoint']}?{'&'.join(parameters)}"
        else:
            url = f"{content_dict['base_url']}{content_dict['endpoint']}"

        return url
    except Exception as e:
        print(f"Error in get_graph_api_url: {str(e)}")
        return None