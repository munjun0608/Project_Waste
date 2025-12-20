import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
import os
import time
from tqdm import tqdm
import numpy as np
from torch.cuda.amp import autocast, GradScaler 

# =========================================================
# [사용자 환경 설정]
# =========================================================

# 1. 데이터셋 경로
DATA_ROOT = r"D:\WasteProject\Final_Dataset"

# 2. 하이퍼파라미터 설정
# 데이터가 20만 장이 넘어서 1 Epoch 도는데 시간이 꽤 걸립니다.
# 10 Epoch만 해도 충분히 학습됩니다.
BATCH_SIZE = 32                 
LEARNING_RATE = 0.001
EPOCHS = 10                     
MODEL_SAVE_PATH = "best_waste_model.pth"

# 3. 속도 설정 (CPU가 좋으면 4, 에러나면 0)
NUM_WORKERS = 4                 

# =========================================================

def get_class_weights(dataset, device):
    """
    [불균형 해결사] 
    Plastic(6만장)은 점수를 낮게, Food(5천장)는 점수를 높게 설정합니다.
    """
    print("\n⚖️ [데이터 불균형 분석 및 가중치 계산]")
    
    # 1. 클래스별 개수 세기
    targets = dataset.targets
    class_counts = np.bincount(targets)
    total_samples = len(dataset)
    num_classes = len(dataset.classes)
    
    # 2. 가중치 계산 (개수의 역수)
    # 개수가 많을수록 weight는 작아지고, 적을수록 커집니다.
    weights = 1.0 / class_counts
    weights = weights / weights.sum() * num_classes  # 정규화
    
    # 3. 로그 출력 (사용자 확인용)
    print(f"   총 데이터: {total_samples}장")
    print("-" * 50)
    print(f"   {'클래스명':<15} | {'개수':<10} | {'가중치(점수배율)':<10}")
    print("-" * 50)
    
    for idx, count in enumerate(class_counts):
        class_name = dataset.classes[idx]
        weight_val = weights[idx]
        print(f"   {class_name:<15} | {count:<10} | x{weight_val:.4f}")
    print("-" * 50)
    print("👉 '가중치'가 높은 클래스(Food 등)를 틀리면 벌점이 큽니다.")
    print("👉 따라서 AI가 적은 데이터도 무시하지 않고 열심히 학습합니다.\n")

    return torch.FloatTensor(weights).to(device)

def train_model():
    torch.multiprocessing.freeze_support()

    # GPU 장치 설정
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[System] 학습 장치: {device}")
    if device.type == 'cuda':
        print(f"         GPU 모델명: {torch.cuda.get_device_name(0)}")
        print("         (데이터가 많아서 GPU가 필수입니다)")

    # ---------------------------------------------------------
    # 1. 데이터 전처리
    # ---------------------------------------------------------
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # ---------------------------------------------------------
    # 2. 데이터셋 로드
    # ---------------------------------------------------------
    train_dir = os.path.join(DATA_ROOT, 'train')
    val_dir = os.path.join(DATA_ROOT, 'val')

    if not os.path.exists(train_dir):
        print(f"❌ 오류: '{train_dir}' 폴더가 없습니다.")
        return

    print("📂 데이터셋 로딩 중... (20만 장이라 시간이 좀 걸립니다)")
    train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transform)
    
    class_names = train_dataset.classes
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, 
                              num_workers=NUM_WORKERS, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, 
                            num_workers=NUM_WORKERS, pin_memory=True)

    # ---------------------------------------------------------
    # 3. 모델 & 가중치 설정
    # ---------------------------------------------------------
    print("🧠 MobileNetV3 모델 준비 중...")
    model = models.mobilenet_v3_large(pretrained=True)
    
    # 분류층 변경 (9개 클래스)
    num_ftrs = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)

    # 🔥 [핵심] 가중치 계산 및 적용
    # 여기서 6만장 vs 5천장의 차이를 수학적으로 보정합니다.
    class_weights = get_class_weights(train_dataset, device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # 데이터가 많으므로 학습률 감소를 천천히 (3 Epoch 마다)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1) 

    scaler = GradScaler() 

    best_acc = 0.0

    print(f"🔥 학습 시작! (총 {EPOCHS} Epoch / 데이터 {len(train_dataset)}장)")
    start_time = time.time()

    for epoch in range(EPOCHS):
        print(f"\nEpoch {epoch+1}/{EPOCHS}")
        print("-" * 20)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
                dataloader = train_loader
            else:
                model.eval()
                dataloader = val_loader

            running_loss = 0.0
            running_corrects = 0
            
            # tqdm에 설명 추가
            loop = tqdm(dataloader, desc=f"{phase}")
            
            for inputs, labels in loop:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with autocast():
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                if phase == 'train':
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / len(dataloader.dataset)
            epoch_acc = running_corrects.double() / len(dataloader.dataset)

            print(f"  [{phase}] Loss: {epoch_loss:.4f} | Acc: {epoch_acc:.4f}")

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save(model.state_dict(), MODEL_SAVE_PATH)
                print(f"  ✨ 정확도 갱신! 모델 저장됨 ({best_acc:.4f})")

    time_elapsed = time.time() - start_time
    print(f"\n🏁 학습 완료! (소요 시간: {time_elapsed // 60:.0f}분 {time_elapsed % 60:.0f}초)")
    
    with open("classes.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(class_names))
    print("📝 classes.txt 생성 완료")

if __name__ == "__main__":
    train_model()
