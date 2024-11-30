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
os.makedirs(SAVE_DIR, exist_ok=True)

load_dotenv()
INFERENCE_API_KEY = os.getenv("INFERENCE_API_KEY")
if not INFERENCE_API_KEY:
    raise ValueError("INFERENCE_API_KEY is not set.")

client_inference = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=INFERENCE_API_KEY
)

client = OpenAI(
    base_url="https://api.endpoints.anyscale.com/v1",
    api_key=os.getenv('OPENAI_API_KEY')
)

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

    with open(PROMPT_FILE, 'r') as file:
        prompt_data = json.load(file)

    prompt_content = f"{player_name}: {question}"
    if visual:
        prompt_content += f"\nVisual context: {visual}"

    prompt_data.append({
        "role": "user",
        "content": prompt_content
    })

    try:
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x22B-Instruct-v0.1",
            messages=prompt_data,
            temperature=1,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        gpt_response = response.choices[0].message.content.strip()

        prompt_data.append({
            "role": "assistant",
            "content": gpt_response
        })

        with open(PROMPT_FILE, 'w') as file:
            json.dump(prompt_data, file, indent=4)

        pending_responses[request_id] = gpt_response
        event = pending_events.get(request_id)
        if event:
            event.set()

        return jsonify({'response': gpt_response})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
