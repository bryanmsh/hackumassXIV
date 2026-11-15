import csv
import json
import math
import pytest
import torch
from subject_model import namer_train


def run(image_roots, out, *extra):
    return namer_train.main(["--roots", *map(str, image_roots), "--out", str(out), "--batch", "4",
                             "--size", "32", "--workers", "0", "--lr", "0.005", "--device", "cpu", *extra])


def test_top1():
    logits = torch.tensor([[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 1.0], [5.0, 0.0, 0.0]])
    assert namer_train.top1(logits, torch.tensor([0, 1, 2, 1])) == 0.75


def test_build_model_is_an_untrained_resnet18():
    model = namer_train.build_model(7)
    assert model.fc.out_features == 7
    assert 11_000_000 < sum(p.numel() for p in model.parameters()) < 12_000_000


def test_watch_counts_right_answers_and_false_alarms():
    class AlwaysPerson(torch.nn.Module):
        def forward(self, x):
            out = torch.zeros(len(x), 3)
            out[:, 2] = 1.0
            return out
    batches = [(torch.zeros(4, 3, 8, 8), torch.tensor([0, 1, 2, 2]))]
    assert namer_train.watch(AlwaysPerson(), batches, ["cat", "dog", "person"], "cpu") == {
        "person": {"right": 2, "of": 2, "false_alarms": 2, "others": 2}}


def test_main_trains_and_writes_checkpoint_log_and_watch(image_roots, tmp_path):
    torch.manual_seed(0)
    out = tmp_path / "run"
    best = run(image_roots, out, "--epochs", "4")
    assert best == out / "best.pt" and best.exists() and (out / "last.pt").exists()
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "classes", "input_size", "epoch", "val_top1"}
    assert saved["classes"] == ["cat", "dog", "person", "sea turtle"] and saved["input_size"] == 32
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]
    assert all(math.isfinite(float(row["train_loss"])) for row in rows)
    assert set(json.load(open(out / "watch.json"))["person"]) == {"right", "of", "false_alarms", "others"}


def test_a_training_set_smaller_than_one_batch_is_refused(image_roots, tmp_path):
    with pytest.raises(ValueError, match="13"):                       # 13 training images, batch 64
        run(image_roots, tmp_path / "run", "--epochs", "1", "--batch", "64")
