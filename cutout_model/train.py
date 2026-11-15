"""Train the U-Net: loss, metric, checkpoints, resume, and the command line.

    python -m cutout_model.train --duts data/datasets/duts/DUTS-TR --out data/models/run_a --epochs 40
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.utils.data import ConcatDataset, DataLoader

from cutout_model.data import CutoutDataset, find_pairs, split
from cutout_model.model import UNet
from cutout_model.prompts import INPUT_SIZE, MARGIN

LOG_FIELDS = ["epoch", "train_loss", "val_iou", "seconds"]


def bce_dice(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Binary cross-entropy plus (1 - Dice), Dice per example with +1 smoothing."""
    bce = F.binary_cross_entropy_with_logits(logits, target)
    prob = torch.sigmoid(logits).flatten(1)
    flat = target.flatten(1)
    dice = (2 * (prob * flat).sum(1) + 1.0) / (prob.sum(1) + flat.sum(1) + 1.0)
    return bce + (1 - dice).mean()


def mean_iou(logits: torch.Tensor, target: torch.Tensor) -> float:
    """Per-example IoU of logits > 0 against target > 0.5, 1.0 when both are empty, averaged."""
    pred = (logits > 0).flatten(1)
    truth = (target > 0.5).flatten(1)
    inter = (pred & truth).sum(1).float()
    union = (pred | truth).sum(1).float()
    iou = torch.where(union > 0, inter / union.clamp(min=1), torch.ones_like(union))
    return float(iou.mean())


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _model_state(model) -> dict:
    return {k: v.detach().cpu() for k, v in model.state_dict().items()}


def save_checkpoint(path, model, *, input_size, margin, epoch, val_iou) -> None:
    """The weights file `predict` reads: model, widths, input_size, margin, epoch, val_iou."""
    torch.save({"model": _model_state(model), "widths": [int(w) for w in model.widths],
                "input_size": int(input_size), "margin": float(margin), "epoch": int(epoch),
                "val_iou": float(val_iou)}, str(path))


def _save_last(path: Path, model, optimizer, scheduler, scaler, *, input_size, epoch, val_iou, best):
    state = {"model": _model_state(model), "widths": [int(w) for w in model.widths],
             "input_size": int(input_size), "margin": float(MARGIN), "epoch": int(epoch),
             "val_iou": float(val_iou), "optimizer": optimizer.state_dict(),
             "scheduler": scheduler.state_dict(), "best_val_iou": float(best)}
    if scaler is not None:
        state["scaler"] = scaler.state_dict()
    temporary = path.with_name(path.name + ".tmp")
    torch.save(state, str(temporary))
    os.replace(temporary, path)  # a disconnect mid-save cannot leave a broken last.pt


def _amp_dtype(device: str):
    """bf16 where the GPU has it (A100, L4); fp16 with loss scaling on a T4."""
    if device != "cuda":
        return None
    return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16


def _loader(dataset, batch, workers, shuffle, device):
    options = {"batch_size": batch, "shuffle": shuffle, "num_workers": workers, "pin_memory": device == "cuda"}
    if workers > 0:
        options.update(persistent_workers=True, prefetch_factor=4)
    return DataLoader(dataset, **options)


def _rewrite_log(log_path: Path, up_to_epoch: int) -> None:
    rows = []
    if log_path.exists():
        with open(log_path, newline="") as f:
            rows = [row for row in csv.DictReader(f) if int(row["epoch"]) <= up_to_epoch]
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _append_log(log_path: Path, row: dict) -> None:
    new = not log_path.exists()
    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def _parse(argv):
    ap = argparse.ArgumentParser(description="Train the Mirai cut-out U-Net.")
    ap.add_argument("--duts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--size", type=int, default=INPUT_SIZE)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--lr", type=float, default=0.001)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--cutouts", type=Path)
    ap.add_argument("--backgrounds", type=Path)
    ap.add_argument("--paste-share", type=float, default=0.5)
    ap.add_argument("--init", type=Path)
    return ap.parse_args(argv)


