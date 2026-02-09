"""
Add SSH credential columns to resources table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate_db():
    print("Migrating database schema...")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns exist
        try:
            conn.execute(text("ALTER TABLE resources ADD COLUMN ssh_port INTEGER DEFAULT 22"))
            print("Added ssh_port")
        except Exception as e:
            print(f"ssh_port might exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE resources ADD COLUMN ssh_username VARCHAR(100) DEFAULT 'root'"))
            print("Added ssh_username")
        except Exception as e:
            print(f"ssh_username might exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE resources ADD COLUMN ssh_password_enc VARCHAR(500)"))
            print("Added ssh_password_enc")
        except Exception as e:
            print(f"ssh_password_enc might exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE resources ADD COLUMN ssh_private_key_enc VARCHAR(2000)"))
            print("Added ssh_private_key_enc")
        except Exception as e:
            print(f"ssh_private_key_enc might exist: {e}")
            
        conn.commit()
    print("Migration completed.")

if __name__ == "__main__":
    migrate_db()
