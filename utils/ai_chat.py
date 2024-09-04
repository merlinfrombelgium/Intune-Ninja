import os
import time
from openai import OpenAI
from utils.oai_assistant import Assistant

client = OpenAI(api_key=os.getenv('LLM_API_KEY'))

def chat_with_ai(message, history, system_prompt):
    messages = [
        {"role": "system", "content": system_prompt['content']},
        {"role": "user", "content": message}
    ]
    
    response = client.chat.completions.create(
        model=os.getenv('LLM_MODEL'),
        messages=messages,
        temperature=0.8,
        stream=True,
        max_tokens=1000,
    )

    partial_response = ""
    for stream_response in response:
        if stream_response.choices[0].delta.content is not None:
            partial_response += stream_response.choices[0].delta.content
            yield [(message, partial_response)]

    return [(message, partial_response)]

def chat_with_assistant(message: str, history: list, thread_id: str = None):
    if thread_id is None:
        thread_id = client.beta.threads.create().id

    for msg in history:
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role=msg["role"],
            content=msg["content"]
        )

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    IntuneCopilotAssistant = Assistant(client).retrieve_assistant()

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=IntuneCopilotAssistant.id,
        instructions="Please provide a detailed response. You can use up to 4000 tokens if needed."
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == "failed":
            raise Exception("Run failed")
        time.sleep(0.5)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data[0].content[0].text.value

def interpret_graph_api_url(url, thread_id: str = None):
    prompt = f"""Interpret and explain the following Graph API URL: {url}

Provide a brief explanation of what this URL does and what kind of data it will retrieve.
If you think the URL could be improved or modified, suggest changes and explain why.
Format your response as follows:

Interpretation: [Your interpretation here]
Suggested Changes: [Your suggested changes here, or 'None' if no changes are needed]
Modified URL: [The modified URL if changes are suggested, or the original URL if no changes are needed]"""

    response = chat_with_assistant(prompt, [], thread_id)
    return {
        "interpretation": response.split("Interpretation:")[1].split("Suggested Changes:")[0].strip(),
        "suggested_changes": response.split("Suggested Changes:")[1].split("Modified URL:")[0].strip(),
        "modified_url": response.split("Modified URL:")[1].strip()
    }