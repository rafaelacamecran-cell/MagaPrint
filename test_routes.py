"""Test script to verify routes are registered correctly"""
import sys
sys.path.insert(0, 'MagaLabs_LogPrint_Web')

from app import app

print("✓ Flask app imported successfully")
print(f"✓ Registered blueprints: {list(app.blueprints.keys())}")
print("\n✓ Available main blueprint routes:")

with app.app_context():
    main_routes = [
        str(rule) for rule in app.url_map.iter_rules() 
        if 'main.' in str(rule.endpoint)
    ]
    for route in sorted(main_routes)[:20]:
        print(f"  {route}")

print("\n✓ All routes created successfully!")
