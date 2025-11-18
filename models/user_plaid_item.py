from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database.database import Base


class UserPlaidItem(Base):
    __tablename__ = "user_plaid_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # Google sub from users table
    item_id = Column(String, unique=True, nullable=False, index=True)  # Plaid item_id
    access_token_encrypted = Column(Text, nullable=False)  # Encrypted access token
    institution_id = Column(String, nullable=True)
    institution_name = Column(String, nullable=True)
    cursor = Column(String, nullable=True)  # For incremental sync
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delete_at = Column(DateTime, nullable=True)