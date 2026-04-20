import os
import shutil
import tempfile
import yt_dlp
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VD-S")

# CORS for frontend/backend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIES_PATH = "cookies.txt"

def get_ydl_opts():
    """Generates the base configuration for yt-dlp."""
    return {
        'nocheckcertificate': True,
        'quiet': False,
        'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        },
        'format_sort': ['res:1080', 'res:720', 'res:360', 'res:240']
    }

def cleanup_temp(path: str):
    """Clean up the temporary directory after the file is downloaded."""
    try:
        shutil.rmtree(path)
    except Exception:
        pass

# --- STATIC FILE SERVING ---
@app.get("/")
def read_index():
    return FileResponse("index.html")

@app.get("/style.css")
def get_style():
    return FileResponse("style.css")

@app.get("/script.js")
def get_script():
    return FileResponse("script.js")

# --- API ENDPOINTS ---
@app.get("/extract")
def extract_info(url: str = Query(..., description="The Video URL")):
    """Extracts video metadata and specific resolutions."""
    opts = get_ydl_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            seen_resolutions = set()
            target_res = [240, 360, 480, 720, 1080]
            
            # Extract video formats
            for f in reversed(info.get('formats', [])):
                h = f.get('height')
                if h in target_res and h not in seen_resolutions:
                    if f.get('vcodec') != 'none':
                        formats.append({
                            "resolution": f"{h}p",
                            "format_id": f.get('format_id'),
                            "type": "video"
                        })
                        seen_resolutions.add(h)
            
            # Add Audio Only Option
            formats.append({
                "resolution": "Audio (MP3/M4A)",
                "format_id": "bestaudio",
                "type": "audio"
            })
            
            return {
                "title": info.get('title', 'Unknown Title'),
                "thumbnail": info.get('thumbnail', ''),
                "formats": formats
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
def download_video(background_tasks: BackgroundTasks, url: str = Query(...), format_id: str = Query(...), type: str = Query("video")):
    """Downloads the file to a temp folder and serves it directly to the browser."""
    opts = get_ydl_opts()
    temp_dir = tempfile.mkdtemp()
    
    if type == "audio":
        opts['format'] = 'bestaudio/best'
        opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        # We don't use postprocessors for ffmpeg since free servers might lack ffmpeg. Best audio directly.
    else:
        opts['format'] = f"{format_id}+bestaudio/best" # Tries to merge if ffmpeg is available
        opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        
    try:
        # Fallback to single format if ffmpeg fails
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                ydl.download([url])
            except Exception:
                # If merging fails (no ffmpeg), just download the video format
                opts['format'] = format_id
                with yt_dlp.YoutubeDL(opts) as ydl2:
                    ydl2.download([url])
            
        files = os.listdir(temp_dir)
        if not files:
            raise HTTPException(status_code=400, detail="Download process failed silently")
            
        downloaded_file = os.path.join(temp_dir, files[0])
        
        # Add background task to delete the folder after serving the file
        background_tasks.add_task(cleanup_temp, temp_dir)
        
        return FileResponse(path=downloaded_file, filename=files[0], media_type='application/octet-stream')
    except Exception as e:
        cleanup_temp(temp_dir)
        raise HTTPException(status_code=400, detail=str(e))
