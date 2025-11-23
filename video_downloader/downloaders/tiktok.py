# video_downloader/downloaders/tiktok.py
import yt_dlp
import requests
import os
from .base import BaseDownloader
from rich.console import Console

console = Console()


class TikTokDownloader(BaseDownloader):
    def __init__(self):
        super().__init__("tiktok")

    def get_platform_specific_options(self):
        """Extend base options with browser cookies to help TikTok extraction."""
        opts = super().get_platform_specific_options()
        cookies_file = os.environ.get('TIKTOK_COOKIES_FILE')
        browser = os.environ.get('TIKTOK_COOKIES_BROWSER')

        # If user provides an exported cookies file, prefer that.
        if cookies_file:
            opts['cookiefile'] = cookies_file
        elif browser and browser.lower() != 'none':
            # Only enable cookies-from-browser when user explicitly opts in.
            opts['cookiesfrombrowser'] = (browser, None, None, None)
        return opts

    def fix_tiktok_url(self, url):
        """Normalize TikTok URLs to avoid redirect/short-link issues."""
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
            try:
                response = requests.head(url, allow_redirects=True, timeout=10)
                return response.url
            except Exception:
                return url

        if '//m.tiktok.com' in url:
            return url.replace('//m.tiktok.com', '//www.tiktok.com')

        return url

    def get_video_info(self, url):
        fixed_url = self.fix_tiktok_url(url)
        try:
            opts = {
                'quiet': True,
                'extract_flat': False,
            }
            opts.update(self.get_platform_specific_options())

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(fixed_url, download=False)
                return {
                    'title': info.get('title', 'TikTok Video'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'description': (
                        info.get('description', '')[:100] + '...'
                    ) if info.get('description') else ''
                }
        except Exception as e:
            console.print(f"[red]Error getting TikTok video info: {e}[/red]")
            return None

    def download(self, url, quality='best', audio_only=False, progress_hook=None):
        fixed_url = self.fix_tiktok_url(url)
        result = super().download(fixed_url, quality, audio_only, progress_hook)

        # If base downloader fails (including its retry), try one more permissive attempt
        if not result.get('success'):
            return self.download_alternative(fixed_url, audio_only, progress_hook)

        return result

    def download_alternative(self, url, audio_only=False, progress_hook=None):
        """Alternative download method for TikTok"""
        console.print("[yellow]Trying alternative TikTok download method...[/yellow]")

        ydl_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'format': 'best[ext=mp4]' if not audio_only else 'bestaudio/best',
        }

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        if audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'success': True,
                    'title': info.get('title', 'TikTok Video'),
                    'filename': ydl.prepare_filename(info),
                    'platform': 'tiktok'
                }
        except Exception as e:
            console.print(f"[red]Alternative TikTok download also failed: {e}[/red]")
            return {'success': False, 'error': str(e)}
