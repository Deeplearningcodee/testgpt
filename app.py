from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        data = request.json
        question = data['question']
        
        # Debugging: Print received question
        print(f"Received question: {question}")

        # Use the OpenAI client to get a chat completion
        response = client.chat.completions.create(
          model="gpt-4o",
          messages=[
            {
              "role": "system",
              "content": [
                {
                  "type": "text",
                  "text": "Please respond to the following question in max 200 characters. This includes all text, spaces, and punctuation also Please respond to the following question in a structured format. The response should contain 'text' and optionally 'command' fields:\n{\n\"text\":\"response\",\n\"command\":\"response\"\n}\n\n"
                }
              ]
            },
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": "move forward"
                }
              ]
            },
            {
              "role": "assistant",
              "content": [
                {
                  "type": "text",
                  "text": "{\n\"text\": \"Moving forward.\",\n\"command\": \"move_forward\"\n}"
                }
              ]
            },
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": "move backward"
                }
              ]
            },
            {
              "role": "assistant",
              "content": [
                {
                  "type": "text",
                  "text": "{\n\"text\": \"Moving backward.\",\n\"command\": \"move_backward\"\n}"
                }
              ]
            },
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": f"{question}"
                }
              ]
            }
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
        gpt_response = response.choices[0].message.content.strip()

        return jsonify({'response': gpt_response})

    except Exception as e:
        # Debugging: Print exception details
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.json
        image_data = data['image']

        # Decode the base64 image data
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))

        # Save the image or process it as needed
        image.save('screenshot.png')

        return jsonify({'status': 'success', 'message': 'Image received and saved'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
