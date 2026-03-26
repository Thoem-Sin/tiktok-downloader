import os
from PySide6.QtCore import QThread, Signal


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _format_speed(bps: float) -> str:
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.1f} MB/s"
    if bps >= 1_000:
        return f"{bps / 1_000:.1f} KB/s"
    return f"{bps:.0f} B/s"


def _base_outtmpl_opts(save_dir: str) -> dict:
    """Common output / reliability options shared by all platforms."""
    return {
        "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
        "outtmpl_na_placeholder": "untitled",
        "restrictfilenames": False,
        "windowsfilenames": True,
        "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "retries": 5,
        "fragment_retries": 5,
        "retry_sleep_functions": {"http": lambda n: 2 ** n},
        "socket_timeout": 30,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
    }


# ── TikTok opts ────────────────────────────────────────────────────────────────

def _build_tiktok_opts(save_dir: str, progress_hook=None) -> dict:
    opts = _base_outtmpl_opts(save_dir)
    opts.update({
        "format": (
            "bestvideo[format_id*=bytevc1]+bestaudio/best[ext=mp4]/"
            "bestvideo+bestaudio/best"
        ),
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.tiktok.com/",
        },
    })
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


# Keep old name as alias so existing callers still work
_build_ydl_opts = _build_tiktok_opts


# ── YouTube opts ───────────────────────────────────────────────────────────────

YOUTUBE_QUALITIES = {
    "Best (up to 4K)":  "bestvideo+bestaudio/best",
    "1080p":            "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p":             "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p":             "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "360p":             "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
    "Audio only (MP3)": "bestaudio/best",
}


def _build_youtube_opts(save_dir: str, quality: str, progress_hook=None) -> dict:
    fmt = YOUTUBE_QUALITIES.get(quality, "bestvideo+bestaudio/best")
    opts = _base_outtmpl_opts(save_dir)
    opts["format"] = fmt

    if quality == "Audio only (MP3)":
        opts["outtmpl"] = os.path.join(save_dir, "%(title)s.%(ext)s")
        opts["merge_output_format"] = "mp3"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


# ── TikTok single-URL worker ───────────────────────────────────────────────────

class DownloadWorker(QThread):
    """Worker thread for downloading a single TikTok video."""

    progress = Signal(int)
    status   = Signal(str)
    finished = Signal(bool, str)
    speed    = Signal(str)

    def __init__(self, url: str, save_dir: str):
        super().__init__()
        self.url = url
        self.save_dir = save_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.finished.emit(False, "yt-dlp not installed. Run: pip install yt-dlp")
            return

        def progress_hook(d):
            if self._cancelled:
                raise Exception("Cancelled by user.")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    self.progress.emit(int(downloaded / total * 100))
                spd = d.get("speed")
                if spd:
                    self.speed.emit(_format_speed(spd))
                self.status.emit(f"Downloading… {d.get('_percent_str', '').strip()}")
            elif d["status"] == "finished":
                self.progress.emit(100)
                self.status.emit("Processing…")

        opts = _build_tiktok_opts(self.save_dir, progress_hook)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, "OK")
        except Exception as e:
            self.finished.emit(False, str(e))


# ── TikTok username worker ─────────────────────────────────────────────────────

class UserDownloadWorker(QThread):
    """Worker thread to fetch and download all videos from a TikTok username."""

    video_found = Signal(str)
    progress    = Signal(int, int)
    status      = Signal(str)
    video_done  = Signal(str, bool, str)
    finished    = Signal(int, int)

    def __init__(self, username: str, save_dir: str, max_videos: int = 0):
        super().__init__()
        self.username   = username.lstrip("@")
        self.save_dir   = save_dir
        self.max_videos = max_videos
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.finished.emit(0, 0)
            return

        profile_url = f"https://www.tiktok.com/@{self.username}"
        self.status.emit(f"Fetching videos from @{self.username}…")

        extract_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": self.max_videos if self.max_videos > 0 else None,
        }

        try:
            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                info = ydl.extract_info(profile_url, download=False)
        except Exception as e:
            self.status.emit(f"Error fetching profile: {e}")
            self.finished.emit(0, 0)
            return

        entries = info.get("entries", []) if info else []
        urls = [e["url"] for e in entries if e and "url" in e]

        if not urls:
            self.status.emit("No videos found.")
            self.finished.emit(0, 0)
            return

        total = len(urls)
        user_folder = os.path.join(self.save_dir, f"@{self.username}")
        os.makedirs(user_folder, exist_ok=True)
        self.status.emit(f"Found {total} videos → {user_folder}")

        success = fail = 0

        for i, url in enumerate(urls):
            if self._cancelled:
                break

            self.video_found.emit(url)
            self.progress.emit(i + 1, total)
            self.status.emit(f"Downloading {i + 1}/{total}…")

            opts = _build_tiktok_opts(user_folder)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                success += 1
                self.video_done.emit(url, True, "OK")
            except Exception as e:
                fail += 1
                self.video_done.emit(url, False, str(e))

        self.finished.emit(success, fail)


