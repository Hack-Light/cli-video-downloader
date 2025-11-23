from .youtube import YouTubeDownloader
from .tiktok import TikTokDownloader
from .instagram import InstagramDownloader
from .facebook import FacebookDownloader


def get_downloader(platform):
    downloaders = {
        'youtube': YouTubeDownloader,
        'tiktok': TikTokDownloader,
        'instagram': InstagramDownloader,
        'facebook': FacebookDownloader
    }
    return downloaders.get(platform)()
