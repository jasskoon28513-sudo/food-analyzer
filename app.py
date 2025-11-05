from google import genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
# Note: The new SDK uses google.api_core.exceptions for errors,
# but we will rely on the general Exception block as requested.

# --- Configuration and Initialization ---

# Azure App Service will securely provide the API key via Application Settings
API_KEY = os.environ.get("GOOGLE_API_KEY")

# -----------------------------------------------------------------
# ### FIX: USE CORRECT MODEL NAME ###
# The model name 'gemini-2.5-flash' was incorrect.
# Corrected to 'gemini-2.5-flash'.
# -----------------------------------------------------------------
MODEL_TO_USE = 'gemini-2.5-flash'

if not API_KEY:
    # In a cloud environment, print a fatal message
    print("FATAL: GOOGLE_API_KEY environment variable not found. The application cannot start.")
else:
    # This debug line might not appear in logs if the app crashes before
    # the print buffer is flushed, which is normal.
    print("DEBUG: GOOGLE_API_KEY was found and loaded from environment variables.")

# --- Use NEW SDK Syntax (google-generativeai >= 1.0.0) ---
try:
    # Initialize using genai.configure and genai.GenerativeModel
    if API_KEY:
        # --- FIX: This code is for the NEW SDK ---
        # The 'configure' and 'GenerativeModel' methods are from the new SDK.
        # The error was caused by an OLD version of the library being installed.
        # The 'requirements.txt' file MUST specify 'google-generativeai>=1.0.0'.
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_TO_USE)
    else:
        model = None
except Exception as e:
    # Handle configuration failure
    print(f"ERROR: Failed to configure Google Generative AI Client: {e}")
    model = None

# Initialize Flask app
# The name must be 'app' for Azure/Gunicorn to easily find it.
app = Flask(__name__)

# Configure CORS (use specific origins in production)
# Set CORS to '*' (Allow All) for development.
CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})

# --- Core LLM Logic ---

def execute_food_analyzer(query: str):
    """
    Skill: Food and Nutrition Analyzer
    Generates a report on a food item using AI and Google Search.
    """
    if not model:
        raise Exception("AI model failed to initialize due to missing or invalid API key.")

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

    # --- Use NEW SDK Syntax for generate_content ---
    # This call uses 'system_instruction' and 'tools',
    # which are features of the new SDK.
    response = model.generate_content(
        contents=query,  # The user's food item (e.g., "Amul Butter")
        system_instruction=system_prompt,
        tools=[{"google_search": {}}]
    )

    # --- Response Check ---
    if not response.parts:
        # This handles cases where the response was blocked
        print(f"Response was blocked by API. Feedback: {response.prompt_feedback}")
        raise Exception(f"The response was blocked by the API. Feedback: {response.prompt_feedback}")

    return response.text

# --- Health Check Route ---

@app.route('/check', methods=['GET'])
def check():
    """
    Simple health check route to confirm the backend server is running.
    """
    status_code = 200
    if not model:
        # Return 503 if the core dependency (AI client) failed to initialize
        status_code = 503
        message = "backend is running, but AI model failed to initialize."
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
    if not model:
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
        
        # This will now return the actual error message to Bruno,
        # which is much better for debugging.
        return jsonify({'error': f'An unexpected internal server error occurred: {str(e)}'}), 500
