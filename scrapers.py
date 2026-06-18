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

def contains_keywords(text, keywords):
    norm_text = normalize_text(text)
    found = []
    for kw in keywords:
        norm_kw = normalize_text(kw)
        if norm_kw in norm_text:
            found.append(kw)
    return found

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

def get_ffmpeg_path():
    # 1. Check local workspace directory first (full-featured FFmpeg)
    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
        
    # 2. Check system PATH first
    if shutil.which("ffmpeg") is not None:
        return "ffmpeg"
    
    # 3. Check Playwright custom installation
    import glob
    playwright_dir = os.path.expanduser(r"~\AppData\Local\ms-playwright")
    ffmpeg_glob = os.path.join(playwright_dir, "ffmpeg-*", "ffmpeg-win64.exe")
    matches = glob.glob(ffmpeg_glob)
    if matches:
        return matches[0]
        
    return None

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

# --- Radio Scraper ---
class RadioScraper:
    def __init__(self, name, tunein_url, keywords, duration=30, whisper_model="tiny"):
        self.name = name
        self.tunein_url = tunein_url
        self.keywords = keywords
        self.duration = duration
        self.whisper_model_name = whisper_model

    def scrape(self):
        import tempfile
        temp_audio = None
        try:
            # 1. Resolve URL with yt-dlp
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.tunein_url, download=False)
                stream_url = None
                if 'url' in info:
                    stream_url = info['url']
                elif 'formats' in info and len(info['formats']) > 0:
                    stream_url = info['formats'][0]['url']
                
            if not stream_url:
                raise ValueError("No stream URL resolved by yt-dlp")

            # 2. Check ffmpeg and record
            ffmpeg_bin = get_ffmpeg_path()
            if not ffmpeg_bin:
                raise FileNotFoundError("ffmpeg not found in PATH or Playwright cache")
                
            temp_dir = tempfile.gettempdir()
            temp_audio = os.path.join(temp_dir, f"radio_temp_{int(time.time())}.wav")
            
            cmd = [
                ffmpeg_bin, "-y", "-i", stream_url, "-t", str(self.duration),
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
                raise RuntimeError(f"FFmpeg failed: {result.stderr.decode('utf-8', errors='ignore')}")
            
            if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
                raise RuntimeError("FFmpeg generated an empty or non-existent audio file")
                
            # 3. Transcribe with Whisper
            model = get_whisper_model(self.whisper_model_name)
            with _whisper_transcription_lock:
                transcription = model.transcribe(temp_audio, language="es")
            text = transcription.get("text", "")
            
            # 4. Keyword Match
            found_kws = contains_keywords(text, self.keywords)
            if found_kws:
                # Save audio to static directory
                media_dir = os.path.join(os.getcwd(), "static")
                os.makedirs(media_dir, exist_ok=True)
                audio_filename = f"radio_{int(time.time())}.wav"
                persistent_path = os.path.join(media_dir, audio_filename)
                
                try:
                    shutil.move(temp_audio, persistent_path)
                    audio_ref = persistent_path
                except Exception:
                    audio_ref = temp_audio
                    
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
                # Clean up audio file if no keyword matches
                if os.path.exists(temp_audio):
                    try: os.remove(temp_audio)
                    except Exception: pass
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
    def __init__(self, channel_url, keywords):
        self.channel_url = channel_url
        self.keywords = keywords
        self.channel_name = extract_youtube_channel_name(channel_url)

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
            
            log(f"Iniciando escaneo de YouTube ({self.channel_name}) (últimos 25 videos)...")
            
            # 1. Get channel videos list
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'playlistend': 25,  # Fetch top 25 videos
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.channel_url, download=False)
                entries = info.get('entries', [])
                video_ids = [entry['id'] for entry in entries if entry.get('id')]
                
                # Build map of video_id -> title
                video_map = {}
                for entry in entries:
                    v_id = entry.get('id')
                    if v_id:
                        video_map[v_id] = entry.get('title') or "Video de YouTube"
                
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
            
            for video_id in video_ids:
                if database.is_processed(video_id):
                    continue
                    
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
                            raise RuntimeError(f"FFmpeg falló: {result.stderr.decode('utf-8', errors='ignore')}")
                            
                        # 3. Transcribe with Whisper
                        log(f"Transcribiendo audio localmente con Whisper para {video_id}...")
                        model_name = engine.whisper_model if (engine and hasattr(engine, 'whisper_model')) else "tiny"
                        model = get_whisper_model(model_name)
                        with _whisper_transcription_lock:
                            transcription = model.transcribe(wav_audio_path, language="es")
                        full_text = transcription.get("text", "")
                        
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
                
                # Scroll down once to load the next batch of posts (total ~16)
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(3000) # Wait for requests to complete
                except Exception:
                    pass
                
                mentions = []
                scanned_count = 0
                
                # Deduplicate edges by shortcode
                seen_shortcodes = set()
                unique_edges = []
                for edge in profile_json.get("edges", []):
                    node = edge.get("node", {})
                    shortcode = node.get("shortcode")
                    if shortcode and shortcode not in seen_shortcodes:
                        seen_shortcodes.add(shortcode)
                        unique_edges.append(edge)
                        
                # Limit to latest 16 posts
                media_edges = unique_edges[:16]
                
                if media_edges:
                    log(f"API de Instagram interceptada. Procesando {len(media_edges)} posts...")
                    for edge in media_edges:
                        node = edge.get("node", {})
                        shortcode = node.get("shortcode")
                        if not shortcode:
                            continue
                            
                        identifier = f"ig_{shortcode}"
                        
                        # Skip if already processed in database
                        if database.is_processed(identifier):
                            continue
                            
                        taken_at = node.get("taken_at_timestamp", 0)
                        scanned_count += 1
                        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                        caption_text = ""
                        if caption_edges:
                            caption_text = caption_edges[0].get("node", {}).get("text", "")
                            
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


