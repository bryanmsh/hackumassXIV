import csv
import torch
from torch.utils.data import DataLoader, TensorDataset
from subject_model.fit import fit


def test_fit_logs_every_epoch_saves_and_returns_best(tmp_path):
    torch.manual_seed(0)
    x = torch.randn(16, 3)
    loader = DataLoader(TensorDataset(x, (x.sum(1) > 0).long()), batch_size=4)
    model = torch.nn.Linear(3, 2)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=0.1, total_steps=4 * len(loader))
    saved = []

    def save(path, epoch, val_metric):
        saved.append((path.name, epoch))
        torch.save({"epoch": epoch}, path)

    best = fit(model, loader, loader, loss_fn=torch.nn.functional.cross_entropy,
               metric_fn=lambda output, target: float((output.argmax(1) == target).float().mean()),
               optimizer=optimizer, scheduler=scheduler, epochs=4, out_dir=tmp_path, save=save, device="cpu")
    assert best == tmp_path / "best.pt" and best.exists()
    assert saved[:2] == [("last.pt", 1), ("best.pt", 1)]              # the first epoch is always the best so far
    assert [name for name, _ in saved].count("last.pt") == 4
    rows = list(csv.DictReader(open(tmp_path / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]
    assert set(rows[0]) == {"epoch", "train_loss", "val_metric", "seconds"}
