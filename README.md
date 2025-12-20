📄 프로젝트 리스크 관리 및 문제 해결 보고서 (Backend)

1. 개요

'버릴까 말까? (AI 분리배출 가이드)' 프로젝트의 백엔드 개발 과정에서 발생한 주요 기술적 리스크와 이슈 사항을 정의하고, 이를 어떻게 해결하였는지에 대한 과정을 기술합니다.

2. 주요 리스크 및 해결 과정 (Risk & Resolution Log)

🔴 Risk 01. 모델 로딩 경로 및 파일 의존성 오류
문제 상황 (Issue): 서버 배포 및 실행 환경에 따라 classes.txt 및 .pth(모델 가중치) 파일을 찾지 못하는 FileNotFoundError 발생.

- Windows 환경 특성상 확장자 중복 문제(classes.txt.txt)로 인한 파일 로딩 실패.

- 학습된 모델의 클래스 인덱스와 서버의 클래스 리스트 순서가 불일치할 잠재적 위험 존재.

해결 방안 (Action)

- 동적 경로 할당: os.path.abspath와 os.path.dirname을 활용하여 프로젝트 루트(BASE_DIR)를 동적으로 계산, 실행 위치와 관계없이 model_data 폴더를 정확히 참조하도록 코드 수정.

- 하드코딩 전환: 외부 파일(classes.txt) 의존성을 제거하고, 소스 코드 내에 클래스 리스트(self.class_names)를 고정(Hard-coding)하여 파일 입출력 에러를 원천 차단.

개선 결과 (Result):

- 서버 구동 안정성 100% 확보 (경로 에러 완전 해결).

- 학습 데이터와 추론 단계의 클래스 순서 불일치 리스크 제거.

🔴 Risk 02. AI 모델과 클라이언트(FE) 간 데이터 구조 불일치
문제 상황 (Issue): AI 모델은 10가지 세부 클래스(Scrap, PET, Food 등)를 분류하지만, 프론트엔드 UI는 8가지 카테고리만 지원.

- "Food(음식물)" 등 특정 클래스가 프론트엔드 로직(wasteTypes)에 정의되지 않아, AI가 정답을 맞춰도 화면에는 '일반쓰레기(Default)' 아이콘이 출력됨.

해결 방안 (Action):

- 매핑 레이어 도입: 백엔드에서 10가지 AI 클래스를 8가지 UI 카테고리로 변환하는 매핑 로직(icon_mapping) 구현 (예: Scrap → Can, PET → Plastic).

- API 스키마 확장: 프론트엔드 코드 수정을 최소화하기 위해, API 응답 스키마에 프론트엔드 로직이 요구하는 type 필드(한글명)를 추가하여 전송.

개선 결과 (Result):

- 프론트엔드 대규모 수정 없이 아이콘 및 텍스트 출력 오류 해결.

- 사용자에게 디자인 시안과 동일한 UI 경험 제공 성공.

🔴 Risk 03. 실사용 환경에서의 정확도 저하 (Generalization Gap)
문제 상황 (Issue): 학습 데이터는 정사각형으로 크롭된 이미지였으나, 사용자가 스마트폰으로 촬영한 원본 이미지는 세로로 긴 직사각형 비율임.

- 기존 전처리(Resize(224, 224)) 적용 시, 이미지가 강제로 찌그러져(Squashing) 원형 물체(병, 캔)의 형태가 왜곡되어 오분류 발생.

- 복잡한 배경(책상 위 잡동사니 등)이 노이즈로 작용하여 주 피사체 인식을 방해함.

해결 방안 (Action):

- 전처리 파이프라인 고도화: 단순 리사이즈 방식을 폐기하고, Resize(256) + CenterCrop(224) 방식 도입.

- 이미지 비율(Aspect Ratio)을 유지하면서 크기를 줄이고, 이미지의 정중앙(Center)만 잘라내어 배경 노이즈를 제거하고 물체 왜곡을 방지함.

개선 결과 (Result):

- 형태 왜곡으로 인한 캔/유리병 혼동 문제 해결.

- 실생활 배경(책상, 손에 든 상태)에서의 인식률 대폭 향상 (체감 정확도 상승).

🔴 Risk 04. 배포 환경 불일치로 인한 빌드 실패 (Environment Consistency)
문제 상황 (Issue): 로컬 개발 환경(Windows)과 배포 서버 환경(Linux/Render)의 OS 차이로 인해, 의존성 패키지 설치 중 호환성 에러(Could not find a version that satisfies the requirement pywin32) 발생. 이로 인한 CI/CD 파이프라인 중단.

해결 방안(Action):

- pip freeze로 추출된 라이브러리 목록 중 pywin32 등 Windows 전용 시스템 라이브러리를 식별하여 제거.

- 배포에 필수적인 핵심 라이브러리(fastapi, tensorflow, uvicorn, pillow 등)만을 명시한 경량화된 requirements.txt 재작성.

개선 결과(Result): Linux 기반의 클라우드 서버에서 빌드 성공률 100% 달성. 불필요한 라이브러리 제거로 컨테이너 이미지 크기 감소.

