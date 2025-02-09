# Welcome to Vod Recovery

This Fork of VodRecovery is used to recover and download Twitch VODs, highlights, and clips, including various adjustments and improvements.

## Installation

1. Install [Python](https://www.python.org/downloads/), during installation check the box labeled "Add Python to environment variables"
2. Download the app by clicking [here](https://github.com/MacielG1/VodRecovery/archive/refs/heads/main.zip) or with the command `git clone https://github.com/MacielG1/VodRecovery`
3. Inside the downloaded folder run the file: `install_dependencies.py`
4. Start the program by running the file `vod_recovery.py` or one of the shortcuts

## Core Features

- Video & Clip Recovery: Find VODs and clips using the listed websites or by manually inputting the values.
- Video Format: Recovered VODs and highlights can be downloaded in various formats such as MP4, MKV, AVI, MOV and TS.
- Download Highlights: Retrieve highlights and VODs using a direct Twitch URL.
- Multiple Formats: Recovered M3U8 links are available in these formats: Chunked (Source Quality), 1080p60, 1080p30, 720p60, 720p30, 480p60, 480p30.
- Platform Compatibility: VodRecovery is compatible with popular platforms such as [TwitchTracker](https://twitchtracker.com/), [Sullygnome](https://sullygnome.com/), and [Streamscharts](https://streamscharts.com/) and also direct Twitch links.
- Bulk Video & Clip Recovery: Recovers multiple VODs and Clips using CSV files from [Sullygnome](https://sullygnome.com/).
- Unmute VODs: Unmute M3U8 files so that they can be played in media players.

## Usage

This is the interactive menu:

```
1) VOD Recovery
2) Clip Recovery
3) Download VOD (default mp4)
4) Unmute & Check M3U8 Availability
5) Options
6) Exit
```

## Latest Release

https://github.com/MacielG1/VodRecovery/releases/latest

## Notes

- Original Repo: [VodRecovery](https://github.com/Shishkebaboo/VodRecovery) by Shishkebaboo
- How Twitch Handles [VOD Storage](https://help.twitch.tv/s/article/video-on-demand#enabling)
