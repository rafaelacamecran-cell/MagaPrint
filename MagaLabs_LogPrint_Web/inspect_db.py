from app import app
from models import db, Ticket, SupportTicket, UsageLog
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    for table_name in ['ticket', 'support_ticket', 'usage_log']:
        try:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            print(f"Table {table_name}: {columns}")
        except Exception as e:
            print(f"Error inspecting {table_name}: {e}")
