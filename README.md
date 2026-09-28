# 버릴까말까 — AI 분리배출 가이드 백엔드

제주대학교 기초웹개발론 5조 "버릴까말까" 프로젝트의 백엔드입니다. (백엔드·AI 담당: 양문준)

쓰레기 사진을 업로드하면 MobileNetV3 모델이 10종으로 분류하고, 분리배출 방법을 알려줍니다.

- 팀 저장소(기획·디자인·산출물): https://github.com/baeksohyun12/trash-or-not-ai
- 프론트엔드: https://github.com/0bini/my-recycling-project
- API 문서(Swagger): https://waste-api-6xd9.onrender.com/docs
  (Render 무료 플랜이라 첫 접속 시 서버가 깨어나는 데 1분 가까이 걸릴 수 있습니다)

## 기술 스택

Python · FastAPI · Uvicorn · PyTorch/Torchvision (MobileNetV3 Large) · Pillow · pytest · Docker · Render

## 담당 범위

| 단계 | 내용 |
|---|---|
| 데이터 | AI Hub 생활폐기물 이미지의 바운딩박스로 물체만 잘라내고(`AI학습/Crop.py`), 세부 품목을 10개 클래스로 묶어 학습/검증 8:2 분할(`AI학습/Split_Dataset.py`) |
| 학습 | MobileNetV3 Large 전이학습, 약 20만 장. 클래스 불균형(플라스틱 약 6만 장, 음식물 약 5천 장)을 클래스별 가중치로 보정 (`AI학습/train.py`) |
| API | 이미지 검증(형식·용량·손상 여부) → 추론 → 프론트엔드 아이콘 카테고리와 안내 문구로 변환 |
| 배포 | Render 무료 인스턴스 (메모리 512MB, CPU 0.1개) |

## API

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/predict` | 이미지(JPG·PNG·WEBP, 10MB 이하) 분석 |
| GET | `/health` | 서버·모델 준비 상태 |
| GET | `/` | 서버 동작 확인 |

응답 예시:

```json
{
  "category": "Can",
  "is_dirty": false,
  "message": "내용물을 비우고 헹군 뒤 찌그러뜨려 배출해주세요.",
  "confidence": 0.98
}
```

| 상태 코드 | 원인 |
|---|---|
| 400 | 지원하지 않는 형식, 또는 이미지로 열 수 없는 파일 |
| 413 | 10MB 초과 |
| 500 | 추론 중 오류 |
| 503 | 모델 미준비 |

AI는 10개 클래스(Can, Scrap, Plastic, PET, Glass, Paper, Styrofoam, Vinyl, Food, General)로 분류하고,
프론트엔드 아이콘이 8종이라 `Scrap → Can`, `PET → Plastic`으로 묶어서 보냅니다. 안내 문구는 세부 클래스 기준입니다.

## 프로젝트 구조

```
app/
├── main.py            # FastAPI 앱, 라우팅, 업로드 검증
├── core/
│   ├── ai_model.py    # 모델 로드(기동 시 1회)·전처리·추론
│   └── guide.py       # 분리배출 안내 문구, 아이콘 매핑
└── schemas/
    └── waste.py       # 응답 스키마 (Pydantic)
model_data/            # 학습된 가중치, 클래스 목록
AI학습/                # 데이터 전처리·분할·학습 코드
tests/                 # API 테스트
scripts/               # 응답 시간 측정, 전처리 방식별 정확도 비교
docs/                  # 로컬 테스트 방법, 성능 측정 기록
```

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

배포 환경(메모리 512MB, CPU 0.1개)과 같은 조건으로 확인하는 방법은 [docs/LOCAL_TEST.md](docs/LOCAL_TEST.md)에 있습니다.

## 버전

- `v1.0-course-submission`: 과제 제출본 (2025.12)
- v1.1: 과제 종료 후 리팩토링. 버그 수정, 응답 시간·메모리 개선, 테스트·CI 추가 → [CHANGELOG.md](CHANGELOG.md), [docs/BENCHMARK.md](docs/BENCHMARK.md)
