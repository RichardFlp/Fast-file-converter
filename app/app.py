from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import NamedTuple
import subprocess

from flask import Flask, render_template, request, send_file

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

ALLOWED_AUDIO_FORMATS = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "4"],
    "aac": ["-c:a", "aac", "-b:a", "192k"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    "flac": ["-c:a", "flac"],
    "wav": ["-c:a", "pcm_s16le"],
}

ALLOWED_VIDEO_FORMATS = {
    "mp4": [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
    ],
    "webm": [
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "32",
        "-c:a",
        "libopus",
        "-b:a",
        "128k",
    ],
    "mov": [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
    ],
    "mkv": [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
    ],
}

MAX_CONTENT_LENGTH = 1024 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


class ConversionRequest(NamedTuple):
    media_type: str
    output_format: str
    input_path: Path
    output_path: Path


def ensure_directories() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_conversion_request(media_type: str, output_format: str, filename: str) -> ConversionRequest:
    request_id = uuid.uuid4().hex
    safe_name = f"{request_id}_{Path(filename).stem}"
    input_path = UPLOAD_DIR / f"{safe_name}{Path(filename).suffix}"
    output_path = OUTPUT_DIR / f"{safe_name}.{output_format}"
    return ConversionRequest(
        media_type=media_type,
        output_format=output_format,
        input_path=input_path,
        output_path=output_path,
    )


def ffmpeg_args(request_data: ConversionRequest) -> list[str]:
    if request_data.media_type == "audio":
        codec_args = ALLOWED_AUDIO_FORMATS[request_data.output_format]
        return ["-vn", *codec_args]
    codec_args = ALLOWED_VIDEO_FORMATS[request_data.output_format]
    return codec_args


def run_ffmpeg(request_data: ConversionRequest) -> None:
    threads = max(1, os.cpu_count() or 1)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(request_data.input_path),
        "-threads",
        str(threads),
        *ffmpeg_args(request_data),
        str(request_data.output_path),
    ]
    subprocess.run(command, check=True)


def validate_request(media_type: str, output_format: str) -> tuple[bool, str]:
    if media_type not in {"audio", "video"}:
        return False, "Choose audio or video conversion."
    if media_type == "audio" and output_format not in ALLOWED_AUDIO_FORMATS:
        return False, "Select a supported audio format."
    if media_type == "video" and output_format not in ALLOWED_VIDEO_FORMATS:
        return False, "Select a supported video format."
    return True, ""


@app.route("/")
def index():
    return render_template(
        "index.html",
        audio_formats=sorted(ALLOWED_AUDIO_FORMATS.keys()),
        video_formats=sorted(ALLOWED_VIDEO_FORMATS.keys()),
    )


@app.route("/convert", methods=["POST"])
def convert():
    ensure_directories()

    media_type = request.form.get("media_type", "").lower()
    output_format = request.form.get("output_format", "").lower()
    is_valid, message = validate_request(media_type, output_format)
    if not is_valid:
        return render_template(
            "index.html",
            error=message,
            audio_formats=sorted(ALLOWED_AUDIO_FORMATS.keys()),
            video_formats=sorted(ALLOWED_VIDEO_FORMATS.keys()),
        ), 400

    uploaded_file = request.files.get("file")
    if uploaded_file is None or uploaded_file.filename == "":
        return render_template(
            "index.html",
            error="Upload a file to convert.",
            audio_formats=sorted(ALLOWED_AUDIO_FORMATS.keys()),
            video_formats=sorted(ALLOWED_VIDEO_FORMATS.keys()),
        ), 400

    request_data = build_conversion_request(media_type, output_format, uploaded_file.filename)
    uploaded_file.save(request_data.input_path)

    try:
        run_ffmpeg(request_data)
    except subprocess.CalledProcessError:
        return render_template(
            "index.html",
            error="Conversion failed. Ensure ffmpeg is installed and the file is valid.",
            audio_formats=sorted(ALLOWED_AUDIO_FORMATS.keys()),
            video_formats=sorted(ALLOWED_VIDEO_FORMATS.keys()),
        ), 500

    return send_file(request_data.output_path, as_attachment=True)


if __name__ == "__main__":
    ensure_directories()
    app.run(host="0.0.0.0", port=5000)
