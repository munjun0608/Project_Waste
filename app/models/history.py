from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from datetime import datetime
from app.core.database import Base

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True) # 고유 번호
    category = Column(String, index=True)   # 쓰레기 종류 (예: PET)
    is_dirty = Column(Boolean)              # 오염 여부
    confidence = Column(Float)              # 정확도
    created_at = Column(DateTime, default=datetime.now) # 찍은 시간