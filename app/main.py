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
    [기능] AI 분석 후, 프론트엔드에 표시할 '배출 꿀팁(Tip)' 메시지를 반환합니다.
    """
    content = await file.read()
    
    # 1. AI 모델 추론
    label_text, conf = waste_classifier.predict_image(content)
    
    # 예외 처리: 분석 실패 시
    if not label_text:
        raise HTTPException(status_code=500, detail="이미지 분석에 실패했습니다.")

    # 2. [핵심] 프론트엔드 팁(Tip) 데이터와 1:1 매핑
    # 기존 프론트엔드 코드에 있던 텍스트를 백엔드로 옮겨왔습니다.
    waste_info = {
        "Can": {
            "type": "캔/고철류",
            "tip": "내용물을 비우고 헹군 뒤 찌그러뜨려 배출해주세요."
        },
        "Glass": {
            "type": "병류",
            "tip": "내용물은 비우고 뚜껑을 분리해 배출해주세요."
        },
        "Paper": {
            "type": "종이류",
            "tip": "테이프 등 이물질을 제거하고 펴서 배출해주세요."
        },
        "Plastic": {
            "type": "플라스틱",
            "tip": "내용물을 비우고 라벨을 제거한 후 압축해서 버려주세요."
        },
        "PET": {
            "type": "플라스틱", # PET는 플라스틱 팁과 동일하게 처리
            "tip": "내용물을 비우고 라벨을 제거한 후 압축해서 버려주세요."
        },
        "Styrofoam": {
            "type": "스티로폼",
            "tip": "테이프와 운송장을 제거하고 흰색의 깨끗한 것만 모아 배출해주세요."
        },
        "Vinyl": {
            "type": "비닐류",
            "tip": "이물질을 씻어내고 흩날리지 않게 한곳에 모아 배출해주세요."
        }
    }

    # 3. 매핑 정보 가져오기
    info = waste_info.get(label_text)
    
    # 기본값 설정 (혹시 모를 에러 방지)
    final_type = label_text
    final_msg = "분리배출 방법을 찾을 수 없습니다."

    if info:
        final_type = info["type"]   # 예: "캔/고철류"
        final_msg = info["tip"]     # 예: "내용물을 비우고..."

    # 4. 결과 반환
    # 이제 프론트엔드는 message만 보여주면 됩니다.
    return AIAnalysisResponse(
        category=label_text,    # 영어 코드 (아이콘 매칭용)
        is_dirty=False,         # 사용 안 함 (고정)
        message=final_msg,      # ✨ 완성된 꿀팁 메시지
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
