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

# Initialize the Gemini model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=(
        "Please respond to the following question in max 350 characters. "
        "This includes all text, spaces, and punctuation. Also, please respond "
        "to the following question in a structured format. The response should "
        "contain 'text' and optionally 'command' fields:\\n{\\n\\\"text\\\":\\\"response\\\",\\n\\\"command\\\":\\\"response\\\"\\n}\\n\\n\n"
    )
)

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

        # Format the question with player name
        formatted_question = f"{player_name}: {question}"

        # Debugging: Print received question and player name
        print(f"Formatted question: {formatted_question}")

        if question.lower() == "clear memory":
            backup_data = load_backup_data()
            with open(PROMPT_FILE, 'w') as file:
                json.dump(backup_data, file, indent=4)
            return jsonify({'response': "Memory cleared and reset to initial state."})

        with open(PROMPT_FILE, 'r') as file:
            prompt_data = json.load(file)

        # Append the new message to the history
        # prompt_data.append({
        #     "role": "user",
        #     "parts": [formatted_question]
        # })

        # Start a chat session
        chat_session = model.start_chat(history=prompt_data)

        # Send the message
        response = chat_session.send_message(formatted_question)

        # Debugging: Print the response
        print("Full response object:", response)

        if response and response['messages']:
            gpt_response_message = response['messages'][-1]['parts'][0].strip()

            # Assuming the response message is a JSON string with 'text' and 'command'
            gpt_response = json.loads(gpt_response_message)

            # Append the response to the history
            # prompt_data.append({
            #     "role": "assistant",
            #     "parts": [gpt_response_message]
            # })

            with open(PROMPT_FILE, 'w') as file:
                json.dump(prompt_data, file, indent=4)

            return jsonify({'response': gpt_response})
        else:
            return jsonify({'error': 'No response from GPT'}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
