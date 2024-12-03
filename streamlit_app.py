import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
import requests

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'memory' not in st.session_state:
    st.session_state['memory'] = ConversationBufferMemory(return_messages=True)
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

# API keys (replace with your own or Streamlit secrets)
openai_api_key = st.secrets["key1"]
google_api_key = st.secrets["api_key"]

# Initialize LangChain ChatOpenAI with streaming
chat = ChatOpenAI(
    openai_api_key=openai_api_key,
    model="gpt-4",
    temperature=0.7,
    streaming=True
)

# Ensure the memory has a default system message
if not st.session_state["memory"].chat_memory.messages:
    st.session_state["memory"].chat_memory.add_message(
        SystemMessage(content="You are a helpful travel guide assistant.")
    )

# Streamlit app UI
st.title("🌍 **Interactive Travel Guide Chatbot** 🤖")
st.markdown("Your personal travel assistant to explore amazing places.")

# Display chat history
for message in st.session_state["messages"]:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# User input box
user_query = st.text_input(
    "🔍 Ask me anything about travel (e.g., 'restaurants in Los Angeles'): ",
    value=st.session_state['user_input'],
    key="input_box",
    on_change=lambda: st.session_state.update({"user_input": ""})
)

if user_query:
    # Add user input to memory
    user_message = HumanMessage(content=user_query)
    st.session_state["memory"].chat_memory.add_message(user_message)
    st.session_state["messages"].append(user_message)
    with st.chat_message("user"):
        st.markdown(user_message.content)

    # Generate a streaming response
    with st.spinner("Generating response..."):
        response_placeholder = st.empty()
        response_stream = chat(messages=st.session_state["memory"].chat_memory.messages)
        full_response = ""
        st.markdown(response_stream.content)
        
    # Add the response to memory and display
    ai_message = AIMessage(content=full_response)
    st.session_state["memory"].chat_memory.add_message(ai_message)
    st.session_state["messages"].append(ai_message)

# Function to fetch places from Google Places API
def fetch_places(query, min_rating=3.5, max_results=10):
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": google_api_key}
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            # Filter and limit results
            filtered_results = [place for place in results if place.get("rating", 0) >= min_rating]
            return filtered_results[:max_results]
        else:
            return {"error": f"API error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Display place details (if requested)
if "places_query" in st.session_state:
    places = fetch_places(st.session_state["places_query"])
    if isinstance(places, dict) and "error" in places:
        st.error(f"Error: {places['error']}")
    elif not places:
        st.warning("No places found matching your criteria.")
    else:
        st.markdown("### 📍 Top Recommendations")
        for idx, place in enumerate(places):
            with st.expander(f"{idx + 1}. {place.get('name', 'No Name')}"):
                st.write(f"📍 **Address**: {place.get('formatted_address', 'No address available')}")
                st.write(f"🌟 **Rating**: {place.get('rating', 'N/A')} (Based on {place.get('user_ratings_total', 'N/A')} reviews)")
                st.write(f"💲 **Price Level**: {place.get('price_level', 'N/A')}")
                if "photos" in place:
                    photo_ref = place["photos"][0]["photo_reference"]
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={google_api_key}"
                    st.image(photo_url, caption=place.get("name", "Photo"), use_column_width=True)
                lat, lng = place["geometry"]["location"].values()
                map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                st.markdown(f"[📍 View on Map]({map_url})", unsafe_allow_html=True)
