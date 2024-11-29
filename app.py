import time
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

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        data = request.json
        question = data['question']
        player_name = data.get('playerName', 'Unknown')  # Get playerName from request

        # Debugging: Print received question and player name
        print(f"Received question: {question}")
        print(f"Player name: {player_name}")

        if question.lower() == "clear memory":
            # Reset prompt file to backup contents
            backup_data = load_backup_data()
            with open(PROMPT_FILE, 'w') as file:
                json.dump(backup_data, file, indent=4)
            return jsonify({'response': "Memory cleared and reset to initial state."})

        # Generate a unique request ID
        request_id = f"{player_name}_{int(time.time())}"

        # Store the question and player name in pending_requests
        pending_requests[request_id] = {
            'question': question,
            'player_name': player_name
        }

        # Trigger capture.py on the different PC
        capture_server_url = 'http://100.121.251.80:5000/trigger_capture'  # Replace with the actual IP and port
        trigger_response = requests.post(capture_server_url, json={'request_id': request_id})

        if trigger_response.status_code != 200:
            return jsonify({'error': 'Failed to trigger capture on the different PC.'}), 500

        # Inform the user that processing is underway
        return jsonify({'response': "Processing your request. Please wait for the response."})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test', methods=['POST'])
def test():
    try:
        # Extract request_id from query parameters
        request_id = request.args.get('request_id')

        if not request_id or request_id not in pending_requests:
            return jsonify({'error': 'Invalid or missing request ID.'}), 400

        # Get the raw binary data from the request body
        image_data = request.data

        if not image_data:
            return jsonify({'error': 'No image data received'}), 400

        # Save the image data to a file for debugging/logging purposes
        image_file_path = os.path.join(SAVE_DIR, f"{request_id}_screenshot.png")
        with open(image_file_path, 'wb') as file:
            file.write(image_data)

        # Send the binary image data to the inference client
        result = client_inference.run_workflow(
            workspace_name="object-detection-f8udo",
            workflow_id="custom-workflow",
            images={"image": image_data}  # Pass binary data directly
        )

        # Parse the response
        parsed_response = []
        for workflow, result_data in result.items():
            try:
                detections = json.loads(result_data)  # Parse the JSON string
                parsed_response.append({
                    "workflow": workflow,
                    "detections": detections.get("detections", []),
                    "answer": detections.get("question/answer", "")
                })
            except json.JSONDecodeError:
                parsed_response.append({
                    "workflow": workflow,
                    "error": "Failed to parse response data."
                })

        # Log the parsed response
        print("Parsed Inference Response:", parsed_response)

        # Now, send the inference result to OpenAI client

        # Load the existing prompt data
        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        # Retrieve the pending request data
        request_info = pending_requests.pop(request_id, None)
        if not request_info:
            return jsonify({'error': 'Request information not found.'}), 400

        question = request_info['question']
        player_name = request_info['player_name']

        # Add the new question to the messages with player name and inference result
        inference_context = json.dumps(parsed_response)
        prompt_data.append({
            "role": "user",
            "content": f"{player_name}: {question}\nVisual context: {inference_context}"
        })

        # Use the OpenAI client to get a chat completion
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x22B-Instruct-v0.1",
            messages=prompt_data,
            temperature=1,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Debugging: Print the entire response object
        print("Full response object:", response)

        # Extract the response text
        gpt_response = response.choices[0].message.content.strip()

        # Add the assistant's response to the messages
        prompt_data.append({
            "role": "assistant",
            "content": gpt_response
        })

        # Save the updated messages back to the prompt file
        with open(PROMPT_FILE, 'w') as file:
            json.dump(prompt_data, file, indent=4)

        # Return the GPT response
        return jsonify({'response': gpt_response})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
