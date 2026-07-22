import os
import sys
import time
import random
import json
import re
import shutil
import hashlib
import queue
import threading
import subprocess
import unicodedata
import warnings
import database

# Silent logger to suppress yt-dlp console error spam
class YtdlSilentLogger:
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass

# Initialize SQLite database
database.initialize_db()

# Helper for keyword matching with accent insensitivity
def normalize_text(text):
    if not text:
        return ""
    # Remove accents/diacritics and convert to lowercase
    return "".join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def evaluate_boolean_query(expression, text):
    """
    Evaluates a boolean search query against a given text.
    Supports AND, OR, NOT, parentheses, and terms/phrases.
    """
    norm_text = normalize_text(text)
    
    # Tokenize the expression
    # Operators: AND, OR, NOT, (, )
    # Terms can be alphanumeric or include special chars like # or @, or quoted phrases.
    token_pattern = re.compile(r'\(|\)|AND|OR|NOT|"[^"]+"|[^\s()]+', re.IGNORECASE)
    tokens = token_pattern.findall(expression)
    
    processed_tokens = []
    terms_matched = []
    
    for token in tokens:
        upper_token = token.upper()
        if upper_token in ('AND', 'OR', 'NOT', '(', ')'):
            processed_tokens.append(upper_token.lower())
        else:
            term = token.strip('"')
            norm_term = normalize_text(term)
            
            # Custom word boundary matching
            # Matches term only when bounded by start/end of string or non-alphanumeric chars
            pattern = rf"(?:^|[^a-zA-Z0-9_]){re.escape(norm_term)}(?:$|[^a-zA-Z0-9_])"
            has_match = re.search(pattern, norm_text) is not None
            
            if has_match:
                processed_tokens.append("True")
                terms_matched.append(term)
            else:
                processed_tokens.append("False")
                
    expr_str = " ".join(processed_tokens)
    
    # Strict validation to prevent arbitrary execution
    allowed_words = {'and', 'or', 'not', 'true', 'false', '(', ')'}
    words = expr_str.replace('(', ' ( ').replace(')', ' ) ').split()
    for w in words:
        if w.lower() not in allowed_words:
            return False, []
            
    try:
        result = bool(eval(expr_str, {"__builtins__": None}, {}))
        return result, terms_matched
    except Exception:
        return False, []

def explain_boolean_query(query_str):
    """
    Genera una explicación en español natural sobre lo que buscará la consulta booleana.
    """
    if not query_str or not str(query_str).strip():
        return ""
    
    q_str = str(query_str).strip()
    
    token_pattern = re.compile(r'\(|\)|AND|OR|NOT|"[^"]+"|[^\s()]+', re.IGNORECASE)
    tokens = token_pattern.findall(q_str)
    if not tokens:
        return ""
        
    has_explicit_boolean = any(t.upper() in ('AND', 'OR', 'NOT') for t in tokens)
    
    if not has_explicit_boolean:
        terms = [t.strip('"') for t in tokens if t not in ('(', ')')]
        if not terms:
            return ""
        if len(terms) == 1:
            return f"Se buscarán publicaciones que incluyan la palabra **'{terms[0]}'**."
        else:
            terms_fmt = ", ".join([f"**'{t}'**" for t in terms[:-1]]) + f" y **'{terms[-1]}'**"
            return f"Se buscarán publicaciones que incluyan las palabras: {terms_fmt}."
            
    and_terms = []
    or_terms = []
    not_terms = []
    
    current_op = "AND"
    for token in tokens:
        upper_tok = token.upper()
        if upper_tok in ('AND', 'OR', 'NOT'):
            current_op = upper_tok
        elif token not in ('(', ')'):
            term = token.strip('"')
            if current_op == "NOT":
                not_terms.append(term)
            elif current_op == "OR":
                or_terms.append(term)
            else:
                and_terms.append(term)
            current_op = "AND"
            
    parts = []
    if and_terms:
        if len(and_terms) == 1:
            parts.append(f"incluyan obligatoriamente **'{and_terms[0]}'**")
        else:
            and_str = " Y ".join([f"**'{t}'**" for t in and_terms])
            parts.append(f"incluyan obligatoriamente las palabras {and_str}")
            
    if or_terms:
        or_str = " O ".join([f"**'{t}'**" for t in or_terms])
        parts.append(f"contengan {or_str}")
        
    if not_terms:
        not_str = " ni ".join([f"**'{t}'**" for t in not_terms])
        parts.append(f"NO incluyan {not_str}")
        
    if not parts:
        return f"Búsqueda configurada: `{q_str}`"
        
    return "Se buscarán publicaciones que " + ", y ".join(parts) + "."

def contains_keywords(text, keywords):
    found = set()
    any_matched = False
    for expr in keywords:
        matched, terms = evaluate_boolean_query(expr, text)
        if matched:
            any_matched = True
            found.update(terms)
    return list(found) if any_matched else []

from urllib.parse import urlparse

def extract_youtube_channel_name(url):
    if not url:
        return "YouTube"
    match = re.search(r'(@[a-zA-Z0-9_\-\.]+)', url)
    if match:
        return match.group(1)
    for pattern in [r'/channel/([^/]+)', r'/c/([^/]+)', r'/user/([^/]+)']:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    clean_url = url.split('?')[0].rstrip('/')
    parts = clean_url.split('/')
    if len(parts) > 1 and parts[-1]:
        if parts[-1] in ["videos", "featured", "shorts", "streams", "playlists"] and len(parts) > 2:
            return parts[-2]
        return parts[-1]
    return "YouTube"

def normalize_youtube_channel_url(url):
    if not url:
        return ""
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://") or url.startswith("www."):
        return url
    if url.startswith("@"):
        return f"https://www.youtube.com/{url}"
    if url.startswith("UC"):
        return f"https://www.youtube.com/channel/{url}"
    return f"https://www.youtube.com/@{url}"

def extract_rss_domain(url):
    if not url:
        return "RSS"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if netloc.startswith("www."):
            return netloc[4:]
        return netloc
    except Exception:
        return "RSS"

def is_direct_stream_url(url):
    """Retorna True si la URL apunta a un stream directo (m3u8, mp3, aac, etc.) que no requiere resolución previa con yt-dlp."""
    if not url:
        return False
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return False
    direct_patterns = [
        ".m3u8", ".mp3", ".aac", ".pls", ".m3u", "/stream",
        "radiojar.com", "zeno.fm", "rcast.net", "hostdime.com",
        "plugstreaming.com", "livecastnet.com", "brlogic.com",
        "grupointernet.com", "cdnradio.com.do", "surfernetwork.com",
        "streamprolive.com", "essastream.com", "radiordomi.com",
        "streamlock.net", "telecablecentral.com.do", "streamhoster.com"
    ]
    return any(p in url_lower for p in direct_patterns)

def clean_ffmpeg_error(stderr_bytes):
    try:
        stderr_str = stderr_bytes.decode('utf-8', errors='ignore')
    except Exception:
        stderr_str = str(stderr_bytes)
        
    lines = [line.strip() for line in stderr_str.split("\n") if line.strip()]
    clean_lines = []
    for line in lines:
        if (line.startswith("ffmpeg version") or 
            line.startswith("built with") or 
            line.startswith("configuration:") or 
            line.startswith("libav") or 
            line.startswith("libsw") or 
            line.startswith("libpostproc") or 
            line.startswith("  built with") or
            line.startswith("  configuration:")):
            continue
        clean_lines.append(line)
        
    if clean_lines:
        return " | ".join(clean_lines[-3:])
    return lines[-1] if lines else "Unknown FFmpeg error"

def get_ffmpeg_path():
    # 1. Check local workspace directory first (full-featured FFmpeg)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(project_dir, "ffmpeg.exe")
    resolved = None
    if os.path.exists(local_ffmpeg):
        resolved = local_ffmpeg
    elif shutil.which("ffmpeg") is not None:
        resolved = "ffmpeg"
    else:
        import glob
        playwright_dir = os.path.expanduser(r"~\AppData\Local\ms-playwright")
        ffmpeg_glob = os.path.join(playwright_dir, "ffmpeg-*", "ffmpeg-win64.exe")
        matches = glob.glob(ffmpeg_glob)
        if matches:
            resolved = matches[0]
            
    # Write to a debug file in the scratch folder
    try:
        log_dir = os.path.join(project_dir, "scratch")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "ffmpeg_resolution_log.txt"), "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - resolved path: {resolved}\n")
    except Exception:
        pass
        
    return resolved


