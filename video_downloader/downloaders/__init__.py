from .youtube import YouTubeDownloader
from .tiktok import TikTokDownloader
from .instagram import InstagramDownloader
from .facebook import FacebookDownloader
from .twitter import TwitterDownloader


def get_downloader(platform):
    downloaders = {
        'youtube': YouTubeDownloader,
        'tiktok': TikTokDownloader,
        'instagram': InstagramDownloader,
        'facebook': FacebookDownloader,
        'twitter': TwitterDownloader
    }
    return downloaders.get(platform)()
