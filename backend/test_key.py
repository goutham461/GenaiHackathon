import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key_single = os.getenv('GEMINI_API_KEY')
api_pool_raw = os.getenv('GEMINI_API_POOL', '')
api_pool = [k.strip() for k in api_pool_raw.split(',') if k.strip() and 'KEY_' not in k]

if api_key_single and api_key_single not in api_pool:
    api_pool.append(api_key_single)

print(f"--- API Pool Test ---")
print(f"Found {len(api_pool)} valid keys in pool.")

for i, key in enumerate(api_pool):
    print(f"\n[Key {i+1}] Testing: {key[:10]}...")
    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents='Hello')
        print(f"  SUCCESS: {response.text.strip()}")
    except Exception as e:
        print(f"  FAILED: {str(e)[:100]}")
