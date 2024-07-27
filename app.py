from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

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
        player_name = data.get('playerName', 'Unknown')

        # Debugging: Print received question and player name
        print(f"Received question: {question}")
        print(f"Player name: {player_name}")

        if question.lower() == "clear memory":
            backup_data = load_backup_data()
            with open(PROMPT_FILE, 'w') as file:
                json.dump(backup_data, file, indent=4)
            return jsonify({'response': "Memory cleared and reset to initial state."})

        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        prompt_data.append({
            "role": "user",
            "content": f"{player_name}: {question}"
        })

        # Generate response using Gemini
        response = genai.chat(prompt_data)
        
        print("Full response object:", response)

        if response and response['messages']:
            gpt_response_message = response['messages'][0]['text'].strip()

            # Debugging: Print the extracted response message
            print("Extracted GPT response message:", gpt_response_message)

            # Assuming the response message contains a JSON string with 'text' and 'command'
            gpt_response = json.loads(gpt_response_message)

            prompt_data.append({
                "role": "assistant",
                "content": gpt_response_message
            })

            with open(PROMPT_FILE, 'w') as file:
                json.dump(prompt_data, file, indent=4)

            return jsonify({'response': json.dumps({'text': gpt_response.get('text'), 'command': gpt_response.get('command')})})
        else:
            return jsonify({'error': 'No response from GPT'}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
