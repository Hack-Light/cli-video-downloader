# video_downloader/downloaders/facebook.py
from .base import BaseDownloader


class FacebookDownloader(BaseDownloader):
    def __init__(self):
        super().__init__("facebook")
