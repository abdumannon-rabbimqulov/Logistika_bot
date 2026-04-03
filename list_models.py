from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')

def list_mods():
    client = genai.Client(api_key=API_KEY)
    try:
        print("Mavjud modellar ro'yxati:")
        for model in client.models.list():
            print(f"- {model.name} (Supported: {model.supported_actions})")
    except Exception as e:
        print(f"Xatolik: {e}")

if __name__ == "__main__":
    list_mods()
