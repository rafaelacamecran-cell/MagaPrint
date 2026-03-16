import os
import sys
from app import app
from models import db, InfraDevice

def populate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust path to reach cds_infra/devices.txt from MagaLabs_LogPrint_Web
    devices_path = os.path.join(os.path.dirname(base_dir), 'cds_infra', 'devices.txt')
    
    if not os.path.exists(devices_path):
        print(f"Error: {devices_path} not found.")
        return

    print(f"Loading devices from {devices_path}...")
    devices = []
    current_category = "General"
    
    with open(devices_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 3 and parts[0].count('.') >= 1:
                devices.append({
                    'ip': parts[0],
                    'name': parts[1],
                    'type': parts[2],
                    'category': current_category
                })
            else:
                current_category = line

    with app.app_context():
        print(f"Syncing {len(devices)} devices to database...")
        for dev in devices:
            existing = InfraDevice.query.filter_by(ip=dev['ip']).first()
            if existing:
                existing.name = dev['name']
                existing.device_type = dev['type']
                existing.category = dev['category']
            else:
                new_dev = InfraDevice(
                    ip=dev['ip'],
                    name=dev['name'],
                    device_type=dev['type'],
                    category=dev['category'],
                    status='OK',
                    is_active=True
                )
                db.session.add(new_dev)
        
        try:
            db.session.commit()
            print("Database successfully populated with printers!")
        except Exception as e:
            db.session.rollback()
            print(f"Error syncing to database: {e}")

if __name__ == "__main__":
    populate()
