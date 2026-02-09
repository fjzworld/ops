from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Middleware(Base):
    __tablename__ = "middlewares"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False) # e.g. mysql, redis
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    password_enc = Column(String, nullable=True)
    service_name = Column(String, nullable=False) # e.g. mysqld
    log_path = Column(String, nullable=False)
    status = Column(String, default='stopped', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    resource = relationship("Resource", backref="middlewares")

    def __repr__(self):
        return f"<Middleware(name='{self.name}', type='{self.type}', status='{self.status}')>"
