"""PyTorch segmenters: SAM 2.1 small and EdgeTAM, both through Hugging Face transformers.

This is the only file in the project that imports torch, and it does so lazily, so the
rest of the pipeline (and the `stub` and `grabcut` segmenters) runs without torch installed.

How it stays fast on a 4-vCPU box:
- Each model is loaded once per process (lazy singleton) and kept.
- The image encoder, the expensive part, runs once per page. Its output is cached by the
  page's pixel hash, so the up-to-5 subject boxes on a page, and later clicks on the same
  page, only run the cheap prompt decoder.
- One lock guards the model: up to PAGE_CONCURRENCY threads call in, and torch already
  spreads one call across all cores, so running them one at a time is faster than fighting.

Weights download from Hugging Face on first use into MODEL_CACHE_DIR (default
$DATA_DIR/models, which is the mounted data/ folder in Docker, so they survive rebuilds).
They are never committed. `python -m pipeline.sam --fetch` downloads them ahead of time.
"""
import hashlib
import os
import threading
import time
from collections import OrderedDict

import numpy as np

MODEL_IDS = {
    "sam2": "facebook/sam2.1-hiera-small",  # Meta, Apache-2.0
    "edgetam": "yonigozlan/EdgeTAM-hf",  # EdgeTAM (successor to EdgeSAM), Apache-2.0
}
EMBEDDING_CACHE_SIZE = 8  # pages; each SAM 2 small embedding is a few MB

_lock = threading.Lock()
_models: dict[str, tuple] = {}  # name -> (model, processor, device)
_embeddings: "OrderedDict[tuple, tuple]" = OrderedDict()  # (name, page key) -> (embeddings, original_sizes)
_threads_set = False

# Timings of the most recent call, for logs and the trial script. Seconds.
last_timing: dict[str, float] = {}


def cache_dir() -> str:
    explicit = os.environ.get("MODEL_CACHE_DIR")
    if explicit:
        return explicit
    return os.path.join(os.environ.get("DATA_DIR") or "data", "models")


def _set_threads(torch) -> None:
    global _threads_set
    if _threads_set:
        return
    wanted = os.environ.get("TORCH_THREADS")
    torch.set_num_threads(int(wanted) if wanted else max(1, os.cpu_count() or 1))
    _threads_set = True


def _load(name: str):
    """Load one model and its processor once. Caller holds the lock."""
    if name in _models:
        return _models[name]
    started = time.perf_counter()  # includes importing torch, which is most of a cold start
    import torch
    from transformers import AutoProcessor

    if name == "sam2":
        from transformers import Sam2Model as ModelClass
    elif name == "edgetam":
        from transformers import EdgeTamModel as ModelClass
    else:
        raise ValueError(f"unknown PyTorch segmenter {name!r}")

    _set_threads(torch)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_id = MODEL_IDS[name]
    processor = AutoProcessor.from_pretrained(model_id, cache_dir=cache_dir())
    model = ModelClass.from_pretrained(model_id, cache_dir=cache_dir()).to(device).eval()
    _models[name] = (model, processor, device)
    last_timing["load"] = time.perf_counter() - started
    return _models[name]


def _page_key(image: np.ndarray) -> str:
    return hashlib.blake2b(np.ascontiguousarray(image).data, digest_size=16).hexdigest() + str(image.shape)


def _embed(name, model, processor, device, image):
    """Image embeddings for one page, from the cache when the page was seen recently."""
    import torch
    from PIL import Image

    key = (name, _page_key(image))
    if key in _embeddings:
        _embeddings.move_to_end(key)
        last_timing["encode"] = 0.0
        return _embeddings[key]
    started = time.perf_counter()
    inputs = processor(images=Image.fromarray(image), return_tensors="pt")
    with torch.inference_mode():
        embeddings = model.get_image_embeddings(inputs["pixel_values"].to(device))
    entry = (embeddings, inputs["original_sizes"])
    _embeddings[key] = entry
    while len(_embeddings) > EMBEDDING_CACHE_SIZE:
        _embeddings.popitem(last=False)
    last_timing["encode"] = time.perf_counter() - started
    return entry


MAX_CLICK_COVER = 0.60  # a click mask covering more of the page than this is background
MIN_BOX_SCORE = 0.5  # the model's own quality score; real artwork scored 0.82 to 0.97 in the trial
MAX_BOX_BORDER = 0.5  # share of the box's edge band a mask may fill before it counts as background


class LowConfidence(RuntimeError):
    """The model's answer to a box looks wrong. segment.py falls back to GrabCut."""


