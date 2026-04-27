import os
import re
import uuid
from pathlib import Path

import yt_dlp
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse


app = FastAPI()

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def clean_filename(title):
    title = title.strip()
    title = re.sub(r'[<>:"/\\|?*]', "", title)
    title = re.sub(r"\s+", " ", title)
    title = title[:120]
    return title or "audio"


def is_valid_url(url):
    url = url.strip()
    return url.startswith("http://") or url.startswith("https://")


def download_m4a(video_url):
    """
    Downloads YouTube audio in M4A format only.
    No MP3 conversion.
    No FFmpeg required.
    """

    file_id = str(uuid.uuid4())
    output_template = str(DOWNLOAD_DIR / f"{file_id}.%(ext)s")

    ydl_opts = {
        "format": "ba[ext=m4a]/ba/best[ext=m4a]/ba/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

    video_title = info.get("title", "audio")
    safe_title = clean_filename(video_title)

    m4a_path = DOWNLOAD_DIR / f"{file_id}.m4a"

    if not m4a_path.exists():
        possible_files = list(DOWNLOAD_DIR.glob(f"{file_id}.*"))

        if not possible_files:
            raise FileNotFoundError("M4A file was not created.")

        downloaded_file = possible_files[0]

        if downloaded_file.suffix.lower() != ".m4a":
            raise FileNotFoundError(
                f"Downloaded file is not M4A. Got: {downloaded_file.suffix}"
            )

        m4a_path = downloaded_file

    return file_id, safe_title, video_title


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube M4A Downloader</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 760px;
                margin: 40px auto;
                padding: 20px;
                background: #111827;
                color: white;
            }
            .box {
                background: #1f2937;
                padding: 24px;
                border-radius: 12px;
                border: 1px solid #374151;
            }
            input[type="text"] {
                width: 100%;
                padding: 12px;
                font-size: 16px;
                margin-top: 8px;
                border-radius: 8px;
                border: 1px solid #4b5563;
                background: #111827;
                color: white;
            }
            button {
                background: #2563eb;
                color: white;
                padding: 12px 18px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 16px;
            }
            button:hover {
                background: #1d4ed8;
            }
            .warning {
                background: #78350f;
                padding: 14px;
                border-radius: 8px;
                margin-bottom: 18px;
                line-height: 1.5;
            }
            .note {
                background: #064e3b;
                padding: 14px;
                border-radius: 8px;
                margin-bottom: 18px;
                line-height: 1.5;
            }
            a {
                color: #93c5fd;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>YouTube M4A Downloader</h1>

            <div class="note">
                This version downloads M4A only. It does not convert to MP3, so it is faster and does not require FFmpeg.
            </div>

            <div class="warning">
                Use only for videos you own, your own lectures/interviews, public-domain content,
                or content where you have explicit permission. Do not use this for copyrighted music,
                paid content, private videos, members-only videos, or content you do not have permission to download.
            </div>

            <form action="/convert" method="post">
                <label>Paste YouTube video link:</label>
                <input type="text" name="video_url" placeholder="https://www.youtube.com/watch?v=..." required>

                <p>
                    <label>
                        <input type="checkbox" name="permission_confirmed" value="yes" required>
                        I confirm I own this content or have permission to download it.
                    </label>
                </p>

                <button type="submit">Download M4A</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.post("/convert", response_class=HTMLResponse)
def convert(video_url: str = Form(...), permission_confirmed: str = Form(...)):
    try:
        if not is_valid_url(video_url):
            return """
            <body style="font-family: Arial; background: #111827; color: white; padding: 40px;">
                <h2>Invalid URL</h2>
                <p>Please enter a URL starting with http:// or https://</p>
                <a href="/" style="color: #93c5fd;">Go back</a>
            </body>
            """

        file_id, safe_title, video_title = download_m4a(video_url.strip())

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>M4A Ready</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 760px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #111827;
                    color: white;
                }}
                .box {{
                    background: #1f2937;
                    padding: 24px;
                    border-radius: 12px;
                    border: 1px solid #374151;
                }}
                a.button {{
                    display: inline-block;
                    background: #16a34a;
                    color: white;
                    padding: 12px 18px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-size: 16px;
                    margin-top: 12px;
                }}
                input {{
                    width: 100%;
                    padding: 12px;
                    margin-top: 12px;
                    border-radius: 8px;
                    border: 1px solid #4b5563;
                    background: #111827;
                    color: white;
                }}
                a {{
                    color: #93c5fd;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>M4A is ready</h1>
                <p><strong>Video title:</strong> {video_title}</p>

                <p>Download link:</p>
                <input value="/download/{file_id}/{safe_title}.m4a" readonly>

                <br>
                <a class="button" href="/download/{file_id}/{safe_title}.m4a">Download M4A</a>

                <p><a href="/">Convert another video</a></p>
            </div>
        </body>
        </html>
        """

    except Exception as error:
        return f"""
        <body style="font-family: Arial; background: #111827; color: white; padding: 40px;">
            <h2>Download failed</h2>
            <pre>{str(error)}</pre>
            <p><a href="/" style="color: #93c5fd;">Go back</a></p>
        </body>
        """


@app.get("/download/{file_id}/{filename}")
def download_file(file_id: str, filename: str):
    m4a_path = DOWNLOAD_DIR / f"{file_id}.m4a"

    if not m4a_path.exists():
        return HTMLResponse(
            """
            <body style="font-family: Arial; background: #111827; color: white; padding: 40px;">
                <h2>File not found or expired.</h2>
                <p>The file may have been deleted or the server restarted.</p>
                <a href="/" style="color: #93c5fd;">Go back</a>
            </body>
            """
        )

    return FileResponse(
        path=str(m4a_path),
        media_type="audio/mp4",
        filename=filename
    )
