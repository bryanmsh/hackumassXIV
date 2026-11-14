"""Mirai pipeline (Owner A): PDF to page images, subject candidates and masks.

The API imports this package and calls the Contract 2 functions below.
`out_dir` is always the book folder: files go in out_dir/pages and out_dir/masks.
"""
from pipeline.click import refine_mask, segment_at_point
from pipeline.ingest import rasterize
from pipeline.outline import mask_from_outline
from pipeline.process import process_page

__all__ = ["rasterize", "process_page", "segment_at_point", "mask_from_outline", "refine_mask"]
