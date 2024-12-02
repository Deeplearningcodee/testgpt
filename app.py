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

def call_groq_api(prompt_data, model="llama-3.2-11b-vision-preview"):
    api_key = "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"
    client = Groq(api_key=api_key)
    
    chat_completion = client.chat.completions.create(
        model=model,
        messages=prompt_data,
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    return chat_completion.choices[0].message.to_dict()

def determine_model(question, player_name):
    api_key = "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"
    client = Groq(api_key=api_key)
    
    prompt_data = [
        {
            "role": "system",
            "content": "you only answer with 'yes' or 'no'  to determine based on the question if the image model should be used example if question is 'what do you see?' the answer should be 'yes' another example if question is 'how many players you see?' the answer should be 'yes' and if question is 'what is the best strategy?' the answer should be 'no' and if question is 'how can I improve my gameplay?' the answer should be 'no' and if question is 'what game am I playing?' the answer should be 'yes'"
        },
        {
            "role": "user",
            "content": f"{player_name}: {question} "
        }
    ]
    
    chat_completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=prompt_data,
        temperature=1,
        max_tokens=10,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    response = chat_completion.choices[0].message.to_dict()
    print("Response from determine_model:", response)
    return response.get("content", "no").lower() == "yes"

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

    # Determine if the image model should be used
    use_image_model = determine_model(question, player_name)
    print(f"Use image model: {use_image_model}")
    


    if use_image_model:
        execute_server_url = 'https://38017396-7be9c047-0074-423e-a4b5-0fc291cd4442.socketxp.com/execute'
        visual = ''
        try:
            execute_response = requests.post(execute_server_url, json={'request_id': request_id}, timeout=10)
            if execute_response.status_code == 200:
                response_data = execute_response.json()
                encoded_image = response_data.get('encodedImage', '')
                
                if encoded_image:
                    # Prepare the user's question with the image for the first API call
                    user_question_with_image = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{player_name}: {question}. max 200 characters answer based on the image." },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}",
                                },
                            },
                        ],
                    }
                    
                    # Call the Groq API to describe the image
                    image_response = call_groq_api([user_question_with_image])
                    
                    # Extract the description from the assistant's response
                    response_data = image_response.get("content", "No description available.")
                    
                    # Append the user's question and response in prompt data
                    with open(PROMPT_FILE, 'r') as file:
                        prompt_data = json.load(file)

                    prompt_data.append({
                        "role": "user",
                        "content": f"{player_name}: {question}"
                    })
                    prompt_data.append({
                        "role": "assistant",
                        "content": response_data
                    })

                    with open(PROMPT_FILE, 'w') as file:
                        json.dump(prompt_data, file, indent=4)

                    # make json with field text and value would be response data
                    response_data = {"text": response_data}
                    print("response_data:", response_data)


                    pending_responses[request_id] = response_data
                    event.set()
                    return jsonify({'response': response_data})
                
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling execute server: {e}")
            return jsonify({'error': 'Failed to call execute server.'}), 500
        
                    
    else:
        try:
            with open(PROMPT_FILE, 'r') as file:
                prompt_data = json.load(file)
        except FileNotFoundError:
            prompt_data = []
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid prompt file format.'}), 500

        prompt_content = f"{player_name}: {question}"

        prompt_data.append({
            "role": "user",
            "content": prompt_content
        })

        # Call the Groq API with the updated prompt data
        assistant_reply = call_groq_api(prompt_data, model="llama3-8b-8192")
        
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
