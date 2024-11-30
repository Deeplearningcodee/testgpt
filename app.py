# serverside.txt

import time
import threading
from flask import Flask, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import requests
import re  # Import regex module

app = Flask(__name__)

SAVE_DIR = "received_images"
os.makedirs(SAVE_DIR, exist_ok=True)

load_dotenv()



# Configure Gemini API
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
if not os.environ["GEMINI_API_KEY"]:
    raise ValueError("GEMINI_API_KEY is not set.")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

PROMPT_FILE = 'prompt_file.json'
BACKUP_FILE = 'backup_file.json'

def load_backup_data():
    with open(BACKUP_FILE, 'r') as file:
        return json.load(file)

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

    request_id = f"{player_name}_{int(time.time())}"
    event = threading.Event()
    pending_events[request_id] = event

    pending_requests[request_id] = {
        'question': question,
        'player_name': player_name
    }

    execute_server_url = 'https://38017396-7be9c047-0074-423e-a4b5-0fc291cd4442.socketxp.com/execute'
    visual = ''
    try:
        execute_response = requests.post(execute_server_url, json={'request_id': request_id}, timeout=5)
        if execute_response.status_code == 200:
            response_data = execute_response.json()
            if isinstance(response_data, list) and len(response_data) > 0:
                visual = response_data[0].get('visual', '')
        else:
            print('Execute server responded with status code:', execute_response.status_code)
    except requests.RequestException as e:
        print(f"Execute server request failed: {e}")

    try:
        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)
    except FileNotFoundError:
        prompt_data = []
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid prompt file format.'}), 500

    prompt_content = f"{player_name}: {question}"
    if visual:
        prompt_content += f"\nVisual context: {visual}"

    prompt_data.append({
        "role": "user",
        "content": prompt_content
    })

    # Construct the history as an ordered list of messages
    history = []
    for msg in prompt_data:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if role in ["user", "assistant"] and content:
            history.append({
                "role": role,
                "parts": [content]
            })

    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 150,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    # Initialize chat session with history
    try:
        chat_session = model.start_chat(history=history)
    except Exception as e:
        print(f"Error initializing chat session: {e}")
        return jsonify({'error': 'Failed to initialize chat session.'}), 500

    # Send message to Gemini
    try:
        response = chat_session.send_message(prompt_content)
        gpt_response = response.text.strip()

        # Remove ```json and ``` if present
        gpt_response = re.sub(r'^```json\s*', '', gpt_response, flags=re.MULTILINE)
        gpt_response = re.sub(r'```\s*$', '', gpt_response, flags=re.MULTILINE).strip()

    except Exception as e:
        print(f"Error during Gemini request: {e}")
        return jsonify({'error': 'Failed to get response from Gemini.'}), 500

    # Append Gemini's response to the prompt data
    prompt_data.append({
        "role": "assistant",
        "content": gpt_response
    })

    # Save the updated prompt data back to the file
    try:
        with open(PROMPT_FILE, 'w') as file:
            json.dump(prompt_data, file, indent=4)
        print("Response saved to prompt_file.json")
    except Exception as e:
        print(f"Error saving response: {e}")
        return jsonify({'error': 'Failed to save response.'}), 500

    pending_responses[request_id] = gpt_response
    event = pending_events.get(request_id)
    if event:
        event.set()

    return jsonify({'response': gpt_response})

if __name__ == '__main__':
    app.run(debug=True)
