from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import google.generativeai as genai

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini client with your API key
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
            "parts": [f"{player_name}: {question}"]
        })

        # Create the model configuration
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        # Create the model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
            system_instruction="Please respond to the following question in max 350 characters. This includes all text, spaces, and punctuation. Also, please respond to the following question in a structured format. The response should contain 'text' and optionally 'command' fields:\\n{\\n\\\"text\\\":\\\"response\\\",\\n\\\"command\\\":\\\"response\\\"\\n}\\n\\n\n",
        )

        # Start a new chat session with the current prompt history
        chat_session = model.start_chat(
            history=prompt_data
        )

        # Send the message to the Gemini model
        response = chat_session.send_message(question)

        # Debugging: Print the entire response object
        print("Full response object:", response)

        # Extract the response text
        gpt_response = response.text.strip()

        # Add the Gemini response to the messages
        prompt_data.append({
            "role": "model",
            "parts": [gpt_response]
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
