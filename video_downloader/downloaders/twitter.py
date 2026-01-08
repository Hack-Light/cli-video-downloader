# video_downloader/downloaders/twitter.py
from .base import BaseDownloader


class TwitterDownloader(BaseDownloader):
    def __init__(self):
        super().__init__("twitter")
