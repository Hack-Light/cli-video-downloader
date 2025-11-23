# video_downloader/downloaders/youtube.py
from pathlib import Path
import yt_dlp

from .base import BaseDownloader
from ..utils import sanitize_filename, create_progress_bar


class YouTubeDownloader(BaseDownloader):
    def __init__(self):
        super().__init__("youtube")

    def get_playlist_info(self, url, playlist_items=None, playlist_start=None, playlist_end=None):
        """Fetch playlist metadata without downloading."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'playlist_items': playlist_items,
            'playliststart': playlist_start,
            'playlistend': playlist_end,
        }
        try:
            with yt_dlp.YoutubeDL({k: v for k, v in ydl_opts.items() if v is not None}) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = [e for e in info.get('entries', []) if e]
                return {
                    'title': info.get('title', 'YouTube Playlist'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'id': info.get('id', ''),
                    'webpage_url': info.get('webpage_url', url),
                    'description': info.get('description', '') or '',
                    'entries': entries,
                    'count': len(entries),
                }
        except Exception as e:
            return None

    def download_playlist(self, url, quality='best', audio_only=False, output_dir=None,
                          playlist_items=None, playlist_start=None, playlist_end=None):
        """Download a YouTube playlist sequentially with progress."""
        info = self.get_playlist_info(url, playlist_items, playlist_start, playlist_end)
        if not info:
            return {'success': False, 'error': 'Could not fetch playlist info'}

        # Choose destination directory
        if output_dir:
            self.download_path = Path(output_dir) / self.platform_name
            self.download_path.mkdir(parents=True, exist_ok=True)

        playlist_dir = self.download_path / sanitize_filename(info['title'] or 'playlist')
        playlist_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            'outtmpl': str(playlist_dir / '%(playlist_index)03d_%(title)s.%(ext)s'),
            'quiet': False,
            'noplaylist': False,
            'progress_hooks': [],
            # Skip already-downloaded files and resume partials if present
            'overwrites': False,
            'continuedl': True,
            'download_archive': str(playlist_dir / '.download_archive'),
        }

        if playlist_items is not None:
            ydl_opts['playlist_items'] = playlist_items
        if playlist_start is not None:
            ydl_opts['playliststart'] = playlist_start
        if playlist_end is not None:
            ydl_opts['playlistend'] = playlist_end

        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif quality != 'best':
            ydl_opts['format'] = quality

        total_videos = info['count'] or 0
        progress = create_progress_bar()
        overall_task = progress.add_task(f"Playlist: {info['title']}", total=total_videos or 1)

        def progress_hook(d):
            if d['status'] == 'finished':
                progress.advance(overall_task, 1)
            elif d.get('status') == 'skipped':
                progress.advance(overall_task, 1)

        ydl_opts['progress_hooks'].append(progress_hook)

        try:
            with progress:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            return {'success': True, 'download_dir': str(playlist_dir), 'count': total_videos}
        except Exception as e:
            return {'success': False, 'error': str(e)}
