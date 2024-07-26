from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
            model="gpt-4",
            messages=prompt_data,
            temperature=1,
            max_tokens=60,
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

if __name__ == '__main__':
    app.run(debug=True)
