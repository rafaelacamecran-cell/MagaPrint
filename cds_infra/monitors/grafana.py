import requests
import os
from dotenv import load_dotenv

load_dotenv()

class GrafanaMonitor:
    def __init__(self):
        self.url = os.getenv("GRAFANA_URL")
        self.token = os.getenv("GRAFANA_TOKEN")

    def check_alerts(self):
        """
        Fetches active alerts from Grafana API.
        Reference: /api/alerts or /api/v1/provisioning/alert-rules
        """
        if not self.url or not self.token:
            return []

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Example endpoint for Grafana alerts
            endpoint = f"{self.url.rstrip('/')}/api/alerts"
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Grafana API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Failed to connect to Grafana: {e}")
            return []
