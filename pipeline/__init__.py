"""Mirai pipeline (Owner A): PDF to page images, subject candidates and masks.

The API imports this package and calls the Contract 2 functions below.
`out_dir` is always the book folder: files go in out_dir/pages and out_dir/masks.
"""
from pipeline.ingest import rasterize

__all__ = ["rasterize"]