# --- RSS Feed Scraper ---
class RSSScraper:
    def __init__(self, feed_url, keywords):
        self.feed_url = feed_url
        self.keywords = keywords
        self.feed_name = extract_rss_domain(feed_url)

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
            with urllib.request.urlopen(req, timeout=10.0) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
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
    def __init__(self, name, stream_url, keywords, duration=20, whisper_model="tiny"):
        self.name = name
        self.stream_url = stream_url
        self.keywords = keywords
        self.duration = duration
        self.whisper_model_name = whisper_model

    def scrape(self):
        import tempfile
        temp_video = None
        temp_audio = None
        try:
            # 1. Resolve URL with yt-dlp
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            resolved_url = self.stream_url
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(self.stream_url, download=False)
                    if 'url' in info:
                        resolved_url = info['url']
                    elif 'formats' in info and len(info['formats']) > 0:
                        resolved_url = info['formats'][0]['url']
                except Exception:
                    pass

            # 2. Check ffmpeg and record video + audio
            ffmpeg_bin = get_ffmpeg_path()
            if not ffmpeg_bin:
                raise FileNotFoundError("ffmpeg not found in PATH or Playwright cache")
                
            temp_dir = tempfile.gettempdir()
            ts = int(time.time())
            temp_video = os.path.join(temp_dir, f"tv_temp_{ts}.mp4")
            temp_audio = os.path.join(temp_dir, f"tv_temp_{ts}.wav")
            
            # Record video (MP4) from live stream for duration seconds
            cmd_video = [
                ffmpeg_bin, "-y", "-i", resolved_url, "-t", str(self.duration),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-ac", "1", "-ar", "16000", temp_video
            ]
            
            result = subprocess.run(cmd_video, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.duration + 20)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg video recording failed: {result.stderr.decode('utf-8', errors='ignore')}")
                
            # Extract audio track to WAV mono 16kHz
            cmd_audio = [
                ffmpeg_bin, "-y", "-i", temp_video, "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", temp_audio
            ]
            subprocess.run(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
                raise RuntimeError("Failed to extract audio track from video clip")
                
            # 3. Transcribe with Whisper
            model = get_whisper_model(self.whisper_model_name)
            with _whisper_transcription_lock:
                transcription = model.transcribe(temp_audio, language="es")
            text = transcription.get("text", "")
            
            if os.path.exists(temp_audio):
                try: os.remove(temp_audio)
                except Exception: pass
                
            # 4. Keyword Match
            found_kws = contains_keywords(text, self.keywords)
            if found_kws:
                # Save video to static directory
                media_dir = os.path.join(os.getcwd(), "static")
                os.makedirs(media_dir, exist_ok=True)
                video_filename = f"tv_{ts}.mp4"
                persistent_path = os.path.join(media_dir, video_filename)
                
                try:
                    shutil.move(temp_video, persistent_path)
                    video_ref = persistent_path
                except Exception:
                    video_ref = temp_video
                    
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
                # Clean up video file if no keyword matches
                if os.path.exists(temp_video):
                    try: os.remove(temp_video)
                    except Exception: pass
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
    def __init__(self, model_name="gemma4:e2b"):
        self.model_name = model_name

    def analyze(self, text):
        try:
            import ollama
            client = ollama.Client(host='http://localhost:11434', timeout=10.0)
            
            prompt = (
                "Eres un analista de PR. Lee este texto extraído de un medio dominicano. "
                "Extrae el sentimiento general (Positivo, Negativo o Neutral) y escribe un resumen estrictamente de una sola línea. "
                "Devuelve el resultado en formato JSON con las claves: 'sentimiento' y 'resumen'."
            )
            
            response = client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': text}
                ]
            )
            
            content = response['message']['content']
            parsed_json = self._parse_json(content)
            parsed_json["ai_analyzed"] = True
            parsed_json["model_used"] = self.model_name
            return parsed_json
            
        except Exception as e:
            # Connect fallback rules on failure
            result = self._analyze_fallback(text)
            result["ai_analyzed"] = False
            result["diagnostic"] = f"Ollama failed ({type(e).__name__}: {str(e)})."
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
    if isinstance(scraper, RadioScraper):
        return f"📻 Radio ({scraper.name})"
    elif isinstance(scraper, TVScraper):
        return f"📺 TV ({scraper.name})"
    elif isinstance(scraper, YouTubeScraper):
        name = getattr(scraper, "channel_name", "") or scraper.channel_url
        if name.startswith("http"):
            if "/@" in name:
                name = "@" + name.split("/@")[-1].split("/")[0]
        return f"🎥 YouTube ({name})"
    elif isinstance(scraper, InstagramScraper):
        return f"📸 Instagram (@{scraper.username})"
    elif isinstance(scraper, RSSScraper):
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
    def __init__(self, keywords, radio_channels=None, youtube_channels=None, instagram_channels=None, rss_feeds=None, tv_channels=None, scan_interval=30, force_simulation=False, whisper_model="tiny", ollama_model="gemma4:e2b", instagram_sessionid=None):
        self.keywords = keywords
        self.scan_interval = scan_interval
        self.force_simulation = force_simulation
        self.whisper_model = whisper_model
        self.ollama_model = ollama_model
        self.instagram_sessionid = instagram_sessionid
        self.uptime_status = {}
        
        self.radio_channels = radio_channels or []
        self.youtube_channels = youtube_channels or []
        self.instagram_channels = instagram_channels or []
        self.rss_feeds = rss_feeds or []
        self.tv_channels = tv_channels or []
        
        # Fallbacks to defaults if everything is empty
        if not self.radio_channels:
            self.radio_channels = [{"name": "Z101", "url": "https://tunein.com/radio/Z101FM-1013-s102394/"}]
        if not self.youtube_channels:
            self.youtube_channels = ["https://www.youtube.com/@nuriapiera/videos"]
        if not self.instagram_channels:
            self.instagram_channels = ["nuriapiera"]
        if not self.rss_feeds:
            self.rss_feeds = ["https://somospueblo.com/feed/"]
        if not self.tv_channels:
            self.tv_channels = [{"name": "CDN 37", "url": "https://www.youtube.com/watch?v=h34A93R1g3E"}]
        
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
            self.scrapers.append(RadioScraper(name=r["name"], tunein_url=r["url"], keywords=self.keywords, duration=20, whisper_model=self.whisper_model))
        for yt in self.youtube_channels:
            self.scrapers.append(YouTubeScraper(channel_url=yt, keywords=self.keywords))
        for ig in self.instagram_channels:
            self.scrapers.append(InstagramScraper(username=ig, keywords=self.keywords, sessionid=self.instagram_sessionid))
        for rss in self.rss_feeds:
            self.scrapers.append(RSSScraper(feed_url=rss, keywords=self.keywords))
        for tv in self.tv_channels:
            self.scrapers.append(TVScraper(name=tv["name"], stream_url=tv["url"], keywords=self.keywords, duration=20, whisper_model=self.whisper_model))
            
        self.analyzer = OllamaAnalyzer(self.ollama_model)

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
                if isinstance(scraper, RadioScraper) or isinstance(scraper, TVScraper):
                    scraper.whisper_model_name = self.whisper_model
                elif isinstance(scraper, InstagramScraper):
                    scraper.sessionid = self.instagram_sessionid
            self.analyzer.model_name = self.ollama_model
            
            num_workers = min(3, len(self.scrapers))
            if num_workers > 0:
                self.log_event(f"Iniciando ciclo de monitoreo paralelo para {len(self.scrapers)} canales...")
                
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {}
                    for scraper in self.scrapers:
                        if self.stop_event.is_set():
                            break
                        
                        # Define wrapper function depending on scraper type and mode
                        if self.force_simulation:
                            futures[executor.submit(scraper.get_simulated_mention)] = scraper
                        else:
                            if isinstance(scraper, YouTubeScraper):
                                futures[executor.submit(scraper.scrape, self)] = scraper
                            elif isinstance(scraper, RSSScraper) or isinstance(scraper, InstagramScraper):
                                futures[executor.submit(scraper.scrape, self)] = scraper
                            elif isinstance(scraper, RadioScraper) or isinstance(scraper, TVScraper):
                                futures[executor.submit(scraper.scrape)] = scraper
                                
                    for future in as_completed(futures):
                        scraper = futures[future]
                        name = get_scraper_display_name(scraper)
                        try:
                            mentions = future.result()
                            if mentions:
                                self._process_mentions(mentions)
                            self.uptime_status[name] = {
                                "status": "Simulando" if self.force_simulation else "Online",
                                "last_checked": time.time(),
                                "error": ""
                            }
                        except Exception as exc:
                            self.uptime_status[name] = {
                                "status": "Offline",
                                "last_checked": time.time(),
                                "error": str(exc)
                            }
                            self.log_event(f"Error ejecutando scraper {name}: {exc}")
            
            self.log_event("Ciclo de monitoreo paralelo completado. Esperando intervalo...")
            # Sleep in increments of 1 second checking stop event to remain responsive
            for _ in range(int(self.scan_interval)):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

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
                    matched_clients.append((first_enabled, m["keywords"]))
                
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
