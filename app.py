from flask import Flask, request, jsonify
from inference_sdk import InferenceHTTPClient
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

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
    api_url="https://detect.roboflow.com",  # Use local inference server
    api_key=INFERENCE_API_KEY
)

# Initialize the OpenAI client with your API key
client = OpenAI(
  base_url = "https://api.endpoints.anyscale.com/v1",
  # Replace with long-lived credentials for production
  api_key=os.getenv('OPENAI_API_KEY')
)

# File paths
PROMPT_FILE = 'prompt_file.json'
BACKUP_FILE = 'backup_file.json'

# Function to load backup data
def load_backup_data():
    with open(BACKUP_FILE, 'r') as file:
        return json.load(file)

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

        # Load the existing prompt data
        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        # Add the new question to the messages with player name
        prompt_data.append({
            "role": "user",
            "content": f"{player_name}: {question}"  # Include player name with the question
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

        # Add the GPT-4 response to the messages
        prompt_data.append({
            "role": "assistant",
            "content": gpt_response
        })

        # Save the updated messages back to the prompt file
        with open(PROMPT_FILE, 'w') as file:
            json.dump(prompt_data, file, indent=4)

        return jsonify({'response': gpt_response})

    except Exception as e:
        # Debugging: Print exception details
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test', methods=['POST'])
def test():
    try:
        # Get the raw binary data from the request body
        image_data = request.data

        if not image_data:
            return jsonify({'error': 'No image data received'}), 400

        # Save the image data to a file for debugging/logging purposes
        image_file_path = os.path.join(SAVE_DIR, "screenshot.png")
        with open(image_file_path, 'wb') as file:
            file.write(image_data)

        # Send the binary image data directly to the inference client
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

        # Log or format the parsed response for debugging
        print("Parsed Inference Response:", parsed_response)

        # Send the parsed response back to Roblox
        return jsonify(parsed_response)

    except Exception as e:
        # Handle and log any exceptions
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
