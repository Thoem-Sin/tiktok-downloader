# TikDL — TikTok Video Downloader

A PySide6 desktop app for bulk-downloading TikTok videos with a clean dark UI.

## Features

- **Batch URL download** — paste multiple URLs, download concurrently (3 at a time)
- **Username bulk download** — fetch and download all videos from any public profile
- **Watermark-free** — uses yt-dlp's best-format selection to avoid watermarked copies
- **Choose save folder** — per-session folder picker
- **Live progress** — per-item progress bars, download speed, status indicators
- **Queue management** — add/remove items, stop all, clear done

## Requirements

- Python 3.11+
- ffmpeg installed and on PATH ([ffmpeg.org](https://ffmpeg.org/download.html))

## Setup

```bash
# 1. Create virtualenv (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

## Project Structure

```
tiktok_downloader/
├── main.py                  # Entry point
├── requirements.txt
├── core/
│   ├── worker.py            # DownloadWorker & UserDownloadWorker (QThread)
│   └── queue_manager.py     # DownloadItem dataclass + DownloadStatus enum
├── ui/
│   ├── main_window.py       # QMainWindow + header
│   ├── batch_tab.py         # Batch URLs tab
│   ├── user_tab.py          # Username bulk-download tab
│   ├── widgets.py           # DownloadItemWidget row
│   └── style.py             # Global QSS stylesheet
```

## Notes

- TikTok's no-watermark format relies on yt-dlp's extractor; availability may vary by region/account.
- `ffmpeg` is required for merging video+audio streams.
- The username downloader first fetches the full playlist metadata, then downloads sequentially.
  For very large accounts, set a **Max videos** limit to avoid extremely long runs.
