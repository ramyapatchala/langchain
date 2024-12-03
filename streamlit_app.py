import streamlit as st
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
import requests
import json

# Streamlit app initialization
st.title("🌍 **Interactive Travel Guide Chatbot** 🤖")
st.markdown("Your personal travel assistant to explore amazing places.")

# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")
    min_rating = st.slider("Minimum Rating", 0.0, 5.0, 3.5, step=0.1)
    max_results = st.number_input("Max Results to Display", min_value=1, max_value=20, value=10)

# API keys
OPENAI_API_KEY = st.secrets["key1"]
WEATHER_API_KEY = st.secrets["OpenWeatherAPIkey"]
GOOGLE_PLACES_API_KEY = st.secrets["api_key"]

# Define tool functions
def get_weather(location):
    """Fetch weather data for a location."""
    try:
        if "," in location:
            location = location.split(",")[0].strip()
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            advice = f"The weather is {weather_desc} with a temperature of {temp}°C. "
            if temp > 25:
                advice += "Wear light clothing and stay hydrated."
            elif 15 <= temp <= 25:
                advice += "Wear comfortable clothing."
            else:
                advice += "Dress warmly to stay comfortable."
            return advice
        else:
            return f"Could not fetch weather data for {location}. Error: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def fetch_places(query):
    """Fetch places using Google Places API."""
    try:
        base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_PLACES_API_KEY
        }
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            results = data.get("results", [])
            filtered_results = [place for place in results if place.get("rating", 0) >= min_rating]
            places_info = []
            for place in filtered_results[:max_results]:
                name = place.get("name", "Unknown")
                rating = place.get("rating", "N/A")
                address = place.get("formatted_address", "No address available")
                places_info.append(f"{name} (Rating: {rating}): {address}")
            return "\n".join(places_info) if places_info else "No places found matching your criteria."
        else:
            return f"API error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error fetching places: {str(e)}"

# Define LangChain tools
weather_tool = Tool(
    name="Weather Information",
    func=get_weather,
    description="Provides weather information for a given location."
)

places_tool = Tool(
    name="Google Places Search",
    func=fetch_places,
    description="Search for places like restaurants, hotels, and attractions."
)

# Initialize LangChain components
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4", temperature=0)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

tools = [weather_tool, places_tool]
agent = initialize_agent(
    tools=tools,
    llm=llm,
    memory=memory,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION
)

# User input
user_input = st.text_input("🔍 What are you looking for?", placeholder="e.g., 'weather in Paris' or 'restaurants in Los Angeles'")

if user_input:
    # Process user input using the LangChain agent
    with st.spinner("Fetching data..."):
        try:
            response = agent.run(user_input)
            st.markdown("### 💬 Response")
            st.markdown(response)
        except Exception as e:
            st.error(f"Error: {e}")

# Display chat history
st.markdown("### 📝 Chat History")
for msg in memory.chat_memory.messages:
    role = msg["role"].capitalize()
    content = msg["content"]
    st.markdown(f"**{role}:** {content}")
