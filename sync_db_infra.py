import os
from MagaLabs_LogPrint_Web.app import app, db
from MagaLabs_LogPrint_Web.models import InfraDevice

with app.app_context():
    db.create_all()
    print("Database tables synchronized (including InfraDevice).")
