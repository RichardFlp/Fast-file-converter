# Fast-file-converter

Fast File Converter is a lightweight Flask app for converting audio and video files with
FFmpeg. It provides a simple web UI and uses multi-threaded presets for quick results.

## Requirements

- Python 3.10+
- FFmpeg installed and available on your PATH

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app/app.py
```

Then open `http://localhost:5000` in your browser, upload a media file, pick an output
format, and download the converted file.
