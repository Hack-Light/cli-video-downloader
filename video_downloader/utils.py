import re
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    DownloadColumn,
    TransferSpeedColumn
)


def detect_platform(url):
    """Detect platform from URL"""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    else:
        return None


def sanitize_filename(filename):
    """Remove invalid characters from filename and truncate if too long"""
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)

    # macOS/Linux max filename length is typically 255 characters
    # Leave some buffer for extensions and path
    max_length = 200

    if len(sanitized) > max_length:
        # Truncate but try to preserve extension if present
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            # Reserve space for extension and dot
            max_name_length = max_length - len(ext) - 1
            if max_name_length > 0:
                sanitized = name[:max_name_length] + '.' + ext
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    return sanitized


def create_progress_bar():
    """Create a rich progress bar for downloads"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        transient=False,
    )


def is_youtube_playlist(url):
    """Detect if a URL is a YouTube playlist."""
    url_lower = url.lower()
    return ('youtube.com/playlist?' in url_lower or 'list=' in url_lower)
