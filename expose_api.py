import os
import sys
import threading
import time
import uvicorn
from pyngrok import ngrok

def start_server():
    uvicorn.run("wasl_ai.src.api:app", host="0.0.0.0", port=8000, log_level="error")

def expose():
    # Start FastAPI in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Open ngrok tunnel
    # Note: If you have an ngrok auth token, set it with: ngrok.set_auth_token("TOKEN")
    try:
        public_url = ngrok.connect(8000).public_url
        print("\n" + "="*50)
        print(f"   PUBLIC URL: {public_url}")
        print("   Share this URL with your friend for the Flutter App!")
        print("   Endpoint: " + public_url + "/resume/parse")
        print("="*50 + "\n")
        
        # Keep main thread alive
        server_thread.join()
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        print("You might need to sign up at https://ngrok.com and run:")
        print("ngrok config add-authtoken <token>")

if __name__ == "__main__":
    expose()
