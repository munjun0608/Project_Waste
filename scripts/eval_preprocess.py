"""학습 때 전처리(Resize 224x224)와 서빙 전처리(Resize 256 + CenterCrop 224)의 정확도를 비교한다.

검증 데이터(ImageFolder 구조: <root>/<클래스명>/*.jpg)가 있는 PC에서 실행한다.
  python scripts/eval_preprocess.py --data D:\\WasteProject\\Final_Dataset\\val
  python scripts/eval_preprocess.py --data ./my_phone_photos --limit 0

자소서/문서에 쓸 정확도 수치는 이 스크립트 결과를 사용한다.
"""
import argparse
import os
import sys
from collections import defaultdict

import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.ai_model import WasteClassifier  # noqa: E402

NORM = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
PIPELINES = {
    "train_style  Resize(224,224)": transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), NORM]),
    "serve_style  Resize(256)+CenterCrop(224)": transforms.Compose(
        [transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(), NORM]
    ),
}


def evaluate(model, class_names, root, tf, limit, seed):
    ds = datasets.ImageFolder(root, transform=tf)
    # 폴더 이름 순서와 모델 클래스 순서를 맞춘다.
    remap = {i: class_names.index(c) for i, c in enumerate(ds.classes)}
    idx = list(range(len(ds)))
    if limit and limit < len(idx):
        g = torch.Generator().manual_seed(seed)
        idx = torch.randperm(len(idx), generator=g)[:limit].tolist()
    loader = DataLoader(Subset(ds, idx), batch_size=32, num_workers=0)
    correct, total = 0, 0
    per_cls = defaultdict(lambda: [0, 0])
    with torch.inference_mode():
        for x, y in loader:
            pred = model(x).argmax(1)
            for p, t in zip(pred.tolist(), y.tolist()):
                t = remap[t]
                per_cls[class_names[t]][1] += 1
                if p == t:
                    per_cls[class_names[t]][0] += 1
                    correct += 1
                total += 1
    return correct / total, total, per_cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=2000, help="평가할 최대 이미지 수 (0 = 전체)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    clf = WasteClassifier()
    clf.load_model()
    for name, tf in PIPELINES.items():
        acc, n, per_cls = evaluate(clf.model, clf.class_names, args.data, tf, args.limit, args.seed)
        print(f"\n{name}: 정확도 {acc * 100:.2f}% ({n}장)")
        for c in sorted(per_cls):
            ok, cnt = per_cls[c]
            print(f"   {c:<10} {ok / cnt * 100:6.2f}%  ({ok}/{cnt})")


if __name__ == "__main__":
    main()
