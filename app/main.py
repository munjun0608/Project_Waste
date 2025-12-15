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

# --- 1. AI 분리배출 가이드 API ---
@app.post("/api/predict", response_model=AIAnalysisResponse, tags=["AI Feature"])
async def predict_waste_image(file: UploadFile = File(...)):
    """
    [기능] AI 분석(10종) -> 프론트엔드 아이콘(8종) 매핑
    딕셔너리 구조 변경 없이, 리턴할 때만 카테고리를 바꿔줍니다.
    """
    content = await file.read()
    
    # 1. AI 추론 (결과: Can, Scrap, PET, Plastic, Food 등 10개 중 하나)
    label_text, conf = waste_classifier.predict_image(content)
    
    if not label_text:
        raise HTTPException(status_code=500, detail="이미지 분석에 실패했습니다.")

    # 2. [팁 정보] 작성자님 기존 스타일 유지 (type, tip만 존재)
    # AI가 인식하는 10가지 클래스에 대한 각각의 멘트를 적습니다.
    waste_info = {
        # --- 캔/고철류 ---
        "Can": {
            "type": "캔류", 
            "tip": "내용물을 비우고 헹군 뒤 찌그러뜨려 배출해주세요."
        },
        "Scrap": {
            "type": "캔/고철류 (고철)", 
            "tip": "프라이팬, 공구, 못 등은 고철로 분리 배출해주세요."
        },

        # --- 플라스틱류 ---
        "Plastic": {
            "type": "플라스틱", 
            "tip": "내용물을 비우고 라벨을 제거한 후 압축해서 버려주세요."
        },
        "PET": {
            "type": "플라스틱 (투명페트)", 
            "tip": "라벨을 떼고 찌그러뜨려 뚜껑을 닫아서 배출해주세요."
        },

        # --- 나머지 ---
        "Glass": {
            "type": "유리병", "tip": "내용물은 비우고 뚜껑을 분리해 배출해주세요."
        },
        "Paper": {
            "type": "종이류", "tip": "테이프, 스프링 등 이물질을 제거하고 펴서 배출해주세요."
        },
        "Styrofoam": {
            "type": "스티로폼", "tip": "테이프와 운송장을 제거하고 흰색의 깨끗한 것만 모아 배출해주세요."
        },
        "Vinyl": {
            "type": "비닐류", "tip": "이물질을 씻어내고 흩날리지 않게 한곳에 모아 배출해주세요."
        },
        "Food": {
            "type": "음식물 쓰레기", "tip": "물기를 꽉 짜고 뼈, 껍데기 등 딱딱한 것은 일반쓰레기로 버려주세요."
        },
        "General": {
            "type": "일반 쓰레기", "tip": "재활용이 불가능합니다. 종량제 봉투에 담아 배출해주세요."
        }
    }

    # 3. [핵심] 프론트엔드 아이콘 매핑 (10개 -> 8개)
    # Scrap이 나오면 프론트엔드에는 'Can'이라고 알려줘야 아이콘이 뜹니다.
    # PET가 나오면 프론트엔드에는 'Plastic'이라고 알려줍니다.
    # 나머지는 자기 이름 그대로 씁니다.
    icon_mapping = {
        "Scrap": "Can",     # 고철 -> 캔 아이콘
        "PET": "Plastic"    # 페트 -> 플라스틱 아이콘
    }
    
    # 매핑된 아이콘 이름 가져오기 (없으면 원래 이름 사용)
    frontend_category = icon_mapping.get(label_text, label_text)

    # 4. 텍스트 정보 가져오기
    info = waste_info.get(label_text, waste_info["General"])

    # 5. 결과 반환
    # category에는 'frontend_category' (Can, Plastic 등 8개 중 하나)를 넣어서 아이콘 오류 방지
    # message에는 AI가 찾은 디테일한 정보(Scrap 팁 등)를 넣음
    return AIAnalysisResponse(
        category=frontend_category,   # 여기가 핵심! (Scrap이어도 Can으로 나감)
        is_dirty=False,
        message=f"[{info['type']}]\n{info['tip']}",
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
    # 0.0.0.0은 "모든 네트워크(외부 IP 포함)에서의 접속을 허용한다"는 뜻입니다.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)