from setuptools import setup, find_packages
from pathlib import Path

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="video-downloader",
    version="1.0.0",
    description="CLI tool to download videos from YouTube, TikTok, Instagram, and Facebook",
    author="Somtochukwu Onoh",
    packages=find_packages(),
    install_requires=requirements,
    data_files=[
        ('share/man/man1', [str(Path("docs/man/video-downloader.1"))]),
    ],
    entry_points={
        'console_scripts': [
            'video-downloader=video_downloader.cli:main',
            'vdl=video_downloader.cli:main',  # Short alias
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
