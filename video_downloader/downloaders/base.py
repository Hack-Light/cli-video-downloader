import yt_dlp
from pathlib import Path
from rich.console import Console

console = Console()

class BaseDownloader:
    def __init__(self, platform_name):
        self.platform_name = platform_name
        # Default to user's Downloads folder per platform
        self.download_path = Path.home() / "Downloads" / platform_name
        self.download_path.mkdir(parents=True, exist_ok=True)

    def get_platform_specific_options(self):
        """Platform-specific yt-dlp tweaks"""
        return {
            'youtube': {},
            'tiktok': {
                'extract_flat': False,
                # Use browser impersonation to keep up with TikTok site changes
                'impersonate': 'Chrome-131',
                'headers': {
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/91.0.4472.124 Safari/537.36'
                    ),
                    'Referer': 'https://www.tiktok.com/',
                },
            },
            'instagram': {
                'extract_flat': False,
            },
            'facebook': {
                'extract_flat': False,
            }
        }.get(self.platform_name, {})
    
    def get_video_info(self, url):
        """Get video information"""
        try:
            ydl_opts = {'quiet': True}
            ydl_opts.update(self.get_platform_specific_options())

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail', '')
                }
        except Exception as e:
            console.print(f"[red]Error getting video info: {e}[/red]")
            return None
    
    def download(self, url, quality='best', audio_only=False, progress_hook=None):
        """Download video/audio"""
        ydl_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': False,
        }

        # Add platform specific options
        ydl_opts.update(self.get_platform_specific_options())
        
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif quality != 'best':
            ydl_opts['format'] = quality
        else:
            # Platform specific default format selectors
            if self.platform_name == 'tiktok' and 'format' not in ydl_opts:
                ydl_opts['format'] = 'best[ext=mp4]/best'
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'filename': ydl.prepare_filename(info),
                    'platform': self.platform_name
                }
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")

            if self.platform_name == 'tiktok':
                return self._retry_tiktok_download(url, audio_only, progress_hook)

            return {'success': False, 'error': str(e)}

    def _retry_tiktok_download(self, url, audio_only=False, progress_hook=None):
        """Fallback attempt for TikTok downloads with alternate options."""
        console.print("[yellow]Retrying TikTok download with different options...[/yellow]")

        ydl_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'format': 'best[ext=mp4]',
            'extract_flat': False,
        }

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
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
            console.print(f"[red]TikTok retry also failed: {e}[/red]")
            return {'success': False, 'error': str(e)}
    
    def get_available_formats(self, url):
        """Get available formats for the video"""
        try:
            ydl_opts = {'quiet': True}
            ydl_opts.update(self.get_platform_specific_options())

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('formats', [])
        except Exception as e:
            console.print(f"[red]Error getting formats: {e}[/red]")
            return []
