import time
import threading
from flask import Flask, request, jsonify
from inference_sdk import InferenceHTTPClient
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import requests

app = Flask(__name__)

SAVE_DIR = "received_images"
os.makedirs(SAVE_DIR, exist_ok=True)  # Ensure the directory exists

# Load environment variables from .env file
load_dotenv()
INFERENCE_API_KEY = os.getenv("INFERENCE_API_KEY")
if not INFERENCE_API_KEY:
    raise ValueError("INFERENCE_API_KEY is not set in the environment variables.")

# InferenceHTTPClient configuration
client_inference = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",  # Use your inference server URL
    api_key=INFERENCE_API_KEY
)

# Initialize the OpenAI client with your API key
client = OpenAI(
    base_url="https://api.endpoints.anyscale.com/v1",  # Replace with your OpenAI base URL
    api_key=os.getenv('OPENAI_API_KEY')
)

# File paths
PROMPT_FILE = 'prompt_file.json'
BACKUP_FILE = 'backup_file.json'

# Function to load backup data
def load_backup_data():
    with open(BACKUP_FILE, 'r') as file:
        return json.load(file)

# Dictionary to store pending requests
pending_requests = {}
pending_responses = {}
pending_events = {}

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    data = request.json
    question = data.get('question')
    player_name = data.get('playerName', 'Unknown')

    if not question:
        return jsonify({'error': 'Question is required.'}), 400

    # Generate a unique request ID
    request_id = f"{player_name}_{int(time.time())}"
    
    # Create an Event to wait for the response
    event = threading.Event()
    pending_events[request_id] = event
    
    # Store the request details
    pending_requests[request_id] = {
        'question': question,
        'player_name': player_name
    }

    # Trigger the external execute
    execute_server_url = 'https://38017396-7be9c047-0074-423e-a4b5-0fc291cd4442.socketxp.com/execute'
    try:
        execute_response = requests.post(execute_server_url, json={'request_id': request_id})
        if execute_response.status_code != 200:
            return jsonify({'error': 'Failed to execute capture on the different server.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Wait for the response from /test
    event.wait(timeout=10)  # Wait up to 5 minutes

    # Retrieve the response
    response = pending_responses.pop(request_id, None)
    pending_events.pop(request_id, None)

    if response:
        return jsonify({'response': response})
    else:
        return jsonify({'error': 'Timed out waiting for response.'}), 504

@app.route('/test', methods=['POST'])
def test():
    data = request.json
    request_id = data.get('request_id')
    response_data = data.get('response')

    if not request_id or not response_data:
        return jsonify({'error': 'request_id and response are required.'}), 400

    # Store the response
    pending_responses[request_id] = response_data

    # Set the event to unblock /ask_gpt
    event = pending_events.get(request_id)
    if event:
        event.set()

    return jsonify({'status': 'Response received.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
