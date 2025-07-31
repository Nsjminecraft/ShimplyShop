from app import app, db
from bson import ObjectId
from datetime import datetime
import os

def init_db():
    # Create indexes for orders collection
    db.orders.create_index([("user_id", 1)])
    db.orders.create_index([("status", 1)])
    db.orders.create_index([("created_at", -1)])
    
    # Create admin user if it doesn't exist
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    if not db.users.find_one({"email": admin_email}):
        from passlib.hash import pbkdf2_sha256
        
        admin_user = {
            "_id": ObjectId(),
            "name": "Admin User",
            "email": admin_email,
            "password": pbkdf2_sha256.hash(admin_password),
            "is_admin": True,
            "created_at": datetime.utcnow()
        }
        
        db.users.insert_one(admin_user)
        print(f"Admin user created with email: {admin_email}")
    else:
        # Ensure the admin flag is set for existing admin user
        db.users.update_one(
            {"email": admin_email},
            {"$set": {"is_admin": True}}
        )
        print(f"Admin user already exists: {admin_email}")
    
    print("Database initialization complete!")

if __name__ == "__main__":
    with app.app_context():
        init_db()
