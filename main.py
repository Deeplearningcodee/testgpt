from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    data = request.json
    question = data['question']
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": question}]
    )
    
    gpt_response = response['choices'][0]['message']['content']
    return jsonify({'response': gpt_response})

if __name__ == '__main__':
    app.run(port=5000)
