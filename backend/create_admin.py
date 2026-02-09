#!/usr/bin/env python3
"""
Create default admin user for OPS Platform
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_admin_user():
    """Create default admin user if not exists"""
    db = SessionLocal()
    
    try:
        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            print("✓ Admin user already exists")
            return
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@opsplatform.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            role="admin",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✓ Admin user created successfully!")
        print(f"  Username: {admin_user.username}")
        print(f"  Email: {admin_user.email}")
        print(f"  Password: admin123")
        print(f"  Role: {admin_user.role}")
        print("\n⚠️  IMPORTANT: Please change the default password after first login!")
        
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Creating default admin user...")
    print("=" * 50)
    create_admin_user()
    print("=" * 50)
