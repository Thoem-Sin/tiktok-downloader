from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DownloadStatus(Enum):
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    DONE = "Done"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class DownloadItem:
    url: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress: int = 0
    message: str = ""
    speed: str = ""

    def display_url(self, max_len: int = 60) -> str:
        return self.url if len(self.url) <= max_len else self.url[:max_len - 3] + "…"
