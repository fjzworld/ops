"""
Create metrics tables in the database
"""
import sys
from sqlalchemy import create_engine
from app.core.config import settings
from app.core.database import Base

# Import models to ensure they're registered with Base
from app.models.metric import Metric, ProcessMetric
from app.models.resource import Resource

def create_tables():
    """Create all tables defined in models"""
    print("Creating database tables...")
    engine = create_engine(settings.DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nExisting tables: {', '.join(tables)}")

if __name__ == "__main__":
    create_tables()
