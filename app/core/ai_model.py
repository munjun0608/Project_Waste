import io
import os

import torch
import torch.nn as nn
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms

# 실행 위치와 관계없이 프로젝트 루트 기준으로 model_data 폴더를 찾는다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "model_data", "best_waste_model.pth")
CLASSES_PATH = os.path.join(BASE_DIR, "model_data", "classes.txt")

# 무료 인스턴스(CPU 0.1개)에서는 스레드를 여러 개 띄워도 빨라지지 않고 경합만 생긴다.
torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", "1")))

# 모델 입력은 224px이므로 스마트폰 원본(약 4000px)을 전부 디코딩할 필요가 없다.
DECODE_MAX_SIDE = 512


class InvalidImageError(Exception):
    """업로드된 파일을 이미지로 열 수 없을 때"""


class ModelNotReadyError(Exception):
    """모델이 로드되지 않았을 때"""


class WasteClassifier:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.class_names = []

        # 학습(train.py)은 Resize((224, 224))로 정사각형 강제 변환을 했지만,
        # 서빙 단계에서는 스마트폰 세로 사진의 비율 왜곡을 막기 위해
        # Resize(256) + CenterCrop(224)를 사용한다.
        # (두 방식의 정확도 비교는 scripts/eval_preprocess.py로 측정)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def load_model(self):
        """서버 시작 시 한 번만 호출된다. 문제가 있으면 예외를 던져 서버 기동을 멈춘다."""
        if not os.path.exists(CLASSES_PATH):
            raise FileNotFoundError(f"classes.txt를 찾을 수 없습니다: {CLASSES_PATH}")
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")

        with open(CLASSES_PATH, "r", encoding="utf-8") as f:
            self.class_names = [line.strip() for line in f if line.strip()]

        state_dict = torch.load(MODEL_PATH, map_location=self.device)

        # 클래스 목록과 학습된 출력층 크기가 다르면 라벨이 어긋난 채로 서비스된다.
        # 조용히 틀리는 대신 기동 시점에 바로 실패시킨다.
        num_outputs = state_dict["classifier.3.weight"].shape[0]
        if num_outputs != len(self.class_names):
            raise ValueError(
                f"classes.txt의 클래스 수({len(self.class_names)})와 "
                f"모델 출력 수({num_outputs})가 다릅니다."
            )

        model = models.mobilenet_v3_large(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_outputs)
        model.load_state_dict(state_dict)
        model.to(self.device).eval()
        self.model = model
        print(f"AI 모델 로드 완료: {len(self.class_names)}개 클래스, device={self.device}")

    def _open_image(self, image_bytes: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # JPEG는 디코딩 단계에서 축소(DCT scaling)해 메모리와 시간을 줄인다.
            image.draft("RGB", (DECODE_MAX_SIDE, DECODE_MAX_SIDE))
            image = image.convert("RGB")  # 투명 배경 PNG 대응
            image.thumbnail((DECODE_MAX_SIDE, DECODE_MAX_SIDE))
            return image
        except (UnidentifiedImageError, OSError, ValueError) as e:
            raise InvalidImageError(str(e)) from e

    def predict_image(self, image_bytes: bytes):
        """이미지 바이트를 받아 (라벨, 확률)을 반환한다."""
        if self.model is None:
            raise ModelNotReadyError("모델이 로드되지 않았습니다.")

        image = self._open_image(image_bytes)
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.inference_mode():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs[0], dim=0)
            confidence, idx = torch.max(probabilities, 0)

        return self.class_names[idx.item()], confidence.item()


# 전역 객체 (main.py에서 import해서 사용)
waste_classifier = WasteClassifier()
