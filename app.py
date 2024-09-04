import streamlit as st

def show_chat_message(message):
    st.write(message[:100] + "...")  # Show first 100 characters

    if st.button("Show Full Response"):
        st.write("Full Response:")
        st.text_area("", value=message, height=300, max_chars=None, key=f"full_response_{hash(message)}")

# Example usage
messages = [
    "This is a short message.",
    "This is a longer message that exceeds 100 characters and will be truncated in the initial view.",
]

for msg in messages:
    show_chat_message(msg)