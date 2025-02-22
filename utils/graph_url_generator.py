import streamlit as st
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
from utils.write_debug import write_debug

class GraphAPIURL(BaseModel):
    base_url: str = Field(default="https://graph.microsoft.com", description="The base URL for the Microsoft Graph API")
    version: str = Field(default="beta", description="The API version (beta or v1.0)")
    endpoint: str = Field(..., description="The API endpoint")
    parameters: Optional[List[str]] = Field(default=None, description="Query parameters for the API call")

def generate_graph_api_url(query: str) -> GraphAPIURL:
    client = OpenAI(api_key=st.session_state.user_secrets['OpenAI API key'])
    
    function_description = {
        "name": "create_graph_api_url",
        "description": "Create a Microsoft Graph API URL based on the user's query, preferring the beta version",
        "parameters": GraphAPIURL.schema()
    }

    try:
        response = client.chat.completions.create(
            model=st.session_state.LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Microsoft Graph API URLs based on user queries. Always prefer using the beta version of the API unless there's a specific reason to use v1.0."},
                {"role": "user", "content": f"Generate a Graph API URL for: {query}"}
            ],
            functions=[function_description],
            function_call={"name": "create_graph_api_url"}
        )

        function_call = response.choices[0].message.function_call
        url_data = GraphAPIURL.parse_raw(function_call.arguments)
        
        # Ensure we're using the beta version
        url_data.version = "beta"
        
        write_debug(f"Generated Graph API URL: {url_data}")
        return url_data
    except Exception as e:
        write_debug(f"Error generating Graph API URL: {str(e)}")
        return None

def format_graph_api_url(url_data: GraphAPIURL) -> str:
    base_url = f"{url_data.base_url}/{url_data.version}/{url_data.endpoint}"
    if url_data.parameters:
        parameters = "&".join(url_data.parameters)
        return f"{base_url}?{parameters}"
    return base_url 