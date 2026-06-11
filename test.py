import os
from google import genai
from dotenv import load_dotenv

# Load variables from  local .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
# Default to the primary production 2.0 flash model if env is messy
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

print(f"Testing connectivity with model: {model_name}...")

try:
    # Initialize client explicitly
    client = genai.Client(api_key=api_key)
    
    # strip any accidental 'models/' prefix if it got appended
    clean_model_name = model_name.replace("models/", "")
    
    response = client.models.generate_content(
        model=clean_model_name,
        contents="Hello! Confirming connection. Reply with a simple 'System Active'.",
    )
    
    print("\n[SUCCESS] Connection Established!")
    print(f"Gemini Response: {response.text}")
    
except Exception as e:
    print("\n[ERROR] Connection failed.")
    print(f"Details: {e}")