def generate_graph_api_request(query) -> str:
    """
    Generate a Graph API request URL based on the provided query.

    Args:
        query (str): The user query for what information to pull from Graph API.

    Returns:
        str: A formatted Graph API request URL.
    """
    base_url = "https://graph.microsoft.com/v1.0/"
    request_url = base_url + endpoint

    return request_url
