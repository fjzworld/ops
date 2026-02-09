import sys
sys.path.insert(0, '/app')
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def reset_password():
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == "admin").first()
        if u:
            u.hashed_password = get_password_hash("admin123")
            db.commit()
            print("Successfully reset admin password to: admin123")
        else:
            print("Error: Admin user not found")
    except Exception as e:
        print(f"Error resetting password: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_password()
