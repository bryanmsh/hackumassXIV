"""Train the namer: a ResNet-18 from random weights on drawn images, plus `person` and `text`.

python -m subject_model.namer_train --roots DIR [DIR ...] --out DIR [--epochs 30] [--batch 256] [--size 160]
    [--workers 12] [--lr 0.2] [--device cuda|mps|cpu]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torchvision
from torch.utils.data import DataLoader

from subject_model.fit import fit, pick_device
from subject_model.namer_data import INPUT_SIZE, NamerDataset, find_images, split


def build_model(num_classes) -> torch.nn.Module:
    return torchvision.models.resnet18(weights=None, num_classes=num_classes)


def top1(logits, target) -> float:
    return float((logits.argmax(1) == target).float().mean())


def save_namer(path, model, *, classes, input_size, epoch, val_top1) -> None:
    """The weights file `namer.name` reads: model, classes, input_size, epoch, val_top1."""
    torch.save({"model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                "classes": list(classes), "input_size": int(input_size), "epoch": int(epoch),
                "val_top1": float(val_top1)}, str(path))


def watch(model, batches, classes, device, names=("person", "text")) -> dict:
    """For each watched class: how many of its examples were named right, and how many others were given its name."""
    watched = {name: classes.index(name) for name in names if name in classes}
    counts = {name: {"right": 0, "of": 0, "false_alarms": 0, "others": 0} for name in watched}
    model.eval()
    with torch.inference_mode():
        for x, y in batches:
            predicted = model(x.to(device)).argmax(1).cpu()
            for name, index in watched.items():
                mine = y == index
                counts[name]["of"] += int(mine.sum())
                counts[name]["right"] += int((mine & (predicted == index)).sum())
                counts[name]["others"] += int((~mine).sum())
                counts[name]["false_alarms"] += int((~mine & (predicted == index)).sum())
    return counts


def _parse(argv):
    parser = argparse.ArgumentParser(description="Train the namer.")
    parser.add_argument("--roots", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--size", type=int, default=INPUT_SIZE)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--lr", type=float, default=0.2)
    parser.add_argument("--device", default=None)
    return parser.parse_args(argv)


def main(argv=None) -> Path:
    args = _parse(argv)
    device = args.device or pick_device()
    items, classes = find_images(args.roots)
    train_items, val_items = split(items)
    if len(train_items) < args.batch:
        raise ValueError(f"{len(train_items)} training images is fewer than one batch of {args.batch}")
    print(f"{len(classes)} classes, {len(train_items)} training and {len(val_items)} validation images, "
          f"device {device}", flush=True)

    loader_args = dict(batch_size=args.batch, num_workers=args.workers, persistent_workers=args.workers > 0,
                       pin_memory=device == "cuda")
    train_loader = DataLoader(NamerDataset(train_items, train=True, size=args.size), shuffle=True,
                              drop_last=True, **loader_args)
    val_loader = DataLoader(NamerDataset(val_items, train=False, size=args.size), shuffle=False, **loader_args)

    model = build_model(len(classes))
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, nesterov=True, weight_decay=5e-5)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=args.lr,
                                                    total_steps=args.epochs * len(train_loader))
    loss = torch.nn.CrossEntropyLoss(label_smoothing=0.1)

    def save(path, epoch, val_metric):
        save_namer(path, model, classes=classes, input_size=args.size, epoch=epoch, val_top1=val_metric)

    best = fit(model, train_loader, val_loader, loss_fn=loss, metric_fn=top1, optimizer=optimizer,
               scheduler=scheduler, epochs=args.epochs, out_dir=args.out, save=save, device=device,
               amp=device == "cuda")

    counts = watch(model, val_loader, classes, device)
    for name, c in counts.items():
        print(f"{name}: {c['right']} of {c['of']} named right; {c['false_alarms']} of {c['others']} others "
              f"named {name}", flush=True)
    with open(Path(args.out) / "watch.json", "w") as f:
        json.dump(counts, f, indent=2)
    return best


if __name__ == "__main__":
    main()
