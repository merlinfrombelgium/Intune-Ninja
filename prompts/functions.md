def generate_graph_api_request(endpoint, query_params=None) -> str:
    """
    Generate a Graph API request URL based on the provided endpoint and query parameters.

    Args:
        endpoint (str): The specific Graph API endpoint to call.
        query_params (dict, optional): A dictionary of query parameters to include in the request.

    Returns:
        str: A formatted Graph API request URL.
    """
    base_url = "https://graph.microsoft.com/v1.0/"
    request_url = base_url + endpoint

    if query_params:
        # Encode query parameters and append to the request URL
        encoded_params = '&'.join(f"{key}={value}" for key, value in query_params.items())
        request_url += f"?{encoded_params}"

    return request_url
