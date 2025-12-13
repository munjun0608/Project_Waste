from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List

# 모듈 가져오기
from app.core.ai_model import waste_classifier
from app.services.cleanhouse_service import cleanhouse_service
from app.schemas.waste import AIAnalysisResponse, CleanHouseInfo

# 서버 수명주기
@asynccontextmanager
async def lifespan(app: FastAPI):
    waste_classifier.load_model()
    yield

app = FastAPI(title="버릴까 말까? API", lifespan=lifespan)

# --- [수정 완료] CORS 설정 (모든 곳에서 접속 허용) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 5500, 3000 등 모든 포트 자동 허용
    allow_credentials=False,    # 전체 허용 시에는 반드시 False여야 함
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------------------------

# --- [수정된 main.py의 predict 부분] ---

@app.post("/api/predict", response_model=AIAnalysisResponse, tags=["AI Feature"])
async def predict_waste_image(file: UploadFile = File(...)):
    """
    [기능] 사진을 업로드하면 쓰레기 종류를 분석해줍니다. (새 모델 적용)
    """
    content = await file.read()
    
    # 1. AI 모델 추론
    label_text, conf = waste_classifier.predict_image(content)
    
    if not label_text:
        raise HTTPException(status_code=500, detail="분석 실패")
    
    # 2. 결과 메시지 생성 (새 데이터셋은 'Can', 'Glass' 등 재질 이름만 나옴)
    # 기존의 '_' 분리 로직 제거 -> 재질 그대로 사용
    category = label_text  # 예: "Can", "Plastic"
    
    # 새 모델은 오염 여부를 학습하지 않았으므로 기본값 False 처리
    is_dirty = False 
    
    # 메시지 커스터마이징 (한글 매핑 추천)
    korean_names = {
        "Can": "캔류",
        "Glass": "유리",
        "Paper": "종이류",
        "PET": "페트",
        "Plastic": "플라스틱",
        "Styrofoam": "스티로폼",
        "Vinyl": "비닐류"
    }
    
    korean_category = korean_names.get(category, category)
    msg = f"✅ 분석 결과: {korean_category} ({category}) 입니다."

    return AIAnalysisResponse(
        category=category,
        is_dirty=is_dirty,   # 항상 False (모델 기능 한계)
        message=msg,
        confidence=conf
    )

# --- 2. 클린하우스 조회 ---
@app.get("/api/clean-houses", response_model=List[CleanHouseInfo], tags=["Location Feature"])
async def get_nearby_houses(
    lat: float = Query(..., description="사용자 위도"),
    lng: float = Query(..., description="사용자 경도")
):
    return cleanhouse_service.get_nearest_cleanhouses(lat, lng)

# --- 3. 가이드 API ---
@app.get("/api/guide", tags=["Info Feature"])
async def get_recycling_guide():
    return cleanhouse_service.get_guide()

@app.get("/")
def read_root():
    return {"message": "Server is running (Open to Network)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
