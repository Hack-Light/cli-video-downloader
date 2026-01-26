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
            },
            'twitter': {
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

    def _truncate_title(self, title):
        """Truncate title if too long to prevent filename errors"""
        if not title:
            return title
        # Limit title to 100 characters to be safe
        # After restrictfilenames processes it (replaces spaces with underscores),
        # and adds extension, we need to stay well under 255 chars
        # 100 chars should be safe even with long extensions
        max_title_length = 100
        if len(title) > max_title_length:
            return title[:max_title_length].strip()
        return title

    def download(self, url, quality='best', audio_only=False, progress_hook=None):
        """Download video/audio"""
        # First, extract info and truncate title BEFORE download
        truncated_title = None
        try:
            info_opts = {'quiet': True}
            info_opts.update(self.get_platform_specific_options())
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'title' in info and info['title']:
                    # Truncate title to 100 chars to be safe
                    truncated_title = self._truncate_title(info['title'])
        except Exception:
            pass  # If we can't pre-fetch, we'll handle it in the exception handler

        ydl_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'restrictfilenames': True,  # Sanitize filenames to be filesystem-safe
        }

        # Add platform specific options
        ydl_opts.update(self.get_platform_specific_options())

        # Use match_filter to inject truncated title BEFORE filename is generated
        # Also use postprocessor_hooks as backup to ensure title is truncated
        if truncated_title:
            def match_filter(info_dict):
                if 'title' in info_dict:
                    info_dict['title'] = truncated_title
                return None  # Don't filter out, just modify

            def truncate_hook(info_dict):
                if 'title' in info_dict and info_dict['title']:
                    info_dict['title'] = truncated_title
                return info_dict

            ydl_opts['match_filter'] = match_filter
            ydl_opts['postprocessor_hooks'] = [truncate_hook]

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
                filename = ydl.prepare_filename(info)

                # Final safety check: if filename is still too long, rename it
                filename_path = Path(filename)
                if filename_path.exists() and len(filename_path.name) > 255:
                    stem = filename_path.stem
                    suffix = filename_path.suffix
                    max_stem_length = 200 - len(suffix)
                    if max_stem_length < 1:
                        max_stem_length = 200

                    if len(stem) > max_stem_length:
                        new_stem = stem[:max_stem_length].strip()
                        new_name = new_stem + suffix
                        new_path = filename_path.parent / new_name
                        if filename_path != new_path:
                            try:
                                filename_path.rename(new_path)
                                filename = str(new_path)
                            except Exception:
                                pass

                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'filename': filename,
                    'platform': self.platform_name
                }
        except Exception as e:
            # Check if error is due to filename length
            error_str = str(e)
            if 'File name too long' in error_str or 'filename too long' in error_str.lower() or 'Errno 63' in error_str:
                # Try to extract and download with a much shorter filename
                console.print(
                    "[yellow]Filename too long, retrying with shorter title...[/yellow]")
                try:
                    # Extract info and truncate title very aggressively
                    info_opts = {'quiet': True}
                    info_opts.update(self.get_platform_specific_options())
                    with yt_dlp.YoutubeDL(info_opts) as ydl_info:
                        info = ydl_info.extract_info(url, download=False)
                        if 'title' in info and info['title']:
                            # Truncate to 100 chars using the same method
                            info['title'] = self._truncate_title(info['title'])

                    # Now download with truncated title using match_filter
                    def match_filter_retry(info_dict):
                        info_dict['title'] = info['title']
                        return None
                    ydl_opts['match_filter'] = match_filter_retry

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl_retry:
                        ydl_retry.download([url])
                        filename = ydl_retry.prepare_filename(info)

                    return {
                        'success': True,
                        'title': info.get('title', 'Unknown'),
                        'filename': filename,
                        'platform': self.platform_name
                    }
                except Exception as retry_error:
                    console.print(
                        f"[red]Retry also failed: {retry_error}[/red]")

            console.print(f"[red]Download failed: {e}[/red]")

            if self.platform_name == 'tiktok':
                return self._retry_tiktok_download(url, audio_only, progress_hook)

            return {'success': False, 'error': str(e)}

    def _retry_tiktok_download(self, url, audio_only=False, progress_hook=None):
        """Fallback attempt for TikTok downloads with alternate options."""
        console.print(
            "[yellow]Retrying TikTok download with different options...[/yellow]")

        # Pre-fetch and truncate title
        truncated_title = None
        try:
            info_opts = {'quiet': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'title' in info and info['title']:
                    truncated_title = self._truncate_title(info['title'])
        except Exception:
            pass

        ydl_opts = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'format': 'best[ext=mp4]',
            'extract_flat': False,
            'restrictfilenames': True,  # Sanitize filenames to be filesystem-safe
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

        # Apply truncated title if available
        if truncated_title:
            def match_filter(info_dict):
                info_dict['title'] = truncated_title
                return None
            ydl_opts['match_filter'] = match_filter

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                downloaded_info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(downloaded_info)

                # Final safety check
                filename_path = Path(filename)
                if filename_path.exists() and len(filename_path.name) > 255:
                    from ..utils import sanitize_filename
                    safe_name = sanitize_filename(filename_path.name)
                    new_path = filename_path.parent / safe_name
                    if filename_path != new_path:
                        filename_path.rename(new_path)
                        filename = str(new_path)

                return {
                    'success': True,
                    'title': downloaded_info.get('title', 'TikTok Video'),
                    'filename': filename,
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
