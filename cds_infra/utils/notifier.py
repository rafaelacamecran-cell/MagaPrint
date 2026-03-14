import requests
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

class GChatNotifier:
    def __init__(self):
        self.webhook_url = os.getenv("GCHAT_LINKS_WEBHOOK")

    def send_alert(self, message: str):
        if not self.webhook_url:
            print("GCHAT_WEBHOOK_URL not set.")
            return

        payload = {"text": message}
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send GChat alert: {e}")

    def get_diagnostic(self, status: str, details: str = "", toner_level: int = None, ribbon_level: int = None, label_level: int = None) -> str:
        """Returns a concise diagnostic based on status, details and supply levels."""
        # High priority: Low supplies
        if toner_level is not None and toner_level <= 10:
            return "Probavel: Toner fim de vida. Acao: Solicite troca ao T.I."
        if ribbon_level is not None and ribbon_level <= 10:
            return "Probavel: Ribbon no fim. Acao: Solicite reposicao ao T.I."
        if label_level is not None and label_level <= 10:
            return "Probavel: Etiquetas no fim. Acao: Solicite reposicao ao T.I."

        if status == "OK":
            return ""

        diagnostics = {
            "DOWN": "Probavel: Desligado ou s/ Rede. Acao: Verifique energia/cabo.",
            "OSCILLATING": "Probavel: Instabilidade no Link. Acao: Reiniciar equipamento.",
            "ERROR": "Probavel: Erro de Software/Driver. Acao: Resetar Equipamento.",
            "Missing Paper": "Probavel: Bandeja Vazia. Acao: Repor papel/etiqueta.",
            "Paper Jam": "Probavel: Papel Preso. Acao: Limpar roletes/trajeto.",
            "Cover Open": "Probavel: Tampa Aberta. Acao: Fechar compartimento.",
            "Maintenance Kit": "Probavel: Kit Manutencao vencido. Acao: Abrir chamado T.I.",
            "Head Open": "Probavel: Cabeca da Zebra aberta. Acao: Fechar e verificar Ribbon.",
            "Ribbon Out": "Probavel: Ribbon esgotado. Acao: Repor Ribbon.",
            "Media Out": "Probavel: Etiquetas esgotadas. Acao: Repor etiquetas."
        }

        if status in diagnostics:
            return diagnostics[status]

        for key, val in diagnostics.items():
            if key.lower() in details.lower():
                return val

        return "Causa: Indeterminada. Acao: Verificacao tecnica local."

    def send_summary_report(self, report_data: Dict[str, List[Dict]]):
        """
        report_data format: { 'Category Name': [ {device_info...}, ... ] }
        """
        if not self.webhook_url:
            print("GCHAT_WEBHOOK_URL not set.")
            return

        full_message = "📊 *LUIZALABS - STATUS DE SUPRIMENTOS E REDE*\n\n"
        
        for category, devices in report_data.items():
            for dev in devices:
                status = dev.get('status', 'UNKNOWN')
                toner = dev.get('toner_level')
                ribbon = dev.get('ribbon_level')
                label = dev.get('label_level')
                dev_type = dev.get('type', '')

                # Group Header for each device: • CATEGORY - NAME:
                full_message += f"• *{category.upper()} - {dev['name'].upper()}:*\n"

                # Check if it's considered an error or warning
                is_offline = (status == "DOWN" or status == "ERROR")
                is_supply_warning = (
                    (toner is not None and toner <= 15) or
                    (ribbon is not None and ribbon <= 15) or
                    (label is not None and label <= 15)
                )

                # 1. Status Line
                if is_offline:
                    # Red button/circle for Offline as requested
                    full_message += f"    🔴 *STATUS: OFFLINE / ERRO DE REDE*\n"
                elif status != "OK":
                    diag = self.get_diagnostic(status, dev.get('details', ''), toner, ribbon, label)
                    full_message += f"    ⚠️ *STATUS: {status}* ({diag})\n"
                # If OK, we skip the status line to keep it clean like the screenshot
                
                # 2. Supply Lines
                if dev_type == "Printer_HP" and toner is not None:
                    supply_emoji = "🟡" if toner <= 15 else "🟢"
                    full_message += f"    {supply_emoji} *Toner:* {toner}.0%\n"
                
                if dev_type == "Printer_Zebra":
                    if ribbon is not None:
                        supply_emoji = "🟡" if ribbon <= 15 else "🟢"
                        full_message += f"    {supply_emoji} *Ribbon:* {ribbon}.0%\n"
                    if label is not None:
                        supply_emoji = "🟡" if label <= 15 else "🟢"
                        full_message += f"    {supply_emoji} *Etiqueta:* {label}.0%\n"

                full_message += "\n"

        self.send_alert(full_message)

    def format_status_message(self, device_name: str, ip: str, status: str, details: str = ""):
        emoji = "✅" if status == "OK" else "❌"
        if status == "OSCILLATING": emoji = "⚠️"
        
        msg = f"{emoji} *{device_name}* ({ip})\n"
        msg += f"Status: {status}\n"
        if details:
            msg += f"Detail: {details}"
        return msg
