@app.route('/ask_gpt', methods=['POST'])
def ask_gpt():
    try:
        data = request.json
        question = data['question']
        
        # Debugging: Print received question
        print(f"Received question: {question}")

        # Modify the prompt to instruct GPT to respond concisely
        prompt = f"Please respond to the following question in max 200 characters. This includes all text, spaces, and punctuation. : {question}"

        # Use the OpenAI client to get a chat completion
        response = client.chat.completions.create(
            model="gpt-4o",  # Replace with the model you are using
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
        gpt_response = response.choices[0].message.content.strip()

        return jsonify({'response': gpt_response})

    except Exception as e:
        # Debugging: Print exception details
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
