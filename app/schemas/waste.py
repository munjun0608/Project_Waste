from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 1. AI 분석 결과 데이터 모델
class AIAnalysisResponse(BaseModel):
    category: str
    is_dirty: bool
    message: str
    confidence: float
