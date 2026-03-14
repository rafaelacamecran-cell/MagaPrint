from app import app
from models import db, VirtualStock, StockLog
from sqlalchemy import text

def sync_schema():
    with app.app_context():
        print("Sincronizando banco de dados...")
        try:
            # Criar tabelas que não existem
            db.create_all()
            
            # Tabela User (Login via E-mail)
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email VARCHAR(100) UNIQUE'))
            
            # Tabela Ticket
            db.session.execute(text('ALTER TABLE ticket ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
            db.session.execute(text('ALTER TABLE ticket ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT \'Open\''))
            db.session.execute(text('ALTER TABLE ticket ADD COLUMN IF NOT EXISTS solicitor_cd VARCHAR(50)'))
            
            # Tabela SupportTicket
            db.session.execute(text('ALTER TABLE support_ticket ADD COLUMN IF NOT EXISTS zendesk_url VARCHAR(500)'))
            
            db.session.commit()
            print("Sincronização concluída com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao sincronizar: {e}")

if __name__ == "__main__":
    sync_schema()
