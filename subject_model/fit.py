"""One training loop, used by the namer and the finder."""
from __future__ import annotations

import contextlib
import csv
import time
from pathlib import Path

import torch

LOG_FIELDS = ["epoch", "train_loss", "val_metric", "seconds"]


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _autocast(device, amp):
    return torch.autocast(device, dtype=torch.bfloat16) if amp else contextlib.nullcontext()


def fit(model, train_loader, val_loader, *, loss_fn, metric_fn, optimizer, scheduler, epochs, out_dir, save,
        device, amp=False) -> Path:
    """Train for `epochs`, stepping `scheduler` after every batch. After each epoch: score the validation set,
    log a row to log.csv, save last.pt, and save best.pt when the score is the best so far. Returns best.pt."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.csv"
    with open(log_path, "w", newline="") as f:
        csv.DictWriter(f, LOG_FIELDS).writeheader()
    model.to(device)
    best = None
    for epoch in range(1, epochs + 1):
        start = time.monotonic()
        model.train()
        loss_sum, seen = torch.zeros((), device=device), 0
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with _autocast(device, amp):
                loss = loss_fn(model(x), y)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            scheduler.step()
            loss_sum += loss.detach().float() * len(x)
            seen += len(x)

        model.eval()
        metric_sum, scored = 0.0, 0
        with torch.inference_mode(), _autocast(device, amp):
            for x, y in val_loader:
                x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
                metric_sum += metric_fn(model(x).float(), y) * len(x)
                scored += len(x)
        val_metric = metric_sum / max(1, scored)

        row = {"epoch": epoch, "train_loss": round(float(loss_sum) / max(1, seen), 5),
               "val_metric": round(val_metric, 5), "seconds": round(time.monotonic() - start, 1)}
        with open(log_path, "a", newline="") as f:
            csv.DictWriter(f, LOG_FIELDS).writerow(row)
        print(",".join(str(row[k]) for k in LOG_FIELDS), flush=True)
        save(out_dir / "last.pt", epoch, val_metric)
        if best is None or val_metric > best:
            best = val_metric
            save(out_dir / "best.pt", epoch, val_metric)
    return out_dir / "best.pt"
