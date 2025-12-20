import json
import os
import cv2
import numpy as np
from tqdm import tqdm

# =========================================================
# [사용자 경로 설정]
# =========================================================

# 1. 원천데이터(이미지) 폴더
IMAGE_ROOT = r"D:\WasteProject\085.생활_폐기물_이미지\01.데이터\1.Training\원천데이터"

# 2. 라벨링데이터(JSON) 폴더 (경로가 정확한지 확인하세요!)
# (주의: 폴더명 뒤에 .zip이 붙어있는 경우 그대로 적어줘야 합니다)
LABEL_ROOT = r"D:\WasteProject\085.생활_폐기물_이미지\01.데이터\1.Training\라벨링데이터"

# 3. 결과 저장 폴더
OUTPUT_ROOT = r"D:\WasteProject\dataset_cropped"

# =========================================================

def create_folder(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def imread_korean(path):
    try:
        stream = open(path.encode("utf-8"), "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        return cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    except Exception:
        return None

def imwrite_korean(filename, img, params=None):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img, params)
        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        return False
    except Exception:
        return False

def process_data():
    create_folder(OUTPUT_ROOT)

    # 1. 이미지 위치 지도 만들기
    print("🔍 이미지 파일 위치 스캔 중... (잠시만 기다려주세요)")
    image_map = {}
    for root, dirs, files in os.walk(IMAGE_ROOT):
        for file in files:
            # 대소문자 구분 없이 jpg, png 찾기
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_map[file] = os.path.join(root, file)
    
    print(f"✅ 이미지 {len(image_map)}장 발견!")

    # 2. JSON 파일 찾기 (대문자 .Json 대응 수정)
    json_files = []
    print("🔍 라벨 파일 찾는 중...")
    for root, dirs, files in os.walk(LABEL_ROOT):
        for file in files:
            # [.lower()] 함수로 대소문자 무시하고 json 찾기
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))

    if len(json_files) == 0:
        print("❌ 여전히 파일을 못 찾았습니다. LABEL_ROOT 경로를 다시 확인해주세요!")
        return

    print(f"🚀 라벨 {len(json_files)}개 처리 시작!")

    success_count = 0
    fail_count = 0

    for json_path in tqdm(json_files):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            image_filename = data.get('FILE NAME')
            if not image_filename: continue

            # 지도에서 이미지 위치 찾기
            image_full_path = image_map.get(image_filename)
            if not image_full_path:
                fail_count += 1
                continue
            
            img = imread_korean(image_full_path)
            if img is None: continue
            
            h_img, w_img, _ = img.shape

            objects = data.get('Bounding', [])
            for idx, obj in enumerate(objects):
                detail_class = obj.get('DETAILS', 'Unknown')
                
                try:
                    x1, y1 = int(obj['x1']), int(obj['y1'])
                    x2, y2 = int(obj['x2']), int(obj['y2'])
                except: continue

                x1 = max(0, x1); y1 = max(0, y1)
                x2 = min(w_img, x2); y2 = min(h_img, y2)

                if x2 <= x1 or y2 <= y1: continue

                cropped_img = img[y1:y2, x1:x2]
                
                if cropped_img.shape[0] < 30 or cropped_img.shape[1] < 30: continue

                save_dir = os.path.join(OUTPUT_ROOT, detail_class)
                create_folder(save_dir)
                
                save_name = f"{os.path.splitext(image_filename)[0]}_{idx}.jpg"
                save_full_path = os.path.join(save_dir, save_name)
                
                imwrite_korean(save_full_path, cropped_img)
                success_count += 1

        except Exception:
            continue

    print(f"\n🎉 작업 끝! 성공: {success_count}장")
    print(f"저장 위치: {OUTPUT_ROOT}")

if __name__ == "__main__":
    process_data()
