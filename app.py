from google import genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
# Note: The new SDK uses google.api_core.exceptions for errors,
# but we will rely on the general Exception block as requested.

# --- Configuration and Initialization ---

# Azure App Service will securely provide the API key via Application Settings
# The new genai.Client() automatically reads "GOOGLE_API_KEY"
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Hardcoded model name as requested
MODEL_TO_USE = 'gemini-2.5-flash' 

if not API_KEY:
    # In a cloud environment, print a fatal message
    print("FATAL: GOOGLE_API_KEY environment variable not found. The application cannot start.")

try:
    # Initialize the new client. 
    # It automatically uses the GOOGLE_API_KEY environment variable.
    if API_KEY:
        client = genai.Client()
    else:
        client = None 
except Exception as e:
    # Handle configuration failure
    print(f"ERROR: Failed to configure Google Generative AI Client: {e}")
    client = None

# Initialize Flask app
# The name must be 'app' for Azure/Gunicorn to easily find it.
app = Flask(__name__)

# Configure CORS (use specific origins in production)
CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})

# --- Core LLM Logic ---

def execute_food_analyzer(query: str):
    """
    Skill: Food and Nutrition Analyzer
    Generates a report on a food item using AI and Google Search.
    """
    if not client:
        raise Exception("AI client failed to initialize due to missing or invalid API key.")

    # System instruction defines the AI's persona and task
    system_prompt = f"""
You are a food and nutrition analysis expert.

Generate a visually engaging report using this structure:
🥗 Summary — brief verdict
🧾 Ingredient Cleanliness — bulleted notes + full-width table
💪 Nutritional Value — bullets + table (compare to eggs, tofu, chicken using Google Search)
🍽 Diet Suitability — bullets + table
🍲 Usage Suggestions — 5 simple vegetarian dishes + table

Maintain clarity, emojis, and clean formatting as in Amul Butter style.
Use Google Search to find all necessary nutritional and ingredient data.
"""
    
    # Use Google Search grounding to find nutritional data
    # Updated syntax for the new genai.Client
    response = client.generate_content(
        model=MODEL_TO_USE,
        contents=query,  # The user's food item (e.g., "Amul Butter")
        system_instruction=system_prompt,
        tools=[{"google_search": {}}]
    )

    if not response.parts:
        print(f"Response blocked by API. Feedback by NSAI: {response.prompt_feedback}")
        rasie Exception(f"THe response was blocked: Feedback: {response.prompt_feedback}")
    return response.text

# --- Health Check Route ---

@app.route('/check', methods=['GET'])
def check():
    """
    Simple health check route to confirm the backend server is running.
    """
    status_code = 200
    if not client:
        # Return 503 if the core dependency (AI client) failed to initialize
        status_code = 503
        message = "backend is running, but AI client failed to initialize."
    else:
        message = "backend is running"

    return jsonify({
        'status': 'ok' if status_code == 200 else 'error', 
        'message': message, 
        'model': MODEL_TO_USE
    }), status_code

# --- Main API Route ---

@app.route('/api/execute', methods=['POST'])
def execute():
    # 1. Input Validation
    if not client:
        return jsonify({'error': 'AI service not initialized. Check API key configuration.'}), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON payload.'}), 400

    query = data.get('query')
    # Validate that query is a non-empty string
    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({'error': 'Missing or empty "query" field in the request.'}), 400
    
    # 2. Execution and Specific Error Handling
    try:
        result = execute_food_analyzer(query)
        
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        # Catch all other unexpected errors
        print(f"Internal Server Error: {e}")
        return jsonify({'error': 'An unexpected internal server error occurred: {str(e)}'}), 500

