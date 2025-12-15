import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io
import os

# 파일 경로 자동 설정
# (현재 파일 위치를 기준으로 model_data 폴더를 찾아갑니다)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "model_data", "best_waste_model.pth")
CLASSES_PATH = os.path.join(BASE_DIR, "model_data", "classes.txt")

class WasteClassifier:
    def __init__(self):
        # GPU 사용 가능 시 GPU, 아니면 CPU 사용
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.class_names = []
        
        # 이미지 전처리 설정 (학습 코드인 train.py와 100% 동일하게 맞춰야 성능이 나옵니다)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def load_model(self):
        """서버 시작 시 모델과 클래스 정보를 메모리에 올립니다."""
        print(f"🔄 AI 모델 로딩 시작... (경로: {MODEL_PATH})")
        
        # 1. 클래스 이름 읽기 (classes.txt)
        if os.path.exists(CLASSES_PATH):
            with open(CLASSES_PATH, "r", encoding="utf-8") as f:
                self.class_names = [line.strip() for line in f.readlines()]
            print(f"   ✅ 클래스 목록 로드됨: {self.class_names}")
        else:
            print(f"   ❌ 오류: classes.txt를 찾을 수 없습니다! 경로: {CLASSES_PATH}")
            return

        # 2. 모델 뼈대 생성 (MobileNetV3 Large)
        try:
            # pretrained=False: 우리는 직접 학습한 가중치를 쓸 것이므로 빈 깡통을 가져옵니다.
            self.model = models.mobilenet_v3_large(pretrained=False)
            
            # 3. 출력층(Classifier) 교체
            # 학습할 때 사용한 클래스 개수에 맞춰서 마지막 레이어를 수정합니다.
            num_classes = len(self.class_names)
            num_ftrs = self.model.classifier[3].in_features
            self.model.classifier[3] = nn.Linear(num_ftrs, num_classes)
            
            # 4. 학습된 가중치(.pth) 주입
            if os.path.exists(MODEL_PATH):
                checkpoint = torch.load(MODEL_PATH, map_location=self.device)
                self.model.load_state_dict(checkpoint)
                self.model.to(self.device)
                self.model.eval() # 추론 모드로 전환 (필수!)
                print("   ✨ AI 모델 로드 성공! (준비 완료)")
            else:
                print(f"   ❌ 오류: 모델 파일이 없습니다! 경로: {MODEL_PATH}")
                self.model = None

        except Exception as e:
            print(f"   ❌ 치명적 오류: 모델 로딩 중 에러 발생\n{e}")

    def predict_image(self, image_bytes):
        """이미지 바이트 데이터를 받아 예측 결과(라벨, 확률)를 반환"""
        if self.model is None:
            # 모델이 로드되지 않았으면 다시 로드 시도
            self.load_model()
            if self.model is None:
                return "Error", 0.0

        try:
            # 1. 이미지 열기 (RGB 변환 필수 - 투명 배경 PNG 대응)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # 2. 전처리 (Resize -> Tensor -> Normalize)
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # 3. 추론 실행
            with torch.no_grad():
                outputs = self.model(input_tensor)
                # Softmax로 확률(%) 계산
                probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
                confidence, preds = torch.max(probabilities, 0)
                
            idx = preds.item()
            label = self.class_names[idx]
            score = confidence.item()
            
            return label, score
            
        except Exception as e:
            print(f"예측 중 에러 발생: {e}")
            return "Error", 0.0

# 전역 객체 생성 (main.py에서 import해서 사용함)
waste_classifier = WasteClassifier()