# ── YouTube single-video worker ────────────────────────────────────────────────

class YoutubeDownloadWorker(QThread):
    """Download a single YouTube video or audio track."""

    progress = Signal(int)
    status   = Signal(str)
    finished = Signal(bool, str)
    speed    = Signal(str)

    def __init__(self, url: str, save_dir: str, quality: str = "Best (up to 4K)"):
        super().__init__()
        self.url      = url
        self.save_dir = save_dir
        self.quality  = quality
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.finished.emit(False, "yt-dlp not installed.")
            return

        def progress_hook(d):
            if self._cancelled:
                raise Exception("Cancelled by user.")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    self.progress.emit(int(downloaded / total * 100))
                spd = d.get("speed")
                if spd:
                    self.speed.emit(_format_speed(spd))
                self.status.emit(f"Downloading… {d.get('_percent_str', '').strip()}")
            elif d["status"] == "finished":
                self.progress.emit(100)
                self.status.emit("Processing…")

        opts = _build_youtube_opts(self.save_dir, self.quality, progress_hook)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, "OK")
        except Exception as e:
            self.finished.emit(False, str(e))


# ── YouTube playlist / channel worker ─────────────────────────────────────────

class YoutubePlaylistWorker(QThread):
    """Download all videos from a YouTube playlist or channel URL."""

    video_found = Signal(str, str)        # url, title
    progress    = Signal(int, int)        # current, total
    status      = Signal(str)
    video_done  = Signal(str, bool, str)  # url, success, message
    finished    = Signal(int, int)        # success, fail

    def __init__(self, url: str, save_dir: str, quality: str = "Best (up to 4K)",
                 max_videos: int = 0):
        super().__init__()
        self.url        = url
        self.save_dir   = save_dir
        self.quality    = quality
        self.max_videos = max_videos
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            import yt_dlp
        except ImportError:
            self.finished.emit(0, 0)
            return

        self.status.emit("Fetching playlist info…")

        extract_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": self.max_videos if self.max_videos > 0 else None,
        }

        try:
            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
        except Exception as e:
            self.status.emit(f"Error: {e}")
            self.finished.emit(0, 0)
            return

        entries = info.get("entries", []) if info else []
        items = [(e.get("url", ""), e.get("title", "")) for e in entries if e and "url" in e]

        if not items:
            self.status.emit("No videos found.")
            self.finished.emit(0, 0)
            return

        total = len(items)
        playlist_title = info.get("title", "playlist") if info else "playlist"
        # Sanitize folder name
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in playlist_title)
        save_folder = os.path.join(self.save_dir, safe_title.strip())
        os.makedirs(save_folder, exist_ok=True)
        self.status.emit(f"Found {total} videos → {save_folder}")

        success = fail = 0

        for i, (url, title) in enumerate(items):
            if self._cancelled:
                break
            self.video_found.emit(url, title)
            self.progress.emit(i + 1, total)
            self.status.emit(f"Downloading {i + 1}/{total}: {title or url}")

            opts = _build_youtube_opts(save_folder, self.quality)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                success += 1
                self.video_done.emit(url, True, "OK")
            except Exception as e:
                fail += 1
                self.video_done.emit(url, False, str(e))

        self.finished.emit(success, fail)
