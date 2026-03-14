import os
import openpyxl
from typing import List, Dict

class ConfigLoader:
    def __init__(self, devices_txt: str, devices_xlsx: str):
        self.devices_txt = devices_txt
        self.devices_xlsx = devices_xlsx

    def load_devices(self) -> List[Dict[str, str]]:
        devices = []
        current_category = "General"
        
        # Load from TXT
        if os.path.exists(self.devices_txt):
            with open(self.devices_txt, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 3 and parts[0].count('.') >= 1: # Basic IP check
                        devices.append({
                            'ip': parts[0],
                            'name': parts[1],
                            'type': parts[2],
                            'category': current_category
                        })
                    else:
                        # Probably a header/category line
                        current_category = line

        # Load from Excel
        if os.path.exists(self.devices_xlsx):
            try:
                wb = openpyxl.load_workbook(self.devices_xlsx)
                sheet = wb.active
                # Assuming header: IP, Name, Type
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if row[0] and row[1] and row[2]:
                        # Avoid duplicates
                        if not any(d['ip'] == str(row[0]) for d in devices):
                            devices.append({
                                'ip': str(row[0]),
                                'name': str(row[1]),
                                'type': str(row[2])
                            })
            except Exception as e:
                print(f"Error loading Excel config: {e}")

        return devices
