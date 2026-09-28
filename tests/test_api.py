import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.guide import ICON_MAPPING, WASTE_GUIDE
from app.main import MAX_FILE_SIZE, app

FRONTEND_CATEGORIES = {"Can", "Plastic", "Glass", "Paper", "Vinyl", "Styrofoam", "General", "Food"}


@pytest.fixture(scope="module")
def client():
    # with 블록 안에서 lifespan이 실행되어 실제 모델이 로드된다.
    with TestClient(app) as c:
        yield c


def make_image(fmt="JPEG", size=(640, 480)):
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 180, 90)).save(buf, format=fmt)
    return buf.getvalue()


def test_root(client):
    assert client.get("/").status_code == 200


def test_health_accepts_head(client):
    # 모니터링 도구(UptimeRobot)는 HEAD 요청을 사용한다
    assert client.head("/health").status_code == 200
    assert client.head("/").status_code == 200


def test_health_reports_model_loaded(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "model_loaded": True, "num_classes": 10}


@pytest.mark.parametrize("fmt,mime", [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")])
def test_predict_valid_image(client, fmt, mime):
    res = client.post("/api/predict", files={"file": (f"a.{fmt.lower()}", make_image(fmt), mime)})
    assert res.status_code == 200
    body = res.json()
    assert body["category"] in FRONTEND_CATEGORIES
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["message"]


def test_predict_portrait_phone_size(client):
    # 스마트폰 세로 사진 해상도
    img = make_image("JPEG", (3024, 4032))
    res = client.post("/api/predict", files={"file": ("p.jpg", img, "image/jpeg")})
    assert res.status_code == 200


def test_reject_unsupported_mime(client):
    res = client.post("/api/predict", files={"file": ("a.gif", b"GIF89a", "image/gif")})
    assert res.status_code == 400


def test_reject_non_image_with_image_mime(client):
    # 확장자/MIME만 이미지로 속인 파일 (v1.0에서는 200과 "Error" 카테고리가 반환되던 버그)
    res = client.post("/api/predict", files={"file": ("fake.jpg", b"not an image", "image/jpeg")})
    assert res.status_code == 400


def test_reject_oversized_file(client):
    res = client.post("/api/predict", files={"file": ("big.jpg", b"0" * (MAX_FILE_SIZE + 1), "image/jpeg")})
    assert res.status_code == 413


def test_every_class_maps_to_frontend_category():
    with open("model_data/classes.txt", encoding="utf-8") as f:
        classes = [c.strip() for c in f if c.strip()]
    for label in classes:
        assert label in WASTE_GUIDE, f"{label} 안내 문구 없음"
        assert ICON_MAPPING.get(label, label) in FRONTEND_CATEGORIES, f"{label} 아이콘 매핑 없음"
