import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

# Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Streamlit app title
st.title("🌍 **Interactive Travel Guide Chatbot** 🤖")
st.markdown("Your personal travel assistant to explore amazing places.")

# API key (replace with your OpenAI API key or Streamlit secrets)
openai_api_key = st.secrets["key1"]

# Initialize LangChain ChatOpenAI
chat = ChatOpenAI(
    openai_api_key=openai_api_key,
    model="gpt-4",
    temperature=0.7
)

# Initialize memory for conversation history
if "memory" not in st.session_state:
    st.session_state["memory"] = ConversationBufferMemory(return_messages=True)

# Display chat history
for message in st.session_state["messages"]:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# User input
user_query = st.text_input("🔍 What are you looking for? (e.g., 'restaurants in Los Angeles'): ")

if user_query:
    # Add user input to memory and display
    user_message = HumanMessage(content=user_query)
    st.session_state["messages"].append(user_message)
    with st.chat_message("user"):
        st.markdown(user_message.content)

    # Generate response using LangChain
    with st.spinner("Generating response..."):
        response = chat(messages=st.session_state["memory"].chat_memory.messages)
        ai_message = AIMessage(content=response.content)

    # Add response to memory and display
    st.session_state["messages"].append(ai_message)
    st.session_state["memory"].chat_memory.add_message(ai_message)
    with st.chat_message("assistant"):
        st.markdown(ai_message.content)
