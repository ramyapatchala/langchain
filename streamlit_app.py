import streamlit as st
import requests
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from datetime import date
from PIL import Image
import io

# Function to fetch places from Google Places API
def fetch_places_from_google(query):
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": api_key}
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

# Helper function to resize images
def fetch_and_resize_image(url, size=(200, 200)):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        img = img.resize(size)  # Resize to uniform dimensions
        return img
    except Exception as e:
        return None  # Return None if fetching or resizing fails

# Display places in 3x3 grid layout with uniform image sizes
def display_places_grid(places):
    cols = st.columns(3)
    for idx, place in enumerate(places):
        with cols[idx % 3]:
            name = place.get("name", "No Name")
            lat, lng = place["geometry"]["location"].values()
            map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            photo_url = None
            if "photos" in place:
                photo_ref = place["photos"][0]["photo_reference"]
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={api_key}"

            if photo_url:
                img = fetch_and_resize_image(photo_url)
                if img:
                    st.image(img, caption=name, use_column_width=False)
                else:
                    st.write(name)
            else:
                st.write(name)

            st.markdown(f"[📍 View on Map]({map_url})", unsafe_allow_html=True)
            if name in st.session_state['itinerary_bucket']:
                st.button("Added", disabled=True, key=f"added_{idx}")
            else:
                if st.button("Add to Itinerary", key=f"add_{idx}"):
                    st.session_state['itinerary_bucket'].append(name)

# Function to generate an itinerary using LangChain
def plan_itinerary_with_langchain():
    if not st.session_state['itinerary_bucket']:
        st.warning("No places in itinerary bucket!")
        return

    st.markdown("### 🗺️ AI-Generated Itinerary")
    places_list = "\n".join(st.session_state['itinerary_bucket'])

    if selected_date:
        st.info(f"Planning itinerary for {selected_date.strftime('%A, %B %d, %Y')} 🎉")
    else:
        st.info("No specific date chosen. Starting from 9:00 AM by default.")

    prompt_template = PromptTemplate(
        input_variables=["places", "date"],
        template="""Plan a travel itinerary for the following places:
        {places}
        Date of travel: {date}
        Provide a detailed plan including the best order to visit, time at each location, transportation time, and meal breaks.
        """
    )

    date_str = selected_date.strftime('%A, %B %d, %Y') if selected_date else "Not specified"
    formatted_prompt = prompt_template.format(places=places_list, date=date_str)

    with st.spinner("Generating your itinerary..."):
        response = llm([HumanMessage(content=formatted_prompt)])
        st.markdown(response.content)
        save_itinerary(response.content)

def save_itinerary(response):
    # Create a text input for the itinerary title
    itinerary_title = st.text_input("Enter a title for this itinerary:", placeholder="Save this itinerary")
    # Add a save button to explicitly trigger saving
    if not itinerary_title:
        st.warning("Please enter a title for your itinerary.")
    elif itinerary_title in st.session_state['itineraries']:
        st.warning("Itinerary with this title already exists. Choose a unique title.")
    else:
            # Save itinerary to session state
        st.session_state['itineraries'][itinerary_title]=response
        st.markdown(f"Itinerary '{itinerary_title}' saved successfully!")
                # Clear the input after saving
        st.experimental_rerun()

# Initialize session state for itinerary bucket and search history
if 'itinerary_bucket' not in st.session_state:
    st.session_state['itinerary_bucket'] = []
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'itineraries' not in st.session_state:
    st.session_state['itineraries'] = {}

# Streamlit app title and sidebar filters
st.title("🌍 **Travel Planner with AI** ✈️")
st.markdown("Discover amazing places and plan your trip effortlessly!")

# Sidebar with filters, search history, and saved itineraries
with st.sidebar:
    st.markdown("### Filters")
    min_rating = st.slider("Minimum Rating", 0.0, 5.0, 3.5, step=0.1)
    max_results = st.number_input("Max Results to Display", min_value=1, max_value=20, value=9)
    st.markdown("___")
    st.markdown("### Search History")
    selected_query = st.selectbox("Recent Searches", options=[""] + st.session_state['search_history'])
    st.markdown("### Saved Itineraries")
    selected_itinerary = st.selectbox("Recent Itinerary", options=[""] + list(st.session_state['itineraries'].keys()))

# API key for Google Places API
api_key = st.secrets["api_key"]
openai_api_key = st.secrets["openai_api_key"]

# Initialize LangChain ChatOpenAI model
llm = ChatOpenAI(temperature=0.3, model="gpt-4o-mini", openai_api_key=openai_api_key, verbose=True)

# Handle search input
user_query = st.text_input("🔍 Search for places (e.g., 'restaurants in Paris'):", value=selected_query)
selected_date = st.date_input("Choose a date for your trip (optional):", value=None)
if user_query:
    if user_query not in st.session_state["search_history"]:
        st.session_state["search_history"].append(user_query)

    st.markdown(f"### Results for: **{user_query}**")
    with st.spinner("Fetching places..."):
        places_data = fetch_places_from_google(user_query)

    if isinstance(places_data, dict) and "error" in places_data:
        st.error(f"Error: {places_data['error']}")
    elif not places_data:
        st.warning("No places found matching your criteria.")
    else:
        display_places_grid(places_data)

    # Show itinerary bucket
    st.markdown("### 📋 Itinerary Bucket")
    if st.session_state['itinerary_bucket']:
        for place in st.session_state['itinerary_bucket']:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(place)
            with col2:
                if st.button("Remove", key=f"remove_{place}"):
                    st.session_state['itinerary_bucket'].remove(place)
    else:
        st.write("Your itinerary bucket is empty.")
    
    # Generate itinerary button
    if st.button("Generate AI Itinerary"):
        plan_itinerary_with_langchain()
    
    if selected_itinerary:
        st.markdown(selected_itinerary)
        selected_places_itinery = st.session_state['itineraries'][selected_itinerary]
        st.markdown(selected_places_itinery)