def download_local_ffmpeg():
    zip_path = None
    temp_dir = None
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        local_ffmpeg = os.path.join(project_dir, "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return True
            
        import urllib.request
        import zipfile
        
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = os.path.join(project_dir, "ffmpeg.zip")
        temp_dir = os.path.join(project_dir, "ffmpeg_temp")
        
        # Download
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Find and copy ffmpeg.exe
        for root, dirs, files in os.walk(temp_dir):
            if "ffmpeg.exe" in files:
                shutil.copy(os.path.join(root, "ffmpeg.exe"), local_ffmpeg)
                break
                
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        return os.path.exists(local_ffmpeg)
    except Exception:
        # Clean up in case of failure
        try:
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass
        return False


# Diagnostic helper
def check_system_status():
    status = {
        "ffmpeg": False,
        "whisper": False,
        "playwright": False,
        "ollama": False,
        "ollama_models": []
    }
    
    # 1. Check FFmpeg
    status["ffmpeg"] = get_ffmpeg_path() is not None
    
    # 2. Check Whisper
    try:
        import whisper
        status["whisper"] = True
    except ImportError:
        status["whisper"] = False
        
    # 3. Check Playwright
    try:
        import playwright
        status["playwright"] = True
    except ImportError:
        status["playwright"] = False
        
    # 4. Check Ollama
    try:
        import ollama
        client = ollama.Client(host='http://localhost:11434', timeout=10.0)
        models_response = client.list()
        status["ollama"] = True
        
        # Support both old SDK (dictionary) and new SDK (list objects) structures
        models_list = []
        if hasattr(models_response, 'models'):
            models_list = models_response.models
        elif isinstance(models_response, dict) and 'models' in models_response:
            models_list = models_response['models']
            
        model_names = []
        for m in models_list:
            if hasattr(m, 'model'):
                model_names.append(m.model)
            elif isinstance(m, dict):
                model_names.append(m.get('name') or m.get('model') or '')
            else:
                model_names.append(str(m))
        status["ollama_models"] = [name for name in model_names if name]
    except Exception:
        status["ollama"] = False
        
    return status

# Lazy loading singleton for Whisper to save memory
_whisper_model_instance = None
_whisper_model_lock = threading.Lock()
# Global lock to serialize Whisper transcription and prevent CPU saturation/WebSocket drops
_whisper_transcription_lock = threading.Lock()

def get_whisper_model(model_name="tiny"):
    global _whisper_model_instance
    with _whisper_model_lock:
        if _whisper_model_instance is None:
            import whisper
            import torch
            # Limit PyTorch to a single thread on CPU to save system resources
            try:
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
            except Exception:
                pass
            # Force tiny/base model to avoid RAM and CPU saturation
            _whisper_model_instance = whisper.load_model(model_name)
        return _whisper_model_instance

def transcribe_audio(audio_path, whisper_model_name="tiny", language_code="es", api_mode="Local (Whisper)", credentials_path=None):
    """
    Transcribes audio using either local Whisper or Google Cloud Speech-to-Text.
    """
    if "cloud" in api_mode.lower() or "google" in api_mode.lower():
        try:
            from google.cloud import speech
            import os
            
            if credentials_path and os.path.exists(credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                
            client = speech.SpeechClient()
            
            with open(audio_path, 'rb') as audio_file:
                content = audio_file.read()
                
            audio = speech.RecognitionAudio(content=content)
            
            gcp_lang_map = {"es": "es-ES", "en": "en-US"}
            gcp_lang = gcp_lang_map.get(language_code, "es-ES")
            
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=gcp_lang,
            )
            
            response = client.recognize(config=config, audio=audio)
            text = ""
            for result in response.results:
                text += result.alternatives[0].transcript + " "
            return text.strip()
        except Exception:
            # Fallback to local whisper on error
            pass
            
    model = get_whisper_model(whisper_model_name)
    with _whisper_transcription_lock:
        transcription = model.transcribe(audio_path, language=language_code, fp16=(model.device.type == "cuda"))
    return transcription.get("text", "")


def concat_media_files(file_list, output_path, is_video=True):
    """
    Concatenates multiple audio/video files using FFmpeg's concat demuxer with re-encoding to prevent PTS/sync issues.
    """
    import subprocess
    import tempfile
    import os
    import shutil
    
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin or not file_list:
        return False
        
    valid_files = [f for f in file_list if f and os.path.exists(f) and os.path.getsize(f) > 0]
    if not valid_files:
        return False
    if len(valid_files) == 1:
        try:
            shutil.copy(valid_files[0], output_path)
            return True
        except Exception:
            return False
        
    temp_txt = None
    try:
        fd, temp_txt = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for filepath in valid_files:
                safe_path = filepath.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                
        if is_video:
            cmd = [
                ffmpeg_bin, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", temp_txt,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ac", "1", "-ar", "16000",
                output_path
            ]
        else:
            cmd = [
                ffmpeg_bin, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", temp_txt,
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
                output_path
            ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        return res.returncode == 0
    except Exception:
        return False
    finally:
        if temp_txt and os.path.exists(temp_txt):
            try: os.remove(temp_txt)
            except Exception: pass


# --- Radio Scraper ---
class RadioScraper:
    def __init__(self, name, tunein_url, keywords, duration=60, whisper_model="tiny", language="es", transcription_mode="Local (Whisper)", credentials_path=None):
        self.name = name
        self.tunein_url = tunein_url
        self.keywords = keywords
        self.duration = duration
        self.whisper_model_name = whisper_model
        self.language = language
        self.transcription_mode = transcription_mode
        self.credentials_path = credentials_path
        self.last_segment_audio = None

    def scrape(self):
        import tempfile
        temp_audio = None
        try:
            # 1. Resolve URL with yt-dlp (Only if not a direct stream URL)
            stream_url = self.tunein_url
            if not is_direct_stream_url(self.tunein_url):
                try:
                    import yt_dlp
                    ydl_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'skip_download': True,
                        'socket_timeout': 15,
                        'logger': YtdlSilentLogger(),
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(self.tunein_url, download=False)
                        if 'url' in info:
                            stream_url = info['url']
                        elif 'formats' in info and len(info['formats']) > 0:
                            stream_url = info['formats'][0]['url']
                except Exception:
                    pass

            # 2. Check ffmpeg and record
            ffmpeg_bin = get_ffmpeg_path()
            if not ffmpeg_bin:
                raise FileNotFoundError("ffmpeg not found in PATH or Playwright cache")
                
            import uuid
            temp_dir = tempfile.gettempdir()
            temp_audio = os.path.join(temp_dir, f"radio_temp_{uuid.uuid4().hex}.wav")
            
            cmd = [ffmpeg_bin, "-y"]
            headers_str = ""
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            if "telemicro.com.do" in stream_url:
                headers_str = "Referer: https://telemicro.com.do/players/5tv/\r\n"
            elif "castr.com" in stream_url:
                headers_str = "Referer: https://player.castr.com/\r\n"
                
            if headers_str:
                cmd += ["-headers", headers_str]
            if user_agent:
                cmd += ["-user_agent", user_agent]
                
            cmd += [
                "-probesize", "32768",
                "-analyzeduration", "1000000",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-timeout", "10000000",
                "-rw_timeout", "15000000",
                "-i", stream_url, "-t", str(self.duration),
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", temp_audio
            ]
            
            # Execute ffmpeg with a timeout to avoid freezing
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.duration + 15
            )
            
            if result.returncode != 0:
                if stream_url.startswith("https://"):
                    fallback_url = stream_url.replace("https://", "http://", 1)
                    cmd_fallback = []
                    for item in cmd:
                        if item == stream_url:
                            cmd_fallback.append(fallback_url)
                        else:
                            cmd_fallback.append(item)
                    
                    result = subprocess.run(
                        cmd_fallback,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=self.duration + 15
                    )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {clean_ffmpeg_error(result.stderr)}")
            
            if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
                raise RuntimeError("FFmpeg generated an empty or non-existent audio file")
                
            # 3. Transcribe
            text = transcribe_audio(
                audio_path=temp_audio,
                whisper_model_name=self.whisper_model_name,
                language_code=self.language,
                api_mode=self.transcription_mode,
                credentials_path=self.credentials_path
            )
            
            # 4. Keyword Match
            found_kws = contains_keywords(text, self.keywords)
            if found_kws:
                temp_audio_next = os.path.join(temp_dir, f"radio_temp_next_{uuid.uuid4().hex}.wav")
                cmd_next = []
                for item in cmd:
                    if item == temp_audio:
                        cmd_next.append(temp_audio_next)
                    elif item == str(self.duration):
                        cmd_next.append("60")
                    else:
                        cmd_next.append(item)
                
                subprocess.run(cmd_next, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=80)
                
                project_dir = os.path.dirname(os.path.abspath(__file__))
                media_dir = os.path.join(project_dir, "static")
                os.makedirs(media_dir, exist_ok=True)
                audio_filename = f"radio_{int(time.time())}.wav"
                persistent_path = os.path.join(media_dir, audio_filename)
                
                concat_list = [self.last_segment_audio, temp_audio, temp_audio_next]
                success = concat_media_files(concat_list, persistent_path, is_video=False)
                
                if success:
                    audio_ref = persistent_path
                else:
                    try:
                        shutil.copy(temp_audio, persistent_path)
                        audio_ref = persistent_path
                    except Exception:
                        audio_ref = temp_audio
                        
                if os.path.exists(temp_audio_next):
                    try: os.remove(temp_audio_next)
                    except Exception: pass
                if os.path.exists(temp_audio):
                    try: os.remove(temp_audio)
                    except Exception: pass
                if self.last_segment_audio and os.path.exists(self.last_segment_audio):
                    try: os.remove(self.last_segment_audio)
                    except Exception: pass
                self.last_segment_audio = None
                
                return [{
                    "source": f"Radio ({self.name})",
                    "text": text.strip(),
                    "keywords": found_kws,
                    "timestamp": time.time(),
                    "identifier": f"radio_{int(time.time())}",
                    "simulated": False,
                    "audio_path": audio_ref
                }]
            else:
                if self.last_segment_audio and os.path.exists(self.last_segment_audio):
                    try: os.remove(self.last_segment_audio)
                    except Exception: pass
                self.last_segment_audio = temp_audio
                return []
            
        except Exception as e:
            # Clean up audio file on failure
            if temp_audio and os.path.exists(temp_audio):
                try: os.remove(temp_audio)
                except Exception: pass
            raise e

    def get_simulated_mention(self, diagnostic_msg=None):
        # 30% probability of generating simulated radio mention per cycle to emulate live radio hits
        if random.random() > 0.3:
            return []
            
        templates = [
            "El gobierno actual anunció hoy un nuevo paquete de medidas para incentivar la economía y contener la inflación en los productos de la canasta básica.",
            "Los partidos de oposición critican la política fiscal del presidente y aseguran que la deuda pública sigue creciendo sin control.",
            "Expertos debaten en el programa de hoy sobre el impacto de las reformas económicas presentadas por el presidente en el Congreso Nacional.",
            "El vocero del gobierno defendió las inversiones en educación y salud pública, asegurando que se está haciendo un uso eficiente de los recursos del estado.",
            f"La política exterior de la República Dominicana ha dado un giro importante en los últimos meses, según opinan analistas en la mesa de discusión de la {self.name}."
        ]
        text = random.choice(templates)
        found_kws = contains_keywords(text, self.keywords)
        
        return [{
            "source": f"Radio ({self.name})",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"radio_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg
        }]


# --- YouTube Scraper ---
class YouTubeScraper:
    def __init__(self, channel_url, keywords, language="es", transcription_mode="Local (Whisper)", credentials_path=None):
        self.channel_url = normalize_youtube_channel_url(channel_url)
        self.keywords = keywords
        self.channel_name = extract_youtube_channel_name(self.channel_url)
        self.language = language
        self.transcription_mode = transcription_mode
        self.credentials_path = credentials_path

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        try:
            import yt_dlp
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Check if this channel is on 1-hour cooldown
            cooldown_key = f"youtube_cooldown_until_{self.channel_name}"
            cooldown_until_str = database.get_state(cooldown_key)
            if cooldown_until_str:
                cooldown_until = float(cooldown_until_str)
                if time.time() < cooldown_until:
                    # Cooldown active! Skip.
                    cooldown_remaining = int(cooldown_until - time.time())
                    log(f"YouTube ({self.channel_name}) en enfriamiento. Siguiente escaneo en {cooldown_remaining}s.")
                    return []
            
            log(f"Iniciando escaneo de YouTube ({self.channel_name}) (hasta 2 semanas de antigüedad)...")
            
            # 1. Get channel videos list
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'playlistend': 100,  # Fetch top 100 videos to cover up to 2 weeks
                'no_warnings': True,
                'socket_timeout': 45,
                'logger': YtdlSilentLogger(),
            }
            video_ids = []
            video_map = {}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.channel_url, download=False)
                    entries = info.get('entries', [])
                    video_ids = [entry['id'] for entry in entries if entry.get('id') and len(entry['id']) == 11]
                    for entry in entries:
                        v_id = entry.get('id')
                        if v_id and len(v_id) == 11:
                            video_map[v_id] = entry.get('title') or "Video de YouTube"
            except Exception as e:
                log(f"yt-dlp falló para {self.channel_name} ({e}). Intentando fallback de RSS feed...")
                try:
                    import urllib.request
                    import re
                    
                    req = urllib.request.Request(
                        self.channel_url,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept-Language': 'en-US,en;q=0.9'
                        }
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        
                    match = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', html)
                    if not match:
                        match = re.search(r'/channel/(UC[a-zA-Z0-9_-]{22})', html)
                        
                    if match:
                        channel_id = match.group(1)
                        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                        rss_req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(rss_req, timeout=10) as rss_resp:
                            xml_content = rss_resp.read().decode('utf-8', errors='ignore')
                            
                        entries = re.findall(r'<entry>.*?</entry>', xml_content, re.DOTALL)
                        for entry in entries:
                            vid_match = re.search(r'<yt:videoId>([^<]+)</yt:videoId>', entry)
                            title_match = re.search(r'<title>([^<]+)</title>', entry)
                            if vid_match:
                                v_id = vid_match.group(1)
                                title = title_match.group(1) if title_match else "Video de YouTube"
                                video_ids.append(v_id)
                                video_map[v_id] = title
                except Exception as fallback_exc:
                    log(f"Fallback RSS falló para {self.channel_name}: {fallback_exc}")
                    
            if not video_ids:
                raise ValueError(f"No se pudieron extraer los IDs de los videos de YouTube ({self.channel_name})")
                
            # Check if the most recent video is already in database
            most_recent_id = video_ids[0]
            if database.is_processed(most_recent_id):
                # Set 1-hour cooldown!
                cooldown_until = time.time() + 3600  # 1 hour from now
                database.set_state(cooldown_key, cooldown_until)
                log(f"El video más reciente de YouTube ({self.channel_name}) ya fue procesado. Activando enfriamiento de 1 hora.")
                return []
                
            # If the most recent is not processed, we scan the ones that are not processed
            mentions = []
            api = YouTubeTranscriptApi()
            new_videos_scanned = 0
            age_checked_count = 0
            
            for video_id in video_ids:
                if database.is_processed(video_id):
                    continue
                    
                # Check video age (must be at most 2 weeks old)
                # Limit the number of age checks to 5 per cycle to prevent rate limit/blocking
                if age_checked_count >= 5:
                    log(f"Límite de verificación de antigüedad (máx 5) alcanzado para YouTube ({self.channel_name}). El resto se verificará en el siguiente ciclo.")
                    break
                    
                age_checked_count += 1
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                is_too_old = False
                try:
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'socket_timeout': 45, 'logger': YtdlSilentLogger()}) as ydl:
                        video_info = ydl.extract_info(video_url, download=False)
                        ts = video_info.get('timestamp')
                        if ts:
                            if time.time() - float(ts) > 14 * 24 * 3600:
                                is_too_old = True
                        else:
                            upload_date_str = video_info.get('upload_date')
                            if upload_date_str:
                                from datetime import datetime
                                upload_dt = datetime.strptime(upload_date_str, "%Y%m%d")
                                if time.time() - upload_dt.timestamp() > 14 * 24 * 3600:
                                    is_too_old = True
                except Exception as e:
                    log(f"Error al verificar la antigüedad del video {video_id}: {e}")
                
                if is_too_old:
                    log(f"El video {video_id} es mayor de 2 semanas. Deteniendo escaneo del canal ya que el resto son más antiguos.")
                    database.mark_processed(video_id, f"youtube_{self.channel_name}", has_mention=False)
                    break
                    
                # Prevent CPU block/saturation in sequential loop (limit to 2 new videos per cycle)
                if new_videos_scanned >= 2:
                    log(f"Límite de videos nuevos por ciclo (máx 2) alcanzado para YouTube ({self.channel_name}). El resto se procesará en los próximos ciclos.")
                    break
                    
                new_videos_scanned += 1
                video_title = video_map.get(video_id, "Video de YouTube")
                log(f"Analizando transcripción de ({self.channel_name}): '{video_title[:40]}...'")
                
                video_had_mention = False
                try:
                    transcript_list = api.list(video_id)
                    # Try Spanish (manual then automatic)
                    try:
                        transcript = transcript_list.find_transcript(['es'])
                    except Exception:
                        try:
                            transcript = transcript_list.find_generated_transcript(['es'])
                        except Exception:
                            # Try English then translate
                            try:
                                transcript = transcript_list.find_transcript(['en']).translate('es')
                            except Exception:
                                # Fallback to first available
                                transcript = next(iter(transcript_list))
                                
                    data = transcript.fetch()
                    
                    # Search keywords and build context
                    for idx, segment in enumerate(data):
                        # Support both dictionary and FetchedTranscriptSnippet object formats
                        text = segment['text'] if isinstance(segment, dict) else segment.text
                        found_kws = contains_keywords(text, self.keywords)
                        
                        if found_kws:
                            video_had_mention = True
                            segment_start = segment['start'] if isinstance(segment, dict) else segment.start
                            mention_id = f"yt_{video_id}_{round(segment_start, 1)}"
                            
                            # Extract context (2 segments before, 2 segments after)
                            start_idx = max(0, idx - 2)
                            end_idx = min(len(data), idx + 3)
                            
                            context_segments = []
                            for i in range(start_idx, end_idx):
                                seg = data[i]
                                seg_text = seg['text'] if isinstance(seg, dict) else seg.text
                                context_segments.append(seg_text)
                            context_text = " ".join(context_segments)
                            
                            mentions.append({
                                "source": f"YouTube ({self.channel_name})",
                                "text": context_text.strip(),
                                "keywords": found_kws,
                                "timestamp": time.time(),
                                "identifier": mention_id,
                                "simulated": False,
                                "metadata": {
                                    "video_url": f"https://youtu.be/{video_id}?t={int(segment_start)}",
                                    "video_id": video_id,
                                    "video_title": video_title,
                                    "seconds": int(segment_start)
                                }
                            })
                            
                    # Mark video as fully processed in database
                    database.mark_processed(video_id, f"youtube_{self.channel_name}", has_mention=video_had_mention)
                except Exception as e:
                    log(f"API de transcripciones falló para {video_id} ({type(e).__name__}). Iniciando fallback de audio local...")
                    
                    video_had_mention = False
                    temp_audio = None
                    raw_audio_path = None
                    wav_audio_path = None
                    try:
                        # 1. Download audio stream with yt-dlp
                        import yt_dlp
                        import tempfile
                        import glob
                        
                        temp_dir = tempfile.gettempdir()
                        audio_filename = f"yt_audio_{video_id}"
                        temp_template = os.path.join(temp_dir, f"{audio_filename}.%(ext)s")
                        
                        # We download only low quality audio to save bandwidth and speed up
                        ydl_opts_audio = {
                            'format': 'wa*[acodec=opus]/ba*[acodec=opus]/ba/wa', # Opus audio or best audio
                            'outtmpl': temp_template,
                            'quiet': True,
                            'no_warnings': True,
                            'max_filesize': 30 * 1024 * 1024, # Limit to 30MB max
                            'socket_timeout': 45,
                            'logger': YtdlSilentLogger(),
                        }
                        
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        log(f"Descargando audio de YouTube para {video_id}...")
                        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                            ydl.download([video_url])
                            
                        # Find the downloaded file
                        downloaded_files = glob.glob(os.path.join(temp_dir, f"{audio_filename}.*"))
                        if not downloaded_files:
                            raise FileNotFoundError("El archivo de audio no pudo ser descargado.")
                            
                        raw_audio_path = downloaded_files[0]
                        
                        # 2. Convert to 16kHz WAV mono for Whisper using FFmpeg
                        ffmpeg_bin = get_ffmpeg_path()
                        if not ffmpeg_bin:
                            raise FileNotFoundError("ffmpeg bin no encontrado")
                            
                        wav_audio_path = os.path.join(temp_dir, f"{audio_filename}.wav")
                        if os.path.exists(wav_audio_path):
                            os.remove(wav_audio_path)
                            
                        log(f"Convirtiendo audio a WAV de 16kHz para {video_id}...")
                        cmd = [
                            ffmpeg_bin, "-y", "-i", raw_audio_path, 
                            "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", wav_audio_path
                        ]
                        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                        
                        if result.returncode != 0:
                            raise RuntimeError(f"FFmpeg falló: {clean_ffmpeg_error(result.stderr)}")
                            
                        # 3. Transcribe
                        log(f"Transcribiendo audio para {video_id}...")
                        model_name = engine.whisper_model if (engine and hasattr(engine, 'whisper_model')) else "tiny"
                        full_text = transcribe_audio(
                            audio_path=wav_audio_path,
                            whisper_model_name=model_name,
                            language_code=self.language,
                            api_mode=self.transcription_mode,
                            credentials_path=self.credentials_path
                        )
                        
                        # 4. Search keywords and build context using Whisper segment timestamps
                        found_kws = contains_keywords(full_text, self.keywords)
                        if found_kws:
                            video_had_mention = True
                            segments = transcription.get("segments", [])
                            for idx, segment in enumerate(segments):
                                seg_text = segment.get("text", "")
                                seg_kws = contains_keywords(seg_text, self.keywords)
                                if seg_kws:
                                    segment_start = segment.get("start", 0)
                                    mention_id = f"yt_{video_id}_{round(segment_start, 1)}"
                                    
                                    # Extract context from segments (+/- 2 segments)
                                    start_idx = max(0, idx - 2)
                                    end_idx = min(len(segments), idx + 3)
                                    context_segments = [segments[i].get("text", "") for i in range(start_idx, end_idx)]
                                    context_text = " ".join(context_segments)
                                    
                                    mentions.append({
                                        "source": f"YouTube ({self.channel_name})",
                                        "text": context_text.strip(),
                                        "keywords": seg_kws,
                                        "timestamp": time.time(),
                                        "identifier": mention_id,
                                        "simulated": False,
                                        "metadata": {
                                            "video_url": f"https://youtu.be/{video_id}?t={int(segment_start)}",
                                            "video_id": video_id,
                                            "video_title": video_title,
                                            "seconds": int(segment_start)
                                        }
                                    })
                                    
                        # Mark video as fully processed in database
                        database.mark_processed(video_id, f"youtube_{self.channel_name}", has_mention=video_had_mention)
                        log(f"Monitoreo local finalizado para {video_id}. Mención detectada: {video_had_mention}")
                        
                    except Exception as yt_err:
                        log(f"Fallo crítico en transcripción local de {video_id}: {type(yt_err).__name__}: {str(yt_err)}")
                        # Mark as processed to prevent infinite loop errors on this video
                        database.mark_processed(video_id, f"youtube_{self.channel_name}", has_mention=False)
                    finally:
                        # Clean up temporary audio files
                        for path in [raw_audio_path, wav_audio_path]:
                            if path and os.path.exists(path):
                                try:
                                    os.remove(path)
                                except Exception:
                                    pass
                        
            if new_videos_scanned == 0:
                log(f"No se encontraron videos nuevos para escanear en YouTube ({self.channel_name}).")
            else:
                log(f"Escaneo de YouTube ({self.channel_name}) completado. {new_videos_scanned} videos analizados.")
                
            return mentions
            
        except Exception as e:
            log(f"Error raspando YouTube en vivo ({self.channel_name}): {str(e)}")
            raise e

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            f"En esta investigación de {self.channel_name}, revelamos cómo los fondos de la cooperativa de maestros COOPNAMA fueron desviados para la campaña política del partido oficialista.",
            f"El último reportaje de {self.channel_name} presenta pruebas contundentes que contradicen el informe oficial del gobierno sobre la caída del paso a desnivel de la 27 de febrero.",
            "Exclusiva: Conversamos con los maestros afectados por el esquema de préstamos irregulares en la cooperativa, quienes exigen respuestas del presidente y el ministro de educación.",
            "Analizamos el impacto en la economía nacional tras la aprobación de nuevas exenciones fiscales para sectores allegados al poder político.",
            f"El reportaje de esta semana de {self.channel_name} expone cómo operaba el vertedero ilegal de San Luis con el consentimiento de autoridades municipales y del gobierno central."
        ]
        text = random.choice(templates)
        found_kws = contains_keywords(text, self.keywords)
        video_id = "mock_yt_chan"
        
        return [{
            "source": f"YouTube ({self.channel_name})",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"yt_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "video_url": f"https://youtu.be/{video_id}",
                "video_id": video_id,
                "video_title": text[:60] + "...",
                "seconds": 45
            }
        }]


