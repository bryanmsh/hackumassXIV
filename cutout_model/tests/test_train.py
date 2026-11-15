import csv

import torch
from cutout_model import train


def test_bce_dice_is_low_when_right_and_high_when_wrong():
    target = torch.zeros(1, 1, 8, 8)
    target[..., 2:6, 2:6] = 1.0
    right = (target * 2 - 1) * 20.0
    assert float(train.bce_dice(right, target)) < 0.01
    assert float(train.bce_dice(-right, target)) > 1.0


def test_mean_iou():
    target = torch.zeros(2, 1, 4, 4)
    target[:, :, :2, :] = 1.0
    logits = torch.full((2, 1, 4, 4), -5.0)
    logits[0, :, :2, :] = 5.0          # first: exact, IoU 1.0
    logits[1, :, :1, :] = 5.0          # second: half of it, IoU 0.5
    assert abs(train.mean_iou(logits, target) - 0.75) < 1e-6


def test_main_trains_and_writes_checkpoint_and_log(duts_root, tmp_path):
    out = tmp_path / "run"
    best = train.main(["--duts", str(duts_root), "--out", str(out), "--epochs", "6",
                       "--batch", "4", "--size", "64", "--workers", "0"])
    assert best == out / "best.pt" and best.exists() and (out / "last.pt").exists()
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "widths", "input_size", "margin", "epoch", "val_iou"}
    assert saved["input_size"] == 64 and saved["widths"] == [32, 64, 128, 256, 512]
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4", "5", "6"]
    assert set(rows[0]) == {"epoch", "train_loss", "val_iou", "seconds"}
    assert float(rows[-1]["train_loss"]) < float(rows[0]["train_loss"])


def test_resume_continues_after_a_disconnect(duts_root, tmp_path):
    out = tmp_path / "run"
    args = ["--duts", str(duts_root), "--out", str(out), "--batch", "4", "--size", "64", "--workers", "0"]
    train.main(args + ["--epochs", "4"])
    cut = list(csv.DictReader(open(out / "log.csv")))[:2]          # pretend it died after epoch 2
    with open(out / "log.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cut[0]))
        writer.writeheader()
        writer.writerows(cut)
    last = torch.load(out / "last.pt", map_location="cpu", weights_only=False)
    last["epoch"] = 2
    torch.save(last, out / "last.pt")
    train.main(args + ["--epochs", "4", "--resume"])
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]


def test_resume_without_last_checkpoint_starts_fresh(duts_root, tmp_path):
    out = tmp_path / "fresh"
    train.main(["--duts", str(duts_root), "--out", str(out), "--epochs", "1", "--batch", "4",
                "--size", "64", "--workers", "0", "--resume"])
    assert [row["epoch"] for row in csv.DictReader(open(out / "log.csv"))] == ["1"]


def test_main_mixes_pasted_examples_and_starts_from_a_checkpoint(duts_root, art, tmp_path):
    fg, bg = art
    first = train.main(["--duts", str(duts_root), "--out", str(tmp_path / "a"), "--epochs", "1",
                        "--batch", "4", "--size", "64", "--workers", "0"])
    best = train.main(["--duts", str(duts_root), "--out", str(tmp_path / "b"), "--epochs", "1",
                       "--batch", "4", "--size", "64", "--workers", "0",
                       "--cutouts", str(fg), "--backgrounds", str(bg), "--init", str(first)])
    assert best.exists()
