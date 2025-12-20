import os
import shutil
import random
from tqdm import tqdm

# =========================================================
# [설정 영역]
# =========================================================
SOURCE_ROOT = r"D:\WasteProject\dataset_cropped"
DEST_ROOT = r"D:\WasteProject\Final_Dataset"

# 폴더 매핑
CLASS_MAPPING = {
    "Can": ["맥주캔", "음료수캔", "커피캔", "통조림캔", "스팸류", "참기름캔"],
    "Glass": ["소주병", "맥주병", "박카스병", "음료수병", "기타술병", "유리병"],
    "Paper": ["신문지", "상자류", "책자", "종이봉투", "신발상자", "포장상자", "노트", "음료수곽", "우유팩", "두유팩", "멸균팩"],
    "Plastic": ["대용량플라스틱통", "밀폐용기", "바구니", "욕실용품", "일회용음료수잔", "주방용기", "장난감", "포장용기"],
    "PET": ["페트병", "물병"],
    "Styrofoam": ["스티로폼", "네모트레이", "보호재"],
    "Vinyl": ["과자봉지", "봉투", "리필용기", "에어캡", "포장제"],
    "Scrap": ["고철", "프라이팬", "주전자", "철옷걸이", "전기프라이팬", "비철금속", "기타", "공구류", "나사", "못", "스프레이", "부탄가스"],
    
    # [중요] dataset_cropped 안에 'General'과 'Food' 폴더를 찾아서 매핑합니다.
    "General": ["General", "휴지", "담배꽁초", "Miscellaneous"], 
    "Food": ["Food", "음식물", "Food_Waste", "biological"] 
}

SPLIT_RATIO = 0.8
# =========================================================

def create_folder(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def main():
    print(f"🚀 [용량 절약 모드] 데이터셋 이동을 시작합니다!")
    
    train_dir = os.path.join(DEST_ROOT, "train")
    val_dir = os.path.join(DEST_ROOT, "val")
    create_folder(train_dir)
    create_folder(val_dir)

    total_moved = 0

    for target_class, source_folders in CLASS_MAPPING.items():
        print(f"\n📂 '{target_class}' 처리 중...")
        
        target_train_dir = os.path.join(train_dir, target_class)
        target_val_dir = os.path.join(val_dir, target_class)
        create_folder(target_train_dir)
        create_folder(target_val_dir)

        all_files = []
        
        # 하위 폴더까지 싹 뒤져서 파일 찾기
        for folder_name in source_folders:
            source_path = os.path.join(SOURCE_ROOT, folder_name)
            if not os.path.exists(source_path): continue

            for root, dirs, files in os.walk(source_path):
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        full_path = os.path.join(root, f)
                        all_files.append(full_path)

        if len(all_files) == 0:
            print(f"  ⚠️ '{target_class}' 데이터 0장 (확인 필요)")
            continue

        random.shuffle(all_files)
        split_point = int(len(all_files) * SPLIT_RATIO)
        train_files = all_files[:split_point]
        val_files = all_files[split_point:]

        print(f"  ✅ {len(all_files)}장 발견 -> Train: {len(train_files)} / Val: {len(val_files)}")

        # [핵심] shutil.copy 대신 shutil.move 사용 (용량 부족 해결)
        for file_path in tqdm(train_files, desc=f"  Train 이동"):
            filename = os.path.basename(file_path)
            # 파일명 중복 방지 난수 추가
            new_filename = f"{target_class}_{random.randint(10000,99999)}_{filename}"
            try:
                shutil.move(file_path, os.path.join(target_train_dir, new_filename))
            except: pass 
            
        for file_path in tqdm(val_files, desc=f"  Val 이동"):
            filename = os.path.basename(file_path)
            new_filename = f"{target_class}_{random.randint(10000,99999)}_{filename}"
            try:
                shutil.move(file_path, os.path.join(target_val_dir, new_filename))
            except: pass

        total_moved += len(all_files)

    print("\n🎉 용량 문제 없이 데이터셋 구축 완료!")
    print(f"저장 위치: {DEST_ROOT}")

if __name__ == "__main__":
    main()
