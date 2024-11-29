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
    try:
        execute_response = requests.post(execute_server_url, json={'request_id': request_id})
        if execute_response.status_code != 200:
            return jsonify({'error': 'Failed to execute capture on the different server.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    event.wait(timeout=300)

    response = pending_responses.pop(request_id, None)
    pending_events.pop(request_id, None)

    if response:
        return jsonify({'response': response})
    else:
        return jsonify({'error': 'Timed out waiting for response.'}), 504

@app.route('/test', methods=['POST'])
def test():
    data = request.json
    print("Received data:", data)
    try:
        request_id = data.get('request_id')
        response_data = data.get('response')

        if not request_id or request_id not in pending_requests:
            return jsonify({'error': 'Invalid or missing request ID.'}), 400

        visual_response = response_data.get('visual', '')

        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        request_info = pending_requests.pop(request_id, None)
        if not request_info:
            return jsonify({'error': 'Request information not found.'}), 400

        question = request_info['question']
        player_name = request_info['player_name']

        prompt_data.append({
            "role": "user",
            "content": f"{player_name}: {question}\nVisual context: {visual_response}"
        })

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

        return jsonify({'status': 'Response processed.'}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
