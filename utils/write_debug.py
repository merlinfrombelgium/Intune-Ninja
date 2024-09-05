import streamlit as st

def write_debug(message):
    if 'debug_messages' not in st.session_state:
        st.session_state.debug_messages = []
    
    st.session_state.debug_messages.append(message)
    print(message)  # Keep console logging
    
    # Ensure the debug container is always created
    if 'debug_container' not in st.session_state:
        st.session_state.debug_container = st.sidebar.empty()
    
    # Update the debug info in the sidebar
    with st.session_state.debug_container.container():
        with st.expander("Debug Info", expanded=False, icon="🔎"):
            st.text_area("", value="\n".join(st.session_state.debug_messages), height=400)

# Add this function to clear debug messages
def clear_debug_messages():
    if 'debug_messages' in st.session_state:
        st.session_state.debug_messages = []
    if 'debug_container' in st.session_state:
        st.session_state.debug_container.empty()

