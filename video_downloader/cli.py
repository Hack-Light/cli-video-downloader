#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from .downloaders import get_downloader
from .utils import detect_platform, create_progress_bar, is_youtube_playlist

console = Console()


class VideoDownloaderCLI:
    def __init__(self):
        self.downloaders = ['youtube', 'tiktok', 'instagram', 'facebook', 'twitter']

    def list_formats(self, url, platform):
        """List available formats for a video"""
        downloader = get_downloader(platform)
        formats = downloader.get_available_formats(url)

        if not formats:
            rprint("[red]No formats available or could not fetch video info[/red]")
            return

        table = Table(title=f"Available formats for {platform}")
        table.add_column("ID", style="cyan")
        table.add_column("Quality", style="green")
        table.add_column("Format", style="yellow")
        table.add_column("Size", style="magenta")
        table.add_column("Codec", style="blue")

        for i, fmt in enumerate(formats[:15]):  # Show first 15 formats
            format_note = fmt.get('format_note', 'unknown')
            ext = fmt.get('ext', 'unknown')
            filesize = fmt.get('filesize', fmt.get('filesize_approx', 0))
            size_str = f"{filesize / (1024*1024):.1f}MB" if filesize else "unknown"
            codec = fmt.get('vcodec', 'none') or fmt.get('acodec', 'none')

            table.add_row(
                str(fmt.get('format_id', '')),
                format_note,
                ext,
                size_str,
                codec
            )

        console.print(table)

    def download_with_progress(self, url, platform, quality, audio_only, output_dir=None):
        """Download a single video with progress bar"""
        downloader = get_downloader(platform)

        if output_dir:
            downloader.download_path = Path(output_dir) / platform
            downloader.download_path.mkdir(parents=True, exist_ok=True)

        # Show video info
        with console.status("[bold green]Fetching video information...[/bold green]"):
            info = downloader.get_video_info(url)

        if info:
            rprint(f"\n[bold cyan]Title:[/bold cyan] {info['title']}")
            rprint(f"[bold cyan]Uploader:[/bold cyan] {info['uploader']}")
            rprint(
                f"[bold cyan]Duration:[/bold cyan] {info['duration']} seconds")
            rprint(f"[bold cyan]Views:[/bold cyan] {info['view_count']}")

        # Progress hook for yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d:
                    progress.update(
                        task, total=d['total_bytes'], completed=d['downloaded_bytes'])
                elif 'total_bytes_estimate' in d:
                    progress.update(
                        task, total=d['total_bytes_estimate'], completed=d['downloaded_bytes'])
                progress.update(
                    task, description=f"Downloading {platform} video")
            elif d['status'] == 'finished':
                progress.update(
                    task, description="[green]Download completed![/green]")

        # Download with progress
        progress = create_progress_bar()
        task = progress.add_task("Starting download...", total=100)

        with progress:
            result = downloader.download(
                url, quality, audio_only, progress_hook)

        if result['success']:
            rprint(f"\n[green]✅ Download completed![/green]")
            rprint(f"[blue]📁 Saved to: {result['filename']}[/blue]")
            return True
        else:
            rprint(f"\n[red]❌ Download failed: {result['error']}[/red]")
            return False

    def batch_download(self, file_path, platform, quality, audio_only, output_dir=None):
        """Download multiple videos from a file"""
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            rprint(f"[red]Error: File '{file_path}' not found[/red]")
            return

        rprint(f"[yellow]Found {len(urls)} URLs to process[/yellow]")

        successful = 0
        for i, url in enumerate(urls, 1):
            rprint(f"\n[bold][{i}/{len(urls)}] Processing: {url}[/bold]")

            detected_platform = detect_platform(url)
            if not detected_platform:
                if not platform:
                    rprint(
                        f"[red]❌ Could not detect platform for URL: {url}[/red]")
                    continue
                detected_platform = platform

            if self.download_with_progress(url, detected_platform, quality, audio_only, output_dir):
                successful += 1

        rprint(
            f"\n[green]🎉 Batch download completed! Successful: {successful}/{len(urls)}[/green]")

    def download_playlist(self, url, quality, audio_only, output_dir=None, playlist_items=None, playlist_start=None, playlist_end=None):
        """Download a YouTube playlist."""
        downloader = get_downloader('youtube')
        if output_dir:
            downloader.download_path = Path(output_dir) / 'youtube'
            downloader.download_path.mkdir(parents=True, exist_ok=True)

        with console.status("[bold green]Fetching playlist information...[/bold green]"):
            info = downloader.get_playlist_info(url, playlist_items, playlist_start, playlist_end)

        if not info:
            rprint("[red]❌ Could not fetch playlist info[/red]")
            return False

        rprint(f"\n[bold green]Playlist:[/bold green] {info['title']}")
        rprint(f"Videos: {info['count']}  |  Uploader: {info['uploader']}")
        if info.get('description'):
            rprint(f"[dim]{info['description'][:200]}[/dim]")

        result = downloader.download_playlist(
            url,
            quality,
            audio_only,
            output_dir,
            playlist_items,
            playlist_start,
            playlist_end
        )

        if result.get('success'):
            rprint(f"\n[green]✅ Playlist download completed![/green]")
            rprint(f"[blue]📁 Saved to: {result.get('download_dir')}[/blue]")
            return True
        else:
            rprint(f"\n[red]❌ Playlist download failed: {result.get('error')}[/red]")
            return False

    def interactive_mode(self):
        """Start interactive mode"""
        console.print(Panel.fit(
            "[bold cyan]🎬 Interactive Video Downloader[/bold cyan]\n"
            "Download videos from YouTube, TikTok, Instagram, Facebook, and Twitter/X",
            subtitle="Press Ctrl+C to exit"
        ))

        while True:
            try:
                url = questionary.text("Enter video URL:").ask()
                if not url:
                    break

                platform = detect_platform(url)
                if not platform:
                    # Detect playlist URLs even if platform not detected
                    if is_youtube_playlist(url):
                        platform = 'youtube'
                    else:
                        rprint("[red]❌ Could not detect platform from URL[/red]")
                        continue

                # Playlist handling
                if platform == 'youtube' and is_youtube_playlist(url):
                    downloader = get_downloader('youtube')
                    with console.status("[bold green]Fetching playlist information...[/bold green]"):
                        playlist_info = downloader.get_playlist_info(url)

                    if not playlist_info:
                        rprint("[red]❌ Could not fetch playlist info[/red]")
                        continue

                    rprint(f"\n[bold green]Playlist Found:[/bold green] {playlist_info['title']}")
                    rprint(f"Videos: {playlist_info['count']}  |  Uploader: {playlist_info['uploader']}")

                    choice = questionary.select(
                        "Playlist action:",
                        choices=[
                            {"name": "Download entire playlist", "value": "all"},
                            {"name": "Select specific items (e.g., 1,3,5-8)", "value": "items"},
                            {"name": "Skip", "value": "skip"},
                        ]
                    ).ask()

                    if choice == "skip":
                        continue

                    playlist_items = None
                    if choice == "items":
                        playlist_items = questionary.text(
                            "Enter items (e.g., 1,3,5-8):").ask() or None
                    download_type = questionary.select(
                        "Download type:",
                        choices=[
                            {"name": "Video", "value": "video"},
                            {"name": "Audio only (MP3)", "value": "audio"},
                        ]
                    ).ask()

                    quality = 'best'
                    if download_type == 'video':
                        quality_choice = questionary.select(
                            "Quality:",
                            choices=[
                                {"name": "Best quality", "value": "best"},
                                {"name": "720p", "value": "best[height<=720]"},
                                {"name": "480p", "value": "best[height<=480]"},
                                {"name": "360p", "value": "best[height<=360]"},
                                {"name": "Worst quality", "value": "worst"},
                            ]
                        ).ask()
                        quality = quality_choice

                    if questionary.confirm("Start playlist download?").ask():
                        self.download_playlist(
                            url,
                            quality,
                            download_type == 'audio',
                            None,
                            playlist_items,
                            None,
                            None
                        )
                    continue

                # Get video info
                with console.status("[bold green]Fetching video information...[/bold green]"):
                    downloader = get_downloader(platform)
                    info = downloader.get_video_info(url)

                if info:
                    rprint(f"\n[bold green]Video Found:[/bold green]")
                    rprint(f"Title: {info['title']}")
                    rprint(f"Platform: {platform}")
                    rprint(f"Duration: {info['duration']}s")
                    rprint(f"Uploader: {info['uploader']}")

                # Ask for download options
                download_type = questionary.select(
                    "Download type:",
                    choices=[
                        {"name": "Video", "value": "video"},
                        {"name": "Audio only (MP3)", "value": "audio"},
                    ]
                ).ask()

                quality = 'best'
                if download_type == 'video':
                    quality_choice = questionary.select(
                        "Quality:",
                        choices=[
                            {"name": "Best quality", "value": "best"},
                            {"name": "720p", "value": "best[height<=720]"},
                            {"name": "480p", "value": "best[height<=480]"},
                            {"name": "360p", "value": "best[height<=360]"},
                            {"name": "Worst quality", "value": "worst"},
                        ]
                    ).ask()
                    quality = quality_choice

                # Confirm download
                if questionary.confirm("Start download?").ask():
                    self.download_with_progress(
                        url,
                        platform,
                        quality,
                        download_type == 'audio'
                    )

                # Ask to continue
                if not questionary.confirm("Download another video?").ask():
                    rprint("[green]👋 Goodbye![/green]")
                    break

            except KeyboardInterrupt:
                rprint("\n[yellow]👋 Goodbye![/yellow]")
                break
            except Exception as e:
                rprint(f"[red]❌ Error: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="Download videos from YouTube, TikTok, Instagram, Facebook, and Twitter/X",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a video (auto-detect platform)
  video-downloader https://www.youtube.com/watch?v=EXAMPLE

  # Interactive mode
  video-downloader -i

  # Download only audio
  video-downloader -a https://instagram.com/reel/EXAMPLE/

  # Specific quality and output directory
  video-downloader -q "best[height<=720]" -o ~/Videos https://tiktok.com/@user/video/123

  # Batch download from file
  video-downloader -b urls.txt

  # List available formats
  video-downloader -l https://youtube.com/watch?v=EXAMPLE
  
  # Download a playlist
  video-downloader --playlist https://www.youtube.com/playlist?list=PL123

  # Short alias also works
  vdl https://youtube.com/watch?v=EXAMPLE
        """
    )

    parser.add_argument('url', nargs='?', help='Video URL to download')
    parser.add_argument('-i', '--interactive',
                        action='store_true', help='Start interactive mode')
    parser.add_argument('-b', '--batch', metavar='FILE',
                        help='Batch download from text file')
    parser.add_argument('-pl', '--playlist', metavar='URL',
                        help='YouTube playlist URL to download')
    parser.add_argument('--playlist-items', metavar='ITEMS',
                        help='Playlist items to download (e.g., "1,3,5-8")')
    parser.add_argument('--playlist-start', type=int, metavar='N',
                        help='Start index for playlist download')
    parser.add_argument('--playlist-end', type=int, metavar='N',
                        help='End index for playlist download')
    parser.add_argument('-p', '--platform', choices=['youtube', 'tiktok', 'instagram', 'facebook', 'twitter'],
                        help='Specify platform explicitly')
    parser.add_argument('-q', '--quality', default='best',
                        help='Video quality (default: best)')
    parser.add_argument('-a', '--audio-only', action='store_true',
                        help='Download audio only (MP3)')
    parser.add_argument('-o', '--output', metavar='DIR',
                        help='Output directory (default: ./downloads)')
    parser.add_argument('-l', '--list-formats', action='store_true',
                        help='List available formats without downloading')

    args = parser.parse_args()

    cli = VideoDownloaderCLI()

    try:
        if args.interactive:
            cli.interactive_mode()

        elif args.playlist:
            success = cli.download_playlist(
                args.playlist,
                args.quality,
                args.audio_only,
                args.output,
                args.playlist_items,
                args.playlist_start,
                args.playlist_end
            )
            sys.exit(0 if success else 1)

        elif args.list_formats and args.url:
            platform = args.platform or detect_platform(args.url)
            if not platform:
                rprint("[red]Error: Could not detect platform from URL[/red]")
                sys.exit(1)
            cli.list_formats(args.url, platform)

        elif args.batch:
            cli.batch_download(args.batch, args.platform,
                               args.quality, args.audio_only, args.output)

        elif args.url:
            platform = args.platform or detect_platform(args.url)
            if not platform:
                rprint("[red]Error: Could not detect platform from URL[/red]")
                sys.exit(1)

            if platform == 'youtube' and (args.playlist or is_youtube_playlist(args.url)):
                success = cli.download_playlist(
                    args.url,
                    args.quality,
                    args.audio_only,
                    args.output,
                    args.playlist_items,
                    args.playlist_start,
                    args.playlist_end
                )
                sys.exit(0 if success else 1)

            success = cli.download_with_progress(
                args.url, platform, args.quality, args.audio_only, args.output)
            sys.exit(0 if success else 1)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        rprint("\n[yellow]Download interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        rprint(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
