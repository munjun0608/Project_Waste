import json
import math
import os
from datetime import datetime

# 데이터 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "model_data", "cleanhouses.json")

class CleanHouseService:
    def __init__(self):
        self.cleanhouses = self._load_data()
        
        # 📌 공통 정보 설정 (모든 클린하우스에 동일하게 적용됨)
        self.COMMON_OPERATING_HOURS = "15:00 - 04:00"
        
        # 요일별 배출 가이드 (월요일 ~ 일요일)
        self.weekly_guide = {
            "Monday": ["플라스틱", "스티로폼", "비닐류"],
            "Tuesday": ["종이류", "화장지", "불연성"],
            "Wednesday": ["캔", "고철류", "유리병"],
            "Thursday": ["플라스틱", "스티로폼", "비닐류"],
            "Friday": ["종이류", "화장지", "불연성"],
            "Saturday": ["캔", "고철류", "유리병", "플라스틱"],
            "Sunday": ["스티로폼", "비닐류", "불연성"]
        }
        # 파이썬의 요일 번호(0~6)를 키값으로 변환하기 위한 리스트
        self.korean_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def _load_data(self):
        """JSON 데이터 로드"""
        if not os.path.exists(DATA_PATH):
            print("⚠️ 클린하우스 데이터 파일이 없습니다.")
            return []
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Haversine 공식을 이용한 두 좌표 간 거리 계산 (m 단위)"""
        R = 6371000 # 지구 반지름 (m)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def get_nearest_cleanhouses(self, user_lat: float, user_lng: float, limit: int = 3):
        """내 위치 주변 클린하우스 찾기 + 공통 정보 주입"""
        if not self.cleanhouses:
            return []

        # 오늘 요일 확인 및 배출 품목 가져오기
        today_idx = datetime.now().weekday() # 0(월) ~ 6(일)
        today_name = self.korean_days[today_idx]
        today_items = self.weekly_guide.get(today_name, [])

        results = []
        for house in self.cleanhouses:
            # 1. 거리 계산
            dist = self.calculate_distance(user_lat, user_lng, house['lat'], house['lng'])
            
            # 2. 정보 병합 (위치 정보 + 거리 + 공통 운영 정보)
            info = house.copy()
            info['distance'] = round(dist, 1) # 소수점 1자리까지
            info['operating_hours'] = self.COMMON_OPERATING_HOURS
            info['today_recycling'] = today_items
            
            results.append(info)

        # 3. 거리순 정렬 (가까운 순서대로)
        results.sort(key=lambda x: x['distance'])
        
        return results[:limit]
    
    def get_guide(self):
        """전체 요일별 가이드 반환"""
        return self.weekly_guide

# 전역 객체 생성 (다른 파일에서 이 변수를 가져다 씁니다)
cleanhouse_service = CleanHouseService()