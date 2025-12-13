from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 1. AI 분석 결과 데이터 모델
class AIAnalysisResponse(BaseModel):
    category: str
    is_dirty: bool
    message: str
    confidence: float

# 2. 클린하우스 정보 데이터 모델
class CleanHouseInfo(BaseModel):
    id: int
    name: str
    address: str
    lat: float
    lng: float
    distance: float
    operating_hours: str
    # [수정] 호환성 문제를 위해 List 대신 list 사용
    today_recycling: list[str]
