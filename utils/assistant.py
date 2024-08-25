from openai import OpenAI
import os, dotenv

dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"))
 
try:
    assistants_list = client.beta.assistants.list()
    IntuneCopilot_assistant = [assistant for assistant in assistants_list if assistant.name == "Intune Copilot"][0]
    if IntuneCopilot_assistant is None:
        print("Intune Copilot not found in list of assistants, creating new one")
        IntuneCopilot_assistant = client.beta.assistants.create(
            name="Intune Copilot",
            instructions=open(os.sep.join([os.pardir, "prompts", "assistant_instructions.md"]), "r").read().strip(),
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
        )
except Exception:
    print("An error occurred while creating or retrieving the assistant")

if IntuneCopilot_assistant.tool_resources.file_search.vector_store_ids is None:
    try:
        vector_store_list = client.beta.vector_stores.list()
        IntuneCopilot_vector_store = next((store for store in vector_store_list if store.name == "Intune Copilot"), None)
        if IntuneCopilot_vector_store is None:
            print("Existing vector store not found, creating new one")
            vector_store = client.beta.vector_stores.create(
                name="Intune_Copilot",
            )
    except Exception as e:
        print(f"An error occurred while creating or retrieving the vector store: {e}")
else:
    IntuneCopilot_vector_store_id = IntuneCopilot_assistant.tool_resources.file_search.vector_store_ids[0]

file_paths = [os.path.join(os.pardir, "files", "graph_api_docs", f) for f in os.listdir(os.path.join(os.pardir, "files", "graph_api_docs")) if f.endswith('.md')]
file_streams = [open(file_path, "rb") for file_path in file_paths]

file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=IntuneCopilot_vector_store_id,
  files=file_streams
)

print(file_batch.status)
print(file_batch.file_counts)

