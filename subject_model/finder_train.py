"""Train the finder for whole pages: the cut-out model's U-Net, shown whole photos with every labelled object marked.

python -m subject_model.finder_train --duts DIR --out DIR [--epochs 40] [--batch 64] [--size 320]
    [--widths 32 64 128 256 512] [--workers 8] [--lr 0.001] [--device cuda|mps|cpu]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader

from cutout_model.data import find_pairs, read_grey, read_rgb, split
from cutout_model.model import UNet
from cutout_model.prompts import build_input
from cutout_model.train import bce_dice, mean_iou, save_checkpoint
from subject_model.fit import fit, pick_device
from subject_model.text_images import draw_lines, find_fonts

PAGE_SHARE = 0.3  # the share of training photos put on paper, with words drawn on them
PAPER_MIN = 225


def on_paper(image: np.ndarray, mask: np.ndarray, rng) -> tuple[np.ndarray, np.ndarray]:
    """The photo shrunk onto a light plain canvas of its own size, leaving a margin of 10% to 35% of the canvas
    on one side, or on one side and the top or bottom; the bool mask moved the same way."""
    height, width = mask.shape
    margin_x = round(rng.uniform(0.10, 0.35) * width)
    margin_y = round(rng.uniform(0.10, 0.35) * height) if rng.random() < 0.5 else 0
    x0 = margin_x if rng.random() < 0.5 else 0
    y0 = margin_y if rng.random() < 0.5 else 0
    inner_w, inner_h = width - margin_x, height - margin_y
    paper = np.empty_like(image)
    paper[:] = rng.integers(PAPER_MIN, 256, 3).astype(np.uint8)
    paper[y0:y0 + inner_h, x0:x0 + inner_w] = cv2.resize(image, (inner_w, inner_h), interpolation=cv2.INTER_AREA)
    moved = np.zeros_like(mask, dtype=bool)
    moved[y0:y0 + inner_h, x0:x0 + inner_w] = cv2.resize(mask.astype(np.uint8), (inner_w, inner_h),
                                                         interpolation=cv2.INTER_NEAREST) > 0
    return paper, moved


class WholeImageDataset(torch.utils.data.Dataset):
    """(input (4, size, size), target (1, size, size)): the whole photo, its box the whole image, every object marked."""

    def __init__(self, pairs, train, size=320, fonts=()):
        self.pairs, self.train, self.size, self.fonts = list(pairs), train, size, list(fonts)
        self._rng = None

    def __len__(self):
        return len(self.pairs)

    def _augment(self, image, mask, rng):
        height, width = mask.shape
        crop_h, crop_w = round(rng.uniform(0.7, 1.0) * height), round(rng.uniform(0.7, 1.0) * width)
        y0, x0 = int(rng.integers(0, height - crop_h + 1)), int(rng.integers(0, width - crop_w + 1))
        image, mask = image[y0:y0 + crop_h, x0:x0 + crop_w], mask[y0:y0 + crop_h, x0:x0 + crop_w]
        if rng.random() < 0.5:
            image, mask = image[:, ::-1], mask[:, ::-1]
        out = image.astype(np.float32)
        mean = out.mean()
        out = ((out - mean) * rng.uniform(0.7, 1.3) + mean) * rng.uniform(0.7, 1.3)
        image = np.clip(out, 0, 255).astype(np.uint8)
        mask = np.ascontiguousarray(mask)
        if rng.random() < PAGE_SHARE:
            image, mask = on_paper(image, mask, rng)
            image = draw_lines(image, rng, self.fonts)
        return image, mask

    def __getitem__(self, index):
        photo_path, mask_path = self.pairs[index]
        image, grey = read_rgb(photo_path), read_grey(mask_path)
        height, width = image.shape[:2]
        if grey.shape != (height, width):
            grey = cv2.resize(grey, (width, height), interpolation=cv2.INTER_NEAREST)
        mask = grey > 127
        if self.train:
            if self._rng is None:
                self._rng = np.random.default_rng()
            image, mask = self._augment(image, mask, self._rng)
            height, width = mask.shape
        x, _ = build_input(np.ascontiguousarray(image), (0, 0, width, height), margin=0.0, size=self.size)
        target = cv2.resize(mask.astype(np.uint8), (self.size, self.size), interpolation=cv2.INTER_NEAREST)
        return torch.from_numpy(x), torch.from_numpy(target.astype(np.float32)[None])


def _parse(argv):
    parser = argparse.ArgumentParser(description="Train the whole-page finder.")
    parser.add_argument("--duts", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--widths", type=int, nargs="+", default=[32, 64, 128, 256, 512])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--device", default=None)
    return parser.parse_args(argv)


def main(argv=None) -> Path:
    args = _parse(argv)
    device = args.device or pick_device()
    train_pairs, val_pairs = split(find_pairs(args.duts))
    fonts = find_fonts()
    print(f"{len(train_pairs)} training and {len(val_pairs)} validation photos, {len(fonts)} fonts, "
          f"device {device}", flush=True)

    loader_args = dict(batch_size=args.batch, num_workers=args.workers, persistent_workers=args.workers > 0,
                       pin_memory=device == "cuda")
    train_loader = DataLoader(WholeImageDataset(train_pairs, train=True, size=args.size, fonts=fonts),
                              shuffle=True, drop_last=True, **loader_args)
    val_loader = DataLoader(WholeImageDataset(val_pairs, train=False, size=args.size), shuffle=False, **loader_args)

    model = UNet(widths=tuple(args.widths))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs * len(train_loader),
                                                           eta_min=0.0)

    def save(path, epoch, val_metric):
        save_checkpoint(path, model, input_size=args.size, margin=0.0, epoch=epoch, val_iou=val_metric)

    return fit(model, train_loader, val_loader, loss_fn=bce_dice, metric_fn=mean_iou, optimizer=optimizer,
               scheduler=scheduler, epochs=args.epochs, out_dir=args.out, save=save, device=device,
               amp=device == "cuda")


if __name__ == "__main__":
    main()
