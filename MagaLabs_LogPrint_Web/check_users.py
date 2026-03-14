from app import app
from models import db, User

with app.app_context():
    print("Listing all users in the database:")
    users = User.query.all()
    if not users:
        print("No users found.")
    for user in users:
        print(f"Username: {user.username}, Email: {user.email}, Role: {user.role}, Name: {user.name}")
    
    target = 'ra_camecran'
    user = User.query.filter((User.username == target) | (User.email == target)).first()
    if user:
        print(f"\nUser '{target}' found!")
        print(f"Details: {user}")
    else:
        print(f"\nUser '{target}' NOT found.")
