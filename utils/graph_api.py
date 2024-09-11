import streamlit as st
import requests
import json
from requests.exceptions import HTTPError
from utils.ai_chat import get_user_secret
from utils.write_debug import write_debug

class MSGraphAPI:
    def __init__(self):
        write_debug(":clock1: Calling MS Graph API...")
        self.client_id = get_user_secret('MS_GRAPH_CLIENT_ID')
        self.client_secret = get_user_secret('MS_GRAPH_CLIENT_SECRET')
        self.tenant_id = get_user_secret('MS_GRAPH_TENANT_ID')
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            st.error(":warning: One or more required secrets are missing. Please check your configuration.")
            return

        self.base_url = "https://graph.microsoft.com/"
        self.version = any(version for version in ['v1.0', 'beta'])
        if 'graph_token' not in st.session_state:
            write_debug(":clock130: Attempting to get access token...")
            self.token = self.get_access_token()
            st.session_state.graph_token = self.token
        else:
            write_debug(":clock130: Using existing access token...")
            self.token = st.session_state.graph_token

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
            write_debug(f":satellite: Sending request to {url}")
            response = requests.post(url, headers=headers, data=body)
            write_debug(f":satellite: Response status code: {response.status_code}")
            response.raise_for_status()
            token = response.json().get("access_token")
            write_debug(":white_check_mark: Successfully obtained access token")
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

    def call_api(self, request, method='GET', data=None):
        url = f"{request}" if request.startswith(self.base_url) else f"{self.base_url}/{request}"
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
    write_debug(f":satellite: Calling API: {api_url}")
    try:
        api_response = ms_graph_api.call_api(api_url)
    except Exception as e:
        write_debug(f":warning: Error calling API: {str(e)}")
        return f"Error calling API: {str(e)}"
    
    # Check if there's more data available
    next_link = api_response.get('@odata.nextLink')
    
    result = {
        'data': api_response.get('value', []),
        'next_link': next_link
    }
    
    write_debug(f":white_check_mark: API call successful")
    return json.dumps(result, indent=2)

def get_next_batch(next_link):
    ms_graph_api = MSGraphAPI()
    try:
        write_debug(f":satellite: Calling next batch: {next_link}")
        api_response = ms_graph_api.call_api(next_link)
        
        # Check if there's more data available
        new_next_link = api_response.get('@odata.nextLink')
        
        result = {
            'data': api_response.get('value', []),
            'next_link': new_next_link
        }
        
        write_debug(f":white_check_mark: Next batch retrieved successfully")
        return json.dumps(result, indent=2)
    except Exception as e:
        write_debug(f":warning: Error retrieving next batch: {str(e)}")
        return f"Error retrieving next batch: {str(e)}"

def get_graph_api_url(client, message, system_prompt):
    messages = [
        {"role": "system", "content": system_prompt["content"]},
        {"role": "user", "content": message}
    ]

    try:
        model = get_user_secret('LLM_MODEL')
        # print(f"Using model in get_graph_api_url: {model}")  # Debug print

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=10,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "GraphAPIURL",
                    "description": "A URL for the Microsoft Graph API.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "base_url": {"type": "string", "enum": ["https://graph.microsoft.com/"]},
                            "version": {"type": "string", "enum": ["v1.0", "beta"], "description": "The version of the Microsoft Graph API to use. Beta will have more recent features. Check the knowledge base for more info."},
                            "endpoint": {"type": "string", "description": "The endpoint of the Microsoft Graph API to use. The choice of endpoint is crucial to get the correct response for the user's query. Note that some endpoints are only available in the beta version of the API. Check the knowledge base for more info. Do not include the base URL nor a leading '/' in the endpoint."},
                            "parameters": {
                                "type": ["array", "null"],
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["base_url", "version", "endpoint", "parameters"]
                    }
                }
            }
        )

        content = response.choices[0].message.content
        content_json = json.loads(content)

        if content_json['parameters']:
            parameters = [param.lstrip('?') for param in content_json['parameters']]
            url = f"{content_json['base_url']}{content_json['version']}/{content_json['endpoint'].strip('/')}?{'&'.join(parameters)}"
        else:
            url = f"{content_json['base_url']}{content_json['version']}/{content_json['endpoint'].strip('/')}"

        write_debug(f"Generated URL: {url}")
        write_debug(f"Generated URL in JSON: {content_json}")
        return {"url": url, "json": content_json}
    except Exception as e:
        write_debug(f"Error in get_graph_api_url: {str(e)}")
        return None