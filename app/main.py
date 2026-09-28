from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from app.core.ai_model import InvalidImageError, ModelNotReadyError, waste_classifier
from app.core.guide import to_response_fields
from app.schemas.waste import AIAnalysisResponse, HealthResponse

# --- 업로드 제한 ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/webp"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 요청마다 모델을 읽지 않고 서버 시작 시 한 번만 메모리에 올린다.
    waste_classifier.load_model()
    yield


app = FastAPI(title="버릴까 말까? API", lifespan=lifespan)

# 공개 API이고 쿠키/인증을 쓰지 않으므로 모든 Origin 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/predict", response_model=AIAnalysisResponse, tags=["AI Feature"])
async def predict_waste_image(file: UploadFile = File(...)):
    # 1. 파일 형식(MIME Type) 검사
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. (JPG, PNG, WEBP만 가능)")

    # 2. 파일 용량 검사 (제한보다 1바이트만 더 읽어서 초과 여부 판단)
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 너무 큽니다. (10MB 이하만 가능)")

    # 3. AI 추론 (CPU 연산이라 이벤트 루프를 막지 않도록 스레드풀에서 실행)
    try:
        label, confidence = await run_in_threadpool(waste_classifier.predict_image, content)
    except InvalidImageError:
        raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다. 손상되었거나 이미지가 아닌 파일입니다.")
    except ModelNotReadyError:
        raise HTTPException(status_code=503, detail="AI 모델이 준비되지 않았습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        raise HTTPException(status_code=500, detail="이미지 분석에 실패했습니다.")

    # 4. 프론트엔드 아이콘 카테고리와 안내 문구로 변환
    category, message = to_response_fields(label)
    return AIAnalysisResponse(
        category=category,
        is_dirty=False,  # 오염 판별 모델은 미구현 (항상 false)
        message=message,
        confidence=confidence,
    )


@app.get("/")
def read_root():
    # 프론트엔드 testConnection()이 사용하는 기존 응답 형식 유지
    return {"message": "Server is running"}


@app.get("/health", response_model=HealthResponse)
def health():
    # 모니터링/슬립 방지 핑용. 모델까지 준비됐는지 함께 알려준다.
    ready = waste_classifier.is_ready
    if not ready:
        raise HTTPException(status_code=503, detail="model not loaded")
    return HealthResponse(status="ok", model_loaded=ready, num_classes=len(waste_classifier.class_names))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
