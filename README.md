# video-downloader

CLI tool to download videos (and audio) from YouTube, TikTok, Instagram, and Facebook. Supports playlists, interactive prompts, batch files, and rich progress bars. Defaults to saving under `~/Downloads/<platform>/`.

## Features
- Single video downloads with quality selection or audio-only (MP3).
- YouTube playlists with numbered files, per-video progress, and skip/resume of already downloaded items.
- Interactive mode with guided prompts.
- Batch mode from a text file (one URL per line).
- Format listing for a given URL.
- TikTok helpers (cookies/impersonation) and sensible defaults for other platforms.
- Man page installed to `share/man/man1/video-downloader.1`.

## Installation
```bash
python3 -m pip install .
# or editable for development
python3 -m pip install -e .
```

Ensure the scripts directory is on your `PATH` (for python.org macOS: `/Library/Frameworks/Python.framework/Versions/3.13/bin`). If not already in your shell config:
```bash
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"
```

## Usage
```bash
video-downloader [options] [URL]
vdl [options] [URL]  # short alias
```

### Common examples
- Download a single video (auto-detect platform):
  ```bash
  video-downloader https://www.youtube.com/watch?v=EXAMPLE
  ```
- Interactive mode:
  ```bash
  video-downloader -i
  ```
- Audio only:
  ```bash
  video-downloader -a https://instagram.com/reel/EXAMPLE/
  ```
- Specific quality and output directory:
  ```bash
  video-downloader -q "best[height<=720]" -o ~/Videos https://tiktok.com/@user/video/123
  ```
- Batch download from file:
  ```bash
  video-downloader -b urls.txt
  ```
- List formats:
  ```bash
  video-downloader -l https://youtube.com/watch?v=EXAMPLE
  ```
- Playlist:
  ```bash
  video-downloader -pl "https://www.youtube.com/playlist?list=PL123"
  video-downloader -pl "https://www.youtube.com/playlist?list=PL123" --playlist-items "1,3,5-8"
  ```

### Options
- `-i, --interactive` start interactive mode.
- `-b, --batch FILE` batch download URLs from a file.
- `-pl, --playlist URL` download a YouTube playlist.
- `--playlist-items ITEMS` choose items, e.g. `1,3,5-8`.
- `--playlist-start N`, `--playlist-end N` range selection.
- `-p, --platform {youtube,tiktok,instagram,facebook}` override platform detection.
- `-q, --quality STRING` yt-dlp format selector (default: `best`).
- `-a, --audio-only` download audio only (MP3).
- `-o, --output DIR` base output directory (platform subfolder is created).
- `-l, --list-formats` list available formats without downloading.

### Defaults and output layout
- Base directory: `~/Downloads/<platform>/`.
- Playlists: `~/Downloads/youtube/<playlist_name>/<index>_<title>.ext` with `.download_archive` to skip already downloaded videos; resumes partials.

## TikTok notes
- Impersonation and cookies are supported via yt-dlp extras (`yt-dlp[curl-cffi,default]`).
- To use browser cookies set:
  ```bash
  TIKTOK_COOKIES_BROWSER=chrome video-downloader "<tiktok_url>"
  # or export cookies:
  /Library/Frameworks/Python.framework/Versions/3.13/bin/yt-dlp --cookies-from-browser chrome --cookies /tmp/tiktok.txt --no-download https://www.tiktok.com
  TIKTOK_COOKIES_FILE=/tmp/tiktok.txt video-downloader "<tiktok_url>"
  ```
- If Safari cookies are needed, grant your terminal Full Disk Access first.

## YouTube JS runtime warning
yt-dlp may warn about missing JS runtime. Install one (node/bun/deno) to silence and unlock more formats. Example:
```bash
brew install node
# then retry downloads
```
Or use `--extractor-args "youtube:player_client=default"` if you want to suppress the warning with potentially fewer formats.

## Man page
After install:
```bash
man video-downloader
```

## Development
- Requirements: see `requirements.txt` (includes yt-dlp with curl-cffi, browser-cookie3, rich, questionary).
- Editable install: `python3 -m pip install -e .`
- Code entry points: `video_downloader/cli.py`, downloaders under `video_downloader/downloaders/`, helpers in `video_downloader/utils.py`.

## Troubleshooting
- PATH: ensure the Python scripts dir is on `PATH` (`which video-downloader` should resolve).
- TikTok extractor errors: update yt-dlp, supply cookies, and/or impersonation; sometimes an upstream fix is needed.
- Skipped playlist items: already downloaded videos are logged in `.download_archive`; delete that file to force re-download.
- Permission issues reading browser cookies (Safari): grant terminal Full Disk Access or export cookies to a file and set `TIKTOK_COOKIES_FILE`.