향후 계획(Future Plan): Docker를 도입하여 개발 단계부터 배포 단계까지 OS에 구애받지 않는 동일한 컨테이너 환경 구축 예정.

🔴 Risk 05. AI 모델 로딩 지연 및 콜드 스타트 (Latency & Cold Start)
문제 상황 (Issue): 무료 PaaS(Render) 특성상 유휴(Idle) 상태 전환 시 서버가 슬립 모드로 진입하며, 재구동 시 거대 AI 모델(tensorflow)을 메모리에 로드하는 과정에서 첫 요청 응답 속도가 30~60초 이상 지연되는 현상 발생.

해결 방안(Action):

- FastAPI Lifespan(수명주기) 매니저 도입: 요청이 들어올 때마다 모델을 로드하는 것이 아니라, 서버 부팅 시점에 단 한 번만 모델을 로드하여 메모리에 상주시키는 Singleton 패턴 적용.

- Pre-warming 전략: 시연 및 테스트 전 헬스 체크(Health Check) API를 호출하여 서버를 미리 활성화 상태(Active)로 전환.

개선 결과(Result): 서버 활성화 이후 추론(Inference) 요청 시 모델 로딩 시간이 제거되어 즉각적인 응답(Latency < 1s) 가능.

향후 계획(Future Plan): UptimeRobot 등을 활용한 주기적 핑(Ping) 전송으로 상시 활성 상태 유지 또는 Serverless Architecture로 전환하여 트래픽에 따른 오토스케일링 구현.

🔴 Risk 06. 제한된 서버 리소스와 메모리 부족 (Resource Optimization)
문제 상황 (Issue): 무료 인스턴스의 메모리 제한(512MB RAM) 상황에서 무거운 딥러닝 모델 구동 시 OOM(Out of Memory) 에러 및 프로세스 강제 종료(Kill) 위험 존재.

해결 방안(Action):

- 모델 경량화: ResNet 등 거대 모델 대신, 모바일/엣지 환경에 최적화된 MobileNetV3 Large 아키텍처 채택으로 메모리 점유율 최소화.

- 코드 최적화: 이미지 전처리 과정에서 메모리 누수를 방지하기 위해 BytesIO 스트림 처리 및 불필요한 객체 생성을 억제.

개선 결과(Result): 512MB의 제한된 환경에서도 안정적으로 AI 추론 서비스 구동 성공.

향후 계획(Future Plan): 모델 양자화(Quantization, INT8) 적용 또는 TensorFlow Lite(.tflite) 변환을 통해 모델 사이즈를 70% 이상 추가 감량 예정.

🔴 Risk 07. 유지보수성 저하 및 데이터 하드코딩 (Maintainability)
문제 상황 (Issue): 분리배출 가이드(팁, 카테고리 분류 등)가 변경될 때마다 프론트엔드 앱을 업데이트하고 심사를 다시 받아야 하는 비효율성 발생.

해결 방안(Action):

- Server-Driven UI 설계: 분리배출 팁, 아이콘 매핑 정보, 카테고리 텍스트 등을 백엔드에서 관리하고 API 응답에 포함하여 전송.

- 데이터 구조화: WasteClassifier 클래스와 응답 스키마(Pydantic)를 분리하여 로직 변경이 API 인터페이스에 영향을 주지 않도록 설계.

개선 결과(Result): 정책 변경 시 서버 코드 수정만으로 모든 클라이언트(App/Web)에 즉시 변경 사항 반영 가능.

향후 계획(Future Plan): 데이터베이스(DB)를 연동하여 코드 수정 없이 관리자 페이지(Admin)에서 실시간으로 분리배출 정보를 업데이트할 수 있는 CMS(Content Management System) 구축.

3. 향후 개선 계획 (Future Improvements)

1) 신뢰도 임계값(Confidence Threshold) 적용
계획: AI 예측 확률(Confidence Score)이 특정 수치(예: 60%) 미만일 경우, 억지로 분류하지 않고 "판독 불가(Unknown)" 또는 "재촬영 요청" 응답을 보내도록 로직 개선.

기대 효과: 낮은 확률로 틀린 정보를 제공하는 것보다, 모른다고 답변하여 AI 신뢰성 확보.

2) 사용자 행동 유도 (UX Writing)
계획: 기술적으로 해결하기 힘든 과도한 배경 노이즈나 빛 반사 문제를 해결하기 위해, 촬영 화면에 가이드 문구 추가.

"물체를 화면 중앙에 꽉 차게 찍어주세요"

"배경이 단순한 곳에서 찍으면 정확해요"

기대 효과: 양질의 입력 이미지를 유도하여 전체적인 서비스 정확도 향상.

3) 앙상블 기법 및 TenCrop 도입 검토
계획: 단일 이미지 추론(CenterCrop)의 한계를 보완하기 위해, 이미지를 10개 영역(네 귀퉁이+중앙+반전)으로 잘라 추론한 뒤 평균을 내는 TenCrop 전처리 방식 도입 테스트.

기대 효과: 물체가 중앙에 있지 않거나 손에 가려진 경우에도 인식률 방어 가능. (단, 추론 속도와의 트레이드오프 고려 필요)
