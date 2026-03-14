import sys
from sqlalchemy import create_engine, text

# Connect to 'postgres' database to create the new one
DB_URI = 'postgresql+pg8000://postgres:R%40f%4008049226*%23@localhost:5432/postgres'

print("\n--- Creating database MagaLabs_LogPrint ---")
try:
    engine = create_engine(DB_URI, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'MagaLabs_LogPrint'"))
        if result.fetchone():
            print("Database MagaLabs_LogPrint already exists.")
        else:
            print("Creating database MagaLabs_LogPrint...")
            conn.execute(text('CREATE DATABASE "MagaLabs_LogPrint"'))
            print("Database created successfully!")
except Exception as e:
    print(f"Failed to create database: {e}")
