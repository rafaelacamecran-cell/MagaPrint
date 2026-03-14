from app import app
from models import db, VirtualStock, StockLog

with app.app_context():
    print("Syncing database schema...")
    try:
        # Tables to recreate if they exist with old names or just create new ones
        db.create_all()
        print("✓ Database tables created/verified.")
        
        # Check if we need to migrate from TonerStock (if it existed)
        # In this specific case, the user previously had TonerStock. 
        # If the table is still there under the old name, we might need a manual SQL or just drop/recreate.
        # Since we found it empty, a simple create_all is usually enough for new tables.
        
        print("✓ Schema sync complete.")
    except Exception as e:
        print(f"Error syncing schema: {e}")
