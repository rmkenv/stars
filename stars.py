import streamlit as st
from st_paywall import add_auth
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add authentication
add_auth(required=True)

# Streamlit page configuration
st.set_page_config(page_title="STARS Report Chatbot", page_icon="🌟", layout="wide")

# Initialize session state for conversation history and website content
if "messages" not in st.session_state:
    st.session_state.messages = []
if "website_content" not in st.session_state:
    st.session_state.website_content = {}

# Fetch website content for specific STARS report sections
def fetch_stars_content(url, max_pages=20):
    try:
        content_dict = {}
        visited = set()
        to_visit = [url]
        
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            
            response = requests.get(current_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Store the content with its URL
            content_dict[current_url] = {
                'title': soup.title.string if soup.title else 'No title',
                'content': soup.get_text()
            }
            
            visited.add(current_url)
            
            # Find child links specific to STARS sections
            for link in soup.find_all('a', href=True):
                child_url = urljoin(url, link['href'])
                if child_url.startswith(url) and child_url not in visited and child_url not in to_visit:
                    to_visit.append(child_url)
        
        return content_dict
    except Exception as e:
        st.error(f"Error fetching website content: {str(e)}")
        return {}

# Generate response tailored for STARS report
def generate_stars_response(user_input, content_dict):
    try:
        conversation = [
            {"role": "user", "parts": ["""You are a helpful assistant specifically designed to guide users through their STARS report submission.
Please follow these guidelines:
1. Use the website content to provide targeted advice for completing report sections.
2. When mentioning specific topics or sections, always refer to the relevant STARS guidelines.
3. If you don't have all details, suggest related web pages or sections for further information.
4. Help the user navigate different parts of the STARS report and provide examples when relevant.
5. Be concise, but informative and focused on assisting with report completion.

Here's the content from the STARS website:"""]},
            {"role": "model", "parts": ["Understood. I'll provide specific, relevant information based on STARS content, including report sections, guidelines, and links to relevant pages. I'll focus on helping users complete their report accurately."]},
        ]
        
        # Add content from each STARS report page
        for url, page_data in content_dict.items():
            conversation.append({"role": "user", "parts": [f"Content from {url}:\nTitle: {page_data['title']}\n\n{page_data['content'][:2000]}..."]})
        
        conversation.append({"role": "user", "parts": [user_input]})
        
        # Generate a response using the Gemini model
        response = genai.generate_content(conversation)
        
        if response.text:
            return response.text
        else:
            return "I couldn't find specific details to answer your question. Please check the STARS website for more information."
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return "An error occurred while processing your request. Please try again."

# Ensure authentication before allowing interaction
if st.session_state.get('is_authenticated', False):

    # Streamlit interface
    st.title("STARS Report Chatbot")

    # Information about the chatbot
    st.markdown("""
    ### STARS Report Assistance Chatbot
    - This chatbot guides users in completing their STARS report.
    - It helps navigate report sections and summarizes relevant content from the STARS website.
    - It provides URLs and page references to specific STARS guidelines when possible.
    - The chatbot offers advice for filling out report sections, following AASHE guidelines.
    """)

    # Gemini API Key input
    gemini_api_key = st.text_input("Enter your Gemini API Key:", type="password")

    if gemini_api_key:
        # Initialize the Gemini client
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-pro')

        # Website URL input (STARS report website)
        website_url = st.text_input("Enter the STARS website URL (e.g., https://stars.aashe.org):")

        if website_url:
            if website_url != st.session_state.get('last_url', ''):
                with st.spinner("Loading STARS content..."):
                    st.session_state.website_content = fetch_stars_content(website_url)
                st.session_state.last_url = website_url
                st.session_state.messages = []  # Clear previous conversation
            
            st.success("STARS content loaded. You can now ask questions about the report!")

            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message("user" if st.session_state.messages.index(message) % 2 == 0 else "assistant"):
                    st.write(message)

            # User input
            user_input = st.chat_input("Your question about the STARS report:")

            # Generate response and display
            if user_input:
                st.session_state.messages.append(user_input)
                with st.chat_message("user"):
                    st.write(user_input)

                with st.chat_message("assistant"):
                    response = generate_stars_response(user_input, st.session_state.website_content)
                    st.write(response)

                st.session_state.messages.append(response)
        else:
            st.warning("Please enter the STARS website URL to start chatting.")
    else:
        st.warning("Please enter your Gemini API Key to use the chatbot.")
else:
    st.warning("Please log in to access the chatbot.")
