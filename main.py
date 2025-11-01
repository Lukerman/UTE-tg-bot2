import os
import threading
from dotenv import load_dotenv
from pyngrok import ngrok

# Load environment variables from a .env file if it exists
load_dotenv()

def run_web():
    """Starts the Flask web server."""
    from web import app
    # The web server will run on port 5000, which Ngrok will expose.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def run_bot():
    """Starts the Telegram bot."""
    from bot import run_bot
    run_bot()

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting File Monetization System")
    print("=" * 50)

    # --- Ngrok Integration Start ---
    
    # Get the Ngrok authtoken from environment variables
    ngrok_authtoken = os.getenv("NGROK_AUTHTOKEN")

    if ngrok_authtoken:
        print("✅ Ngrok authtoken found. Initializing Ngrok tunnel...")
        ngrok.set_auth_token(ngrok_authtoken)
        
        try:
            # Open an HTTP tunnel to the local Flask app on port 5000
            public_url = ngrok.connect(5000).public_url
            
            # Dynamically update the BASE_URL environment variable for this session
            # This ensures both the bot and web server use the public Ngrok URL
            os.environ['BASE_URL'] = public_url
            
            print(f"✅ Ngrok tunnel established at: {public_url}")
            print(f"✅ BASE_URL has been dynamically set to the Ngrok URL.")

        except Exception as e:
            print(f"❌ Could not start Ngrok tunnel: {e}")
            print("   Please ensure Ngrok is installed and your authtoken is correct.")
            print("   Falling back to the pre-defined BASE_URL.")

    else:
        print("⚠️  Ngrok authtoken not found in environment variables.")
        print("   Skipping Ngrok setup. The bot will use the BASE_URL from your .env file or secrets.")
        print("   If running locally, the bot may not be accessible from the internet.")

    # --- Ngrok Integration End ---

    # Start the Flask web server in a separate thread
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("✅ Flask Web Server started on port 5000.")
    
    # Start the Telegram bot in the main thread
    print("✅ Starting Telegram Bot...")
    run_bot()
