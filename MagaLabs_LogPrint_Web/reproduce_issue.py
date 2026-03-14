import sys
from sqlalchemy import create_engine

# Hardcoded URI from app.py
DB_URI = 'postgresql+pg8000://postgres:R%40f%4008049226*%23@localhost:5432/MagaLabs_LogPrint'

print("\n--- Testing pg8000 driver connection ---")
try:
    engine = create_engine(DB_URI)
    with engine.connect() as conn:
        print("SQLAlchemy connection successful with pg8000!")
except Exception as e:
    print(f"SQLAlchemy connection failed with pg8000: {e}")
    # import traceback
    # traceback.print_exc()
