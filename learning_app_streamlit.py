import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from typing import List, Tuple
import re
import base64
import json
import boto3
from botocore.exceptions import NoCredentialsError
import uuid
from config import *  # Import all variables from config.py
from config import get_system_message_tutor  # Add this import
import os

# Fetch secrets from Streamlit and set them as environment variables
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]
os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]

# Set up S3 client
s3_client = boto3.client('s3')
s3_base_url = ""

# Function to generate embeddings using OpenAI
def generate_embedding(text: str, api_key: str) -> List[float]:
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

# Function to extract YouTube video title from URL
def get_youtube_title(url: str) -> str:
    # This is a simple regex to extract the video ID
    video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if video_id:
        return f"YouTube Video (ID: {video_id.group(1)})"
    return "YouTube Video"

# Function to generate AI response with streaming and memory
def generate_ai_response(prompt: str, context: str, api_key: str, chat_history: List[dict], image_url=None, is_query_generation: bool = False):
    client = OpenAI(api_key=api_key)
    try:
        if is_query_generation:
            system_message = SYSTEM_MESSAGE_QUERY_GENERATION
        else:
            system_message = get_system_message_tutor(st.session_state.current_objective).format(context=context)

        messages = [{"role": "system", "content": system_message}]
        
        # Add chat history to messages
        for msg in chat_history[-5:]:  # Include last 5 messages for context
            messages.append(msg)
        
        # Create a dictionary of parameters
        params = {
            "model": MODEL_CHAT,
            "messages": messages,
            "max_tokens": 100 if is_query_generation else 1600,
            "n": 1,
            "temperature": 0.7,
            "stream": not is_query_generation,
        }
        
        response = client.chat.completions.create(**params)
        
        return response
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Function to query Pinecone and get relevant context
def get_context(user_message: str, chat_history: List[dict], openai_api_key: str, pinecone_api_key: str, image_url=None) -> Tuple[str, List[dict]]:
    # Generate contextual query
    contextual_query_response = generate_ai_response(user_message, "", openai_api_key, chat_history, image_url, is_query_generation=True)
    
    if isinstance(contextual_query_response, str):  # Error occurred
        print(f"Error in generating contextual query: {contextual_query_response}")
        return "", []
    
    contextual_query = contextual_query_response.choices[0].message.content
    print(f"Responding to user message: {user_message} and chat_history: \n{chat_history}")
    print(f"Contextual Query Response: {contextual_query}")


    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(PINECONE_INDEX_NAME)
    
    query_embedding = generate_embedding(contextual_query, openai_api_key)
    results = index.query(vector=query_embedding, top_k=5, namespace=PINECONE_NAMESPACE, include_metadata=True)
    
    context = ""
    references = []
    for match in results['matches']:
        context += match['metadata']['text'] + "\n\n"
        reference = {
            'text': match['metadata']['text'],
            'score': match['score']
        }
        if 'source' in match['metadata']:
            reference['source'] = match['metadata']['source']
        references.append(reference)
    
    return context, references

# Function to upload the image to S3
def upload_to_s3(file, file_name, bucket_name):
    global s3_base_url
    try:
        s3_client.upload_fileobj(file, bucket_name, f"learning_app/{file_name}")
        return f"{s3_base_url}/learning_app/{file_name}"
    except NoCredentialsError:
        st.error("AWS credentials not available. Please configure your AWS credentials.")
        return None
    except Exception as e:
        st.error(f"An error occurred while uploading the file to S3: {str(e)}")
        return None


# Add this function to send a hidden message
def send_hidden_message(openai_api_key, pinecone_api_key, previous_objective, current_objective):
    hidden_message = f"You just helped me complete '{previous_objective}'. What am I looking forward to, in this one?"
    
    # Add the hidden message to chat history without displaying it
    st.session_state.messages.append({"role": "user", "content": hidden_message, "hidden": True})
    
    # Get context and generate AI response
    context, references = get_context(hidden_message, st.session_state.messages, openai_api_key, pinecone_api_key)
    response = generate_ai_response(hidden_message, context, openai_api_key, st.session_state.messages)
    
    full_response = ""
    if isinstance(response, str):  # Error occurred
        full_response = response
    elif hasattr(response, 'choices'):  # Non-streamed response
        full_response = response.choices[0].message.content
    else:  # Streamed response
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                yield full_response
    
    # Add AI response to chat history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response, 
        "references": references,
    })
    
    yield full_response


