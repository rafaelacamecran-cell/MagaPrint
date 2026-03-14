import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, send_gchat_alert

def test_config():
    print("\n--- Testing GChat Configuration in App Context ---")
    
    # Check if webhook is loaded
    webhook = os.environ.get('GCHAT_SOLICITATION_WEBHOOK')
    print(f"GCHAT_SOLICITATION_WEBHOOK from os.environ: {webhook}")
    
    if not webhook:
        print("Webhook NOT found in environment. Checking .env file manually...")
        # Check parent dir (where .env usually is)
        parent_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        print(f"Checking {parent_env_path}: {os.path.exists(parent_env_path)}")
        
        if os.path.exists(parent_env_path):
            load_dotenv(parent_env_path)
            webhook = os.environ.get('GCHAT_SOLICITATION_WEBHOOK')
            print(f"After manual load_dotenv: {webhook}")
    
    if webhook:
        print("Webhook found! Attempting to send a test alert...")
        msg = "🧪 *Teste de Depuração (MagaPrint)*\nSe você recebeu isso, a configuração do `app.py` está carregando o Webhook corretamente."
        try:
            # We need app context if send_gchat_alert uses app.logger
            with app.app_context():
                send_gchat_alert(msg)
            print("Alert attempt finished. Check GChat.")
        except Exception as e:
            print(f"Error during alert attempt: {e}")
    else:
        print("CRITICAL: Webhook URL could not be loaded!")

if __name__ == "__main__":
    test_config()
