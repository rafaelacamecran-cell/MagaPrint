import time
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from utils.config_loader import ConfigLoader
from utils.notifier import GChatNotifier
from monitors.ping import PingMonitor
from monitors.printer import PrinterMonitor
from monitors.grafana import GrafanaMonitor

load_dotenv()

class DbSync:
    def __init__(self, db_url):
        self.db_url = db_url

    def get_db_devices(self):
        if not self.db_url: return []
        devices = []
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT ip, name, device_type, toner_level, label_level, ribbon_level, category FROM infra_device WHERE is_active = True")
                    for row in cur.fetchall():
                        devices.append({
                            'ip': row[0], 
                            'name': row[1], 
                            'type': row[2], 
                            'old_toner': row[3], 
                            'old_label': row[4], 
                            'old_ribbon': row[5],
                            'category': row[6]
                        })
        except Exception as e:
            print(f"DB Error (get_db_devices): {e}")
        return devices

    def update_status(self, ip, status, details, toner_level=None, label_level=None, ribbon_level=None):
        if not self.db_url: return
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE infra_device SET status = %s, details = %s, last_check = %s WHERE ip = %s",
                        (status, details, datetime.now(), ip)
                    )
                    if toner_level is not None:
                        cur.execute("UPDATE infra_device SET toner_level = %s WHERE ip = %s", (toner_level, ip))
                    if label_level is not None:
                        cur.execute("UPDATE infra_device SET label_level = %s WHERE ip = %s", (label_level, ip))
                    if ribbon_level is not None:
                        cur.execute("UPDATE infra_device SET ribbon_level = %s WHERE ip = %s", (ribbon_level, ip))
                conn.commit()
        except Exception as e:
            print(f"DB Error (update_status): {e}")

    def sync_device_config(self, ip, name, dev_type, category):
        """Updates name, type and category from file to DB."""
        if not self.db_url: return
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    # check if exists
                    cur.execute("SELECT id FROM infra_device WHERE ip = %s", (ip,))
                    if cur.fetchone():
                        cur.execute(
                            "UPDATE infra_device SET name = %s, device_type = %s, category = %s WHERE ip = %s",
                            (name, dev_type, category, ip)
                        )
                    else:
                        cur.execute(
                            "INSERT INTO infra_device (ip, name, device_type, category, status) VALUES (%s, %s, %s, %s, 'OK')",
                            (ip, name, dev_type, category)
                        )
                conn.commit()
        except Exception as e:
            print(f"DB Error (sync_device_config): {e}")

    def record_toner_change(self, ip):
        """Updates last_toner_change timestamp."""
        self.record_supply_change(ip, 'toner')

    def record_supply_change(self, ip, supply_type):
        """Updates the last change timestamp for a given supply type."""
        col_map = {'toner': 'last_toner_change', 'label': 'last_label_change', 'ribbon': 'last_ribbon_change'}
        col = col_map.get(supply_type)
        if not col: return
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute(f'UPDATE infra_device SET {col} = %s WHERE ip = %s', (datetime.now(), ip))
                conn.commit()
        except Exception as e:
            print(f"DB Error (record_supply_change): {e}")

    def require_toner_form(self, ip):
        """Sets pending_toner_form = True for the device when a physical change is detected."""
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE infra_device SET pending_toner_form = True WHERE ip = %s", (ip,))
                conn.commit()
        except Exception as e:
            print(f"DB Error (require_toner_form): {e}")

    def get_latest_toner_change_info(self, ip_or_name):
        """Attempts to find who changed the toner by looking at recent tickets/stock logs."""
        try:
            url = self.db_url.replace("postgresql+pg8000://", "postgresql://")
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    # Look for the last closed ticket for this printer
                    cur.execute(
                        "SELECT resolver_name, resolved_at FROM ticket WHERE (asset_identifier LIKE %s) AND status = 'Closed' ORDER BY resolved_at DESC LIMIT 1",
                        (f"%{ip_or_name}%",)
                    )
                    row = cur.fetchone()
                    if row:
                        return row[0], row[1]
        except Exception as e:
            print(f"DB Error (get_latest_toner_change_info): {e}")
        return "N/A", None

