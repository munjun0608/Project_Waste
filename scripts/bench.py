"""배포 서버 또는 로컬 서버의 응답 시간을 측정한다.

사용 예)
  python scripts/bench.py --url http://localhost:8000 --image sample.jpg
  python scripts/bench.py --url https://waste-api-6xd9.onrender.com --image sample.jpg -n 10

첫 요청(콜드 스타트 포함)과 이후 요청을 나눠서 출력한다.
"""
import argparse
import mimetypes
import statistics
import time

import httpx


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--image", required=True)
    p.add_argument("-n", type=int, default=5, help="예측 요청 횟수")
    args = p.parse_args()

    mime = mimetypes.guess_type(args.image)[0] or "image/jpeg"
    data = open(args.image, "rb").read()

    with httpx.Client(timeout=180) as client:
        t = time.perf_counter()
        r = client.get(f"{args.url}/health")
        print(f"[health] {r.status_code} {time.perf_counter() - t:.2f}s (슬립 상태였다면 콜드 스타트 포함)")

        times = []
        for i in range(args.n):
            t = time.perf_counter()
            r = client.post(f"{args.url}/api/predict", files={"file": ("img", data, mime)})
            dt = time.perf_counter() - t
            times.append(dt)
            print(f"[predict {i + 1}] {r.status_code} {dt:.2f}s {r.json()}")

    warm = times[1:] or times
    print(f"\n예측 응답: 첫 요청 {times[0]:.2f}s / 이후 중앙값 {statistics.median(warm):.2f}s, 최대 {max(warm):.2f}s")


if __name__ == "__main__":
    main()
