"""
ShopGraph - Raw Dataset Downloader
Reproducible script to download selected Amazon Reviews '23 subsets from authoritative McAuley Lab Hugging Face repository.
"""

import os
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

# Category selected: Musical_Instruments
CATEGORY = "Musical_Instruments"
BASE_URL = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main"

FILES = [
    {
        "name": f"meta_{CATEGORY}.jsonl",
        "url": f"{BASE_URL}/raw/meta_categories/meta_{CATEGORY}.jsonl",
        "expected_size": 631877970,  # ~602.6 MB
    },
    {
        "name": f"{CATEGORY}.jsonl",
        "url": f"{BASE_URL}/raw/review_categories/{CATEGORY}.jsonl",
        "expected_size": 1557845107,  # ~1485.7 MB
    }
]

def download_file(url: str, dest_path: Path, expected_size: int = None, chunk_size: int = 1024 * 1024):
    """Download a file with progress reporting and resume capability."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {"User-Agent": "ShopGraph-DataIngestion/1.0"}
    existing_bytes = 0
    
    if dest_path.exists():
        existing_bytes = dest_path.stat().st_size
        if expected_size and existing_bytes == expected_size:
            print(f"[OK] {dest_path.name} already fully downloaded ({existing_bytes / (1024*1024):.2f} MB). Skipping.")
            return
        elif existing_bytes > 0:
            print(f"[RESUME] Resuming {dest_path.name} from {existing_bytes / (1024*1024):.2f} MB...")
            headers["Range"] = f"bytes={existing_bytes}-"

    req = urllib.request.Request(url, headers=headers)
    start_time = time.time()
    last_print = start_time
    downloaded_bytes = existing_bytes

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            total_bytes = expected_size
            if not total_bytes:
                content_len = resp.headers.get("Content-Length")
                if content_len:
                    total_bytes = int(content_len) + existing_bytes

            mode = "ab" if existing_bytes > 0 and resp.status == 206 else "wb"
            if mode == "wb":
                downloaded_bytes = 0

            with open(dest_path, mode) as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    
                    now = time.time()
                    if now - last_print >= 5.0:  # Report every 5 seconds
                        pct = (downloaded_bytes / total_bytes * 100) if total_bytes else 0.0
                        elapsed = now - start_time
                        speed = (downloaded_bytes - existing_bytes) / (1024 * 1024) / max(elapsed, 0.001)
                        print(f"[{dest_path.name}] {downloaded_bytes / (1024*1024):.1f} MB / {total_bytes / (1024*1024):.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s", flush=True)
                        last_print = now

        total_elapsed = time.time() - start_time
        avg_speed = (downloaded_bytes - existing_bytes) / (1024 * 1024) / max(total_elapsed, 0.001)
        print(f"[DONE] {dest_path.name} downloaded: {downloaded_bytes / (1024*1024):.2f} MB in {total_elapsed:.1f}s ({avg_speed:.2f} MB/s)", flush=True)

    except Exception as e:
        print(f"[ERROR] Failed downloading {dest_path.name}: {e}", file=sys.stderr)
        raise

def main():
    print(f"=== Starting ShopGraph Raw Dataset Acquisition ===")
    print(f"Category: {CATEGORY}")
    print(f"Target directory: {DATA_RAW_DIR}")
    for item in FILES:
        dest = DATA_RAW_DIR / item["name"]
        print(f"\nTarget file: {item['name']}")
        download_file(item["url"], dest, expected_size=item.get("expected_size"))
    print("\n=== Dataset Download Complete ===")

if __name__ == "__main__":
    main()
