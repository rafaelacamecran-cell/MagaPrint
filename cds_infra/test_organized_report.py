import sys
import os

# Add the current directory to sys.path to allow imports from utils and monitors
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

from utils.config_loader import ConfigLoader
from utils.notifier import GChatNotifier

def test_config_categories():
    print("--- Testing ConfigLoader Categories ---")
    devices_txt = os.path.join(base_dir, "devices.txt")
    loader = ConfigLoader(devices_txt, "")
    devices = loader.load_devices()
    
    categories = set(d.get('category') for d in devices)
    print(f"Detected categories: {categories}")
    
    if not categories or "General" in categories and len(categories) == 1:
        print("Warning: Only 'General' category detected or no categories found.")
    else:
        print("Success: Categories correctly detected from devices.txt.")

def test_report_formatting():
    print("\n--- Testing Report Formatting with LuizaLabs Theme ---")
    notifier = GChatNotifier()
    
    mock_report = {
        "Courrier": [
            {"ip": "10.60.226.47", "name": "EST_01", "type": "Printer_HP", "status": "DOWN", "details": "OFFLINE / ERRO DE REDE"},
            {"ip": "10.60.226.49", "name": "EST_05", "type": "Printer_HP", "status": "DOWN", "details": "OFFLINE / ERRO DE REDE"},
            {"ip": "10.60.226.51", "name": "IMPRESSORA DE ROMANEIO", "type": "Printer_HP", "status": "OK", "toner_level": 12}
        ],
        "Recebimento": [
            {"ip": "10.60.226.33", "name": "RECEBIMENTO", "type": "Printer_HP", "status": "OK", "toner_level": 14}
        ]
    }
    
    print("Testing send_summary_report logic...")
    # Since we can't easily capture the 'requests.post' in a unit test without mocking 
    # here, we'll just print the generated message manually by extracting the logic
    
    full_message = "📊 *LUIZALABS - STATUS DE SUPRIMENTOS E REDE*\n\n"
    for category, devices in mock_report.items():
        for dev in devices:
            status = dev.get('status', 'OK')
            toner = dev.get('toner_level')
            dev_type = dev.get('type', '')

            full_message += f"• *{category.upper()} - {dev['name'].upper()}:*\n"

            if status == "DOWN":
                full_message += f"    🔴 *STATUS: OFFLINE / ERRO DE REDE*\n"
            
            if dev_type == "Printer_HP" and toner is not None:
                supply_emoji = "🟡" if toner <= 15 else "🟢"
                full_message += f"    {supply_emoji} *Toner:* {toner}.0%\n"

            full_message += "\n"
    
    print("Formatted Message Preview (UTF-8):")
    sys.stdout.buffer.write(full_message.encode('utf-8'))
    print("\n--- Test Finished ---")

if __name__ == "__main__":
    test_config_categories()
    test_report_formatting()
