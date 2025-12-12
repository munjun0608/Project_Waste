from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List

# 모듈 가져오기 (DB 관련 모듈 제거됨)
from app.core.ai_model import waste_classifier
from app.services.cleanhouse_service import cleanhouse_service
from app.schemas.waste import AIAnalysisResponse, CleanHouseInfo

@asynccontextmanager
async def lifespan(app: FastAPI):
    # AI 모델 로드
    try:
        waste_classifier.load_model()
    except Exception as e:
        print(f"모델 로드 중 오류: {e}")
    yield

app = FastAPI(title="버릴까 말까? API", lifespan=lifespan)

# 🔥 [CORS 설정] 프론트엔드 연결 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. AI 분석 API (DB 저장 로직 삭제됨) ---
@app.post("/api/predict", response_model=AIAnalysisResponse, tags=["AI Feature"])
async def predict_waste_image(file: UploadFile = File(...)):
    # 이미지 읽기
    content = await file.read()
    
    # AI 예측
    label_text, conf = waste_classifier.predict_image(content)
    
    if not label_text:
        raise HTTPException(status_code=500, detail="분석 실패")
    
    # 결과 파싱
    category = label_text
    is_dirty = False
    if "_" in label_text:
        try:
            category, state = label_text.split('_')
            is_dirty = (state == "Dirty")
        except:
            pass
            
    msg = "세척 필요!" if is_dirty else "깨끗합니다."

    # DB 저장 없이 바로 결과 반환
    return AIAnalysisResponse(
        category=category,
        is_dirty=is_dirty,
        message=msg,
        confidence=conf
    )

# --- 2. 클린하우스 조회 ---
@app.get("/api/clean-houses", response_model=List[CleanHouseInfo], tags=["Location Feature"])
async def get_nearby_houses(lat: float, lng: float):
    return cleanhouse_service.get_nearest_cleanhouses(lat, lng)

# --- 3. 가이드 API ---
@app.get("/api/guide", tags=["Info Feature"])
async def get_recycling_guide():
    return cleanhouse_service.get_guide()

@app.get("/")
def read_root():
    return {"message": "Server is running (No DB Mode)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)