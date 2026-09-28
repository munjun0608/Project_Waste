from pydantic import BaseModel


class AIAnalysisResponse(BaseModel):
    category: str      # 프론트엔드 아이콘용 카테고리 (8종)
    is_dirty: bool     # 오염 여부 (현재 항상 false)
    message: str       # 분리배출 안내 문구
    confidence: float  # 예측 확률 (0.0 ~ 1.0)


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    num_classes: int
