# app.py
import os
import requests
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv, find_dotenv
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Use find_dotenv() to locate and load the .env file automatically
load_dotenv(find_dotenv())

# --- Database Configuration ---
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
database_uri = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

# Initialize the Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model Definition ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    persona = db.Column(db.String(255), nullable=False)
    tone = db.Column(db.String(50), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    caption = db.Column(db.Text, nullable=False)
    image_prompt = db.Column(db.Text, nullable=False)
    hashtags = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Post {self.id}: {self.topic}>'

# --- Main Route to Serve the Frontend ---
@app.route('/')
def index():
    """
    This function renders the main HTML page when a user visits the root URL.
    """
    return render_template('index.html')

# --- API Route to Generate and Save Social Media Post ---
@app.route('/generate', methods=['POST'])
def generate_post():
    """
    Handles content generation and saves the result to the database.
    """
    try:
        # 1. Get data from the incoming JSON request
        data = request.json
        topic = data.get('topic')
        tone = data.get('tone')
        platform = data.get('platform')
        persona = data.get('persona')

        if not all([topic, tone, platform, persona]):
            return jsonify({"error": "Missing required fields"}), 400

        # 2. Get API Key and call Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "GEMINI_API_KEY not found."}), 500

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

        prompt = f"""
        You are an expert social media manager. Your task is to generate a social media post based on the provided details.
        - Persona: "{persona}"
        - Topic: "{topic}"
        - Tone: "{tone}"
        - Platform: "{platform}"
        Please provide three things:
        1.  A caption that is engaging and informative. Use Markdown for formatting.
        2.  A descriptive prompt for an AI image generator.
        3.  A list of 5-7 relevant hashtags.
        Format your response as a single, minified JSON object with three keys: "caption", "imagePrompt", and "hashtags" (an array of strings).
        """

        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        
        # Extract the generated content
        gemini_response = response.json()
        content_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
        generated_content = json.loads(content_text)

        # 3. Save the new post to the database
        new_post = Post(
            topic=topic,
            persona=persona,
            tone=tone,
            platform=platform,
            caption=generated_content['caption'],
            image_prompt=generated_content['imagePrompt'],
            hashtags=json.dumps(generated_content['hashtags']) # Store hashtags as a JSON string
        )
        db.session.add(new_post)
        db.session.commit()
        
        # *** NEW DEBUGGING LINE ***
        # This will only print if the commit was successful.
        print(f"✅ Successfully saved post with ID: {new_post.id} to the database.")

        # 4. Send the successful response back to the frontend
        return jsonify(gemini_response)

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return jsonify({"error": f"Failed to connect to the AI service: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        db.session.rollback() # Rollback the transaction on error
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

# --- API Route to Get All Saved Posts ---
@app.route('/posts', methods=['GET'])
def get_posts():
    """
    Retrieves all saved posts from the database.
    """
    try:
        posts = Post.query.order_by(Post.created_at.desc()).all()
        posts_list = [
            {
                "id": post.id,
                "topic": post.topic,
                "caption": post.caption,
                "image_prompt": post.image_prompt,
                "hashtags": json.loads(post.hashtags),
                "created_at": post.created_at.isoformat()
            } for post in posts
        ]
        return jsonify(posts_list)
    except Exception as e:
        print(f"Database query error: {e}")
        return jsonify({"error": "Failed to retrieve posts."}), 500


# This allows the script to be run directly
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # This creates the 'post' table if it doesn't exist
    app.run(debug=True, use_reloader=False)
