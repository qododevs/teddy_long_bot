from sqlalchemy import Column, Integer, BigInteger, Text, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

class ConversationContext(Base):
    __tablename__ = 'conversation_context'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)

class ApiKey(Base):
    __tablename__ = 'api_keys'
    id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False, unique=True)
    is_active = Column(Integer, default=1)
    blocked_until = Column(DateTime, nullable=True)  # ← НОВОЕ ПОЛЕ