def box_border_cover(mask: np.ndarray, box, inset: float = 0.02) -> float:
    """Share of a thin band just inside the box edges that the mask fills.

    A subject touches its box only at a few extreme points; a mask that fills the band is
    the background inside the box (SAM does this on flat, synthetic shapes).
    """
    height, width = mask.shape
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, x1 = sorted((max(0, min(width, x0)), max(0, min(width, x1))))
    y0, y1 = sorted((max(0, min(height, y0)), max(0, min(height, y1))))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 0.0
    dx, dy = max(1, int(inset * (x1 - x0))), max(1, int(inset * (y1 - y0)))
    band = np.zeros(mask.shape, bool)
    band[y0:y1, x0:x1] = True
    band[y0 + dy:y1 - dy, x0 + dx:x1 - dx] = False
    return float((mask[band] > 0).mean())


def pick_click_mask(masks: np.ndarray) -> np.ndarray:
    """Choose among the masks a single click produced: the largest one that is not background.

    SAM returns part, sub-part and whole-object masks for one click and scores the small
    part highest, but a teacher clicking an animal means the whole animal. In the trial on
    the sample pages, the largest mask was the whole subject every time (IoU 0.90 and 0.97)
    while the top-scored one was the wing or the body only (0.22 and 0.58).
    """
    masks = np.asarray(masks).astype(bool)
    covers = masks.reshape(len(masks), -1).mean(axis=1)
    allowed = [i for i, cover in enumerate(covers) if cover <= MAX_CLICK_COVER]
    if not allowed:
        return masks[int(covers.argmin())]
    return masks[max(allowed, key=lambda i: covers[i])]


def segment(name: str, image: np.ndarray, box, points) -> np.ndarray:
    """Run SAM 2.1 small or EdgeTAM on one prompt.

    image:  RGB uint8 (height, width, 3), the master page.
    box:    (x0, y0, x1, y1) in master pixels, or None.
    points: list of (x, y, label) in master pixels; label 1 = on the subject, 0 = not.
    Returns uint8 (height, width), 255 = subject. Raw: callers clean it.
    Raises on any failure; process_page turns that into a Failed page.
    """
    import torch

    height, width = image.shape[:2]
    with _lock:
        last_timing.clear()
        model, processor, device = _load(name)
        embeddings, original_sizes = _embed(name, model, processor, device, image)

        started = time.perf_counter()
        prompt = {}
        if box is not None:
            prompt["input_boxes"] = [[[float(v) for v in box]]]
        if points:
            prompt["input_points"] = [[[[float(x), float(y)] for x, y, _ in points]]]
            prompt["input_labels"] = [[[int(label) for _, _, label in points]]]
        inputs = processor(original_sizes=original_sizes, return_tensors="pt", **prompt)
        # One lone click is ambiguous (the wing? the whole bird?), so ask for three masks.
        # A box is not ambiguous: ask for one.
        multimask = box is None and len(points) == 1
        model_inputs = {k: v.to(device) for k, v in inputs.items()
                        if k in ("input_boxes", "input_points", "input_labels")}
        with torch.inference_mode():
            outputs = model(image_embeddings=embeddings, multimask_output=multimask, **model_inputs)
        masks = processor.post_process_masks(outputs.pred_masks.cpu(), original_sizes)[0]  # (objects, k, H, W)
        chosen = pick_click_mask(masks[0].numpy()) if multimask else masks[0, 0].numpy()
        score = float(outputs.iou_scores[0, 0].max())
        last_timing["decode"] = time.perf_counter() - started
        last_timing["score"] = score

    if chosen.shape != (height, width):
        raise RuntimeError(f"segmenter returned {chosen.shape}, expected {(height, width)}")
    mask = chosen.astype(np.uint8) * 255
    if box is not None:
        # A click's whole-object mask is often scored low by the model even when right
        # (0.14 on the trial bird), so only box answers are checked.
        if score < MIN_BOX_SCORE:
            raise LowConfidence(f"{name} scored its mask {score:.2f}")
        if box_border_cover(mask, box) > MAX_BOX_BORDER:
            raise LowConfidence(f"{name} returned the background inside the box")
    return mask


def fetch(names=("sam2", "edgetam")) -> None:
    """Download weights ahead of time so the first page does not wait on the network."""
    from transformers import AutoProcessor

    for name in names:
        AutoProcessor.from_pretrained(MODEL_IDS[name], cache_dir=cache_dir())
        with _lock:
            _load(name)
        print(f"{name}: {MODEL_IDS[name]} ready in {cache_dir()} ({last_timing.get('load', 0):.1f} s load)")


if __name__ == "__main__":
    import sys

    if "--fetch" in sys.argv:
        fetch([a for a in sys.argv[1:] if not a.startswith("--")] or ("sam2", "edgetam"))
    else:
        print("usage: python -m pipeline.sam --fetch [sam2] [edgetam]")
