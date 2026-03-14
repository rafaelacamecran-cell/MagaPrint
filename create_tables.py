"""Script to create database tables for new models"""
import sys
sys.path.insert(0, 'MagaLabs_LogPrint_Web')

from app import app, db

with app.app_context():
    db.create_all()
    print("✓ Database tables created successfully!")
    print("✓ New tables: Device, UsageLog, SupportTicket")
