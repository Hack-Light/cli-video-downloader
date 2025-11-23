# video_downloader/downloaders/instagram.py
from .base import BaseDownloader


class InstagramDownloader(BaseDownloader):
    def __init__(self):
        super().__init__("instagram")
