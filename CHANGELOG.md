# 변경 기록

## v1.1 (2026-09) — 과제 종료 후 리팩토링

과제 제출본은 `v1.0-course-submission` 태그로 보존한다.

### 버그 수정
- 이미지가 아닌 파일을 `image/jpeg`로 보내면 200과 category `"Error"`가 반환되던 문제 → 400 반환
- 모델 로드에 실패해도 서버가 떠서 요청마다 로드를 재시도하던 문제 → 기동 시 실패, 미준비 시 503

### 성능·안정성 (측정: `docs/BENCHMARK.md`)
- JPEG 축소 디코딩과 PyTorch 스레드 1개 고정으로 스마트폰 사진 응답 3.2~4.6초 → 1.5~1.8초 (CPU 0.1개 기준)
- 메모리 최대 사용량 505~512MB → 404MB (512MB 제한 기준)
- 추론을 스레드풀에서 실행해 이벤트 루프 차단 해소. 동시 5건 요청 시 OOM 없이 모두 처리

### 구조
- 분리배출 안내 문구와 아이콘 매핑을 `app/core/guide.py`로 분리
- `classes.txt` 클래스 수와 모델 출력 수가 다르면 기동 시 실패하도록 검증 추가
- `/health` 엔드포인트 추가 (모니터링·슬립 방지용)

### 배포·개발 환경
- `requirements.txt`를 pip freeze 전체(UTF-16, 약 120개 패키지)에서 실행에 필요한 6개 패키지로 정리하고 CPU 전용 PyTorch 인덱스 지정
- `__pycache__` 제거, `.gitignore` 추가
- `Dockerfile` 추가 (로컬에서 Render 사양 재현용)
- 테스트 코드(`tests/`)와 GitHub Actions CI 추가
- 측정 스크립트 추가: `scripts/bench.py`(응답 시간), `scripts/eval_preprocess.py`(전처리 방식별 정확도)
