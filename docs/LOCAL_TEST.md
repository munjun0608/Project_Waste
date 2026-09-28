# 배포 환경과 비슷한 조건으로 로컬에서 확인하기

Render 무료 인스턴스는 15분 동안 요청이 없으면 슬립에 들어가고, 깨어날 때 1분 가까이 걸린다.
아래 방법으로 로컬에서 같은 조건을 재현해 확인한다.

## 1. 가장 가까운 방법: Docker로 사양 제한 걸고 실행

Render와 같은 Linux 환경에서, 메모리 512MB·CPU 0.1개 제한을 걸고 실행한다.
Windows/Mac은 Docker Desktop을 설치한다.

```bash
docker build -t waste-api .
docker run --rm -p 8000:8000 --memory=512m --memory-swap=512m --cpus=0.1 waste-api
```

- `--memory-swap`을 같은 값으로 주어야 스왑 없이 512MB에서 막힌다 (Render와 동일).
- 메모리 사용량 확인: 다른 터미널에서 `docker stats`
- 메모리 초과로 죽으면 `docker run`이 종료 코드 137로 끝난다.

## 2. Docker 없이 빠르게: 가상환경에서 실행

사양 제한은 없지만 코드 동작을 확인하기에는 충분하다.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   /   Mac·Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --port 8000
```

## 3. 확인할 것

```bash
# 자동 테스트 (정상 이미지, 잘못된 형식, 용량 초과, 가짜 이미지, 클래스 매핑)
pytest -q

# 응답 시간 측정 (로컬 또는 배포 서버)
python scripts/bench.py --url http://localhost:8000 --image 사진.jpg -n 5
python scripts/bench.py --url https://waste-api-6xd9.onrender.com --image 사진.jpg -n 5
```

- Swagger UI: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/health

## 4. 프론트엔드까지 연결해서 확인

프론트엔드 저장소(`0bini/my-recycling-project`)의 `js/ai/api.js`에서 주소만 바꾸면 된다.

```js
const API_BASE_URL = 'http://localhost:8000';
```

그 다음 VS Code Live Server 등으로 `main.html`을 연다. 확인이 끝나면 주소를 되돌린다.

## 5. 배포 서버 슬립 방지

- [UptimeRobot](https://uptimerobot.com) 무료 플랜에서 HTTP 모니터를 만들고
  URL `https://waste-api-6xd9.onrender.com/health`, 주기 5분으로 설정한다.
- Render 무료 플랜은 계정당 월 750시간이 제공된다. 서비스 1개를 한 달 내내 켜 두면 약 744시간이므로 한도 안에 들어간다. 무료 서비스를 여러 개 상시 가동하면 한도를 넘는다.
- `/health`는 모델까지 로드된 경우에만 200을 반환하므로 모니터링 결과로 AI 준비 상태도 알 수 있다.

## 6. 정확도 확인 (학습 데이터가 있는 PC에서)

학습 때 전처리(Resize 224×224)와 서빙 전처리(Resize 256 + CenterCrop 224)의 정확도를 비교한다.

```bash
python scripts/eval_preprocess.py --data D:\WasteProject\Final_Dataset\val
```

검증 데이터는 바운딩박스로 잘라낸 이미지라 실제 사용 환경과 다르다.
클래스별로 직접 찍은 스마트폰 사진 10장 정도를 같은 폴더 구조(`<폴더>/<클래스명>/*.jpg`)로 모아 한 번 더 측정하면 실사용 정확도에 가까운 수치를 얻을 수 있다.
