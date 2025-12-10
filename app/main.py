from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from contextlib import asynccontextmanager
from typing import List

# 우리가 만든 모듈들 가져오기
from app.core.ai_model import waste_classifier
from app.services.cleanhouse_service import cleanhouse_service
from app.schemas.waste import AIAnalysisResponse, CleanHouseInfo

# 서버 수명주기 관리 (서버 켜질 때 할 일)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 서버 시작 시 AI 모델을 미리 로드합니다 (속도 향상)
    waste_classifier.load_model()
    yield
    # 2. 서버 종료 시 할 일이 있다면 여기에 작성 (지금은 없음)

# 앱 초기화
app = FastAPI(title="버릴까 말까? API Server", lifespan=lifespan)

# --- 1. AI 이미지 분석 API ---
@app.post("/api/predict", response_model=AIAnalysisResponse, tags=["AI Feature"])
async def predict_waste_image(file: UploadFile = File(...)):
    """
    [기능] 사진을 업로드하면 쓰레기 종류와 오염 여부를 알려줍니다.
    """
    # 이미지 파일 읽기
    content = await file.read()
    
    # AI 예측 수행
    label_text, conf = waste_classifier.predict_image(content)
    
    if not label_text:
        raise HTTPException(status_code=500, detail="이미지 분석에 실패했습니다.")
    
    # 결과 파싱 (예: "Can_Dirty" -> Category: Can, Dirty: True)
    try:
        if "_" in label_text:
            category, state = label_text.split('_')
            is_dirty = (state == "Dirty")
        else:
            category = label_text
            is_dirty = False
            
        # 사용자 안내 메시지 생성
        if is_dirty:
            msg = f"⚠️ {category}가 오염된 상태입니다. 깨끗이 씻어서 배출해주세요."
        else:
            msg = f"✅ 깨끗한 {category}입니다. 분리수거함에 넣어주세요!"
            
    except Exception:
        category, is_dirty, msg = "Unknown", False, "분석 오류 발생"

    return AIAnalysisResponse(
        category=category,
        is_dirty=is_dirty,
        message=msg,
        confidence=conf
    )

# --- 2. 내 주변 클린하우스 API ---
@app.get("/api/clean-houses", response_model=List[CleanHouseInfo], tags=["Location Feature"])
async def get_nearby_houses(
    lat: float = Query(..., description="사용자 위도"),
    lng: float = Query(..., description="사용자 경도")
):
    """
    [기능] 내 위도/경도를 보내면 가장 가까운 클린하우스 3곳의 정보를 반환합니다.
    """
    return cleanhouse_service.get_nearest_cleanhouses(lat, lng)

# --- 3. 요일별 배출 가이드 API ---
@app.get("/api/guide", tags=["Info Feature"])
async def get_recycling_guide():
    """
    [기능] 요일별 배출 가능한 품목 전체 리스트를 반환합니다.
    """
    return cleanhouse_service.get_guide()

# 기본 접속 테스트용
@app.get("/")
def read_root():
    return {"message": "버릴까 말까? 서버가 정상적으로 실행 중입니다."}

if __name__ == "__main__":
    import uvicorn
    # 윈도우에서 멀티프로세싱 에러 방지
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)