# --- Instagram Scraper ---
class InstagramScraper:
    def __init__(self, username, keywords, sessionid=None):
        self.username = username
        self.keywords = keywords
        self.sessionid = sessionid

    def _scrape_imginn(self, page, log_func):
        imginn_url = f"https://imginn.com/{self.username}/"
        log_func(f"Instagram restringido. Navegando a Imginn como bypass público: {imginn_url}")
        
        try:
            page.goto(imginn_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)
            
            # Select all post elements via page.evaluate (fast and robust)
            posts = page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a');
                    for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        if (href.includes('/p/')) {
                            const img = a.querySelector('img');
                            const alt = img ? img.getAttribute('alt') || '' : '';
                            const src = img ? img.getAttribute('src') || '' : '';
                            results.push({ href, alt, src });
                        }
                    }
                    return results;
                }
            """)
            
            mentions = []
            scanned_count = 0
            
            for post in posts:
                if scanned_count >= 16:
                    break
                href = post["href"]
                # Extract shortcode
                parts = href.split("/p/")
                shortcode = None
                if len(parts) > 1:
                    shortcode = parts[1].split("/")[0].strip()
                if not shortcode:
                    continue
                    
                identifier = f"ig_{shortcode}"
                
                # Skip if already processed in database
                if database.is_processed(identifier):
                    continue
                    
                caption_text = post["alt"]
                if not caption_text:
                    continue
                
                scanned_count += 1
                found_kws = contains_keywords(caption_text, self.keywords)
                
                # Mark as processed in database
                has_mention = len(found_kws) > 0
                database.mark_processed(identifier, "instagram", has_mention=has_mention)
                
                if found_kws:
                    post_url = f"https://www.instagram.com/p/{shortcode}/"
                    mentions.append({
                        "source": f"Instagram (@{self.username})",
                        "text": caption_text.strip(),
                        "keywords": found_kws,
                        "timestamp": time.time(),
                        "identifier": identifier,
                        "simulated": False,
                        "metadata": {
                            "post_url": post_url
                        }
                    })
            log_func(f"Bypass de Imginn completado. {scanned_count} posts analizados.")
            return mentions
        except Exception as imginn_err:
            log_func(f"Error en bypass de Imginn: {str(imginn_err)}")
            return []

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        try:
            # Import playwright inside scrape to avoid global loading delays
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            
            log(f"Iniciando escaneo de Instagram (@{self.username})...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                # Add Instagram sessionid cookie if provided to bypass login walls
                if self.sessionid:
                    context.add_cookies([{
                        'name': 'sessionid',
                        'value': self.sessionid,
                        'domain': '.instagram.com',
                        'path': '/'
                    }])
                
                # Intercept internal GraphQL profile info and scroll query APIs
                profile_json = {"edges": []}
                def handle_response(response):
                    url = response.url
                    if "web_profile_info" in url or "graphql/query" in url:
                        try:
                            data = response.json()
                            user_data = data.get("data", {}).get("user", {})
                            edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
                            if not edges:
                                edges = data.get("data", {}).get("xdt_api__v1__feed__user_timeline_graphql_connection", {}).get("edges", [])
                            if edges:
                                profile_json["edges"].extend(edges)
                        except Exception:
                            pass
                page.on("response", handle_response)
                
                url = f"https://www.instagram.com/{self.username}/"
                
                use_imginn = False
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(3000) # Give extra time for React rendering
                    
                    if "/accounts/login" in page.url or "login" in page.url.lower():
                        log("Instagram redirigió al muro de inicio de sesión. Activando bypass de Imginn...")
                        use_imginn = True
                except Exception as e:
                    log(f"Error cargando instagram.com: {str(e)}. Intentando bypass de Imginn...")
                    use_imginn = True
                
                if use_imginn:
                    mentions = self._scrape_imginn(page, log)
                    browser.close()
                    return mentions
                
                # Scroll down dynamically until we have loaded posts older than 2 weeks (or max 5 scrolls)
                max_scrolls = 5
                for scroll in range(max_scrolls):
                    # Check the oldest post timestamp we have so far
                    oldest_timestamp = None
                    for edge in profile_json.get("edges", []):
                        node = edge.get("node", {})
                        ts = node.get("taken_at_timestamp") or node.get("taken_at")
                        if ts:
                            ts = float(ts)
                            if oldest_timestamp is None or ts < oldest_timestamp:
                                oldest_timestamp = ts
                                
                    if oldest_timestamp and (time.time() - oldest_timestamp > 14 * 24 * 3600):
                        log(f"Se cargaron posts de Instagram con fecha límite (antigüedad > 2 semanas). Deteniendo scroll.")
                        break
                        
                    log(f"Haciendo scroll en Instagram (@{self.username}) para cargar posts más antiguos (scroll {scroll+1}/{max_scrolls})...")
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(3000) # Wait for requests to complete
                    except Exception:
                        break
                
                mentions = []
                scanned_count = 0
                
                # Deduplicate edges by shortcode
                seen_shortcodes = set()
                unique_edges = []
                for edge in profile_json.get("edges", []):
                    node = edge.get("node", {})
                    shortcode = node.get("shortcode") or node.get("code")
                    if shortcode and shortcode not in seen_shortcodes:
                        seen_shortcodes.add(shortcode)
                        unique_edges.append(edge)
                        
                # No longer limit to 16 posts; process all unique edges loaded within 2 weeks
                media_edges = unique_edges
                
                if media_edges:
                    log(f"API de Instagram interceptada. Procesando {len(media_edges)} posts...")
                    for edge in media_edges:
                        node = edge.get("node", {})
                        shortcode = node.get("shortcode") or node.get("code")
                        if not shortcode:
                            continue
                            
                        identifier = f"ig_{shortcode}"
                        
                        # Skip if already processed in database
                        if database.is_processed(identifier):
                            continue
                            
                        taken_at = node.get("taken_at_timestamp") or node.get("taken_at", 0)
                        if taken_at > 0:
                            if time.time() - float(taken_at) > 14 * 24 * 3600:
                                log(f"El post de Instagram {shortcode} es mayor de 2 semanas. Marcándolo como procesado y omitiéndolo.")
                                database.mark_processed(identifier, "instagram", has_mention=False)
                                continue
                        scanned_count += 1
                        caption_text = ""
                        
                        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                        if caption_edges:
                            caption_text = caption_edges[0].get("node", {}).get("text", "")
                        
                        if not caption_text and isinstance(node.get("caption"), dict):
                            caption_text = node.get("caption", {}).get("text", "")
                            
                        if not caption_text:
                            # Still mark empty captions as processed to avoid re-checking
                            database.mark_processed(identifier, "instagram", has_mention=False)
                            continue
                            
                        found_kws = contains_keywords(caption_text, self.keywords)
                        
                        # Mark as processed in database
                        has_mention = len(found_kws) > 0
                        database.mark_processed(identifier, "instagram", has_mention=has_mention)
                        
                        if found_kws:
                            post_url = f"https://www.instagram.com/p/{shortcode}/"
                            mentions.append({
                                "source": f"Instagram (@{self.username})",
                                "text": caption_text.strip(),
                                "keywords": found_kws,
                                "timestamp": taken_at,
                                "identifier": identifier,
                                "simulated": False,
                                "metadata": {
                                    "post_url": post_url
                                }
                            })
                else:
                    # Fallback to HTML img scraper
                    log("No se pudo interceptar la API. Usando raspador HTML de respaldo en instagram.com...")
                    imgs = page.locator('img').all()
                    
                    for img in imgs:
                        if scanned_count >= 16:
                            break
                        alt = img.get_attribute("alt")
                        if not alt:
                            continue
                            
                        if len(alt) > 15 and self.username.lower() in alt.lower():
                            clean_text = alt
                            if ":" in alt:
                                parts = alt.split(":", 1)
                                clean_text = parts[1].strip()
                                
                            try:
                                post_href = img.evaluate("el => el.closest('a') ? el.closest('a').href : null")
                            except Exception:
                                post_href = None
                                
                            if not post_href:
                                post_href = url
                                
                            shortcode = None
                            if "/p/" in post_href:
                                parts = post_href.split("/p/")
                                if len(parts) > 1:
                                    shortcode = parts[1].replace("/", "").strip()
                                    
                            identifier = f"ig_{shortcode}" if shortcode else f"ig_{hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:8]}"
                            
                            # Skip if already processed in database
                            if database.is_processed(identifier):
                                continue
                                
                            scanned_count += 1
                            found_kws = contains_keywords(clean_text, self.keywords)
                            
                            # Mark as processed in database
                            has_mention = len(found_kws) > 0
                            database.mark_processed(identifier, "instagram", has_mention=has_mention)
                            
                            if found_kws:
                                mentions.append({
                                    "source": f"Instagram (@{self.username})",
                                    "text": clean_text.strip(),
                                    "keywords": found_kws,
                                    "timestamp": time.time(),
                                    "identifier": identifier,
                                    "simulated": False,
                                    "metadata": {
                                        "post_url": post_href
                                    }
                                })
                    
                    if scanned_count == 0:
                        log("Cero posts obtenidos de instagram.com. Intentando bypass de Imginn...")
                        mentions = self._scrape_imginn(page, log)
                                
                log(f"Escaneo de Instagram completado. {scanned_count} posts nuevos analizados.")
                browser.close()
                return mentions
                
        except Exception as e:
            log(f"Error raspando Instagram en vivo: {str(e)}")
            raise e

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            "🇩🇴 Denuncia ciudadana: Comunitarios protestan en el Cibao exigiendo que el gobierno cumpla con el arreglo de las calles prometido por el presidente. ¿Qué opinan ustedes? 👇 #SomosPueblo #Denuncia",
            "📉 La economía dominicana según el Banco Central está de maravilla, pero la realidad en la calle es otra. Los precios de los alimentos por las nubes. #SomosPueblo #EconomiaRD #CanastaBasica",
            "📢 Fuertes declaraciones del presidente sobre el control fronterizo. ¿Crees que son efectivas o pura política electoral de cara al próximo período? Comenta abajo. #SomosPuebloRD #Frontera #Politica",
            "🚨 Escándalo de corrupción: Diputados aprueban una nueva ley que otorgaría incentivos injustos. La política dominicana sigue golpeando a la clase media. #SomosPueblo #Congreso #Corrupcion",
            "⚠️ Usuarios denuncian fallas constantes en el servicio de transporte masivo. Exigen al gobierno una auditoría transparente. ¿Hasta cuándo tendremos este servicio? #SomosPuebloRD #MetroSD #Transporte"
        ]
        text = random.choice(templates)
        found_kws = contains_keywords(text, self.keywords)
        
        return [{
            "source": f"Instagram (@{self.username})",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"ig_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "post_url": f"https://www.instagram.com/{self.username}/"
            }
        }]


# --- Twitter (X) Scraper ---
class TwitterScraper:
    def __init__(self, keywords, auth_token=None):
        self.keywords = keywords
        self.auth_token = auth_token

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        if not self.keywords:
            log("Twitter: No hay palabras clave configuradas para buscar.")
            return []
            
        all_mentions = []
        log("Iniciando búsqueda de Twitter por palabras clave...")
        
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            import urllib.parse
            import hashlib
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                # Add Twitter auth_token cookie if provided to bypass login walls
                if self.auth_token:
                    context.add_cookies([{
                        'name': 'auth_token',
                        'value': self.auth_token,
                        'domain': '.x.com',
                        'path': '/'
                    }, {
                        'name': 'auth_token',
                        'value': self.auth_token,
                        'domain': '.twitter.com',
                        'path': '/'
                    }])
                
                for keyword in self.keywords:
                    if engine and hasattr(engine, "stop_event") and engine.stop_event.is_set():
                        break
                        
                    log(f"Buscando en Twitter: '{keyword}'")
                    t_q = re.compile(r'\band\b', re.IGNORECASE).sub('AND', keyword)
                    t_q = re.compile(r'\bor\b', re.IGNORECASE).sub('OR', t_q)
                    t_q = re.compile(r'\bnot\b', re.IGNORECASE).sub('NOT', t_q)
                    
                    url = f"https://x.com/search?q={urllib.parse.quote(t_q)}&f=live"
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000) # Give extra time for React rendering
                    
                    # Check for login redirection
                    if "/login" in page.url.lower():
                        log(f"Twitter redirigió al muro de inicio de sesión. Asegúrate de configurar un 'auth_token' válido.")
                        break
                    
                    # Scroll down once/twice to trigger page load
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                        
                    # Extract tweets
                    tweets = page.evaluate("""
                        () => {
                            const results = [];
                            const tweetElements = document.querySelectorAll('article[data-testid="tweet"]');
                            for (const el of tweetElements) {
                                // Text of the tweet
                                const textEl = el.querySelector('[data-testid="tweetText"]');
                                const text = textEl ? textEl.innerText : '';
                                
                                // Link/status URL and datetime
                                const links = el.querySelectorAll('a');
                                let tweetUrl = '';
                                for (const a of links) {
                                    const href = a.getAttribute('href') || '';
                                    if (href.includes('/status/')) {
                                        tweetUrl = 'https://x.com' + href;
                                        break;
                                    }
                                }
                                
                                const timeEl = el.querySelector('time');
                                const datetime = timeEl ? timeEl.getAttribute('datetime') : '';
                                
                                results.push({ text, url: tweetUrl, datetime });
                            }
                            return results;
                        }
                    """)
                    
                    scanned_count = 0
                    for tw in tweets:
                        tweet_text = tw["text"]
                        tweet_url = tw["url"]
                        datetime_str = tw["datetime"]
                        
                        if not tweet_text or not tweet_url:
                            continue
                            
                        # Extract unique tweet status ID
                        tweet_id = None
                        parts = tweet_url.split("/status/")
                        if len(parts) > 1:
                            tweet_id = parts[1].split("?")[0].strip()
                        
                        if not tweet_id:
                            tweet_id = hashlib.md5(tweet_url.encode()).hexdigest()
                            
                        identifier = f"tw_{tweet_id}"
                        
                        if database.is_processed(identifier):
                            continue
                            
                        # Parse timestamp if datetime exists
                        taken_at = 0
                        if datetime_str:
                            try:
                                import datetime as dt
                                clean_dt = datetime_str.split(".")[0].replace("Z", "")
                                parsed_dt = dt.datetime.strptime(clean_dt, "%Y-%m-%dT%H:%M:%S")
                                taken_at = parsed_dt.replace(tzinfo=dt.timezone.utc).timestamp()
                            except Exception:
                                taken_at = 0
                        
                        # Skip tweets older than 2 weeks
                        if taken_at > 0 and (time.time() - taken_at > 14 * 24 * 3600):
                            database.mark_processed(identifier, "twitter", has_mention=False)
                            continue
                        
                        scanned_count += 1
                        found_kws = contains_keywords(tweet_text, self.keywords)
                        has_mention = len(found_kws) > 0
                        database.mark_processed(identifier, "twitter", has_mention=has_mention)
                        
                        if found_kws:
                            all_mentions.append({
                                "source": "Twitter",
                                "text": tweet_text.strip(),
                                "keywords": found_kws,
                                "timestamp": taken_at if taken_at > 0 else time.time(),
                                "identifier": identifier,
                                "simulated": False,
                                "metadata": {
                                    "post_url": tweet_url
                                }
                            })
                    log(f"Búsqueda de '{keyword}' completada en Twitter. {scanned_count} tuits nuevos analizados.")
                    
                browser.close()
                return all_mentions
        except Exception as e:
            log(f"Error raspando Twitter en vivo: {str(e)}")
            return []

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            "🚨 ÚLTIMA HORA: Se reporta un fuerte incendio en la Zona Industrial de Herrera. Los bomberos ya están en el lugar intentando sofocar las llamas. Se pide precaución. #NoticiasRD #SomosPueblo",
            "📊 Encuesta: ¿Qué opina la población sobre la nueva propuesta de reforma fiscal del gobierno? La clase media teme el impacto en el costo de la vida. #Opinión #SomosPuebloRD",
            "📢 Ciudadanos denuncian en redes sociales la falta de patrullaje policial en sectores de Santo Domingo Este tras ola de asaltos. Exigen respuesta de las autoridades.",
            "⚠️ Atención: El COE coloca varias provincias en alerta verde por la incidencia de una vaguada que generará lluvias moderadas en las próximas horas. #ClimaRD #COE",
            "💰 Denuncia: Se destapan supuestas irregularidades en la compra de insumos de una entidad pública. Exigen investigación de las autoridades. #SomosPueblo"
        ]
        text = random.choice(templates)
        found_kws = contains_keywords(text, self.keywords)
        
        return [{
            "source": "Twitter",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"tw_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "post_url": "https://x.com/search"
            }
        }]


# --- Facebook Scraper ---
class FacebookScraper:
    def __init__(self, keywords, cookies_str=None):
        self.keywords = keywords
        self.cookies_str = cookies_str

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            import urllib.parse
            import hashlib
            import time
            import json
            
            if not self.keywords:
                log("Facebook: No hay palabras clave configuradas para buscar.")
                return []
                
            all_mentions = []
            log("Iniciando búsqueda de Facebook por palabras clave...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                # Add Facebook cookies if provided to bypass login walls
                if self.cookies_str:
                    try:
                        cookies_list = json.loads(self.cookies_str)
                        if isinstance(cookies_list, list):
                            for cookie in cookies_list:
                                if 'domain' not in cookie:
                                    cookie['domain'] = '.facebook.com'
                                context.add_cookies([cookie])
                        else:
                            raise ValueError()
                    except Exception:
                        # Parse as key-value semicolon-separated
                        parts = self.cookies_str.split(";")
                        cookies_to_add = []
                        for part in parts:
                            part = part.strip()
                            if "=" in part:
                                name, val = part.split("=", 1)
                                cookies_to_add.append({
                                    'name': name.strip(),
                                    'value': val.strip(),
                                    'domain': '.facebook.com',
                                    'path': '/'
                                })
                        if cookies_to_add:
                            context.add_cookies(cookies_to_add)
                
                # Search Facebook for each keyword
                for keyword in self.keywords:
                    if engine and hasattr(engine, "stop_event") and engine.stop_event.is_set():
                        break
                        
                    log(f"Buscando en Facebook: '{keyword}'")
                    fb_q = re.compile(r'\band\b', re.IGNORECASE).sub('AND', keyword)
                    fb_q = re.compile(r'\bor\b', re.IGNORECASE).sub('OR', fb_q)
                    fb_q = re.compile(r'\bnot\b', re.IGNORECASE).sub('NOT', fb_q)
                    
                    url = f"https://www.facebook.com/search/posts/?q={urllib.parse.quote(fb_q)}"
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000) # Give extra time for rendering
                    
                    # Check for login redirect or banner
                    if "login" in page.url.lower() and not self.cookies_str:
                        log("Facebook redirigió a la página de login. Se requieren cookies para continuar.")
                        browser.close()
                        return all_mentions
                    
                    # Scroll down multiple times to load a larger list of search results
                    for i in range(5):
                        if engine and hasattr(engine, "stop_event") and engine.stop_event.is_set():
                            break
                        try:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(2000)
                        except Exception:
                            pass
                    
                    # Extract posts
                    posts = page.evaluate("""
                        () => {
                            const results = [];
                            const articles = document.querySelectorAll('div[role="article"]');
                            for (const el of articles) {
                                let text = '';
                                const msgEl = el.querySelector('div[data-ad-preview="message"]');
                                if (msgEl) {
                                    text = msgEl.innerText;
                                } else {
                                    const dirs = el.querySelectorAll('div[dir="auto"]');
                                    let textParts = [];
                                    const ignoreWords = ['me gusta', 'comentar', 'compartir', 'ver más', 'ver traducción', 'escribe un comentario', 'compartido con'];
                                    for (const d of dirs) {
                                        const val = d.innerText.trim();
                                        if (val.length > 0) {
                                            const lowerVal = val.toLowerCase();
                                            const isReactions = /^\d+$/.test(val) || /^\d+\s*(mil|m)?$/i.test(val);
                                            const isIgnore = ignoreWords.some(word => lowerVal.includes(word));
                                            if (!isReactions && !isIgnore) {
                                                textParts.push(val);
                                            }
                                        }
                                    }
                                    textParts = [...new Set(textParts)];
                                    text = textParts.join('\\n');
                                }
                                
                                // Find link
                                const links = el.querySelectorAll('a');
                                let postUrl = '';
                                for (const a of links) {
                                    const href = a.getAttribute('href') || '';
                                    if (href.includes('/posts/') || href.includes('/permalink.php') || href.includes('/photos/') || href.includes('/story.php') || href.includes('/videos/') || href.includes('/groups/')) {
                                        if (href.startsWith('/')) {
                                            postUrl = 'https://www.facebook.com' + href;
                                        } else if (href.startsWith('https://')) {
                                            postUrl = href;
                                        }
                                        if (postUrl) {
                                            postUrl = postUrl.split('?')[0];
                                            break;
                                        }
                                    }
                                }
                                results.push({ text, url: postUrl });
                            }
                            return results;
                        }
                    """)
                    
                    scanned_count = 0
                    for pt in posts:
                        post_text = pt["text"]
                        post_url = pt["url"]
                        
                        if not post_text:
                            continue
                        
                        # Generate a unique identifier
                        if post_url:
                            h = hashlib.md5(post_url.encode()).hexdigest()
                        else:
                            h = hashlib.md5(post_text.encode()).hexdigest()
                            post_url = f"https://www.facebook.com/search/posts/?q={urllib.parse.quote(keyword)}"
                            
                        identifier = f"fb_{h}"
                        
                        if database.is_processed(identifier):
                            continue
                        
                        scanned_count += 1
                        found_kws = contains_keywords(post_text, self.keywords)
                        # Since this post is retrieved from search for 'keyword', it is a valid match!
                        if keyword not in found_kws:
                            found_kws.append(keyword)
                            
                        has_mention = len(found_kws) > 0
                        database.mark_processed(identifier, "facebook", has_mention=has_mention)
                        
                        if found_kws:
                            all_mentions.append({
                                "source": f"Facebook (Búsqueda: {keyword})",
                                "text": post_text.strip(),
                                "keywords": found_kws,
                                "timestamp": time.time(),
                                "identifier": identifier,
                                "simulated": False,
                                "metadata": {
                                    "post_url": post_url
                                }
                            })
                    log(f"Búsqueda de '{keyword}' completada. {scanned_count} posts analizados.")
                
                browser.close()
                return all_mentions
        except Exception as e:
            log(f"Error raspando Facebook en vivo: {str(e)}")
            return []

    def get_simulated_mention(self, diagnostic_msg=None):
        import urllib.parse
        if random.random() > 0.3:
            return []
        
        templates = [
            "🔴 EN VIVO: Conversando con líderes comunitarios sobre los problemas de agua y electricidad en el municipio. Déjanos tus preguntas en los comentarios y comparte esta transmisión.",
            "📝 EDITORIAL: La necesidad de una verdadera transparencia legislativa. No basta con discursos, se necesitan hechos y auditorías reales de cada peso invertido en nuestro país.",
            "📸 Reportan vertedero improvisado afectando la salud de decenas de familias en Los Alcarrizos. Hacemos un llamado a la alcaldía para resolver esta preocupante situación de inmediato.",
            "🤝 Hoy estuvimos acompañando a los jóvenes del sector en su torneo de baloncesto, apoyando el deporte y alejándolos de los vicios. ¡El cambio comienza desde los barrios!",
            "🚨 ALERTA: Estafadores están utilizando perfiles falsos para ofrecer empleos en nombre de nuestra organización. Recuerda que no solicitamos dinero para postularte."
        ]
        text = random.choice(templates)
        
        if self.keywords:
            kw = random.choice(self.keywords)
            text = f"{text} #{kw}"
            
        found_kws = contains_keywords(text, self.keywords)
        kw_for_source = found_kws[0] if found_kws else (self.keywords[0] if self.keywords else "búsqueda")
        
        return [{
            "source": f"Facebook (Búsqueda: {kw_for_source})",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"fb_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "post_url": f"https://www.facebook.com/search/posts/?q={urllib.parse.quote(kw_for_source)}"
            }
        }]



# --- Google News Scraper ---
class GoogleNewsScraper:
    def __init__(self, keywords, language="es", country="DO"):
        self.keywords = keywords
        self.language = language
        self.country = country

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        if not self.keywords:
            return []
            
        all_mentions = []
        log(f"Iniciando búsqueda en Google News (Región: {self.country}, Idioma: {self.language})...")
        
        import urllib.request
        import xml.etree.ElementTree as ET
        import email.utils
        import hashlib
        import urllib.parse
        import re
        
        hl, gl, ceid = "es-419", "DO", "DO:es-419"
        if self.language == "en":
            hl = "en"
            gl = "US"
            ceid = "US:en"
        else:
            if self.country == "DO":
                hl, gl, ceid = "es-419", "DO", "DO:es-419"
            elif self.country == "MX":
                hl, gl, ceid = "es-419", "MX", "MX:es-419"
            elif self.country == "ES":
                hl, gl, ceid = "es", "ES", "ES:es"
            else:
                hl, gl, ceid = "es-419", "US", "US:es-419"
                
        for keyword in self.keywords:
            if engine and hasattr(engine, "stop_event") and engine.stop_event.is_set():
                break
                
            log(f"Buscando en Google News RSS: '{keyword}'")
            gnews_q = re.compile(r'\band\b', re.IGNORECASE).sub('AND', keyword)
            gnews_q = re.compile(r'\bor\b', re.IGNORECASE).sub('OR', gnews_q)
            gnews_q = re.compile(r'\bnot\b', re.IGNORECASE).sub('NOT', gnews_q)
            
            q = urllib.parse.quote(gnews_q)
            feed_url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
            
            try:
                req = urllib.request.Request(
                    feed_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=15.0) as response:
                    xml_data = response.read()
                    
                xml_str = xml_data.decode('utf-8', errors='replace')
                xml_str = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', xml_str)
                
                root = ET.fromstring(xml_str.encode('utf-8'))
                items = root.findall('.//item')
                
                scanned_count = 0
                for item in items:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""
                    desc = desc_elem.text if desc_elem is not None else ""
                    
                    title = clean_html_text(title)
                    desc = clean_html_text(desc)
                    
                    if not link:
                        continue
                        
                    identifier = f"gnews_{hashlib.md5(link.encode('utf-8')).hexdigest()[:12]}"
                    
                    if database.is_processed(identifier):
                        continue
                        
                    pubdate_elem = item.find('pubDate')
                    pubdate_text = pubdate_elem.text if pubdate_elem is not None else ""
                    is_too_old = False
                    pub_dt = None
                    if pubdate_text:
                        try:
                            pub_dt = email.utils.parsedate_to_datetime(pubdate_text)
                            if time.time() - pub_dt.timestamp() > 14 * 24 * 3600:
                                is_too_old = True
                        except Exception:
                            pass
                            
                    if is_too_old:
                        database.mark_processed(identifier, "google_news", has_mention=False)
                        continue
                        
                    scanned_count += 1
                    full_text = f"{title}. {desc}"
                    found_kws = contains_keywords(full_text, self.keywords)
                    
                    if keyword not in found_kws:
                        found_kws.append(keyword)
                        
                    database.mark_processed(identifier, "google_news", has_mention=len(found_kws) > 0)
                    
                    if found_kws:
                        publisher = "Google News"
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            if len(parts) > 1:
                                publisher = parts[1].strip()
                                
                        all_mentions.append({
                            "source": f"📰 Google News ({publisher})",
                            "text": f"{title}. {desc}".strip(),
                            "keywords": found_kws,
                            "timestamp": pub_dt.timestamp() if pub_dt else time.time(),
                            "identifier": identifier,
                            "simulated": False,
                            "metadata": {
                                "post_url": link
                            }
                        })
                log(f"Búsqueda de '{keyword}' en Google News completada. {scanned_count} noticias nuevas analizadas.")
            except Exception as e:
                log(f"Error buscando '{keyword}' en Google News: {str(e)}")
                
        return all_mentions

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            "El presidente Luis Abinader anuncia nuevas medidas económicas para la estabilización de los precios de la canasta básica en República Dominicana.",
            "Aumento en el flujo de turistas en Punta Cana alcanza niveles récord durante el último trimestre, consolidando la reactivación del sector.",
            "Especialistas advierten sobre la necesidad de reformas estructurales en el sector eléctrico para evitar pérdidas y mejorar el servicio.",
            "Inauguran nuevo centro educativo tecnológico en Santiago con capacidad para más de 500 estudiantes de escasos recursos."
        ]
        text = random.choice(templates)
        
        if self.keywords:
            kw = random.choice(self.keywords)
            text = f"{text} Buscan solucionar tema de {kw}."
            
        found_kws = contains_keywords(text, self.keywords)
        kw_for_source = found_kws[0] if found_kws else (self.keywords[0] if self.keywords else "noticia")
        
        return [{
            "source": f"📰 Google News (Simulado)",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"gnews_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "post_url": "https://news.google.com"
            }
        }]


# --- RSS Feed Scraper ---
class RSSScraper:
    def __init__(self, feed_url, keywords):
        self.feed_url = feed_url
        self.keywords = keywords
        
        domain = extract_rss_domain(feed_url)
        if "news.google.com" in feed_url:
            import urllib.parse
            try:
                parsed = urllib.parse.urlparse(feed_url)
                params = urllib.parse.parse_qs(parsed.query)
                q_val = params.get("q", [""])[0]
                if q_val:
                    self.feed_name = f"Google News: {q_val}"
                else:
                    self.feed_name = "Google News"
            except Exception:
                self.feed_name = "Google News"
        else:
            self.feed_name = domain

    def scrape(self, engine=None):
        def log(msg):
            if engine and hasattr(engine, "log_event"):
                engine.log_event(msg)
                
        try:
            import urllib.request
            import xml.etree.ElementTree as ET
            import html
            import hashlib
            
            log(f"Iniciando escaneo de RSS ({self.feed_name})...")
            
            req = urllib.request.Request(
                self.feed_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=45.0) as response:
                xml_data = response.read()
                
            # Clean XML string to avoid strict parsing issues
            xml_str = xml_data.decode('utf-8', errors='replace')
            # Replace unescaped & with &amp;
            xml_str = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', xml_str)
            
            root = ET.fromstring(xml_str.encode('utf-8'))
            items = root.findall('.//item')
            log(f"RSS ({self.feed_name}) parseado. {len(items)} noticias encontradas.")
            
            mentions = []
            scanned_count = 0
            
            for item in items:
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                desc = desc_elem.text if desc_elem is not None else ""
                
                title = clean_html_text(title)
                desc = clean_html_text(desc)
                
                if not link:
                    continue
                    
                identifier = f"rss_{hashlib.md5(link.encode('utf-8')).hexdigest()[:12]}"
                
                if database.is_processed(identifier):
                    continue
                    
                # Check RSS item age (must be at most 2 weeks old)
                pubdate_elem = item.find('pubDate')
                pubdate_text = pubdate_elem.text if pubdate_elem is not None else ""
                is_too_old = False
                if pubdate_text:
                    try:
                        import email.utils
                        pub_dt = email.utils.parsedate_to_datetime(pubdate_text)
                        if time.time() - pub_dt.timestamp() > 14 * 24 * 3600:
                            is_too_old = True
                    except Exception:
                        pass
                        
                if is_too_old:
                    database.mark_processed(identifier, f"rss_{self.feed_name}", has_mention=False)
                    continue
                    
                scanned_count += 1
                full_text = f"{title}. {desc}"
                found_kws = contains_keywords(full_text, self.keywords)
                
                database.mark_processed(identifier, f"rss_{self.feed_name}", has_mention=len(found_kws) > 0)
                
                if found_kws:
                    mentions.append({
                        "source": f"RSS ({self.feed_name})",
                        "text": full_text.strip(),
                        "keywords": found_kws,
                        "timestamp": time.time(),
                        "identifier": identifier,
                        "simulated": False,
                        "metadata": {
                            "post_url": link,
                            "title": title
                        }
                    })
                    
            log(f"Escaneo de RSS ({self.feed_name}) completado. {scanned_count} noticias nuevas analizadas.")
            return mentions
            
        except Exception as e:
            log(f"Error raspando RSS en vivo ({self.feed_name}): {str(e)}")
            raise e

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            ("Denuncian sobrefacturación en el Ministerio de Obras Públicas",
             f"Una investigación de {self.feed_name} revela contratos millonarios adjudicados de manera directa a empresas vinculadas con funcionarios gubernamentales."),
            ("Cámara de Cuentas detecta graves irregularidades en auditoría",
             "El informe detalla el desvío de fondos públicos que debieron ser utilizados en el desarrollo de la red vial nacional, afectando directamente la economía pública."),
            ("Sectores sociales anuncian protestas en rechazo a la reforma fiscal",
             "Comunitarios y sindicatos aseguran que el proyecto del presidente golpeará duramente a la clase media y a los pequeños empresarios."),
            ("Escándalo de corrupción sacude a directiva de cooperativa de maestros",
             "Miembros exigen transparencia tras descubrirse desvíos de ahorros en COOPNAMA para inversiones de alto riesgo no aprobadas."),
            ("El presidente inaugura nuevo proyecto de energía renovable en el sur",
             "El gobierno destaca que esta iniciativa beneficiará la generación eléctrica limpia y reducirá la dependencia de combustibles fósiles.")
        ]
        title, desc = random.choice(templates)
        full_text = f"{title}. {desc}"
        found_kws = contains_keywords(full_text, self.keywords)
        
        sim_url = f"https://{self.feed_name}/noticia-simulada"
        identifier = f"rss_sim_{int(time.time())}"
        
        return [{
            "source": f"RSS ({self.feed_name})",
            "text": full_text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": identifier,
            "simulated": True,
            "diagnostic": diagnostic_msg,
            "metadata": {
                "post_url": sim_url,
                "title": title
            }
        }]


# --- TV Scraper ---
class TVScraper:
    def __init__(self, name, stream_url, keywords, duration=60, whisper_model="tiny", language="es", transcription_mode="Local (Whisper)", credentials_path=None):
        self.name = name
        self.stream_url = stream_url
        self.keywords = keywords
        self.duration = duration
        self.whisper_model_name = whisper_model
        self.language = language
        self.transcription_mode = transcription_mode
        self.credentials_path = credentials_path
        self.last_segment_video = None
        self.last_segment_audio = None

    def scrape(self):
        import tempfile
        import time
        ts = int(time.time())
        temp_video = None
        temp_audio = None
        try:
            # 1. Resolve URL with yt-dlp (Only for YouTube or non-direct stream URLs)
            is_youtube = "youtube.com" in self.stream_url.lower() or "youtu.be" in self.stream_url.lower()
            resolved_url = None
            
            if is_youtube or not is_direct_stream_url(self.stream_url):
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'socket_timeout': 15,
                    'logger': YtdlSilentLogger(),
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(self.stream_url, download=False)
                        if 'url' in info:
                            resolved_url = info['url']
                        elif 'formats' in info and len(info['formats']) > 0:
                            for f in info['formats']:
                                if f.get('protocol') == 'm3u8_native' or '.m3u8' in f.get('url', ''):
                                    resolved_url = f['url']
                                    break
                            if not resolved_url:
                                resolved_url = info['formats'][0]['url']
                    except Exception as e:
                        if is_youtube:
                            err_msg = str(e)
                            if "not currently live" in err_msg or "is not live" in err_msg:
                                raise Exception("El canal de YouTube no está transmitiendo en vivo actualmente.")
                            else:
                                raise Exception(f"No se pudo resolver la transmisión en vivo de YouTube: {err_msg}")
                        pass
                        
            if not resolved_url:
                if is_youtube:
                    raise Exception("No se pudo obtener la URL de transmisión en vivo de YouTube.")
                resolved_url = self.stream_url

            # 2. Check ffmpeg and record video + audio
            ffmpeg_bin = get_ffmpeg_path()
            if not ffmpeg_bin:
                raise FileNotFoundError("ffmpeg not found in PATH or Playwright cache")
                
            import uuid
            temp_dir = tempfile.gettempdir()
            unique_id = uuid.uuid4().hex
            temp_video = os.path.join(temp_dir, f"tv_temp_{unique_id}.mp4")
            temp_audio = os.path.join(temp_dir, f"tv_temp_{unique_id}.wav")
            
            # Record video (MP4) from live stream for duration seconds
            cmd_video = [ffmpeg_bin, "-y"]
            headers_str = ""
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            if "telemicro.com.do" in resolved_url:
                headers_str = "Referer: https://telemicro.com.do/players/5tv/\r\n"
            elif "castr.com" in resolved_url:
                headers_str = "Referer: https://player.castr.com/\r\n"
                
            if headers_str:
                cmd_video += ["-headers", headers_str]
            if user_agent:
                cmd_video += ["-user_agent", user_agent]
                
            cmd_video += [
                "-probesize", "32768",
                "-analyzeduration", "1000000",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-timeout", "10000000",
                "-rw_timeout", "15000000",
                "-i", resolved_url, "-t", str(self.duration),
                "-c:v", "copy",
                "-c:a", "aac", "-ac", "1", "-ar", "16000", temp_video
            ]
            
            result = subprocess.run(cmd_video, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.duration + 20)
            if result.returncode != 0:
                if resolved_url.startswith("https://"):
                    fallback_url = resolved_url.replace("https://", "http://", 1)
                    cmd_video_fallback = []
                    for item in cmd_video:
                        if item == resolved_url:
                            cmd_video_fallback.append(fallback_url)
                        else:
                            cmd_video_fallback.append(item)
                    
                    result = subprocess.run(
                        cmd_video_fallback,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=self.duration + 20
                    )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg video recording failed: {clean_ffmpeg_error(result.stderr)}")
                
            # Extract audio track to WAV mono 16kHz
            cmd_audio = [
                ffmpeg_bin, "-y", "-i", temp_video, "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", temp_audio
            ]
            subprocess.run(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
                raise RuntimeError("Failed to extract audio track from video clip")
                
            # 3. Transcribe
            text = transcribe_audio(
                audio_path=temp_audio,
                whisper_model_name=self.whisper_model_name,
                language_code=self.language,
                api_mode=self.transcription_mode,
                credentials_path=self.credentials_path
            )
            
            if os.path.exists(temp_audio):
                try: os.remove(temp_audio)
                except Exception: pass
                
            # 4. Keyword Match
            found_kws = contains_keywords(text, self.keywords)
            if found_kws:
                temp_video_next = os.path.join(temp_dir, f"tv_temp_next_{uuid.uuid4().hex}.mp4")
                cmd_video_next = []
                for item in cmd_video:
                    if item == temp_video:
                        cmd_video_next.append(temp_video_next)
                    elif item == str(self.duration):
                        cmd_video_next.append("60")
                    else:
                        cmd_video_next.append(item)
                        
                subprocess.run(cmd_video_next, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=80)
                
                project_dir = os.path.dirname(os.path.abspath(__file__))
                media_dir = os.path.join(project_dir, "static")
                os.makedirs(media_dir, exist_ok=True)
                video_filename = f"tv_{ts}.mp4"
                persistent_path = os.path.join(media_dir, video_filename)
                
                concat_list = [self.last_segment_video, temp_video, temp_video_next]
                success = concat_media_files(concat_list, persistent_path, is_video=True)
                
                if success:
                    video_ref = persistent_path
                else:
                    try:
                        shutil.copy(temp_video, persistent_path)
                        video_ref = persistent_path
                    except Exception:
                        video_ref = temp_video
                        
                if os.path.exists(temp_video_next):
                    try: os.remove(temp_video_next)
                    except Exception: pass
                if os.path.exists(temp_video):
                    try: os.remove(temp_video)
                    except Exception: pass
                if self.last_segment_video and os.path.exists(self.last_segment_video):
                    try: os.remove(self.last_segment_video)
                    except Exception: pass
                self.last_segment_video = None
                
                return [{
                    "source": f"TV ({self.name})",
                    "text": text.strip(),
                    "keywords": found_kws,
                    "timestamp": time.time(),
                    "identifier": f"tv_{ts}",
                    "simulated": False,
                    "video_path": video_ref
                }]
            else:
                if self.last_segment_video and os.path.exists(self.last_segment_video):
                    try: os.remove(self.last_segment_video)
                    except Exception: pass
                self.last_segment_video = temp_video
                return []
                
        except Exception as e:
            for path in [temp_video, temp_audio]:
                if path and os.path.exists(path):
                    try: os.remove(path)
                    except Exception: pass
            raise e

    def get_simulated_mention(self, diagnostic_msg=None):
        if random.random() > 0.3:
            return []
            
        templates = [
            "En el debate televisado de hoy, los ministros defendieron el plan nacional de desarrollo y el presupuesto asignado por el presidente.",
            "Reportajes especiales de televisión revelan el descontento de la población con el aumento del costo de la canasta básica y la inflación.",
            "Analistas políticos discuten en vivo sobre la transparencia electoral y las reformas del congreso propuestas por el partido de gobierno.",
            "La cobertura de prensa televisiva de esta noche destaca el impacto social de la nueva reforma fiscal en el sector empresarial."
        ]
        text = random.choice(templates)
        found_kws = contains_keywords(text, self.keywords)
        
        return [{
            "source": f"TV ({self.name})",
            "text": text,
            "keywords": found_kws,
            "timestamp": time.time(),
            "identifier": f"tv_sim_{int(time.time())}",
            "simulated": True,
            "diagnostic": diagnostic_msg
        }]


# --- AI Ollama Analyzer ---
class OllamaAnalyzer:
    def __init__(self, model_name="gemma4:e2b", api_mode="Local (Ollama/Gemma)", credentials_path=None, api_key=None):
        self.model_name = model_name
        self.api_mode = api_mode
        self.credentials_path = credentials_path
        self.api_key = api_key

    def generate_text(self, system_prompt, prompt_text):
        """
        Generates text using the selected API mode (Ollama, Vertex AI, or Generative AI Developer API).
        """
        api_mode_lower = self.api_mode.lower()
        
        if "vertex" in api_mode_lower or "cloud" in api_mode_lower:
            # Google Cloud Vertex AI Gemini
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel
                import json
                import os
                
                if self.credentials_path and os.path.exists(self.credentials_path):
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
                    with open(self.credentials_path, 'r') as f:
                        creds = json.load(f)
                        project_id = creds.get("project_id")
                else:
                    project_id = None
                    
                vertexai.init(project=project_id, location="us-central1")
                model = GenerativeModel("gemini-1.5-flash")
                
                combined_prompt = f"{system_prompt}\n\n{prompt_text}"
                response = model.generate_content(combined_prompt)
                return response.text
            except Exception as e:
                raise RuntimeError(f"Vertex AI Gemini failed: {str(e)}")
                
        elif "api key" in api_mode_lower or "generative" in api_mode_lower or "developer" in api_mode_lower:
            # Google Generative AI (Developer API Key)
            try:
                import google.generativeai as genai
                
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                combined_prompt = f"{system_prompt}\n\n{prompt_text}"
                response = model.generate_content(combined_prompt)
                return response.text
            except Exception as e:
                raise RuntimeError(f"Gemini API Key failed: {str(e)}")
                
        else:
            # Local Ollama
            try:
                import ollama
                client = ollama.Client(host='http://localhost:11434', timeout=30.0)
                response = client.chat(
                    model=self.model_name,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': prompt_text}
                    ]
                )
                return response['message']['content']
            except Exception as e:
                raise RuntimeError(f"Ollama local failed: {str(e)}")

    def analyze(self, text):
        try:
            system_prompt = (
                "Eres un analista de PR. Lee este texto extraído de un medio dominicano. "
                "Extrae el sentimiento general (Positivo, Negativo o Neutral) y escribe un resumen estrictamente de una sola línea. "
                "Devuelve el resultado en formato JSON con las claves: 'sentimiento' y 'resumen'."
            )
            
            content = self.generate_text(system_prompt, text)
            parsed_json = self._parse_json(content)
            parsed_json["ai_analyzed"] = True
            parsed_json["model_used"] = "Gemini" if "local" not in self.api_mode.lower() else self.model_name
            return parsed_json
            
        except Exception as e:
            # Connect fallback rules on failure
            result = self._analyze_fallback(text)
            result["ai_analyzed"] = False
            result["diagnostic"] = f"AI Analysis failed ({type(e).__name__}: {str(e)})."
            return result

    def _parse_json(self, response_text):
        # Look for standard JSON blocks
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                # Validate keys
                if "sentimiento" in data and "resumen" in data:
                    # Clean sentiment case
                    sent = data["sentimiento"].strip().capitalize()
                    if sent in ["Positivo", "Negativo", "Neutral"]:
                        data["sentimiento"] = sent
                    return data
            except json.JSONDecodeError:
                pass
                
        # Clean markdown code blocks
        clean_text = response_text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
                
        # Regex extraction fallback if JSON format is broken
        sentiment_match = re.search(r'"sentimiento"\s*:\s*"([^"]+)"', response_text, re.IGNORECASE)
        resumen_match = re.search(r'"resumen"\s*:\s*"([^"]+)"', response_text, re.IGNORECASE)
        
        if sentiment_match and resumen_match:
            sent = sentiment_match.group(1).strip().capitalize()
            if sent not in ["Positivo", "Negativo", "Neutral"]:
                sent = "Neutral"
            return {
                "sentimiento": sent,
                "resumen": resumen_match.group(1).strip()
            }
            
        # Parse crude text indicators
        text_lower = response_text.lower()
        sentiment = "Neutral"
        if "negativo" in text_lower: sentiment = "Negativo"
        elif "positivo" in text_lower: sentiment = "Positivo"
        
        # Simple extraction of one-line summaries
        resumen = "Resumen no estructurado del análisis de medios."
        lines = [l.strip() for l in response_text.split('\n') if len(l.strip()) > 10 and not l.startswith('{') and not l.startswith('}')]
        if lines:
            resumen = lines[0]
            
        return {
            "sentimiento": sentiment,
            "resumen": resumen
        }

    def _analyze_fallback(self, text):
        text_lower = text.lower()
        
        # Keyword scoring for sentiment
        pos_words = ["inversión", "inversion", "apoya", "desarrollo", "beneficia", "éxito", "exito", "positivo", "logro", "mejoría", "mejoria", "avanza", "transparencia"]
        neg_words = ["protesta", "escándalo", "escandalo", "corrupción", "corrupcion", "robo", "crisis", "inflación", "inflacion", "queja", "crítica", "critica", "daño", "colapso", "falta", "irregularidad"]
        
        pos_count = sum(1 for w in pos_words if w in text_lower)
        neg_count = sum(1 for w in neg_words if w in text_lower)
        
        if pos_count > neg_count:
            sentiment = "Positivo"
        elif neg_count > pos_count:
            sentiment = "Negativo"
        else:
            sentiment = "Neutral"
            
        # Context-dependent summaries
        resumen = "Mención relevante sobre temas gubernamentales y sociales."
        if "gobierno" in text_lower or "presidente" in text_lower:
            if sentiment == "Negativo":
                resumen = "Reporte sobre denuncias y descontento social hacia la administración gubernamental."
            elif sentiment == "Positivo":
                resumen = "Destacan iniciativas positivas y proyectos de desarrollo impulsados por el gobierno."
        elif "política" in text_lower or "politica" in text_lower:
            resumen = "Análisis del escenario político dominicano y dinámicas de partidos legislativos."
            
        return {
            "sentimiento": sentiment,
            "resumen": resumen
        }

def get_scraper_display_name(scraper):
    cls_name = scraper.__class__.__name__
    if cls_name == "RadioScraper":
        return f"📻 Radio ({scraper.name})"
    elif cls_name == "TVScraper":
        return f"📺 TV ({scraper.name})"
    elif cls_name == "YouTubeScraper":
        name = getattr(scraper, "channel_name", "") or scraper.channel_url
        if name.startswith("http"):
            if "/@" in name:
                name = "@" + name.split("/@")[-1].split("/")[0]
        return f"🎥 YouTube ({name})"
    elif cls_name == "InstagramScraper":
        return f"📸 Instagram (@{scraper.username})"
    elif cls_name == "TwitterScraper":
        return "🐦 Twitter (Búsqueda)"
    elif cls_name == "FacebookScraper":
        return "📘 Facebook (Búsqueda)"
    elif cls_name == "RSSScraper":
        return f"📰 RSS ({scraper.feed_name})"
    return str(scraper)


def clean_html_text(raw_html):
    if not raw_html:
        return ""
    import html
    # Remove CDATA wrapper
    text = raw_html.replace("<![CDATA[", "").replace("]]>", "")
    # Remove scripts, styles and comments
    text = re.sub(r'<script.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', ' ', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# --- Async/Threading Orchestrator Engine ---
class MonitoringEngine:
    def __init__(self, keywords, radio_channels=None, youtube_channels=None, instagram_channels=None, rss_feeds=None, tv_channels=None, scan_interval=0, force_simulation=False, whisper_model="tiny", ollama_model="gemma4:e2b", instagram_sessionid=None, twitter_authtoken=None, facebook_cookies=None, facebook_active=None, twitter_active=None, language="es", country="DO", transcription_mode="Local (Whisper)", ai_mode="Local (Ollama/Gemma)", google_vision_credentials=None, google_gemini_api_key=None):
        self.keywords = keywords
        self.scan_interval = scan_interval
        self.force_simulation = force_simulation
        self.whisper_model = whisper_model
        self.ollama_model = ollama_model
        self.instagram_sessionid = instagram_sessionid
        self.twitter_authtoken = twitter_authtoken
        self.facebook_cookies = facebook_cookies
        self.uptime_status = {}
        self.language = language
        self.country = country
        self.transcription_mode = transcription_mode
        self.ai_mode = ai_mode
        self.google_vision_credentials = google_vision_credentials
        self.google_gemini_api_key = google_gemini_api_key
        
        self.twitter_active = twitter_active if twitter_active is not None else False
        self.facebook_active = facebook_active if facebook_active is not None else False
            
        self.radio_channels = radio_channels if radio_channels is not None else [{"name": "Z101", "url": "https://tunein.com/radio/Z101FM-1013-s102394/"}]
        self.youtube_channels = [normalize_youtube_channel_url(yt) for yt in youtube_channels if yt.strip()] if youtube_channels is not None else ["https://www.youtube.com/@nuriapiera/videos"]
        self.instagram_channels = instagram_channels if instagram_channels is not None else ["nuriapiera"]
        self.rss_feeds = rss_feeds if rss_feeds is not None else ["https://somospueblo.com/feed/"]
        self.tv_channels = tv_channels if tv_channels is not None else [{"name": "CDN 37", "url": "https://www.youtube.com/watch?v=h34A93R1g3E"}]
        
        self.alerts_queue = queue.Queue()
        self.logs_queue = queue.Queue()
        self.processed_identifiers = set()
        self.processed_lock = threading.Lock()
        
        # Threading control
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.active = False
        
        # Instantiate Scrapers
        self.scrapers = []
        for r in self.radio_channels:
            self.scrapers.append(RadioScraper(name=r["name"], tunein_url=r["url"], keywords=self.keywords, duration=40, whisper_model=self.whisper_model, language=self.language, transcription_mode=self.transcription_mode, credentials_path=self.google_vision_credentials))
        for yt in self.youtube_channels:
            self.scrapers.append(YouTubeScraper(channel_url=yt, keywords=self.keywords, language=self.language, transcription_mode=self.transcription_mode, credentials_path=self.google_vision_credentials))
        for ig in self.instagram_channels:
            self.scrapers.append(InstagramScraper(username=ig, keywords=self.keywords, sessionid=self.instagram_sessionid))
            
        # Instantiate TwitterScraper once if active
        if self.twitter_active:
            self.scrapers.append(TwitterScraper(keywords=self.keywords, auth_token=self.twitter_authtoken))
        
        # Instantiate FacebookScraper once if active
        if self.facebook_active:
            self.scrapers.append(FacebookScraper(keywords=self.keywords, cookies_str=self.facebook_cookies))
            
        # Instantiate GoogleNewsScraper if RSS is active
        if self.rss_feeds:
            transformed_feeds = []
            for rss in self.rss_feeds:
                rss = rss.strip()
                if not rss:
                    continue
                if not (rss.startswith("http://") or rss.startswith("https://")):
                    import urllib.parse
                    q = urllib.parse.quote(rss)
                    hl, gl, ceid = "es-419", "DO", "DO:es-419"
                    if self.language == "en":
                        hl, gl, ceid = "en", "US", "US:en"
                    else:
                        if self.country == "DO":
                            hl, gl, ceid = "es-419", "DO", "DO:es-419"
                        elif self.country == "MX":
                            hl, gl, ceid = "es-419", "MX", "MX:es-419"
                        elif self.country == "ES":
                            hl, gl, ceid = "es", "ES", "ES:es"
                        else:
                            hl, gl, ceid = "es-419", "US", "US:es-419"
                    rss_url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
                else:
                    rss_url = rss
                transformed_feeds.append(rss_url)
            
            self.rss_feeds = transformed_feeds
            self.scrapers.append(GoogleNewsScraper(keywords=self.keywords, language=self.language, country=self.country))
            for rss in self.rss_feeds:
                self.scrapers.append(RSSScraper(feed_url=rss, keywords=self.keywords))
        for tv in self.tv_channels:
            self.scrapers.append(TVScraper(name=tv["name"], stream_url=tv["url"], keywords=self.keywords, duration=40, whisper_model=self.whisper_model, language=self.language, transcription_mode=self.transcription_mode, credentials_path=self.google_vision_credentials))
            
        self.analyzer = OllamaAnalyzer(self.ollama_model, api_mode=self.ai_mode, credentials_path=self.google_vision_credentials, api_key=self.google_gemini_api_key)

    def log_event(self, message):
        log_time = time.strftime("%H:%M:%S")
        self.logs_queue.put(f"⏱️ `{log_time}` {message}")

    def start(self):
        if self.active:
            return
        self.active = True
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._run_monitoring, daemon=True)
        self.worker_thread.start()

    def stop(self):
        if not self.active:
            return
        self.active = False
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=3)
            self.worker_thread = None

    def _run_monitoring(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        self.log_event("Motor de Monitoreo iniciado con escaneo paralelo.")
        
        while not self.stop_event.is_set():
            # Update keywords dynamically based on all active clients from the database
            try:
                clients = database.get_all_clients()
                union_kws_set = set()
                for client in clients:
                    # Skip disabled clients
                    if client.get("enabled", 1) == 0:
                        continue
                    kws = [k.strip().lower() for k in client["keywords"].split(",") if k.strip()]
                    union_kws_set.update(kws)
                if union_kws_set:
                    self.keywords = list(union_kws_set)
                else:
                    self.keywords = []
            except Exception as e:
                self.log_event(f"Error cargando palabras clave de clientes de la BD: {e}")

            # If no keywords are active (and we are not forcing simulation), skip the scan cycle
            if not self.keywords and not self.force_simulation:
                self.log_event("No hay palabras clave activas. Omitiendo ciclo de escaneo...")
                for _ in range(int(self.scan_interval)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
                continue

            # Update scraper configurations dynamically
            for scraper in self.scrapers:
                scraper.keywords = self.keywords
                cls_name = scraper.__class__.__name__
                if cls_name in ("RadioScraper", "TVScraper"):
                    scraper.whisper_model_name = self.whisper_model
                elif cls_name == "InstagramScraper":
                    scraper.sessionid = self.instagram_sessionid
                elif cls_name == "TwitterScraper":
                    scraper.auth_token = self.twitter_authtoken
                elif cls_name == "FacebookScraper":
                    scraper.cookies_str = self.facebook_cookies
            self.analyzer.model_name = self.ollama_model
            
            fast_scrapers = [s for s in self.scrapers if s.__class__.__name__ in ("RSSScraper", "GoogleNewsScraper", "InstagramScraper", "TwitterScraper", "FacebookScraper", "YouTubeScraper")]
            stream_scrapers = [s for s in self.scrapers if s.__class__.__name__ in ("RadioScraper", "TVScraper")]
            
            num_workers = len(self.scrapers)
            if num_workers > 0:
                self.log_event(f"Iniciando ciclo simultáneo: {len(fast_scrapers)} fuentes digitales/RSS + {len(stream_scrapers)} canales de radio/TV...")
                
                futures = {}
                fast_max = min(max(len(fast_scrapers), 1), 12)
                stream_max = min(max(len(stream_scrapers), 1), 8)
                
                with ThreadPoolExecutor(max_workers=fast_max) as fast_executor, ThreadPoolExecutor(max_workers=stream_max) as stream_executor:
                    # 1. Submit fast RSS and web scrapers FIRST so they execute immediately on second 0
                    for scraper in fast_scrapers:
                        if self.stop_event.is_set():
                            break
                        if self.force_simulation:
                            futures[fast_executor.submit(scraper.get_simulated_mention)] = scraper
                        else:
                            cls_name = scraper.__class__.__name__
                            if cls_name in ("YouTubeScraper", "RSSScraper", "InstagramScraper", "TwitterScraper", "FacebookScraper", "GoogleNewsScraper"):
                                futures[fast_executor.submit(scraper.scrape, self)] = scraper

                    # 2. Submit stream scrapers (Radio/TV) simultaneously on second 0
                    for scraper in stream_scrapers:
                        if self.stop_event.is_set():
                            break
                        if self.force_simulation:
                            futures[stream_executor.submit(scraper.get_simulated_mention)] = scraper
                        else:
                            futures[stream_executor.submit(scraper.scrape)] = scraper

                    for future in as_completed(futures):
                        scraper = futures[future]
                        name = get_scraper_display_name(scraper)
                        try:
                            mentions = future.result()
                            if mentions:
                                self._process_mentions(mentions)
                            cls_name = scraper.__class__.__name__
                            url = getattr(scraper, "tunein_url", None) or getattr(scraper, "stream_url", None)
                            media_type = "Radio" if cls_name == "RadioScraper" else ("TV" if cls_name == "TVScraper" else "Other")
                            self.uptime_status[name] = {
                                "status": "Simulando" if self.force_simulation else "Online",
                                "last_checked": time.time(),
                                "error": "",
                                "url": url,
                                "type": media_type
                            }
                        except Exception as exc:
                            cls_name = scraper.__class__.__name__
                            url = getattr(scraper, "tunein_url", None) or getattr(scraper, "stream_url", None)
                            media_type = "Radio" if cls_name == "RadioScraper" else ("TV" if cls_name == "TVScraper" else "Other")
                            
                            exc_str = str(exc)
                            is_not_live = "no está transmitiendo en vivo actualmente" in exc_str or "is not live" in exc_str
                            
                            if is_not_live:
                                self.uptime_status[name] = {
                                    "status": "No en vivo",
                                    "last_checked": time.time(),
                                    "error": exc_str,
                                    "url": url,
                                    "type": media_type
                                }
                                self.log_event(f"ℹ️ [TV] Canal {name} no está transmitiendo en vivo actualmente.")
                            else:
                                self.uptime_status[name] = {
                                    "status": "Offline",
                                    "last_checked": time.time(),
                                    "error": exc_str,
                                    "url": url,
                                    "type": media_type
                                }
                                ffmpeg_bin = get_ffmpeg_path()
                                self.log_event(f"Error ejecutando scraper {name}: {exc} (ffmpeg: `{ffmpeg_bin}`)")
            
            if self.scan_interval > 0:
                self.log_event(f"Ciclo de monitoreo paralelo completado. Esperando intervalo ({self.scan_interval}s)...")
                # Sleep in increments of 1 second checking stop event to remain responsive
                for _ in range(int(self.scan_interval)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
            else:
                self.log_event("Ciclo de monitoreo paralelo completado. Reanudando inmediatamente el siguiente ciclo...")

    def _process_mentions(self, mentions):
        if not mentions:
            return
            
        for m in mentions:
            ident = m["identifier"]
            
            with self.processed_lock:
                if ident in self.processed_identifiers:
                    continue
                # Cap the processed cache to prevent memory saturation (max 500 records)
                if len(self.processed_identifiers) > 500:
                    self.processed_identifiers.pop()
                self.processed_identifiers.add(ident)
            
            # Send the matched text for AI analysis
            analysis = self.analyzer.analyze(m["text"])
            
            # Load clients to determine routing
            try:
                clients = database.get_all_clients()
            except Exception as e:
                self.log_event(f"Error obteniendo clientes al procesar mención: {e}")
                clients = []
            
            matched_clients = []
            for client in clients:
                # Skip disabled clients
                if client.get("enabled", 1) == 0:
                    continue
                client_kws = [k.strip().lower() for k in client["keywords"].split(",") if k.strip()]
                # Check which of this client's keywords match the text
                matched_kws = contains_keywords(m["text"], client_kws)
                if matched_kws:
                    matched_clients.append((client, matched_kws))
            
            # If no client matched (fallback)
            if not matched_clients and clients:
                # Fallback to the first enabled client
                first_enabled = next((c for c in clients if c.get("enabled", 1) == 1), None)
                if first_enabled:
                    # Filter to only contain keywords of this enabled client
                    client_kws = [k.strip().lower() for k in first_enabled["keywords"].split(",") if k.strip()]
                    matched_kws = contains_keywords(m["text"], client_kws)
                    matched_clients.append((first_enabled, matched_kws))
                
            for client, matched_kws in matched_clients:
                # Build full Alert structure
                alert = {
                    "source": m["source"],
                    "text": m["text"],
                    "keywords": matched_kws,
                    "timestamp": m["timestamp"],
                    "identifier": m["identifier"],
                    "sentimiento": analysis.get("sentimiento", "Neutral"),
                    "resumen": analysis.get("resumen", "Sin resumen."),
                    "ai_analyzed": analysis.get("ai_analyzed", False),
                    "model_used": analysis.get("model_used", "fallback"),
                    "metadata": m.get("metadata", {}),
                    "simulated": m.get("simulated", False),
                    "diagnostic": m.get("diagnostic") or analysis.get("diagnostic"),
                    "audio_path": m.get("audio_path"),
                    "video_path": m.get("video_path")
                }
                
                try:
                    # Save to SQLite database with client_id
                    database.save_alert(alert, client_id=client["id"], status='pending')
                except Exception as e:
                    self.log_event(f"Error al guardar alerta para cliente {client['name']}: {e}")
                
                alert_queued = alert.copy()
                alert_queued["client_id"] = client["id"]
                self.alerts_queue.put(alert_queued)

    def retry_scraper(self, name):
        """Ejecuta de forma individual y síncrona el scraper especificado por 'name' y actualiza su uptime_status."""
        target_scraper = None
        for scraper in self.scrapers:
            if get_scraper_display_name(scraper) == name:
                target_scraper = scraper
                break
                
        if not target_scraper:
            return False, f"Scraper '{name}' no encontrado"

        cls_name = target_scraper.__class__.__name__
        url = getattr(target_scraper, "tunein_url", None) or getattr(target_scraper, "stream_url", None)
        media_type = "Radio" if cls_name == "RadioScraper" else ("TV" if cls_name == "TVScraper" else "Other")

        self.log_event(f"🔄 Reintentando conexión individual para {name}...")
        try:
            if self.force_simulation:
                mentions = target_scraper.get_simulated_mention()
            else:
                if cls_name == "YouTubeScraper":
                    mentions = target_scraper.scrape(self)
                elif cls_name in ("RSSScraper", "InstagramScraper", "TwitterScraper", "FacebookScraper"):
                    mentions = target_scraper.scrape(self)
                elif cls_name in ("RadioScraper", "TVScraper"):
                    mentions = target_scraper.scrape()
                else:
                    mentions = None
                    
            if mentions:
                self._process_mentions(mentions)
                
            self.uptime_status[name] = {
                "status": "Simulando" if self.force_simulation else "Online",
                "last_checked": time.time(),
                "error": "",
                "url": url,
                "type": media_type
            }
            self.log_event(f"✅ Reintento exitoso para {name}: Estado actualizado a Online.")
            return True, "Online"
        except Exception as exc:
            exc_str = str(exc)
            is_not_live = "no está transmitiendo en vivo actualmente" in exc_str or "is not live" in exc_str
            new_status = "No en vivo" if is_not_live else "Offline"
            
            self.uptime_status[name] = {
                "status": new_status,
                "last_checked": time.time(),
                "error": exc_str,
                "url": url,
                "type": media_type
            }
            self.log_event(f"❌ Reintento para {name} falló: {exc_str}")
            return False, exc_str

    def retry_all_offline(self):
        """Reintenta secuencialmente todos los canales que se encuentran actualmente Offline."""
        offline_names = [name for name, info in self.uptime_status.items() if info.get("status") in ("Offline", "No en vivo")]
        if not offline_names:
            return 0, 0
            
        self.log_event(f"🔄 Iniciando reintento masivo para {len(offline_names)} canales offline...")
        recovered = 0
        for name in offline_names:
            success, _ = self.retry_scraper(name)
            if success:
                recovered += 1
        self.log_event(f"✅ Reintento masivo completado: {recovered}/{len(offline_names)} canales restablecidos.")
        return recovered, len(offline_names)