# Streamlit app layout
st.set_page_config(page_title=PAGE_TITLE, layout=PAGE_LAYOUT)

# Custom CSS for learning steps
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Add this CSS to the existing CUSTOM_CSS in config.py
st.markdown("""
<style>
.stButton > button {
    width: 100%;
}
.next-objective {
    background-color: #4CAF50;
    color: white;
    padding: 15px 32px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    margin: 4px 2px;
    cursor: pointer;
    border: none;
    border-radius: 4px;
    transition-duration: 0.4s;
}
.next-objective:hover {
    background-color: #45a049;
}
</style>
""", unsafe_allow_html=True)

st.title(PAGE_TITLE)

# Sidebar for API keys input and learning objectives
with st.sidebar:
    objectives = LEARNING_OBJECTIVES
    # Initialize session state for current objective if not exists
    if 'current_objective' not in st.session_state:
        st.session_state.current_objective = 0
    # Settings in a dropdown
    with st.expander("Settings"):
        openai_api_key = st.text_input("Enter your OpenAI API key", type="password", value=st.secrets.get("OPENAI_API_KEY", ""))
        pinecone_api_key = st.text_input("Enter your Pinecone API key", type="password", value=st.secrets.get("PINECONE_API_KEY", ""))
        s3_base_url = st.text_input("Enter your S3 URL", value=st.secrets.get("S3_BASE_URL", ""))
        
        # Add numeric input for toggling objectives
        objective_toggle = st.number_input("Toggle Objective", min_value=0, max_value=len(objectives)-1, value=st.session_state.current_objective)
        if objective_toggle != st.session_state.current_objective:
            st.session_state.current_objective = objective_toggle
            st.session_state.messages = []  # Clear chat history
        
        # Move Reset Progress button here
        if st.button("Reset Chat"):
            # st.session_state.clear()
            st.session_state.messages = []  # Clear chat history
            st.rerun()

    # Learning objectives

    # Display learning steps in sidebar
    st.markdown("""
    <div class="steps-container">
        <h3>
            <span class="target-emoji">🎯</span>
            Learning Steps
        </h3>
        <div class="steps">
            <div class="progress-line"></div>
    """, unsafe_allow_html=True)

    for i, objective in enumerate(objectives):
        if i < st.session_state.current_objective:
            class_name = "completed"
            text_class = "completed-text"
        elif i == st.session_state.current_objective:
            class_name = "active"
            text_class = "active-text"
        else:
            class_name = ""
            text_class = "inactive-text"
        
        st.markdown(f"""
        <div class="step {class_name}">
            <div class="circle"></div>
            <span class="step-text {text_class}">{objective}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Add image uploader at the bottom of the sidebar
    st.markdown("---")
    st.subheader("Attach Image")
    
    # Use a unique key for the file uploader each time an image is used
    if 'image_upload_key' not in st.session_state:
        st.session_state.image_upload_key = 0
    
    uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"], key=f"image_uploader_{st.session_state.image_upload_key}")

# Main chat interface
st.subheader(objectives[st.session_state.current_objective])

# Initialize session state for messages if not exists
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    if message.get("hidden", False):
        continue  # Skip hidden messages
    with st.chat_message(message["role"]):
        if isinstance(message["content"], list) and "text" in message["content"][0] and "image_url" in message["content"][1]:
            st.markdown(message["content"][0]["text"])
            st.image(message["content"][1]["image_url"]["url"], caption="Attached Image", use_column_width=True)
        else:
            st.markdown(message["content"])
        
        if message["role"] == "assistant" and "references" in message:
            with st.expander("Show References"):
                for i, ref in enumerate(message["references"], 1):
                    st.markdown(f"**Reference {i}** (Relevance Score: {ref['score']:.2f})")
                    st.markdown(ref['text'])
                    if 'source' in ref and 'youtube.com' in ref['source']:
                        video_title = get_youtube_title(ref['source'])
                        st.markdown(f"[{video_title}]({ref['source']})")
                    st.markdown("---")

# User input
user_input = st.chat_input("Type your message here...")

if user_input and openai_api_key and pinecone_api_key:
    # Add user message to chat history
    if uploaded_image:
        # Generate a unique filename for the uploaded image
        file_extension = uploaded_image.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Upload the image to S3
        image_url = upload_to_s3(uploaded_image, unique_filename, S3_BUCKET)
        print("Image uploaded to s3")
        print(f"image_url: {image_url}")
        
        if image_url:
            user_message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_input},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
            # Increment the image upload key to force a new file uploader on next rerun
            st.session_state.image_upload_key += 1
            # Set a flag to indicate that we need to clear the uploader
            st.session_state.clear_uploader = True
        else:
            st.error("Failed to upload image. Please try again.")
            user_message = {"role": "user", "content": user_input}
    else:
        user_message = {"role": "user", "content": user_input}
    
    st.session_state.messages.append(user_message)

    # Display the new user message
    with st.chat_message("user"):
        if isinstance(user_message["content"], list) and "text" in user_message["content"][0] and "image_url" in user_message["content"][1]:
            st.markdown(user_message["content"][0]["text"])
            st.image(user_message["content"][1]["image_url"]["url"], caption="Attached Image", use_column_width=True)
        else:
            st.markdown(user_message["content"])

    # Create a placeholder for the AI response
    with st.chat_message("assistant"):
        with st.spinner("Retrieving context..."):
            # Get context from Pinecone using the updated get_context function
            context, references = get_context(user_input, st.session_state.messages, openai_api_key, pinecone_api_key, image_url if uploaded_image else None)

        message_placeholder = st.empty()
        thinking_placeholder = st.empty()
        
        with thinking_placeholder:
            with st.spinner("Thinking..."):
                full_response = ""
                response = generate_ai_response(user_input, context, openai_api_key, st.session_state.messages, image_url if uploaded_image else None)
                
                print(f"History for final response: {st.session_state.messages}")

                if isinstance(response, str):  # Error occurred
                    full_response = response
                    message_placeholder.markdown(full_response)
                elif hasattr(response, 'choices'):  # Non-streamed response
                    full_response = response.choices[0].message.content
                    message_placeholder.markdown(full_response)
                else:  # Streamed response
                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            if not full_response:  # First chunk
                                thinking_placeholder.empty()  # Remove the "Thinking..." spinner
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)

        # Add an expander to show references
        with st.expander("Show References"):
            for i, ref in enumerate(references, 1):
                st.markdown(f"**Reference {i}** (Relevance Score: {ref['score']:.2f})")
                st.markdown(ref['text'])
                if 'source' in ref and 'youtube.com' in ref['source']:
                    video_title = get_youtube_title(ref['source'])
                    st.markdown(f"[{video_title}]({ref['source']})")
                st.markdown("---")

    # Add AI response to chat history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response, 
        "references": references,
    })

    # Check if the current objective is completed
    if "OBJECTIVE_COMPLETED" in full_response:
        st.balloons()  # Add confetti effect
        st.success(f"Congratulations! You've completed the objective: {objectives[st.session_state.current_objective]}")
        
        if st.session_state.current_objective < len(objectives) - 1:
            st.session_state.objective_completed = True
        else:
            st.success("Congratulations! You've completed all objectives!")

# Add a button to reset progress
if 'objective_completed' in st.session_state and st.session_state.objective_completed:
    if st.button("Next Objective 🚀 Let's Go!", key="next_objective", type="primary"):
        previous_objective = objectives[st.session_state.current_objective]
        st.session_state.current_objective += 1
        current_objective = objectives[st.session_state.current_objective]
        st.session_state.messages = []
        st.session_state.objective_completed = False
        
        # Clear the screen
        st.empty()
        
        # Show placeholder with "Prepping for the next objective..."
        with st.chat_message("assistant"):
            prep_placeholder = st.empty()
            prep_placeholder.markdown("Prepping for the next objective...")
        
            # Send hidden message and get response
            for partial_response in send_hidden_message(openai_api_key, pinecone_api_key, previous_objective, current_objective):
                prep_placeholder.markdown(partial_response + "▌")
            
            # Final update without the cursor
            prep_placeholder.markdown(partial_response)
        
        st.rerun()
# else:
#     if st.button("Reset Progress"):
#         st.session_state.clear()
#         st.rerun()

# At the end of the script, add this block to clear the uploader if needed
if 'clear_uploader' in st.session_state and st.session_state.clear_uploader:
    st.session_state.clear_uploader = False
    st.rerun()
