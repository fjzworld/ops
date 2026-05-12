from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class AlgorithmDashboardConfig(Base):
    __tablename__ = "algorithm_dashboard_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=3306)
    username = Column(String(120), nullable=False)
    password_enc = Column(String, nullable=True)
    database_name = Column(String(120), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return (
            f"<AlgorithmDashboardConfig(name='{self.name}', host='{self.host}', "
            f"database_name='{self.database_name}', enabled={self.enabled})>"
        )
