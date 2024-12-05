import streamlit as st
import requests
from openai import OpenAI
import json
import time
import os
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb

# Initialize session state for chat history and search history
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

# Streamlit app title and sidebar filters
st.title("🌍 **Interactive Travel Guide Chatbot** 🤖")
st.markdown("Your personal travel assistant to explore amazing places.")

with st.sidebar:
    st.markdown("### Filters")
    min_rating = st.slider("Minimum Rating", 0.0, 5.0, 3.5, step=0.1)
    max_results = st.number_input("Max Results to Display", min_value=1, max_value=20, value=10)
    st.markdown("___")
    st.markdown("### Search History")
    selected_query = st.selectbox("Recent Searches", options=[""] + st.session_state['search_history'])

# API keys
api_key = st.secrets["api_key"]
openai_api_key = st.secrets["key1"]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_Weather",
            "description": "Get the weather for the location mentioned in the user prompt",
            "parameters": {
                "type": "object",
                "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        }
                },
                "required": ["location"],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "get_places_from_google",
            "description": "Get data about places, hotels, restaurants, tourism locations, lakes, mountain, parks etc. from Google Places API. As long as it is some information about Cities or Towns, any minute details of facilities or places in cities, we can get that information here e.g places in New York, Tourist places in Syracuse etc give details about places in that cities",
            "parameters": {
                "type": "object",
                "properties": {
                               "query": {"type": "string", 
                                         "description": "Places or facilities in city/location e.g Places in New York"}
                },
                "required": ["query"],
            },
        },
    }
]



import chromadb

# Initialize ChromaDB client
client = chromadb.Client()

# Assume "locations" collection exists in ChromaDB
collection = client.get_or_create_collection("locations")

def setup_vectordb():
    """
    Set up the ChromaDB vector database for travel locations. 
    It initializes the collection, adds documents, and checks for an existing database.
    """
    db_path = "Travel_VectorDB"

    if not os.path.exists(db_path):
        st.info("Setting up VectorDB for the first time...")
        client = chromadb.PersistentClient(path=db_path)
        
        # Load travel locations data
        data_file = "locations.json"  # Ensure this file exists in the working directory
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            
            for location in data:
                collection.add(
                    documents=[{
                        "id": str(location["id"]),  # Ensure ID is a string
                        "name": location["name"],
                        "state": location["state"],
                        "country": location["country"],
                        "coord": location["coord"]
                    }],
                    metadatas=[{
                        "id": location["id"],
                        "name": location["name"],
                        "state": location["state"],
                        "country": location["country"]
                    }],
                    ids=[str(location["id"])]
                )
        else:
            st.error(f"Data file '{data_file}' not found!")
            return None
    else:
        client = chromadb.PersistentClient(path=db_path)

    # Return collection for further use
    return client.get_collection(name="locations")

def get_Weather(location, API_key):
    # Process location (e.g., "Syracuse, NY")
    city, state = location.split(",")[0].strip(), None
    if "," in location:
        state = location.split(",")[1].strip()
    
    # RAG Lookup in ChromaDB
    try:
        query_text = city if not state else f"{city}, {state}"
        query_results = collection.query(
            query_texts=[query_text],
            n_results=1  # Return the best match
        )
        if query_results["documents"]:
            # Get the first match's ID
            location_id = query_results["documents"][0]["id"]
            st.markdown(f"Location found: **{query_results['documents'][0]['name']}** (ID: {location_id})")
        else:
            st.error(f"Location '{location}' not found in database.")
            return None
    except Exception as e:
        st.error(f"Error during location lookup: {e}")
        return None

    # Use the `id` in the Weather API URL
    url = f"https://api.openweathermap.org/data/2.5/weather?id={location_id}&appid={API_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching weather: {response.status_code} - {response.text}")
        return None


# Function to fetch places from Google Places API
def fetch_places_from_google(query):
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": api_key
    }
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            # Filter by minimum rating and limit results
            filtered_results = [place for place in results if place.get("rating", 0) >= min_rating]
            return filtered_results[:max_results]
        else:
            return {"error": f"API error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


# Function for interacting with OpenAI's API
def chat_completion_request(messages):
    try:
        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        return response
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return None


# Handle function calls from GPT response
def handle_tool_calls(tool_call):
    arguments = {}
    if len(tool_call) == 2:
        for tool in tool_call:
            arguments.update(json.loads(tool.function.arguments))
    else:
        tool_call_data = tool_call[0]
        arguments = json.loads(tool_call_data.function.arguments)
    weather_data, places_data = None, None

    if 'location' in arguments:
            location = arguments.get("location")
            if location:
                st.markdown(f"Fetching weather for: **{location}**")
                open_api_key = st.secrets['OpenWeatherAPIkey']
                weather_data = get_Weather(location, open_api_key)
                messages = [
                    {"role": "user", "content": "Explain in normal English in few words including what kind of clothing can be worn and what tips need to be taken based on the following weather data."},
                    {"role": "user", "content": json.dumps(weather_data)}
                ]
                client = OpenAI(api_key=openai_api_key)
                stream = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    stream = True
                )
                location = ''
                message_placeholder = st.empty()
                full_response = ""
                if stream:
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                
        # Process get_places_from_google if provided
    if 'query' in arguments:
            query = arguments.get("query")
            if query:
                st.markdown(f"Searching for: **{query}**")
                places_data = fetch_places_from_google(query)
                query = ''
                if isinstance(places_data, dict) and "error" in places_data:
                    st.error(f"Error: {places_data['error']}")
                elif not places_data:
                    st.warning("No places found matching your criteria.")
                else:
                    st.markdown("### 📍 Top Recommendations")
                    for idx, place in enumerate(places_data):
                        with st.expander(f"{idx + 1}. {place.get('name', 'No Name')}"):
                            st.write(f"📍 **Address**: {place.get('formatted_address', 'No address available')}")
                            st.write(f"🌟 **Rating**: {place.get('rating', 'N/A')} (Based on {place.get('user_ratings_total', 'N/A')} reviews)")
                            st.write(f"💲 **Price Level**: {place.get('price_level', 'N/A')}")
                            if "photos" in place:
                                photo_ref = place["photos"][0]["photo_reference"]
                                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={api_key}"
                                st.image(photo_url, caption=place.get("name", "Photo"), use_column_width=True)
                            lat, lng = place["geometry"]["location"].values()
                            map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                            st.markdown(f"[📍 View on Map]({map_url})", unsafe_allow_html=True)

setup_vectordb()
      
# handle user input
user_query = st.text_input("🔍 What are you looking for? (e.g., 'restaurants in Los Angeles'):", value=selected_query)

if user_query:
    if user_query not in st.session_state["search_history"]:
        st.session_state["search_history"].append(user_query)
    user_query = user_query + " and tell me the weather at this place"
    message = {"role": "user", "content": user_query}

    # Get response from OpenAI
    with st.spinner("Generating response..."):
        response = chat_completion_request([message])

    if response:
        tool_call = response.choices[0].message.tool_calls
        
        # Handle function call from GPT
        if tool_call:
            handle_tool_calls(tool_call)
        else:
            with st.chat_message("assistant"):
                st.markdown(response_message.content)
