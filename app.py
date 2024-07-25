from flask import Flask, request, jsonify
from openai import OpenAI
import os
client = OpenAI()



# Initialize the Flask application
app = Flask(__name__)

# Load the OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        data = request.json
        question = data['question']
        
        # Debugging: Print received question
        print(f"Received question: {question}")

        # Modify the prompt to instruct GPT to respond concisely
        prompt = f"Please respond to the following question in max 200 characters. This includes all text, spaces, and punctuation: {question}"

        # Use the OpenAI client to get a chat completion
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Replace with the model you are using
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_tokens=40,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Debugging: Print the entire response object
        print("Full response object:", response)

        # Extract the response text
        gpt_response = response.choices[0].message['content'].strip()

        return jsonify({'response': gpt_response})

    except Exception as e:
        # Debugging: Print exception details
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