def _training_set(args, train_pairs):
    duts = CutoutDataset(train_pairs, train=True, size=args.size)
    if not (args.cutouts and args.backgrounds):
        return duts
    from cutout_model.paste import PasteDataset
    cutouts = sorted(p for p in Path(args.cutouts).rglob("*.png"))
    backgrounds = sorted(p for p in Path(args.backgrounds).rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not cutouts or not backgrounds:
        raise FileNotFoundError(f"no cut-outs in {args.cutouts} or no backgrounds in {args.backgrounds}")
    share = min(max(args.paste_share, 0.0), 0.95)
    length = max(1, round(len(duts) * share / (1 - share)))
    return ConcatDataset([duts, PasteDataset(cutouts, backgrounds, length, size=args.size)])


def main(argv=None) -> Path:
    args = _parse(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = pick_device()
    amp_dtype = _amp_dtype(device)
    if device == "cuda":
        torch.backends.cudnn.benchmark = True

    train_pairs, val_pairs = split(find_pairs(args.duts))
    train_loader = _loader(_training_set(args, train_pairs), args.batch, args.workers, True, device)
    val_loader = _loader(CutoutDataset(val_pairs, train=False, size=args.size), args.batch, args.workers, False, device)

    model = UNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    total_steps = max(1, args.epochs * len(train_loader))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps, eta_min=0.0)
    scaler = torch.amp.GradScaler("cuda") if amp_dtype == torch.float16 else None

    last_path, best_path, log_path = out / "last.pt", out / "best.pt", out / "log.csv"
    start, best = 1, -1.0
    if args.resume and last_path.exists():
        last = torch.load(str(last_path), map_location=device, weights_only=False)
        model.load_state_dict(last["model"])
        optimizer.load_state_dict(last["optimizer"])
        scheduler.load_state_dict(last["scheduler"])
        if scaler is not None and "scaler" in last:
            scaler.load_state_dict(last["scaler"])
        best, start = float(last["best_val_iou"]), int(last["epoch"]) + 1
        _rewrite_log(log_path, int(last["epoch"]))
        print(f"resuming after epoch {last['epoch']}, best val_iou {best:.4f}", flush=True)
    else:
        if args.init:
            model.load_state_dict(torch.load(str(args.init), map_location=device, weights_only=True)["model"])
        _rewrite_log(log_path, 0)
    print(f"device {device}, amp {amp_dtype}, {len(train_loader.dataset)} train, {len(val_pairs)} val", flush=True)

    for epoch in range(start, args.epochs + 1):
        began = time.perf_counter()
        model.train()
        losses = []
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=amp_dtype, enabled=amp_dtype is not None):
                logits = model(x)
            loss = bce_dice(logits.float(), y)
            if scaler is not None:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            scheduler.step()
            losses.append(float(loss.detach()))

        model.eval()
        scores, weights = [], []
        with torch.inference_mode():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                with torch.autocast("cuda", dtype=amp_dtype, enabled=amp_dtype is not None):
                    logits = model(x)
                scores.append(mean_iou(logits.float(), y))
                weights.append(len(x))
        val_iou = sum(s * w for s, w in zip(scores, weights)) / max(1, sum(weights))

        row = {"epoch": epoch, "train_loss": round(sum(losses) / max(1, len(losses)), 5),
               "val_iou": round(val_iou, 5), "seconds": round(time.perf_counter() - began, 1)}
        _append_log(log_path, row)
        print(row, flush=True)
        if val_iou > best or not best_path.exists():
            best = val_iou
            save_checkpoint(best_path, model, input_size=args.size, margin=MARGIN, epoch=epoch, val_iou=val_iou)
        _save_last(last_path, model, optimizer, scheduler, scaler, input_size=args.size,
                   epoch=epoch, val_iou=val_iou, best=best)
    return best_path


if __name__ == "__main__":
    main()
