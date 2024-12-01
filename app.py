# serverside.txt

import time
import threading
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import requests
import re  # Import regex module
import base64
from groq import Groq

app = Flask(__name__)

SAVE_DIR = "received_images"
os.makedirs(SAVE_DIR, exist_ok=True)

load_dotenv()

PROMPT_FILE = 'prompt_file.json'
BACKUP_FILE = 'backup_file.json'

def load_backup_data():
    with open(BACKUP_FILE, 'r') as file:
        return json.load(file)

def decode_image(base64_image):
    return base64.b64decode(base64_image)

def call_groq_api(prompt_data):
    api_key = "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"
    client = Groq(api_key=api_key)
    
    chat_completion = client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=prompt_data,
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    return chat_completion.choices[0].message.to_dict()

pending_requests = {}
pending_responses = {}
pending_events = {}

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    data = request.json
    
    # Handle the case where data is a list
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            data = data[0]
            print("Received data as list. Using the first item.")
        else:
            return jsonify({'error': 'Invalid data format. Expected a dictionary.'}), 400
    
    # Now, data should be a dictionary
    question = data.get('question')
    player_name = data.get('playerName', 'Unknown')

    if not question:
        return jsonify({'error': 'Question is required.'}), 400

    # Check for "clear memory" command
    if question.strip().lower() == "clear memory":
        try:
            backup_data = load_backup_data()
            with open(PROMPT_FILE, 'w') as file:
                json.dump(backup_data, file, indent=4)
            return jsonify({'response': 'Memory has been cleared.'}), 200
        except FileNotFoundError:
            return jsonify({'error': 'Backup file not found.'}), 500
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid backup file format.'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
        execute_response = requests.post(execute_server_url, json={'request_id': request_id}, timeout=10)
        if execute_response.status_code == 200:
            response_data = execute_response.json()
            if isinstance(response_data, list) and len(response_data) > 0:
                encoded_image = response_data[0].get('encodedImage', '')
                
                
                if encoded_image:
                   
                    # Prepare the user's question with the image for the first API call
                    user_question_with_image = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "describe the image max 200 characters"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}",
                                },
                            },
                        ],
                    }
                    
                    # Call the Groq API to describe the image
                    image_description_reply = call_groq_api([user_question_with_image])
                    
                    # Extract the description from the assistant's response
                    image_description = image_description_reply.get("content", "No description available.")
                    visual = image_description
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

    # Call the Groq API with the updated prompt data
    assistant_reply = call_groq_api(prompt_data)
    
    # Append the assistant's response to the prompt data
    prompt_data.append(assistant_reply)
    
    # Save the updated prompt data back to the file
    try:
        with open(PROMPT_FILE, 'w') as file:
            json.dump(prompt_data, file, indent=4)
        print("Response saved to prompt_file.json")
    except Exception as e:
        print(f"Error saving response: {e}")
        return jsonify({'error': 'Failed to save response.'}), 500

    pending_responses[request_id] = assistant_reply.get("content", "")
    event = pending_events.get(request_id)
    if event:
        event.set()

    return jsonify({'response': assistant_reply.get("content", "")})

if __name__ == '__main__':
    app.run(debug=True)
