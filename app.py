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

# Function to initialize files if they don't exist
def initialize_files():
    # Initialize prompt file if it doesn't exist
    if not os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, 'w') as file:
            json.dump([], file)
    
    # Initialize backup file with fine-tuning information if it doesn't exist
    if not os.path.exists(BACKUP_FILE):
        backup_data = [
            {
              "role": "system",
              "content": "Please respond to the following question in max 200 characters. This includes all text, spaces, and punctuation also Please respond to the following question in a structured format. The response should contain 'text' and optionally 'command' fields:\n{\n\"text\":\"response\",\n\"command\":\"response\"\n}\n\n"
            },
            {
              "role": "user",
              "content": "move forward"
            },
            {
              "role": "assistant",
              "content": "{\n\"text\": \"Moving forward.\",\n\"command\": \"move_forward\"\n}"
            },
            {
              "role": "user",
              "content": "move backward"
            },
            {
              "role": "assistant",
              "content": "{\n\"text\": \"Moving backward.\",\n\"command\": \"move_backward\"\n}"
            }
        ]
        with open(BACKUP_FILE, 'w') as file:
            json.dump(backup_data, file)

# Initialize files at startup
initialize_files()

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        data = request.json
        question = data['question']
        
        # Debugging: Print received question
        print(f"Received question: {question}")

        # Load the existing prompt data
        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        # Add the new question to the messages
        prompt_data.append({
            "role": "user",
            "content": question
        })

        # Use the OpenAI client to get a chat completion
        response = client.chat.completions.create(
            model="gpt-4",
            messages=prompt_data,
            temperature=1,
            max_tokens=40,
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
