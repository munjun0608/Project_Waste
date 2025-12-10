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
        
        # 이미지 전처리 설정 (학습 때와 100% 동일해야 함)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def load_model(self):
        """서버 시작 시 모델과 클래스 정보를 로드합니다."""
        print(f"🔄 AI 모델 로딩 중... ({MODEL_PATH})")
        
        # 1. 클래스 이름 읽기
        if os.path.exists(CLASSES_PATH):
            with open(CLASSES_PATH, "r", encoding="utf-8") as f:
                self.class_names = [line.strip() for line in f.readlines()]
        else:
            print(f"⚠️ 오류: classes.txt 파일을 찾을 수 없습니다.")
            return

        # 2. 모델 뼈대 생성 (MobileNetV3 Large)
        self.model = models.mobilenet_v3_large(weights=None)
        
        # 3. 출력층(Classifier) 교체
        num_classes = len(self.class_names)
        num_ftrs = self.model.classifier[3].in_features
        self.model.classifier[3] = nn.Linear(num_ftrs, num_classes)
        
        # 4. 학습된 가중치 로드
        if os.path.exists(MODEL_PATH):
            try:
                checkpoint = torch.load(MODEL_PATH, map_location=self.device)
                self.model.load_state_dict(checkpoint)
                self.model.to(self.device)
                self.model.eval() # 추론 모드로 전환 (학습 X)
                print("✅ AI 모델 로드 완료!")
            except Exception as e:
                print(f"⚠️ 모델 로드 중 에러 발생: {e}")
        else:
            print(f"⚠️ 오류: 모델 파일(.pth)이 없습니다. model_data 폴더를 확인해주세요.")

    def predict_image(self, image_bytes):
        """이미지 바이트 데이터를 받아 예측 결과 반환"""
        if self.model is None:
            return None, 0.0

        try:
            # 이미지 열기 및 변환
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # 추론 실행
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
                _, preds = torch.max(outputs, 1)
                
            idx = preds.item()
            return self.class_names[idx], probabilities[idx].item()
            
        except Exception as e:
            print(f"예측 중 에러 발생: {e}")
            return None, 0.0

# 전역 객체 생성 (이 변수를 다른 파일에서 가져다 씁니다)
waste_classifier = WasteClassifier()