def main():
    print("CDS Infra Support Bot starting...")
    
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    devices_txt = os.path.join(base_dir, "devices.txt")
    devices_xlsx = os.path.join(base_dir, "devices.xlsx")
    
    # Initialize components
    config = ConfigLoader(devices_txt, devices_xlsx)
    db_sync = DbSync(os.getenv("DATABASE_URL"))
    notifier = GChatNotifier()
    ping_mon = PingMonitor(
        timeout=int(os.getenv("PING_TIMEOUT_SECONDS", 2)),
        latency_threshold=int(os.getenv("LATENCY_THRESHOLD_MS", 200))
    )
    printer_mon = PrinterMonitor()
    grafana_mon = GrafanaMonitor()
    
    # State tracking to avoid spamming alerts
    last_state = {} # ip -> state

    check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", 60))

    while True:
        # Load from both sources
        file_devices = config.load_devices()
        db_devices = db_sync.get_db_devices()
        
        # Merge (IP as key). File configurations take precedence for names/categories.
        all_devices = {d['ip']: d for d in file_devices}
        
        # Add DB-only devices or preserve DB state (like old toner levels) for file-based devices
        for db_dev in db_devices:
            ip = db_dev['ip']
            if ip in all_devices:
                # Device is in both. Keep file's Name/Category but DB's supply history
                all_devices[ip].update({
                    'old_toner': db_dev.get('old_toner'),
                    'old_label': db_dev.get('old_label'),
                    'old_ribbon': db_dev.get('old_ribbon')
                })
                # Sync file info to DB
                db_sync.sync_device_config(ip, all_devices[ip]['name'], all_devices[ip]['type'], all_devices[ip]['category'])
            else:
                # Multi-source: and it's ONLY in DB
                all_devices[ip] = db_dev
        
        print(f"Checking {len(all_devices)} devices...")
        
        # Group results for the report
        report_data = {} # category -> list of devices with status
        
        for ip, dev in all_devices.items():
            name = dev['name']
            dev_type = dev['type']
            category = dev.get('category', 'General')
            
            current_status = "OK"
            details = ""
            toner_level = None
            ribbon_level = None
            label_level = None

            # 1. Ping Check
            ping_status = ping_mon.check_status(ip)
            if ping_status != "OK":
                current_status = ping_status
                details = "Device unreachable via ping" if ping_status == "DOWN" else "High latency detected"
            
            # 2. Specific Checks
            toner_level = None
            if dev_type.startswith("Printer_HP"):
                hp_status, hp_details, toner_level = printer_mon.check_hp_laser(ip)
                if hp_status != "OK":
                    current_status = hp_status
                    details = hp_details
                
                # Toner Tracking Logic
                old_toner = dev.get('old_toner')
                if toner_level is not None and old_toner is not None:
                    # Detect Toner Change (Level jumped significantly)
                    if toner_level > old_toner + 15:
                        print(f"🔔 Toner replacement detected for {name} ({ip})")
                        db_sync.record_toner_change(ip)
                        db_sync.require_toner_form(ip) # Mark as pending manual register
                        
                        who, when = db_sync.get_latest_toner_change_info(ip)
                        
                        change_msg = f"🔔 *Troca de Toner Detetada*\n📍 *Impressora:* {name} ({ip})\n👤 *Quem trocou:* {who}\n📅 *Data:* {when.strftime('%d/%m/%Y %H:%M') if when else 'N/A'}"
                        change_msg += f"\n⚠️ *Ação Obrigatória:* O formulário de baixa deve ser preenchido no sistema."
                        
                        # Detect Improper Replacement (Changed while still > 20%)
                        if old_toner > 20:
                            change_msg += f"\n❌ *ALERTA:* Troca indevida! O toner anterior ainda tinha {old_toner}%."
                        
                        notifier.send_alert(change_msg)
            
            elif dev_type.startswith("Printer_Zebra"):
                z_status, z_details, ribbon_level, label_level = printer_mon.check_zebra_zt411(ip)
                toner_level = None
                if z_status != "OK":
                    current_status = z_status
                    details = z_details

                # Ribbon Tracking
                old_ribbon = dev.get('old_ribbon')
                if ribbon_level is not None and old_ribbon is not None and ribbon_level > old_ribbon + 20:
                    db_sync.record_supply_change(ip, 'ribbon')
                    who, when = db_sync.get_latest_toner_change_info(ip)
                    msg = f"\U0001f514 *Troca de Ribbon Detetada*\n\U0001f4cd *Impressora:* {name} ({ip})\n\U0001f464 *Quem trocou:* {who}\n\U0001f4c5 *Data:* {when.strftime('%d/%m/%Y %H:%M') if when else 'N/A'}"
                    if old_ribbon > 20:
                        msg += f"\n\u26a0\ufe0f *ALERTA:* Troca indevida! Ribbon ainda tinha {old_ribbon}%."
                    notifier.send_alert(msg)

                # Label Tracking
                old_label = dev.get('old_label')
                if label_level is not None and old_label is not None and label_level > old_label + 20:
                    db_sync.record_supply_change(ip, 'label')
                    who, when = db_sync.get_latest_toner_change_info(ip)
                    msg = f"\U0001f514 *Reposicao de Etiquetas*\n\U0001f4cd *Impressora:* {name} ({ip})\n\U0001f464 *Quem fez:* {who}\n\U0001f4c5 *Data:* {when.strftime('%d/%m/%Y %H:%M') if when else 'N/A'}"
                    if old_label > 20:
                        msg += f"\n\u26a0\ufe0f *ALERTA:* Reposicao indevida! Etiqueta ainda tinha {old_label}%."
                    notifier.send_alert(msg)
            else:
                ribbon_level = None
                label_level = None

            # Update DB
            db_sync.update_status(ip, current_status, details, toner_level, label_level, ribbon_level)

            # Add to report
            if category not in report_data:
                report_data[category] = []

            report_data[category].append({
                'ip': ip,
                'name': name,
                'type': dev_type,
                'status': current_status,
                'details': details,
                'toner_level': toner_level,
                'ribbon_level': ribbon_level if dev_type.startswith('Printer_Zebra') else None,
                'label_level': label_level if dev_type.startswith('Printer_Zebra') else None
            })
            
            # Optional: Local logging
            if last_state.get(ip) != current_status:
                print(f"Status change for {name} ({ip}): {current_status}")
                last_state[ip] = current_status
        
        # 3. Send Summary Report
        print("Sending organized summary report to GChat...")
        notifier.send_summary_report(report_data)
        
        # 3. Grafana Check (Global)
        grafana_alerts = grafana_mon.check_alerts()
        # ... logic for grafana alerts ...

        print(f"Sleeping for {check_interval}s...")
        time.sleep(check_interval)

if __name__ == "__main__":
    main()
