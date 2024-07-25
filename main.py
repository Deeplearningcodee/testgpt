from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

# Replace 'your-api-key' with your OpenAI API key
openai.api_key = 'sk-proj-rYLLqp3EKXujVjU30TW9T3BlbkFJrbZ5GcwxidDebnIkCc00'

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
