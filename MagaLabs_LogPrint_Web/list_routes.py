import sys
import os

# Adiciona o diretório do projeto ao sys.path
sys.path.append(r'd:\Meus projetos\MagaLabs_LogPrint_web\MagaLabs_LogPrint_Web')

from app import app

def list_routes():
    with app.app_context():
        print(f"{'Endpoint':<40} {'Methods':<20} {'Rule'}")
        print("-" * 80)
        for rule in app.url_map.iter_rules():
            methods = ', '.join(sorted(rule.methods))
            print(f"{rule.endpoint:<40} {methods:<20} {rule}")

if __name__ == "__main__":
    list_routes()
