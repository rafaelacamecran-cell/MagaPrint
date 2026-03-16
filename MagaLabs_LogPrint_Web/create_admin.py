from app import app
from models import db, User
import sys

def create_admin():
    with app.app_context():
        # Check if administrative user already exists
        admin_username = 'ra_camecran'
        existing_user = User.query.filter_by(username=admin_username).first()
        
        if existing_user:
            print(f"User '{admin_username}' already exists. Updating password...")
            existing_user.set_password('Maga@2026')
            existing_user.first_login = False
            db.session.commit()
            print("Password updated successfully.")
            return

        print(f"Creating administrative user: {admin_username}")
        new_user = User(
            username=admin_username,
            name='Rafaela Admin',
            email='rafaela.admin@magazine.intranet',
            employee_id='ADMIN01',
            role='superadmin',
            cd='Matriz',
            sector='TI',
            first_login=False
        )
        new_user.set_password('Maga@2026')
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"User '{admin_username}' created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            sys.exit(1)

if __name__ == "__main__":
    create_admin()
