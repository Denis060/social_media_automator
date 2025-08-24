# app.py
import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from a .env file (optional but good practice)
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Main Route to Serve the Frontend ---
@app.route('/')
def index():
    """
    This function renders the main HTML page when a user visits the root URL.
    """
    return render_template('index.html')

# --- API Route to Generate Social Media Post ---
@app.route('/generate', methods=['POST'])
def generate_post():
    """
    This function handles the API request to generate content.
    It receives data from the frontend, calls the Gemini API, and returns the response.
    """
    try:
        # 1. Get data from the incoming JSON request
        data = request.json
        topic = data.get('topic')
        tone = data.get('tone')
        platform = data.get('platform')
        persona = data.get('persona')

        # Basic validation
        if not all([topic, tone, platform, persona]):
            return jsonify({"error": "Missing required fields"}), 400

        # 2. Get your Gemini API Key (TEMPORARY TEST)
        # This is hardcoded for our test. We will switch back to .env later.
        api_key = "AIzaSyBADRbNLQFk9tZ9jw2bfnCJgjBIQc7ZYqI"

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

        # 3. Construct the detailed prompt for the AI model
        prompt = f"""
        You are an expert social media manager. Your task is to generate a social media post based on the provided details.

        - Persona: "{persona}"
        - Topic: "{topic}"
        - Tone: "{tone}"
        - Platform: "{platform}"

        Please provide three things:
        1.  A caption that is engaging and informative. Use Markdown for formatting (e.g., use '**' for bold text, and use bullet points with '-' for lists).
        2.  A descriptive prompt for an AI image generator to create a relevant, visually appealing image for this post. The prompt should be creative and detailed.
        3.  A list of 5-7 relevant and popular hashtags for the specified platform.

        Format your response as a single, minified JSON object with three keys: "caption", "imagePrompt", and "hashtags" (an array of strings).
        """

        # 4. Prepare the payload for the Gemini API
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
            }
        }

        # 5. Make the request to the Gemini API
        response = requests.post(api_url, json=payload)
        response.raise_for_status()  # This will raise an error for bad responses (4xx or 5xx)

        # 6. Send the successful response back to the frontend
        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        # Handle network or API errors
        print(f"API Request Error: {e}")
        return jsonify({"error": f"Failed to connect to the AI service: {e}"}), 500
    except Exception as e:
        # Handle other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

# This allows the script to be run directly
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
