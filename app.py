import os
import sys
import time
from datetime import datetime
import streamlit as st
import queue
import textwrap

# Import scrapers backend
import scrapers
import database
import importlib
importlib.reload(database)
importlib.reload(scrapers)
import subprocess
import tempfile
import base64

DEFAULT_RADIO_CHANNELS = """Alofoke FM (99.3) | https://radiordomi.com/8566/stream/1/
CDN Radio (92.5) | https://play.cdnradio.com.do/cdnlive
Dale 101.9 | https://stream.zeno.fm/2h6plesly3nvv
Escándalo 102.5 | https://stream.zeno.fm/iwqlyzpyry1uv
Estación 97.7 | https://stream2.rcast.net/61187
Fidelity (94.1) | https://autodiscover.fidelityfm.com.do/fid
Independencia (93.3) | https://stream.radiojar.com/nc893hafc8zuv
La 91 FM | https://stream.zeno.fm/859cd7buqg8uv
La Bakana (105.7) | https://stream.zeno.fm/eym18zp7cyptv
La Nota Diferente | https://tunein.com/radio/La-Nota-957-FM-s256372/
La Nueva 106.9 | https://lanueva106.radioca.st/stream/1/
La Voz FF.AA. (HIFA) | https://rs2.radiordomi.com/8412/stream/1/
La X 102.1 | https://audio.livecastnet.com:2535/stream
La Z101 FM | https://streaming.z101digital.com/z101
Latidos FM (93.7) | https://rstream.hostdime.com/proxy/latidos?mp=/8880
Los 40 (103.3) | https://stream.zeno.fm/sse58hcighnvv?dist=play
Pura Vida (96.7) | https://stream.zeno.fm/veeugp2tz68uv
Radio Monumental | http://radio2.grupointernet.com:8103/stream
Ritmo 96.5 FM | https://stream-49.zeno.fm/y0br5ck4ququv
Rumba FM | https://stream.zeno.fm/eticl2rpposvv
Sentido 89.3 | https://stream.zeno.fm/vghmq0fffvftv
Súper Q 100.9 | https://cast10.plugstreaming.com/stream/superq
Top Latina 101.7 | https://stream.zeno.fm/rprhbqiwozovv
Turbo 98 FM | https://stream.zeno.fm/s6c01714pa0uv
Zol 106.5 FM | https://stream.zeno.fm/w6x7q7dtpy5tv"""

DEFAULT_TV_CHANNELS = """Acento TV | https://acentotv01.streamprolive.com/hls/live.m3u8
Ahora TV | https://stream.haislin.com/ahoratv/index.m3u8
Boreal Televisión | https://edge.essastream.com/borealtelevision/tracks-v1a1/mono.m3u8
Canal del Sol | https://stream.canaldelsol.com/sol26/live_1080.m3u8
Canal Seis | https://stream.elseis.do/canal6/live_1080.m3u8
Cibao Súper TV (Canal 55) | https://ss2.tvrdomi.com:1936/supertv55/supertv55/playlist.m3u8
Cine Visión 19 | https://5790d294af2dc.streamlock.net/tvhdlive/tvhdlive/playlist.m3u8
Color Vision | http://190.122.104.210:5080/LiveApp/streams/cvision1.m3u8
Digital Quince | http://190.122.104.210:5080/LiveApp/streams/Di15.m3u8
El Nuevo Diario TV | https://nuevodiario01.streamprolive.com/hls/live.m3u8
En Televisión (Canal 31) | https://stream.haislin.com/entelevision/index.m3u8
Hilando Fino TV | https://hilandofinotv.essastream.com:3606/live/canalhilandofinotvlive.m3u8
Luna TV (Canal 53) | https://tv.wracanal10.com:3671/live/lunatvcanal53live.m3u8
Mia Visión | https://edge.essastream.com/miavisiontv/playlist.m3u8
Microvisión (Canal 10) | https://streaming.telecablecentral.com.do/live/MicroHD/playlist.m3u8
RNN | https://2-fss-2.streamhoster.com/pl_138/206532-6829902-1/playlist.m3u8
RTVD (Canal 4) | https://protvradiostream.com:1936/canal4rd-1/ngrp:canal4rd-1_all/playlist.m3u8
Súper Canal | https://cnn.hostlagarto.com/supercanalhd/playlist.m3u8
Telecentro | http://190.122.104.210:5080/LiveApp/streams/tcentro.m3u8
Telecontacto (Canal 57) | https://streaming.grupomediosdelnorte.com:19360/telecontacto/telecontacto.m3u8
Teleunion (Canal 16) | http://server2grupocam.com:1945/teleunion/TU/playlist.m3u8
Teleuniverso Canal 29 | https://videoserver.tmcreativos.com:19360/kptjeckkaa/kptjeckkaa.m3u8
VTV (Canal 32) | https://cnn.livestreaminggroup.info:3507/live/vtv32live.m3u8"""

DEFAULT_RSS_FEEDS = """https://news.google.com/rss?hl=es-419&gl=US&ceid=US:es-419
https://www.diariolibre.com/rss/portada.xml
https://eldia.com.do/feed/
https://elnuevodiario.com.do/feed/
https://remolacha.net/feed/
https://almomento.net/feed/
https://noticiassin.com/feed/
https://deultimominuto.net/feed/
https://eldinero.com.do/feed/"""

def test_smtp_connection(config):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    server = config.get("server")
    port = config.get("port")
    user = config.get("user")
    password = config.get("password")
    security = config.get("security")
    to_emails = [e.strip() for e in config.get("to", "").split(",") if e.strip()]
    
    if not to_emails:
        return False, "No hay destinatarios especificados."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = "War Room - Prueba de Conexión SMTP"
        
        body = (
            "Este es un correo de prueba automático del sistema War Room Monitoreo.\n\n"
            "Si estás recibiendo esto, significa que la configuración del servidor SMTP es correcta y la conexión es exitosa.\n\n"
            "Detalles de la conexión:\n"
            f"- Servidor: {server}:{port}\n"
            f"- Usuario: {user}\n"
            f"- Seguridad: {security}\n"
        )
        msg.attach(MIMEText(body, 'plain'))
        
        if security == "SSL/TLS":
            smtp_conn = smtplib.SMTP_SSL(server, port, timeout=10.0)
        else:
            smtp_conn = smtplib.SMTP(server, port, timeout=10.0)
            if security == "STARTTLS":
                smtp_conn.ehlo()
                smtp_conn.starttls()
                smtp_conn.ehlo()
                
        smtp_conn.login(user, password)
        smtp_conn.sendmail(user, to_emails, msg.as_string())
        smtp_conn.quit()
        return True, None
    except Exception as e:
        return False, str(e)

def send_email_report_thread(config, report_md, csv_data, ai_summary, override_to_email=None):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    server = config.get("server")
    port = config.get("port")
    user = config.get("user")
    password = config.get("password")
    security = config.get("security")
    
    to_field = override_to_email if override_to_email else config.get("to", "")
    to_emails = [e.strip() for e in to_field.split(",") if e.strip()]
    
    try:
        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = f"War Room - Reporte Ejecutivo de Monitoreo ({datetime.now().strftime('%Y-%m-%d')})"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ padding: 20px; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; }}
                .header {{ background: linear-gradient(45deg, #1abc9c, #3498db); padding: 15px; color: white; border-radius: 6px 6px 0 0; text-align: center; }}
                .summary {{ background-color: #f7fafc; padding: 15px; border-left: 4px solid #3498db; border-radius: 4px; margin: 20px 0; }}
                .footer {{ font-size: 0.85rem; color: #718096; text-align: center; margin-top: 35px; border-top: 1px solid #e2e8f0; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin:0;">War Room - Monitoreo de Medios</h2>
                </div>
                <p>Estimado/a cliente,</p>
                <p>Adjunto a este correo encontrará el reporte consolidado diario correspondiente al monitoreo de prensa del día de hoy.</p>
                
                <div class="summary">
                    <strong style="color:#2c5282;">Resumen Ejecutivo (IA):</strong>
                    <p style="margin: 5px 0 0 0;">{ai_summary or "Consulte el archivo Markdown adjunto para ver la síntesis ejecutiva consolidada."}</p>
                </div>
                
                <p>El reporte incluye el desglose detallado de las menciones aprobadas de Radio, TV, YouTube, Instagram y RSS, así como sus estadísticas de cobertura y sentimiento correspondientes.</p>
                
                <div class="footer">
                    Este es un reporte automático del sistema <strong>War Room Monitoreo</strong>.<br/>
                    © {datetime.now().year} War Room Inc. Todos los derechos reservados.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))
        
        md_part = MIMEBase('application', 'octet-stream')
        md_part.set_payload(report_md.encode('utf-8'))
        encoders.encode_base64(md_part)
        md_part.add_header('Content-Disposition', 'attachment', filename=f"reporte_monitoreo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        msg.attach(md_part)
        
        csv_part = MIMEBase('application', 'octet-stream')
        csv_part.set_payload(csv_data.encode('utf-8'))
        encoders.encode_base64(csv_part)
        csv_part.add_header('Content-Disposition', 'attachment', filename=f"reporte_monitoreo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        msg.attach(csv_part)
        
        if security == "SSL/TLS":
            smtp_conn = smtplib.SMTP_SSL(server, port, timeout=15.0)
        else:
            smtp_conn = smtplib.SMTP(server, port, timeout=15.0)
            if security == "STARTTLS":
                smtp_conn.ehlo()
                smtp_conn.starttls()
                smtp_conn.ehlo()
                
        smtp_conn.login(user, password)
        smtp_conn.sendmail(user, to_emails, msg.as_string())
        smtp_conn.quit()
        
        st.session_state.smtp_status = "success"
        st.session_state.smtp_result = "Reporte enviado exitosamente."
    except Exception as e:
        st.session_state.smtp_status = "error"
        st.session_state.smtp_result = str(e)
    finally:
        st.session_state.smtp_sending = False

def get_lightweight_audio_uri(wav_path):
    if not wav_path or not os.path.exists(wav_path):
        return None
    try:
        ffmpeg_bin = scrapers.get_ffmpeg_path()
        if not ffmpeg_bin:
            # Fallback to direct WAV encoding if ffmpeg is missing
            with open(wav_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:audio/wav;base64,{b64}"
            
        import uuid
        temp_mp3 = os.path.join(tempfile.gettempdir(), f"temp_report_{uuid.uuid4().hex}.mp3")
        
        # Compress to 32kbps mono MP3 to make it extremely light (~80KB for 20s)
        cmd = [
            ffmpeg_bin, "-y", "-i", wav_path, 
            "-codec:a", "libmp3lame", "-b:a", "32k", "-ac", "1", temp_mp3
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        
        if result.returncode == 0 and os.path.exists(temp_mp3):
            with open(temp_mp3, "rb") as f:
                mp3_data = f.read()
            b64 = base64.b64encode(mp3_data).decode("utf-8")
            uri = f"data:audio/mp3;base64,{b64}"
            try: os.remove(temp_mp3)
            except Exception: pass
            return uri
        else:
            # Fallback to direct WAV
            with open(wav_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:audio/wav;base64,{b64}"
    except Exception:
        # Fallback to direct WAV
        try:
            with open(wav_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:audio/wav;base64,{b64}"
        except Exception:
            return None

def upload_to_catbox(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        import requests
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        with open(file_path, "rb") as f:
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files, timeout=30)
        if response.status_code == 200:
            link = response.text.strip()
            if link.startswith("http"):
                return link
    except Exception:
        pass
    return None

# Page Configuration
st.set_page_config(
    page_title="War Room - Monitoreo con IA",
    page_icon="📻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Font Awesome CSS globally
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', unsafe_allow_html=True)

# Premium Custom CSS Styles
st.markdown("""
<style>
    /* Styling for Alert Cards */
    .pr-card {
        background-color: #121826;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #95a5a6;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .pr-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .pr-card-positivo {
        border-left-color: #2ecc71; /* Harmonious Green */
    }
    .pr-card-negativo {
        border-left-color: #e74c3c; /* Harmonious Red */
    }
    .pr-card-neutral {
        border-left-color: #3498db; /* Harmonious Blue */
    }
    
    /* Micro-badges styles */
    .badge-sentiment {
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #ffffff;
    }
    .badge-pos { background-color: #2ecc71; }
    .badge-neg { background-color: #e74c3c; }
    .badge-neu { background-color: #3498db; }
    
    .badge-kw {
        background-color: rgba(255, 255, 255, 0.1);
        color: #e0e0e0;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        margin-right: 5px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .badge-simulated {
        background-color: #7f8c8d;
        color: #ffffff;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    
    /* Live Status Animation */
    .pulse-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        background: rgba(46, 204, 113, 0.1);
        padding: 10px 15px;
        border-radius: 8px;
        border: 1px solid rgba(46, 204, 113, 0.2);
        max-width: fit-content;
    }
    .pulse {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #2ecc71;
        box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7);
        animation: pulse-animation 1.8s infinite linear;
        margin-right: 10px;
    }
    @keyframes pulse-animation {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 10px rgba(46, 204, 113, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(46, 204, 113, 0);
        }
    }
    .inactive-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        background: rgba(149, 165, 166, 0.1);
        padding: 10px 15px;
        border-radius: 8px;
        border: 1px solid rgba(149, 165, 166, 0.2);
        max-width: fit-content;
    }
    .dot-inactive {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #95a5a6;
        margin-right: 10px;
    }
    
    /* Header design elements */
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(45deg, #1abc9c, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    .pr-quote {
        background-color: #1b2336;
        border-left: 4px solid #7f8c8d;
        padding: 12px 18px;
        border-radius: 4px;
        margin: 10px 0px 15px 0px;
        font-size: 0.95rem;
        line-height: 1.5;
        border-right: 1px solid rgba(255, 255, 255, 0.02);
        border-top: 1px solid rgba(255, 255, 255, 0.02);
        border-bottom: 1px solid rgba(255, 255, 255, 0.02);
    }
</style>
""", unsafe_allow_html=True)

# Initialize SQLite database and load persistent alerts on every rerun
database.initialize_db()
clients = database.get_all_clients()
client_ids = [c["id"] for c in clients]

if "active_client_id" not in st.session_state or st.session_state.active_client_id not in client_ids:
    if clients:
        st.session_state.active_client_id = clients[0]["id"]
    else:
        st.session_state.active_client_id = 1
    st.session_state.should_reload = True
    st.session_state.should_reload_approved = True

if "alerts" not in st.session_state or st.session_state.get("should_reload", True):
    st.session_state.alerts = database.get_alerts_by_status('pending', st.session_state.active_client_id)
    st.session_state.should_reload = False

if "approved_alerts" not in st.session_state or st.session_state.get("should_reload_approved", True):
    st.session_state.approved_alerts = database.get_alerts_by_status('approved', st.session_state.active_client_id)
    st.session_state.approved_count = len(st.session_state.approved_alerts)
    st.session_state.should_reload_approved = False

import json
# Load SMTP configuration from SQLite database
smtp_config_str = database.get_state("smtp_config", "{}")
try:
    smtp_config = json.loads(smtp_config_str)
except Exception:
    smtp_config = {}

if "smtp_sending" not in st.session_state:
    st.session_state.smtp_sending = False
if "smtp_status" not in st.session_state:
    st.session_state.smtp_status = None
if "smtp_result" not in st.session_state:
    st.session_state.smtp_result = None

if "system_logs" not in st.session_state:
    st.session_state.system_logs = []
if "ai_summary_report" not in st.session_state:
    st.session_state.ai_summary_report = None
if "monitoring_active" not in st.session_state:
    st.session_state.monitoring_active = False
if "system_status" not in st.session_state:
    with st.spinner("Realizando diagnóstico del sistema..."):
        st.session_state.system_status = scrapers.check_system_status()

# Detect default simulation state based on requirements
sys_status = st.session_state.system_status
missing_deps = not (sys_status["ffmpeg"] and sys_status["whisper"] and sys_status["playwright"] and sys_status["ollama"])

if "force_simulation" not in st.session_state:
    # Default to simulation if dependencies are missing, to guarantee smooth operation out-of-the-box
    st.session_state.force_simulation = missing_deps

# Initialize persistent configuration values from database
if "radio_channels_val" not in st.session_state:
    saved_val = database.get_state("config_radio_channels", "")
    st.session_state["radio_channels_val"] = saved_val if saved_val else DEFAULT_RADIO_CHANNELS
if "tv_channels_val" not in st.session_state:
    saved_val = database.get_state("config_tv_channels", "")
    st.session_state["tv_channels_val"] = saved_val if saved_val else DEFAULT_TV_CHANNELS
if "youtube_channels_val" not in st.session_state:
    saved_val = database.get_state("config_youtube_channels", "")
    st.session_state["youtube_channels_val"] = saved_val if saved_val else "https://www.youtube.com/@nuriapiera/videos"
if "instagram_users_val" not in st.session_state:
    saved_val = database.get_state("config_instagram_users", "")
    st.session_state["instagram_users_val"] = saved_val if saved_val else "nuriapiera"

if "twitter_authtoken_val" not in st.session_state:
    st.session_state["twitter_authtoken_val"] = database.get_state("config_twitter_authtoken", "")
if "facebook_cookies_val" not in st.session_state:
    st.session_state["facebook_cookies_val"] = database.get_state("config_facebook_cookies", "")
if "rss_feeds_val" not in st.session_state:
    saved_val = database.get_state("config_rss_feeds", "")
    st.session_state["rss_feeds_val"] = saved_val if saved_val else DEFAULT_RSS_FEEDS
if "google_vision_credentials_val" not in st.session_state:
    saved_val = database.get_state("config_google_vision_credentials", "")
    if not saved_val:
        if os.path.exists("google_vision_creds.json"):
            saved_val = "google_vision_creds.json"
        else:
            import glob
            gen_lang_files = glob.glob("gen-lang-client-*.json")
            if gen_lang_files:
                saved_val = gen_lang_files[0]
    st.session_state["google_vision_credentials_val"] = saved_val
if "engine_transcription_mode_val" not in st.session_state:
    st.session_state["engine_transcription_mode_val"] = database.get_state("config_engine_transcription_mode", "Local (Whisper)")
if "engine_ai_mode_val" not in st.session_state:
    st.session_state["engine_ai_mode_val"] = database.get_state("config_engine_ai_mode", "Local (Ollama/Gemma)")
if "google_gemini_api_key_val" not in st.session_state:
    st.session_state["google_gemini_api_key_val"] = database.get_state("config_google_gemini_api_key", "")
if "engine_language_val" not in st.session_state:
    st.session_state["engine_language_val"] = database.get_state("config_engine_language", "Español")
if "engine_country_val" not in st.session_state:
    st.session_state["engine_country_val"] = database.get_state("config_engine_country", "República Dominicana (RD)")

# Initialize persistent active media switches
for m_key in ["media_radio_active", "media_tv_active", "media_youtube_active", "media_instagram_active", "media_twitter_active", "media_facebook_active", "media_rss_active"]:
    if m_key not in st.session_state:
        st.session_state[m_key] = (database.get_state(f"config_{m_key}", "true") == "true")

def save_config(key, db_key):
    val = st.session_state.get(key, "")
    database.set_state(db_key, val)

def save_bool_config(key, db_key):
    val = "true" if st.session_state.get(key, True) else "false"
    database.set_state(db_key, val)

# --- SIDEBAR: Configuration & Control ---
if os.path.exists("assets/logo.png"):
    st.sidebar.image("assets/logo.png", use_container_width=True)
else:
    st.sidebar.image("https://img.icons8.com/nolan/128/war.png", width=80)
st.sidebar.markdown("<h2 style='margin-top:0; display: flex; align-items: center; gap: 10px;'><i class='fa-solid fa-sliders'></i> Centro de Control</h2>", unsafe_allow_html=True)

# Media Source Toggle switches
st.sidebar.markdown("### <i class='fa-solid fa-tower-broadcast'></i> Fuentes de Monitoreo", unsafe_allow_html=True)

# Radio
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-solid fa-radio' style='color: #9b59b6; margin-right: 6px;'></i>Radio</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_radio_active", on_change=save_bool_config, args=("media_radio_active", "config_media_radio_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# TV
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-solid fa-tv' style='color: #3498db; margin-right: 6px;'></i>TV</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_tv_active", on_change=save_bool_config, args=("media_tv_active", "config_media_tv_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# YouTube
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-brands fa-youtube' style='color: #e74c3c; margin-right: 6px;'></i>YouTube</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_youtube_active", on_change=save_bool_config, args=("media_youtube_active", "config_media_youtube_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# Instagram
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-brands fa-instagram' style='color: #e1306c; margin-right: 6px;'></i>Instagram</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_instagram_active", on_change=save_bool_config, args=("media_instagram_active", "config_media_instagram_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# Twitter
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-brands fa-x-twitter' style='color: #f1f2f6; margin-right: 6px;'></i>Twitter</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_twitter_active", on_change=save_bool_config, args=("media_twitter_active", "config_media_twitter_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# Facebook
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-brands fa-facebook' style='color: #1877f2; margin-right: 6px;'></i>Facebook</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_facebook_active", on_change=save_bool_config, args=("media_facebook_active", "config_media_facebook_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

# RSS
c_icon, c_toggle = st.sidebar.columns([0.75, 0.25])
c_icon.markdown("<div style='padding-top: 4px; font-size: 0.95rem;'><i class='fa-solid fa-rss' style='color: #f1c40f; margin-right: 6px;'></i>RSS</div>", unsafe_allow_html=True)
c_toggle.toggle("", key="media_rss_active", on_change=save_bool_config, args=("media_rss_active", "config_media_rss_active"), disabled=st.session_state.monitoring_active, label_visibility="collapsed")

st.sidebar.markdown("---")

# Main Engine Controls
if not st.session_state.monitoring_active:
    any_active = any(st.session_state.get(k, True) for k in ["media_radio_active", "media_tv_active", "media_youtube_active", "media_instagram_active", "media_twitter_active", "media_facebook_active", "media_rss_active"])
    if not any_active:
        st.sidebar.warning("⚠️ Selecciona al menos una fuente de monitoreo.")
        
    if st.sidebar.button("🚀 INICIAR MONITOREO", use_container_width=True, type="primary", disabled=not any_active):
        # Parse keywords from the visible text input in the configuration section
        kws_str = st.session_state.get("keywords_input_state", "")
        st.session_state.keywords_str = kws_str
        kws = [k.strip() for k in kws_str.split(",") if k.strip()]
        
        # Parse Radio channels
        radio_list = []
        if st.session_state.get("media_radio_active", True):
            radio_lines = st.session_state.get("radio_channels_val", "").split("\n")
            for line in radio_lines:
                line = line.strip()
                if not line:
                    continue
                if "|" in line:
                    parts = line.split("|", 1)
                    name = parts[0].strip()
                    url = parts[1].strip()
                else:
                    name = "Radio"
                    url = line
                radio_list.append({"name": name, "url": url})
            
        # Parse TV channels
        tv_list = []
        if st.session_state.get("media_tv_active", True):
            tv_lines = st.session_state.get("tv_channels_val", "").split("\n")
            for line in tv_lines:
                line = line.strip()
                if not line:
                    continue
                if "|" in line:
                    parts = line.split("|", 1)
                    name = parts[0].strip()
                    url = parts[1].strip()
                else:
                    name = "TV"
                    url = line
                tv_list.append({"name": name, "url": url})
            
        # Parse YouTube channels
        youtube_list = []
        if st.session_state.get("media_youtube_active", True):
            yt_lines = st.session_state.get("youtube_channels_val", "").split("\n")
            youtube_list = [line.strip() for line in yt_lines if line.strip()]
        
        # Parse Instagram usernames
        instagram_list = []
        if st.session_state.get("media_instagram_active", True):
            ig_lines = st.session_state.get("instagram_users_val", "").split("\n")
            instagram_list = [line.strip() for line in ig_lines if line.strip()]
        
        # Parse RSS feeds
        rss_list = []
        if st.session_state.get("media_rss_active", True):
            rss_lines = st.session_state.get("rss_feeds_val", "").split("\n")
            rss_list = [line.strip() for line in rss_lines if line.strip()]
        
        # Resolve language and country codes
        lang_val = st.session_state.get("engine_language_val", "Español")
        lang_code = "en" if lang_val == "Inglés" else "es"
        
        country_val = st.session_state.get("engine_country_val", "República Dominicana (RD)")
        if "República Dominicana" in country_val:
            country_code = "DO"
        elif "Estados Unidos" in country_val:
            country_code = "US"
        elif "España" in country_val:
            country_code = "ES"
        else:
            country_code = "MX"
            
        # Instantiate and run engine
        st.session_state.engine = scrapers.MonitoringEngine(
            keywords=kws,
            radio_channels=radio_list,
            youtube_channels=youtube_list,
            instagram_channels=instagram_list,
            twitter_active=st.session_state.get("media_twitter_active", True),
            facebook_active=st.session_state.get("media_facebook_active", True),
            rss_feeds=rss_list,
            tv_channels=tv_list,
            scan_interval=st.session_state.get("scan_interval_val", 30),
            force_simulation=st.session_state.force_simulation,
            whisper_model=st.session_state.get("whisper_model_val", "tiny"),
            ollama_model=st.session_state.get("ollama_model_val", "gemma4:e2b"),
            instagram_sessionid=st.session_state.get("instagram_sessionid_val", ""),
            twitter_authtoken=st.session_state.get("twitter_authtoken_val", ""),
            facebook_cookies=st.session_state.get("facebook_cookies_val", ""),
            language=lang_code,
            country=country_code,
            transcription_mode=st.session_state.get("engine_transcription_mode_val", "Local (Whisper)"),
            ai_mode=st.session_state.get("engine_ai_mode_val", "Local (Ollama/Gemma)"),
            google_vision_credentials=st.session_state.get("google_vision_credentials_val", ""),
            google_gemini_api_key=st.session_state.get("google_gemini_api_key_val", "")
        )
        st.session_state.engine.start()
        st.session_state.monitoring_active = True
        st.rerun()
else:
    if st.sidebar.button("🛑 DETENER MONITOREO", use_container_width=True, type="secondary"):
        if "engine" in st.session_state and st.session_state.engine:
            st.session_state.engine.stop()
            st.session_state.engine = None
        st.session_state.monitoring_active = False
        st.rerun()

st.sidebar.markdown("---")

# Monitoring Parameters
st.sidebar.markdown("### <i class='fa-solid fa-gear'></i> Configuración del Motor", unsafe_allow_html=True)

# Simulation toggle
st.session_state.force_simulation = st.sidebar.toggle(
    "Forzar Modo Simulación",
    value=st.session_state.force_simulation,
    help="Si está activo, generará datos de prueba simulados y evitará peticiones de red reales y procesamiento local pesado."
)

st.sidebar.slider(
    "Frecuencia de Escaneo (segundos)",
    min_value=10,
    max_value=120,
    value=30,
    step=5,
    key="scan_interval_val",
    disabled=st.session_state.monitoring_active
)

st.sidebar.selectbox(
    "País de Monitoreo (Google News)",
    options=["República Dominicana (RD)", "Estados Unidos (US)", "España (ES)", "México (MX)"],
    key="engine_country_val",
    disabled=st.session_state.monitoring_active,
    on_change=save_config,
    args=("engine_country_val", "config_engine_country"),
    help="Define la región para las búsquedas de Google News."
)

st.sidebar.selectbox(
    "Idioma de Monitoreo",
    options=["Español", "Inglés"],
    key="engine_language_val",
    disabled=st.session_state.monitoring_active,
    on_change=save_config,
    args=("engine_language_val", "config_engine_language"),
    help="Define el idioma para Google News y transcripciones locales con Whisper."
)

st.sidebar.selectbox(
    "Motor de Transcripción",
    options=["Local (Whisper)", "Google Cloud Speech-to-Text"],
    key="engine_transcription_mode_val",
    disabled=st.session_state.monitoring_active,
    on_change=save_config,
    args=("engine_transcription_mode_val", "config_engine_transcription_mode"),
    help="Selecciona el servicio para convertir audio a texto."
)

st.sidebar.selectbox(
    "Modelo Whisper (Audio local)",
    options=["tiny", "base"],
    index=0,
    key="whisper_model_val",
    disabled=st.session_state.monitoring_active or st.session_state.force_simulation or st.session_state.engine_transcription_mode_val != "Local (Whisper)",
    help="Modelos más pesados incrementan el uso de CPU/RAM."
)

st.sidebar.selectbox(
    "Motor de Análisis IA",
    options=["Local (Ollama/Gemma)", "Google Cloud Gemini (Vertex AI)", "Google Gemini (API Key)"],
    key="engine_ai_mode_val",
    disabled=st.session_state.monitoring_active,
    on_change=save_config,
    args=("engine_ai_mode_val", "config_engine_ai_mode"),
    help="Selecciona el motor de inteligencia artificial para resúmenes y análisis."
)

if st.session_state.engine_ai_mode_val == "Google Gemini (API Key)":
    st.sidebar.text_input(
        "Google Gemini API Key",
        type="password",
        key="google_gemini_api_key_val",
        disabled=st.session_state.monitoring_active,
        on_change=save_config,
        args=("google_gemini_api_key_val", "config_google_gemini_api_key"),
        help="Ingresa tu clave de API de Gemini Developer (de Google AI Studio)."
    )

# Fetch active models for selection if Ollama is running
ollama_options = ["gemma4:e2b", "gemma4:e4b", "gemma:2b", "gemma:7b"]
if sys_status["ollama_models"]:
    for m in sys_status["ollama_models"]:
        if m not in ollama_options:
            ollama_options.append(m)

st.sidebar.selectbox(
    "Modelo Ollama (IA local)",
    options=ollama_options,
    index=0,
    key="ollama_model_val",
    disabled=st.session_state.monitoring_active or st.session_state.engine_ai_mode_val != "Local (Ollama/Gemma)",
    help="Modelo local de Ollama cargado a través de localhost:11434"
)

st.sidebar.text_input(
    "Instagram sessionid (Cookie)",
    type="password",
    key="instagram_sessionid_val",
    help="Opcional. Si deseas hacer scraping real de Instagram sin ser bloqueado, ingresa tu cookie 'sessionid'.",
    disabled=st.session_state.monitoring_active
)

st.sidebar.text_input(
    "Twitter auth_token (Cookie)",
    type="password",
    key="twitter_authtoken_val",
    help="Opcional. Si deseas hacer scraping real de Twitter (X), ingresa tu cookie 'auth_token'.",
    disabled=st.session_state.monitoring_active
)

st.sidebar.text_input(
    "Facebook cookies (Cookie header)",
    type="password",
    key="facebook_cookies_val",
    help="Opcional. Si deseas hacer scraping real de Facebook, ingresa tus cookies.",
    disabled=st.session_state.monitoring_active
)

# Load union of all active clients' keywords dynamically
clients_db = database.get_all_clients()
union_kws = set()
for c in clients_db:
    if c.get("enabled", 1) == 0:
        continue
    union_kws.update([k.strip() for k in c["keywords"].split(",") if k.strip()])
union_kws_str = ", ".join(sorted(list(union_kws)))

# Sync with running engine in-place if active
if st.session_state.get("monitoring_active") and "engine" in st.session_state and st.session_state.engine:
    new_kws_list = [k.strip() for k in union_kws_str.split(",") if k.strip()]
    # Check if they are actually different to avoid unnecessary list operations
    if sorted(st.session_state.engine.keywords) != sorted(new_kws_list):
        st.session_state.engine.keywords.clear()
        st.session_state.engine.keywords.extend(new_kws_list)
        st.session_state.keywords_str = union_kws_str
        st.session_state.keywords_input_state = union_kws_str

# Text area for keywords and channels shown dynamically if not monitoring
if not st.session_state.monitoring_active:
    st.sidebar.text_input(
        "Palabras Clave Activas (Unificadas)",
        value=union_kws_str,
        key="keywords_input_state_display",
        disabled=True,
        help="Estas son las palabras clave unificadas de todos los clientes configurados. Para modificarlas, vaya a la pestaña 'Clientes'."
    )
    st.session_state.keywords_input_state = union_kws_str
    st.session_state.keywords_str = union_kws_str
    
    DEFAULT_RADIO_CHANNELS = """Alofoke FM (99.3) | https://radiordomi.com/8566/stream/1/
CDN Radio (92.5) | https://play.cdnradio.com.do/cdnlive
Dale 101.9 | https://stream.zeno.fm/2h6plesly3nvv
Escándalo 102.5 | https://stream.zeno.fm/iwqlyzpyry1uv
Estación 97.7 | https://stream2.rcast.net/61187
Fidelity (94.1) | https://autodiscover.fidelityfm.com.do/fid
Independencia (93.3) | https://stream.radiojar.com/nc893hafc8zuv
La 91 FM | https://stream.zeno.fm/859cd7buqg8uv
La Bakana (105.7) | https://stream.zeno.fm/eym18zp7cyptv
La Nota Diferente | https://tunein.com/radio/La-Nota-957-FM-s256372/
La Nueva 106.9 | https://lanueva106.radioca.st/stream/1/
La Voz FF.AA. (HIFA) | https://rs2.radiordomi.com/8412/stream/1/
La X 102.1 | https://audio.livecastnet.com:2535/stream
La Z101 FM | https://streaming.z101digital.com/z101
Latidos FM (93.7) | https://rstream.hostdime.com/proxy/latidos?mp=/8880
Los 40 (103.3) | https://stream.zeno.fm/sse58hcighnvv?dist=play
Pura Vida (96.7) | https://stream.zeno.fm/veeugp2tz68uv
Radio Monumental | http://radio2.grupointernet.com:8103/stream
Ritmo 96.5 FM | https://stream-49.zeno.fm/y0br5ck4ququv
Rumba FM | https://stream.zeno.fm/eticl2rpposvv
Sentido 89.3 | https://stream.zeno.fm/vghmq0fffvftv
Súper Q 100.9 | https://cast10.plugstreaming.com/stream/superq
Top Latina 101.7 | https://stream.zeno.fm/rprhbqiwozovv
Turbo 98 FM | https://stream.zeno.fm/s6c01714pa0uv
Zol 106.5 FM | https://stream.zeno.fm/w6x7q7dtpy5tv"""

    DEFAULT_TV_CHANNELS = """Acento TV | https://acentotv01.streamprolive.com/hls/live.m3u8
Ahora TV | https://stream.haislin.com/ahoratv/index.m3u8
Boreal Televisión | https://edge.essastream.com/borealtelevision/tracks-v1a1/mono.m3u8
Canal del Sol | https://stream.canaldelsol.com/sol26/live_1080.m3u8
Canal Seis | https://stream.elseis.do/canal6/live_1080.m3u8
Cibao Súper TV (Canal 55) | https://ss2.tvrdomi.com:1936/supertv55/supertv55/playlist.m3u8
Cine Visión 19 | https://5790d294af2dc.streamlock.net/tvhdlive/tvhdlive/playlist.m3u8
Color Vision | http://190.122.104.210:5080/LiveApp/streams/cvision1.m3u8
Digital Quince | http://190.122.104.210:5080/LiveApp/streams/Di15.m3u8
El Nuevo Diario TV | https://nuevodiario01.streamprolive.com/hls/live.m3u8
En Televisión (Canal 31) | https://stream.haislin.com/entelevision/index.m3u8
Hilando Fino TV | https://hilandofinotv.essastream.com:3606/live/canalhilandofinotvlive.m3u8
Luna TV (Canal 53) | https://tv.wracanal10.com:3671/live/lunatvcanal53live.m3u8
Mia Visión | https://edge.essastream.com/miavisiontv/playlist.m3u8
Microvisión (Canal 10) | https://streaming.telecablecentral.com.do/live/MicroHD/playlist.m3u8
RNN | https://2-fss-2.streamhoster.com/pl_138/206532-6829902-1/playlist.m3u8
RTVD (Canal 4) | https://protvradiostream.com:1936/canal4rd-1/ngrp:canal4rd-1_all/playlist.m3u8
Súper Canal | https://cnn.hostlagarto.com/supercanalhd/playlist.m3u8
Telecentro | http://190.122.104.210:5080/LiveApp/streams/tcentro.m3u8
Telecontacto (Canal 57) | https://streaming.grupomediosdelnorte.com:19360/telecontacto/telecontacto.m3u8
Teleunion (Canal 16) | http://server2grupocam.com:1945/teleunion/TU/playlist.m3u8
Teleuniverso Canal 29 | https://videoserver.tmcreativos.com:19360/kptjeckkaa/kptjeckkaa.m3u8
VTV (Canal 32) | https://cnn.livestreaminggroup.info:3507/live/vtv32live.m3u8"""

    DEFAULT_RSS_FEEDS = """https://news.google.com/rss?hl=es-419&gl=US&ceid=US:es-419
https://www.diariolibre.com/rss/portada.xml
https://eldia.com.do/feed/
https://elnuevodiario.com.do/feed/
https://remolacha.net/feed/
https://almomento.net/feed/
https://noticiassin.com/feed/
https://deultimominuto.net/feed/
https://eldinero.com.do/feed/"""

    if st.session_state.get("media_radio_active", True):
        st.sidebar.text_area(
            "Emisoras de Radio (Nombre | URL)",
            key="radio_channels_val",
            on_change=save_config,
            args=("radio_channels_val", "config_radio_channels"),
            help="Ingresa Nombre | URL de streaming de audio por línea."
        )
    if st.session_state.get("media_tv_active", True):
        st.sidebar.text_area(
            "Canales de TV (Nombre | URL)",
            key="tv_channels_val",
            on_change=save_config,
            args=("tv_channels_val", "config_tv_channels"),
            help="Ingresa Nombre | URL de streaming de video por línea."
        )
    if st.session_state.get("media_youtube_active", True):
        st.sidebar.text_area(
            "Canales de YouTube (URLs)",
            key="youtube_channels_val",
            on_change=save_config,
            args=("youtube_channels_val", "config_youtube_channels"),
            help="Ingresa una URL de canal por línea."
        )
    if st.session_state.get("media_instagram_active", True):
        st.sidebar.text_area(
            "Usuarios de Instagram",
            key="instagram_users_val",
            on_change=save_config,
            args=("instagram_users_val", "config_instagram_users"),
            help="Ingresa un usuario por línea (sin @)."
        )
    if st.session_state.get("media_rss_active", True):
        st.sidebar.text_area(
            "Feeds RSS (URLs)",
            key="rss_feeds_val",
            on_change=save_config,
            args=("rss_feeds_val", "config_rss_feeds"),
            help="Ingresa una URL de feed RSS por línea."
        )
else:
    st.sidebar.info(f"🔍 **Buscando:** `{st.session_state.get('keywords_str', '')}`")
    
    # Format active lists
    engine = st.session_state.get("engine")
    if engine:
        st.sidebar.markdown("**Canales Activos:**")
        if engine.radio_channels:
            r_names = [f"📻 {r['name']}" for r in engine.radio_channels]
            st.sidebar.caption(" / ".join(r_names))
        
        tv_ch = getattr(engine, "tv_channels", [])
        if tv_ch:
            tv_names = [f"📺 {tv['name']}" for tv in tv_ch]
            st.sidebar.caption(" / ".join(tv_names))
            
        if engine.youtube_channels:
            yt_names = [f"🎥 {scrapers.extract_youtube_channel_name(url)}" for url in engine.youtube_channels]
            st.sidebar.caption(" / ".join(yt_names))
            
        if engine.instagram_channels:
            ig_names = [f"📸 @{user}" for user in engine.instagram_channels]
            st.sidebar.caption(" / ".join(ig_names))
            
        if getattr(engine, "twitter_active", False):
            st.sidebar.caption("🐦 Twitter (Búsqueda de Palabras Clave)")
            
        if getattr(engine, "facebook_active", False):
            st.sidebar.caption("📘 Facebook (Búsqueda de Palabras Clave)")
            
        if engine.rss_feeds:
            rss_names = [f"📰 {scrapers.extract_rss_domain(url)}" for url in engine.rss_feeds]
            st.sidebar.caption(" / ".join(rss_names))

st.sidebar.markdown("---")

# --- SMTP MAIL CONFIGURATION ---
with st.sidebar.expander("📧 Configuración SMTP"):
    smtp_server = st.text_input("Servidor SMTP", value=smtp_config.get("server", ""), key="smtp_server_val")
    smtp_port = st.number_input("Puerto SMTP", value=int(smtp_config.get("port", 587)), min_value=1, max_value=65535, key="smtp_port_val")
    smtp_user = st.text_input("Usuario (Email)", value=smtp_config.get("user", ""), key="smtp_user_val")
    smtp_password = st.text_input("Contraseña", value=smtp_config.get("password", ""), type="password", key="smtp_password_val")
    smtp_to = st.text_area("Destinatarios (separados por comas)", value=smtp_config.get("to", ""), key="smtp_to_val")
    security_options = ["STARTTLS (587)", "SSL/TLS (465)", "Ninguna"]
    saved_security = smtp_config.get("security", "STARTTLS")
    default_security_idx = 0 if saved_security == "STARTTLS" else (1 if saved_security == "SSL/TLS" else 2)
    smtp_security = st.selectbox("Seguridad", options=security_options, index=default_security_idx, key="smtp_security_val")

    # If any SMTP config changes, save it to database
    new_smtp_config = {
        "server": smtp_server,
        "port": int(smtp_port),
        "user": smtp_user,
        "password": smtp_password,
        "to": smtp_to,
        "security": "STARTTLS" if smtp_security.startswith("STARTTLS") else ("SSL/TLS" if smtp_security.startswith("SSL/TLS") else "None")
    }
    
    if new_smtp_config != smtp_config:
        database.set_state("smtp_config", json.dumps(new_smtp_config))
        smtp_config = new_smtp_config
        
    if st.button("🧪 Probar Conexión", use_container_width=True):
        if not smtp_server or not smtp_user or not smtp_password or not smtp_to:
            st.error("Por favor completa todos los campos del servidor.")
        else:
            with st.spinner("Probando conexión SMTP..."):
                test_success, test_err = test_smtp_connection(new_smtp_config)
                if test_success:
                    st.success("✅ Conexión SMTP exitosa. Correo de prueba enviado.")
                else:
                    st.error(f"❌ Error de conexión: {test_err}")

# --- DANGER ZONE (RESET DATABASE) ---
with st.sidebar.expander("⚠️ Zona de Peligro"):
    st.markdown("<small style='color: #e74c3c;'>Esta acción borrará todas las alertas, historial y clientes registrados, restableciendo el sistema a su estado inicial. Las configuraciones de canales no se perderán.</small>", unsafe_allow_html=True)
    confirm_reset = st.checkbox("Confirmar borrado completo", key="confirm_reset_db_checkbox")
    if st.button("🗑️ Borrar Todos los Datos", type="primary", use_container_width=True, disabled=not confirm_reset):
        # 1. Stop monitoring if running
        if st.session_state.monitoring_active and "engine" in st.session_state and st.session_state.engine:
            st.session_state.engine.stop()
            st.session_state.monitoring_active = False
            
        # 2. Reset database
        database.reset_entire_database()
        
        # 3. Reset session states
        st.session_state.active_client_id = 1
        st.session_state.alerts = []
        st.session_state.approved_alerts = []
        st.session_state.approved_count = 0
        st.session_state.system_logs = ["⏱️ `[" + datetime.now().strftime("%H:%M:%S") + "]` Base de datos restablecida completamente."]
        
        st.success("✅ Base de datos borrada con éxito.")
        st.rerun()

# --- DIAGNOSTICS DISPLAY ---
st.sidebar.markdown("### 🔍 Diagnóstico de Dependencias")
col_diag1, col_diag2 = st.sidebar.columns(2)

def status_badge(available):
    return "🟢 OK" if available else "❌ N/A"

with col_diag1:
    st.markdown(f"**FFmpeg:** {status_badge(sys_status['ffmpeg'])}")
    st.markdown(f"**Whisper:** {status_badge(sys_status['whisper'])}")
with col_diag2:
    st.markdown(f"**Playwright:** {status_badge(sys_status['playwright'])}")
    st.markdown(f"**Ollama:** {status_badge(sys_status['ollama'])}")

st.sidebar.markdown(f"**FFmpeg Path:** `{scrapers.get_ffmpeg_path()}`")

# Auto-download option if ffmpeg.exe is missing on the client PC
local_ffmpeg_exists = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"))
if not local_ffmpeg_exists:
    st.sidebar.warning("⚠️ No se detectó 'ffmpeg.exe' local en la raíz del proyecto. El motor podría fallar al grabar streams.")
    if st.sidebar.button("📥 Descargar FFmpeg Completo", use_container_width=True, help="Descarga e instala automáticamente la versión completa de FFmpeg (gyan.dev) requerida para la grabación de transmisiones."):
        with st.spinner("Descargando y extrayendo FFmpeg... (Puede tomar 1 o 2 minutos)"):
            success = scrapers.download_local_ffmpeg()
            if success:
                st.sidebar.success("✅ ¡FFmpeg instalado con éxito!")
                st.session_state.system_status = scrapers.check_system_status()
                st.rerun()
            else:
                st.sidebar.error("❌ Falló la descarga. Intente de nuevo o ejecute 'setup.bat'.")

if sys_status["ollama"]:
    st.sidebar.caption(f"Modelos detectados: `{', '.join(sys_status['ollama_models']) or 'Ninguno'}`")
else:
    st.sidebar.caption("Ollama offline en puerto `11434`.")

if missing_deps and not st.session_state.force_simulation:
    st.sidebar.warning("⚠️ Faltan dependencias en el sistema. Se recomienda activar 'Forzar Modo Simulación' para evitar fallas.")

if st.sidebar.button("🔄 Re-verificar Dependencias", use_container_width=True):
    st.session_state.system_status = scrapers.check_system_status()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧹 Mantenimiento")
if st.sidebar.button("🧹 Resetear Caché y Enfriamientos", use_container_width=True, help="Borra la bitácora de contenidos procesados y restablece los enfriamientos para permitir re-escanear videos anteriores."):
    import database
    database.clear_cache_and_cooldowns()
    st.sidebar.success("✅ Caché y enfriamientos restablecidos con éxito.")

st.sidebar.markdown("### ⚙️ Actualizaciones")
try:
    import subprocess
    # Check if git is available and inside a work tree
    res_status = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=5)
    is_git = (res_status.returncode == 0)
except (FileNotFoundError, Exception):
    is_git = False

if is_git:
    if st.sidebar.button("🔄 Buscar Actualizaciones", use_container_width=True, key="git_update_btn"):
        with st.spinner("Buscando e instalando actualizaciones..."):
            try:
                # Run git pull
                res = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=20)
                if "Already up to date" in res.stdout or "Ya está al día" in res.stdout:
                    st.sidebar.success("✅ El sistema ya está actualizado.")
                elif res.returncode == 0:
                    st.sidebar.success("🎉 ¡Actualización descargada! Instalando dependencias...")
                    # Re-run requirements installation
                    pip_path = os.path.join(os.getcwd(), "venv", "Scripts", "pip.exe")
                    if not os.path.exists(pip_path):
                        pip_path = "pip" # Fallback
                    subprocess.run([pip_path, "install", "-r", "requirements.txt"])
                    st.sidebar.info("Reiniciando aplicación...")
                    st.rerun()
                else:
                    # If git pull failed (e.g. conflicts)
                    st.sidebar.error(f"Error al conectar con el repositorio. Detalle: {res.stderr[:100]}")
            except Exception as e:
                st.sidebar.error(f"Error al actualizar via Git: {e}")
else:
    # ZIP-based update fallback for private repositories
    github_token = database.get_state("github_token", "")
    
    st.sidebar.warning("📦 Instalación ZIP (Repositorio Privado)")
    
    github_token_val = st.sidebar.text_input(
        "GitHub Token (PAT)", 
        value=github_token, 
        type="password", 
        help="Requerido para la descarga automática desde el repositorio privado. Consigue un PAT en tu cuenta de GitHub con acceso de lectura (read:packages o repo).",
        key="github_token_input"
    )
    if github_token_val != github_token:
        database.set_state("github_token", github_token_val)
        st.rerun()
    
    if st.sidebar.button("🔄 Buscar Actualizaciones", use_container_width=True, key="zip_update_btn"):
        with st.spinner("Buscando e instalando actualizaciones desde GitHub..."):
            try:
                import urllib.request
                import zipfile
                import io
                import shutil
                import subprocess
                
                zip_data = None
                
                # 1. Try public download first (anonymous)
                try:
                    public_url = "https://github.com/Vaporwaver/warroom/archive/refs/heads/main.zip"
                    req = urllib.request.Request(
                        public_url, 
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    with urllib.request.urlopen(req, timeout=45) as response:
                        zip_data = response.read()
                except Exception:
                    # 2. If public fails, fall back to authenticated token download
                    if github_token_val:
                        private_url = "https://api.github.com/repos/Vaporwaver/warroom/zipball/main"
                        req = urllib.request.Request(
                            private_url, 
                            headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                                'Authorization': f'Bearer {github_token_val}'
                            }
                        )
                        with urllib.request.urlopen(req, timeout=45) as response:
                            zip_data = response.read()
                    else:
                        raise Exception("El repositorio es privado o inaccesible. Configure un GitHub Token en la barra lateral o use la opción manual subiendo el archivo ZIP.")
                
                if not zip_data:
                    raise Exception("No se obtuvieron datos de la actualización.")
                    
                st.sidebar.info("📂 Extrayendo y aplicando actualización...")
                temp_dir = os.path.join(os.getcwd(), "temp_update")
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                os.makedirs(temp_dir)
                
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                extracted_root = temp_dir
                if dirs:
                    test_root = os.path.join(temp_dir, dirs[0])
                    if os.path.exists(os.path.join(test_root, "app.py")):
                        extracted_root = test_root
                
                # Copy files
                for root_dir, subdirs, files in os.walk(extracted_root):
                    rel_path = os.path.relpath(root_dir, extracted_root)
                    dest_dir = os.path.normpath(os.path.join(os.getcwd(), rel_path)) if rel_path != "." else os.getcwd()
                    
                    dest_dir_lower = dest_dir.lower()
                    if "temp_update" in dest_dir_lower or "venv" in dest_dir_lower or "static" in dest_dir_lower:
                        continue
                        
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                        
                    for file in files:
                        src_file = os.path.join(root_dir, file)
                        dest_file = os.path.join(dest_dir, file)
                        
                        if file.lower() == "db.sqlite":
                            continue
                            
                        shutil.copy2(src_file, dest_file)
                
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
                
                st.sidebar.success("🎉 ¡Actualización aplicada con éxito! Instalando dependencias...")
                
                # Re-run requirements installation
                pip_path = os.path.join(os.getcwd(), "venv", "Scripts", "pip.exe")
                if not os.path.exists(pip_path):
                    pip_path = "pip" # Fallback
                subprocess.run([pip_path, "install", "-r", "requirements.txt"])
                
                st.sidebar.info("Reiniciando aplicación...")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error al actualizar desde el ZIP: {e}")

    # Manual Update Options
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Actualización Manual (Sin Token)**")
    st.sidebar.markdown(
        "[📥 Descargar ZIP desde GitHub](https://github.com/Vaporwaver/warroom/archive/refs/heads/main.zip)", 
        help="Abre GitHub en tu navegador para descargar el archivo ZIP directamente (requiere estar logueado en tu cuenta con acceso al repositorio)."
    )
    
    uploaded_zip = st.sidebar.file_uploader("Cargar archivo ZIP descargado", type=["zip"], key="uploaded_zip_sidebar")
    if uploaded_zip is not None:
        if st.sidebar.button("🚀 Aplicar ZIP cargado", use_container_width=True, key="manual_zip_apply_btn"):
            with st.spinner("Aplicando actualización desde el archivo cargado..."):
                try:
                    import zipfile
                    import io
                    import shutil
                    import subprocess
                    
                    zip_data = uploaded_zip.read()
                    
                    temp_dir = os.path.join(os.getcwd(), "temp_update")
                    if os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except Exception:
                            pass
                    os.makedirs(temp_dir)
                    
                    with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                    extracted_root = temp_dir
                    if dirs:
                        test_root = os.path.join(temp_dir, dirs[0])
                        if os.path.exists(os.path.join(test_root, "app.py")):
                            extracted_root = test_root
                    
                    # Copy files
                    for root_dir, subdirs, files in os.walk(extracted_root):
                        rel_path = os.path.relpath(root_dir, extracted_root)
                        dest_dir = os.path.normpath(os.path.join(os.getcwd(), rel_path)) if rel_path != "." else os.getcwd()
                        
                        dest_dir_lower = dest_dir.lower()
                        if "temp_update" in dest_dir_lower or "venv" in dest_dir_lower or "static" in dest_dir_lower:
                            continue
                            
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                            
                        for file in files:
                            src_file = os.path.join(root_dir, file)
                            dest_file = os.path.join(dest_dir, file)
                            
                            if file.lower() == "db.sqlite":
                                continue
                                
                            shutil.copy2(src_file, dest_file)
                    
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                    
                    st.sidebar.success("🎉 ¡Actualización del ZIP aplicada! Instalando dependencias...")
                    
                    # Re-run requirements
                    pip_path = os.path.join(os.getcwd(), "venv", "Scripts", "pip.exe")
                    if not os.path.exists(pip_path):
                        pip_path = "pip"
                    subprocess.run([pip_path, "install", "-r", "requirements.txt"])
                    
                    st.sidebar.info("Reiniciando aplicación...")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error al aplicar el archivo ZIP: {e}")


@st.fragment(run_every=2)
def render_right_column():
    # 1. Process queues from background engine
    if st.session_state.monitoring_active and "engine" in st.session_state and st.session_state.engine:
        engine = st.session_state.engine
        new_alerts_added = False
        new_logs_added = False
        
        while not engine.alerts_queue.empty():
            try:
                _ = engine.alerts_queue.get_nowait()
                new_alerts_added = True
            except queue.Empty:
                break
                
        while not engine.logs_queue.empty():
            try:
                log_msg = engine.logs_queue.get_nowait()
                st.session_state.system_logs.insert(0, log_msg)
                new_logs_added = True
            except queue.Empty:
                break
                
        if len(st.session_state.system_logs) > 300:
            st.session_state.system_logs = st.session_state.system_logs[:300]
            
        if new_alerts_added:
            st.session_state.should_reload = True
            st.rerun(scope="app")

    # 2. Track SMTP transitions
    if "prev_smtp_sending" not in st.session_state:
        st.session_state.prev_smtp_sending = False
        
    current_smtp_sending = st.session_state.get("smtp_sending", False)
    if not current_smtp_sending and st.session_state.prev_smtp_sending:
        st.session_state.prev_smtp_sending = False
        st.rerun(scope="app")
    st.session_state.prev_smtp_sending = current_smtp_sending

    # 3. Render the metrics and logs in col_right
    st.markdown("### <i class='fa-solid fa-chart-simple'></i> Métricas de Medios", unsafe_allow_html=True)
    
    # Contador de noticias/contenido verificado (Instagram, RSS, YouTube, Twitter, Facebook)
    processed_counts = database.get_processed_counts()
    st.markdown("##### <i class='fa-solid fa-circle-check'></i> Contenido Verificado (Escaneado)", unsafe_allow_html=True)
    col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns(5)
    with col_v1:
        st.metric(label="📸 Instagram", value=processed_counts["instagram"])
    with col_v2:
        st.metric(label="📰 RSS", value=processed_counts["rss"])
    with col_v3:
        st.metric(label="🎥 YouTube", value=processed_counts["youtube"])
    with col_v4:
        st.metric(label="🐦 Twitter", value=processed_counts.get("twitter", 0))
    with col_v5:
        st.metric(label="📘 Facebook", value=processed_counts.get("facebook", 0))
    
    st.markdown("---")
    
    # Graphic: Distribution by source
    sources = [a["source"] for a in st.session_state.alerts]
    radio_cnt = sum(1 for s in sources if "Radio" in s)
    tv_cnt = sum(1 for s in sources if "TV" in s)
    yt_cnt = sum(1 for s in sources if "YouTube" in s)
    ig_cnt = sum(1 for s in sources if "Instagram" in s)
    tw_cnt = sum(1 for s in sources if "Twitter" in s)
    fb_cnt = sum(1 for s in sources if "Facebook" in s)
    rss_cnt = sum(1 for s in sources if "RSS" in s)
    
    total_m = len(st.session_state.alerts)
    pos_cnt = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Positivo")
    neu_cnt = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Neutral")
    neg_cnt = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Negativo")
    
    st.markdown("##### <i class='fa-solid fa-chart-column'></i> Volumen por Canal", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-radio' style='color: #9b59b6; margin-right: 6px;'></i>Radio ({radio_cnt})</div>", unsafe_allow_html=True)
    st.progress(radio_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-tv' style='color: #3498db; margin-right: 6px;'></i>TV ({tv_cnt})</div>", unsafe_allow_html=True)
    st.progress(tv_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-brands fa-youtube' style='color: #e74c3c; margin-right: 6px;'></i>YouTube ({yt_cnt})</div>", unsafe_allow_html=True)
    st.progress(yt_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-brands fa-instagram' style='color: #e1306c; margin-right: 6px;'></i>Instagram ({ig_cnt})</div>", unsafe_allow_html=True)
    st.progress(ig_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-brands fa-x-twitter' style='color: #f1f2f6; margin-right: 6px;'></i>Twitter ({tw_cnt})</div>", unsafe_allow_html=True)
    st.progress(tw_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-brands fa-facebook' style='color: #1877f2; margin-right: 6px;'></i>Facebook ({fb_cnt})</div>", unsafe_allow_html=True)
    st.progress(fb_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-rss' style='color: #f1c40f; margin-right: 6px;'></i>RSS ({rss_cnt})</div>", unsafe_allow_html=True)
    st.progress(rss_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("---")
    st.markdown("##### <i class='fa-solid fa-heart-pulse'></i> Distribución de Sentimiento", unsafe_allow_html=True)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-circle-check' style='color: #2ecc71; margin-right: 6px;'></i>Positivo ({pos_cnt})</div>", unsafe_allow_html=True)
    st.progress(pos_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-circle-info' style='color: #3498db; margin-right: 6px;'></i>Neutral ({neu_cnt})</div>", unsafe_allow_html=True)
    st.progress(neu_cnt / total_m if total_m > 0 else 0.0)
    
    st.markdown("<div style='font-size: 0.9rem; margin-bottom: 2px;'><i class='fa-solid fa-circle-exclamation' style='color: #e74c3c; margin-right: 6px;'></i>Negativo ({neg_cnt})</div>", unsafe_allow_html=True)
    st.progress(neg_cnt / total_m if total_m > 0 else 0.0)
    
    # --- Media Uptime Panel ---
    if st.session_state.monitoring_active and "engine" in st.session_state and st.session_state.engine:
        engine = st.session_state.engine
        if hasattr(engine, "uptime_status") and engine.uptime_status:
            st.markdown("---")
            st.markdown("### <i class='fa-solid fa-circle-nodes'></i> Uptime de Medios", unsafe_allow_html=True)
            for name, info in sorted(engine.uptime_status.items()):
                status = info["status"]
                err = info["error"]
                if status == "Online":
                    status_badge = f"<span style='color:#2ecc71; font-weight:bold;'>🟢 Online</span>"
                elif status == "Simulando":
                    status_badge = f"<span style='color:#3498db; font-weight:bold;'>🔵 Simulando</span>"
                elif status == "No en vivo":
                    status_badge = f"<span style='color:#f39c12; font-weight:bold;' title='{err}'>🟡 No en vivo</span>"
                else:
                    status_badge = f"<span style='color:#e74c3c; font-weight:bold;' title='{err}'>🔴 Offline</span>"
                
                st.markdown(f"{name}: {status_badge}", unsafe_allow_html=True)
                if status in ("Online", "Simulando"):
                    url = info.get("url")
                    media_type = info.get("type")
                    if url:
                        clean_name = name.replace("📻 Radio (", "").replace("📺 TV (", "").replace(")", "")
                        if media_type == "Radio":
                            with st.expander(f"🔊 Escuchar {clean_name}"):
                                st.audio(url)
                        elif media_type == "TV":
                            with st.expander(f"📺 Ver {clean_name}"):
                                st.video(url)
                if err:
                    st.caption(f"⚠️ `{err[:120]}`")

    st.markdown("---")
    
    # System Diagnostic Logs Panel
    st.markdown("### <i class='fa-solid fa-clock-history'></i> Bitácora del Sistema", unsafe_allow_html=True)
    with st.container(height=300):
        if not st.session_state.system_logs:
            st.caption("No hay eventos registrados en la bitácora aún. Inicia el motor para ver trazas de depuración.")
        else:
            for log in st.session_state.system_logs:
                st.markdown(log)
                
    if st.session_state.system_logs:
        clean_logs = "\n".join([log.replace("⏱️ `", "[").replace("`", "]") for log in st.session_state.system_logs])
        st.download_button(
            label="💾 Descargar Bitácora Completa (.txt)",
            data=clean_logs,
            file_name=f"bitacora_sistema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )


# --- CENTRAL PANEL: Dashboard Visuals ---
st.markdown("<h1 class='main-title'>War Room - Monitoreo de Medios con IA</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#a0a0a0; font-size:1.1rem; margin-bottom:25px;'>Monitoreo local en vivo de Radio, YouTube e Instagram con procesamiento lingüístico inteligente local.</p>", unsafe_allow_html=True)

# Selectbox for Active Client
clients = database.get_all_clients()
client_names = [c["name"] for c in clients]
if client_names:
    active_idx = 0
    for idx, c in enumerate(clients):
        if c["id"] == st.session_state.active_client_id:
            active_idx = idx
            break
    
    selected_client_name = st.selectbox(
        "👥 **Seleccione Cliente Activo:**",
        options=client_names,
        index=active_idx,
        key="active_client_selectbox_val",
        help="Seleccione el cliente para visualizar sus alertas filtradas, métricas y reportes."
    )
    selected_client = next(c for c in clients if c["name"] == selected_client_name)
    if selected_client["id"] != st.session_state.active_client_id:
        st.session_state.active_client_id = selected_client["id"]
        st.session_state.page_num = 1  # Reset page number to 1 when client changes
        st.session_state.should_reload = True
        st.session_state.should_reload_approved = True
        st.rerun()
else:
    st.warning("⚠️ No hay clientes configurados en el sistema. Vaya a la pestaña de Clientes para agregar uno.")

# Status indicators
if st.session_state.monitoring_active:
    mode_desc = "SIMULACIÓN COMPLETA" if st.session_state.force_simulation else "MONITOREO REAL EN VIVO"
    st.markdown(f"""
    <div class="pulse-container">
        <span class="pulse"></span>
        <span style="color: #2ecc71; font-weight: bold; font-size: 0.95rem;">MOTOR ACTIVO ({mode_desc})</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="inactive-container">
        <span class="dot-inactive"></span>
        <span style="color: #95a5a6; font-weight: bold; font-size: 0.95rem;">MOTOR DETENIDO</span>
    </div>
    """, unsafe_allow_html=True)

# Metric Summary Bar
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

total_mentions = len(st.session_state.alerts)
approved_mentions = st.session_state.approved_count

# Calculate sentiment breakdown
pos_count = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Positivo")
neg_count = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Negativo")
neu_count = sum(1 for a in st.session_state.alerts if a["sentimiento"] == "Neutral")

if st.session_state.alerts:
    dom_sent = max(["Positivo", "Negativo", "Neutral"], key=lambda s: sum(1 for a in st.session_state.alerts if a["sentimiento"] == s))
    if dom_sent == "Positivo": dom_sent_str = "🟢 Positivo"
    elif dom_sent == "Negativo": dom_sent_str = "🔴 Negativo"
    else: dom_sent_str = "🔵 Neutral"
else:
    dom_sent_str = "N/A"

with col_m1:
    st.metric("Alertas en Bandeja", total_mentions, help="Menciones detectadas que esperan por validación.")
with col_m2:
    st.metric("Total Aprobadas", approved_mentions, help="Menciones validadas por el operador.")
with col_m3:
    st.metric("Sentimiento Predominante", dom_sent_str, help="Sentimiento más recurrente en la bandeja actual.")
with col_m4:
    # Distribution index
    neg_pct = int((neg_count / total_mentions) * 100) if total_mentions > 0 else 0
    st.metric("Índice de Alertas Críticas", f"{neg_pct}%", help="Porcentaje de menciones con sentimiento Negativo.")

st.markdown("---")

# Main Content Grid: Split between alerts list and details
col_left, col_right = st.columns([0.65, 0.35])

with col_left:
    tab_validation, tab_report, tab_face, tab_clients = st.tabs(["📥 Bandeja de Validación", "📝 Generador de Reportes", "🔍 Búsqueda Facial", "👥 Clientes"])
    
    with tab_validation:
        # Render filters
        if st.session_state.alerts:
            st.markdown("##### <i class='fa-solid fa-filter'></i> Filtrar y Buscar Alertas", unsafe_allow_html=True)
            
            # Obtener todas las palabras clave únicas presentes en las alertas de la bandeja de validación
            all_keywords = set()
            for alert in st.session_state.alerts:
                if alert.get("keywords"):
                    for kw in alert["keywords"]:
                        if kw.strip():
                            all_keywords.add(kw.strip())
            sorted_keywords = sorted(list(all_keywords))
            
            col_f1, col_f2, col_f3, col_f4 = st.columns([0.35, 0.25, 0.22, 0.18])
            with col_f1:
                selected_keywords = st.multiselect(
                    "Palabras Clave",
                    options=sorted_keywords,
                    default=[],
                    placeholder="Seleccionar...",
                    key="selected_keywords_val"
                )
            with col_f2:
                selected_media = st.multiselect("Tipo de Medio", ["📻 Radio", "📺 TV", "🎥 YouTube", "📸 Instagram", "🐦 Twitter", "📘 Facebook", "📰 RSS"], default=["📻 Radio", "📺 TV", "🎥 YouTube", "📸 Instagram", "🐦 Twitter", "📘 Facebook", "📰 RSS"], key="selected_media_val")
            with col_f3:
                # Find all sources in the alerts cache
                all_sources = list(set([a["source"] for a in st.session_state.alerts]))
                # Filter specific sources based on selected media types
                matching_sources = []
                if not selected_media:
                    matching_sources = all_sources
                else:
                    for src in all_sources:
                        src_lower = src.lower()
                        for m_type in selected_media:
                            if "Radio" in m_type and "radio" in src_lower:
                                matching_sources.append(src)
                            elif "TV" in m_type and "tv" in src_lower:
                                matching_sources.append(src)
                            elif "YouTube" in m_type and "youtube" in src_lower:
                                matching_sources.append(src)
                            elif "Instagram" in m_type and "instagram" in src_lower:
                                matching_sources.append(src)
                            elif "Twitter" in m_type and "twitter" in src_lower:
                                matching_sources.append(src)
                            elif "Facebook" in m_type and "facebook" in src_lower:
                                matching_sources.append(src)
                            elif "RSS" in m_type and "rss" in src_lower:
                                matching_sources.append(src)
                matching_sources = sorted(list(set(matching_sources)))
                selected_sources = st.multiselect("Fuente/Canal", options=matching_sources, default=matching_sources, key="selected_sources_val")
            with col_f4:
                selected_sentiments = st.multiselect("Sentimiento", options=["Positivo", "Neutral", "Negativo"], default=["Positivo", "Neutral", "Negativo"], key="selected_sentiments_val")
                
            filtered_alerts = []
            for alert in st.session_state.alerts:
                keyword_match = True
                if selected_keywords:
                    alert_kws_set = {kw.lower().strip() for kw in alert.get("keywords", [])}
                    selected_kws_set = {kw.lower().strip() for kw in selected_keywords}
                    keyword_match = bool(alert_kws_set.intersection(selected_kws_set))
                
                source_match = True if not selected_sources else (alert["source"] in selected_sources)
                sentiment_match = True if not selected_sentiments else (alert["sentimiento"] in selected_sentiments)
                
                # Check medium type match
                source_lower = alert["source"].lower()
                media_type_match = False
                if not selected_media:
                    media_type_match = True
                else:
                    for m_type in selected_media:
                        if "Radio" in m_type and "radio" in source_lower:
                            media_type_match = True
                        elif "TV" in m_type and "tv" in source_lower:
                            media_type_match = True
                        elif "YouTube" in m_type and "youtube" in source_lower:
                            media_type_match = True
                        elif "Instagram" in m_type and "instagram" in source_lower:
                            media_type_match = True
                        elif "Twitter" in m_type and "twitter" in source_lower:
                            media_type_match = True
                        elif "Facebook" in m_type and "facebook" in source_lower:
                            media_type_match = True
                        elif "RSS" in m_type and "rss" in source_lower:
                            media_type_match = True
                        
                if keyword_match and source_match and sentiment_match and media_type_match:
                    filtered_alerts.append(alert)
        else:
            filtered_alerts = []

        # Pagination Settings for Inbox
        PAGE_SIZE = 10
        total_filtered = len(filtered_alerts)
        total_pages = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)
        
        if "page_num" not in st.session_state:
            st.session_state.page_num = 1
            
        # Bounds check
        if st.session_state.page_num > total_pages:
            st.session_state.page_num = total_pages
        if st.session_state.page_num < 1:
            st.session_state.page_num = 1
            
        start_idx = (st.session_state.page_num - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_filtered)
        
        page_alerts = filtered_alerts[start_idx:end_idx]

        # Render alerts list
        if not st.session_state.alerts:
            st.info("💡 **Bandeja vacía.** Inicia el motor de monitoreo en la barra lateral para capturar menciones o espera a que se detecten eventos.")
            
            # Design a cute empty state placeholder graphic
            st.markdown("""
            <div style="text-align: center; padding: 40px; color: #6f7c7d;">
                <img src="https://img.icons8.com/dotty/80/null/document-delivery.png" style="opacity: 0.3; margin-bottom:15px;"/><br/>
                <span>No hay menciones pendientes de validar en este momento.</span>
            </div>
            """, unsafe_allow_html=True)
        elif not filtered_alerts:
            st.info("💡 **Sin resultados.** Ninguna mención coincide con los filtros de búsqueda aplicados.")
        else:
            # Loop through alerts in page
            for idx, alert in enumerate(page_alerts):
                # Select icon
                source_lower = alert["source"].lower()
                if "radio" in source_lower: source_icon = '<i class="fa-solid fa-radio" style="color: #9b59b6;"></i>'
                elif "tv" in source_lower: source_icon = '<i class="fa-solid fa-tv" style="color: #3498db;"></i>'
                elif "youtube" in source_lower: source_icon = '<i class="fa-brands fa-youtube" style="color: #e74c3c;"></i>'
                elif "twitter" in source_lower: source_icon = '<i class="fa-brands fa-x-twitter" style="color: #f1f2f6;"></i>'
                elif "facebook" in source_lower: source_icon = '<i class="fa-brands fa-facebook" style="color: #1877f2;"></i>'
                elif "google news" in source_lower: source_icon = '<i class="fa-solid fa-newspaper" style="color: #ee802f;"></i>'
                elif "rss" in source_lower: source_icon = '<i class="fa-solid fa-rss" style="color: #f1c40f;"></i>'
                else: source_icon = '<i class="fa-brands fa-instagram" style="color: #e1306c;"></i>'
                
                # Select Sentiment Style classes and badge
                sent = alert["sentimiento"].lower()
                if sent == "positivo":
                    card_class = "pr-card-positivo"
                    sent_badge = f"<span class='badge-sentiment badge-pos'>Positivo</span>"
                    sent_color = "#2ecc71"
                elif sent == "negativo":
                    card_class = "pr-card-negativo"
                    sent_badge = f"<span class='badge-sentiment badge-neg'>Negativo</span>"
                    sent_color = "#e74c3c"
                else:
                    card_class = "pr-card-neutral"
                    sent_badge = f"<span class='badge-sentiment badge-neu'>Neutral</span>"
                    sent_color = "#3498db"
                    
                formatted_time = datetime.fromtimestamp(alert["timestamp"]).strftime("%I:%M:%S %p")
                
                # Keywords html badges
                kw_badges = "".join([f"<span class='badge-kw'>#{kw}</span>" for kw in alert["keywords"]])
                
                # Simulated flag badge
                sim_badge = "<span class='badge-simulated'>Simulación</span>" if alert["simulated"] else ""
                
                # Construct card html content (concatenated without leading spacing to avoid Markdown block-code rendering bugs)
                html_card = (
                    f'<div class="pr-card {card_class}">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
                    f'<div style="display: flex; align-items: center; gap: 8px;">'
                    f'<span style="font-size: 1.4rem;">{source_icon}</span>'
                    f'<strong style="font-size: 1.1rem; color: #f1f2f6;">{alert["source"]}</strong>'
                    f'{sim_badge}'
                    f'</div>'
                    f'<span style="color: #7f8c8d; font-size: 0.85rem; font-family: monospace;">{formatted_time}</span>'
                    f'</div>'
                    f'<div class="pr-quote">"{alert["text"]}"</div>'
                    f'<div style="background-color: rgba(255, 255, 255, 0.03); border-left: 3px solid {sent_color}; padding: 12px; border-radius: 4px; margin-bottom: 12px;">'
                    f'<strong style="color: {sent_color}; font-size: 0.9rem;">ANÁLISIS DE RESUMEN (IA):</strong>'
                    f'<p style="margin: 4px 0 0 0; font-size: 1rem; color: #e1e2e6;">{alert["resumen"]}</p>'
                    f'</div>'
                    f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">'
                    f'<div style="display: flex; gap: 5px; align-items: center; flex-wrap: wrap;">'
                    f'{sent_badge}'
                    f'{kw_badges}'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
                
                # Display inside structured container with action columns
                with st.container():
                    col_card, col_btn = st.columns([0.88, 0.12])
                    with col_card:
                        st.markdown(html_card, unsafe_allow_html=True)
                        
                        # Render YouTube specific details (title, timestamp) and external link button
                        metadata = alert.get("metadata", {})
                        if "youtube" in source_lower:
                            video_title = metadata.get("video_title", "Video de YouTube")
                            seconds = metadata.get("seconds")
                            
                            if seconds is not None:
                                minutes = seconds // 60
                                secs = seconds % 60
                                st.markdown(f"🎥 **Video:** `{video_title}` | ⏱️ **Momento:** `{minutes:02d}:{secs:02d}` ({seconds}s)")
                            else:
                                st.markdown(f"🎥 **Video:** `{video_title}`")
                                
                            video_url = metadata.get("video_url")
                            if video_url:
                                st.link_button("📺 Ver Video en YouTube", video_url)
                        
                        # Render Instagram specific details and external link button
                        elif "instagram" in source_lower:
                            post_url = metadata.get("post_url")
                            if post_url:
                                st.link_button("📸 Ver Publicación en Instagram", post_url)
                                
                        elif "twitter" in source_lower:
                            post_url = metadata.get("post_url")
                            if post_url:
                                st.link_button("🐦 Ver Publicación en Twitter (X)", post_url)
                                
                        elif "facebook" in source_lower:
                            post_url = metadata.get("post_url")
                            if post_url:
                                st.link_button("📘 Ver Publicación en Facebook", post_url)
                                
                        # Render RSS specific details and external link button
                        elif "rss" in source_lower:
                            post_url = metadata.get("post_url")
                            title = metadata.get("title", "Artículo de RSS")
                            st.markdown(f"📰 **Artículo:** `{title}`")
                            if post_url:
                                st.link_button("📰 Leer Artículo en Somos Pueblo", post_url)
                                
                        # Render st.audio player if audio path exists for this mention
                        audio_path = alert.get("audio_path")
                        if audio_path and os.path.exists(audio_path):
                            file_name = os.path.basename(audio_path)
                            st.link_button("↗️ Abrir Audio en otra pestaña", f"static/{file_name}")
                            
                            audio_key = f"play_audio_{alert['identifier']}"
                            if audio_key not in st.session_state:
                                st.session_state[audio_key] = False
                            
                            btn_label = "🔇 Ocultar Reproductor local" if st.session_state[audio_key] else "🎧 Escuchar Audio localmente"
                            if st.button(btn_label, key=f"btn_{audio_key}"):
                                st.session_state[audio_key] = not st.session_state[audio_key]
                                st.rerun()
                            
                            if st.session_state[audio_key]:
                                try:
                                    with open(audio_path, "rb") as f:
                                        audio_bytes = f.read()
                                    st.audio(audio_bytes, format="audio/wav")
                                except Exception as e:
                                    st.error(f"Error al reproducir audio: {e}")
                                    
                        # Render st.video player if video path exists for this mention
                        video_path = alert.get("video_path")
                        if video_path and os.path.exists(video_path):
                            file_name = os.path.basename(video_path)
                            st.link_button("↗️ Abrir Video en otra pestaña", f"static/{file_name}")
                            
                            video_key = f"play_video_{alert['identifier']}"
                            if video_key not in st.session_state:
                                st.session_state[video_key] = False
                            
                            btn_label = "🔇 Ocultar Reproductor local" if st.session_state[video_key] else "📺 Ver Clip de Video localmente"
                            if st.button(btn_label, key=f"btn_{video_key}"):
                                st.session_state[video_key] = not st.session_state[video_key]
                                st.rerun()
                            
                            if st.session_state[video_key]:
                                try:
                                    with open(video_path, "rb") as f:
                                        video_bytes = f.read()
                                    st.video(video_bytes, format="video/mp4")
                                except Exception as e:
                                    st.error(f"Error al reproducir video: {e}")
                    with col_btn:
                        # Provide vertical spacer aligning button
                        st.write("")
                        st.write("")
                        st.write("")
                        if st.button("Aprobar", key=f"aprov_{alert['identifier']}", use_container_width=True):
                            database.update_alert_status(st.session_state.active_client_id, alert['identifier'], 'approved')
                            st.session_state.should_reload = True
                            st.session_state.should_reload_approved = True
                            st.rerun()
                            
            # Page Controls
            if total_pages > 1:
                st.markdown("---")
                col_page_1, col_page_2, col_page_3 = st.columns([0.3, 0.4, 0.3])
                with col_page_1:
                    if st.button("⬅️ Anterior", disabled=(st.session_state.page_num == 1), use_container_width=True, key="prev_page_btn"):
                        st.session_state.page_num -= 1
                        st.rerun()
                with col_page_2:
                    st.markdown(f"<div style='text-align:center; padding-top:5px; color:#a0a0a0;'>Página <strong>{st.session_state.page_num}</strong> de <strong>{total_pages}</strong> ({total_filtered} alertas)</div>", unsafe_allow_html=True)
                with col_page_3:
                    if st.button("Siguiente ➡️", disabled=(st.session_state.page_num == total_pages), use_container_width=True, key="next_page_btn"):
                        st.session_state.page_num += 1
                        st.rerun()
                        
    with tab_report:
        st.markdown("### <i class='fa-solid fa-file-invoice'></i> Reporte Ejecutivo de Monitoreo", unsafe_allow_html=True)
        
        if "approved_alerts" not in st.session_state or not st.session_state.approved_alerts:
            st.info("💡 **Sin datos para reportar.** Aprueba alertas de la bandeja de validación para agregarlas al reporte diario.")
            st.markdown("""
            <div style="text-align: center; padding: 40px; color: #6f7c7d;">
                <img src="https://img.icons8.com/dotty/80/null/document-delivery.png" style="opacity: 0.3; margin-bottom:15px;"/><br/>
                <span>Una vez que apruebes menciones, podrás generar minutas y exportarlas a Excel o Markdown aquí.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"✅ Tienes **{len(st.session_state.approved_alerts)}** menciones aprobadas listas en esta sesión.")
            
            # --- Section 1: AI Consolidator ---
            st.markdown("#### <i class='fa-solid fa-robot'></i> Síntesis Consolidada por IA", unsafe_allow_html=True)
            
            # Button to trigger AI summary using Ollama
            if st.button("🤖 Generar Resumen por IA", use_container_width=True):
                with st.spinner("Ollama local analizando menciones y redactando el reporte ejecutivo..."):
                    # Compile text blocks
                    text_blocks = ""
                    for idx, a in enumerate(st.session_state.approved_alerts):
                        text_blocks += f"[{idx+1}] Fuente: {a['source']} | Sentimiento: {a['sentimiento']}\nContenido: {a['text']}\nResumen: {a['resumen']}\n\n"
                        
                    # Load active client description/context for IA
                    active_client = next((c for c in clients if c["id"] == st.session_state.active_client_id), None)
                    client_desc = active_client["description"] if active_client else ""
                    
                    prompt = (
                        "Eres un analista experto de PR y monitoreo de medios. "
                        "A continuación tienes una lista de menciones de prensa aprobadas hoy. "
                        f"Contexto del cliente: {client_desc}\n\n"
                        "Redacta un reporte ejecutivo consolidado de un máximo de dos párrafos en español, resumiendo los temas clave tratados, la distribución del sentimiento y cualquier alerta de crisis o tendencia relevante, enfocándote en los aspectos de mayor interés para el cliente según su contexto. Usa un tono formal y corporativo.\n\n"
                        f"Menciones:\n{text_blocks}"
                    )
                    
                    try:
                        import scrapers
                        
                        api_mode = st.session_state.get("engine_ai_mode_val", "Local (Ollama/Gemma)")
                        creds_path = st.session_state.get("google_vision_credentials_val", "")
                        gemini_key = st.session_state.get("google_gemini_api_key_val", "")
                        
                        analyzer = scrapers.OllamaAnalyzer(
                            model_name=st.session_state.get("ollama_model_val", "gemma4:e2b"),
                            api_mode=api_mode,
                            credentials_path=creds_path,
                            api_key=gemini_key
                        )
                        
                        summary = analyzer.generate_text(
                            system_prompt='Eres un analista de PR que redacta reportes consolidados corporativos.',
                            prompt_text=prompt
                        )
                        st.session_state.ai_summary_report = summary
                    except Exception as e:
                        # Fallback heuristic summary
                        pos_c = sum(1 for a in st.session_state.approved_alerts if a["sentimiento"] == "Positivo")
                        neg_c = sum(1 for a in st.session_state.approved_alerts if a["sentimiento"] == "Negativo")
                        sources_list = list(set([a["source"] for a in st.session_state.approved_alerts]))
                        
                        st.session_state.ai_summary_report = (
                            f"Reporte Heurístico: Se procesaron {len(st.session_state.approved_alerts)} menciones validadas "
                            f"a través de los medios monitorizados ({', '.join(sources_list)}). "
                            f"El análisis de sentimiento muestra un total de {pos_c} menciones positivas y {neg_c} menciones críticas de atención. "
                            "Las temáticas giran en torno al impacto institucional en las políticas de desarrollo social y las dinámicas legislativas."
                        )
                st.rerun()
                
            if st.session_state.get("ai_summary_report"):
                st.info(st.session_state.ai_summary_report)
                
            st.markdown("---")
            
            # --- Section 2: Formats & Downloads ---
            st.markdown("#### <i class='fa-solid fa-download'></i> Descargar Reportes", unsafe_allow_html=True)
            
            # Calculate sentiment and source counts for approved alerts
            approved_total = len(st.session_state.approved_alerts)
            app_pos = sum(1 for a in st.session_state.approved_alerts if a["sentimiento"] == "Positivo")
            app_neu = sum(1 for a in st.session_state.approved_alerts if a["sentimiento"] == "Neutral")
            app_neg = sum(1 for a in st.session_state.approved_alerts if a["sentimiento"] == "Negativo")
            
            app_sources = [a["source"] for a in st.session_state.approved_alerts]
            app_radio = sum(1 for s in app_sources if "Radio" in s)
            app_tv = sum(1 for s in app_sources if "TV" in s)
            app_yt = sum(1 for s in app_sources if "YouTube" in s)
            app_ig = sum(1 for s in app_sources if "Instagram" in s)
            app_tw = sum(1 for s in app_sources if "Twitter" in s)
            app_fb = sum(1 for s in app_sources if "Facebook" in s)
            app_rss = sum(1 for s in app_sources if "RSS" in s)

            # 1. Compile Markdown
            report_md = f"# REPORTE DIARIO DE MONITOREO DE MEDIOS\n"
            report_md += f"**Fecha de Emisión:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
            report_md += f"**Total Menciones Aprobadas:** {approved_total}\n\n"
            
            report_md += "## 📊 ESTADÍSTICAS DE COBERTURA\n\n"
            report_md += "### Distribución de Sentimiento\n"
            report_md += f"- **🟢 Positivo:** {app_pos} ({int(app_pos/approved_total*100) if approved_total > 0 else 0}%)\n"
            report_md += f"- **🔵 Neutral:** {app_neu} ({int(app_neu/approved_total*100) if approved_total > 0 else 0}%)\n"
            report_md += f"- **🔴 Negativo:** {app_neg} ({int(app_neg/approved_total*100) if approved_total > 0 else 0}%)\n\n"
            
            report_md += "### Impacto por Tipo de Medio\n"
            report_md += f"- **📻 Radio:** {app_radio} menciones\n"
            report_md += f"- **📺 TV:** {app_tv} menciones\n"
            report_md += f"- **🎥 YouTube:** {app_yt} menciones\n"
            report_md += f"- **📸 Instagram:** {app_ig} menciones\n"
            report_md += f"- **🐦 Twitter:** {app_tw} menciones\n"
            report_md += f"- **📘 Facebook:** {app_fb} menciones\n"
            report_md += f"- **📰 RSS:** {app_rss} menciones\n\n"
            report_md += "---\n\n"
            
            if st.session_state.get("ai_summary_report"):
                report_md += f"## 🤖 RESUMEN EJECUTIVO (IA)\n{st.session_state.ai_summary_report}\n\n"
                
            report_md += "## 📋 DETALLE DE MENCIONES ENCONTRADAS\n\n"
            for a in st.session_state.approved_alerts:
                source_lower_rpt = a["source"].lower()
                if "radio" in source_lower_rpt: source_icon = "📻"
                elif "tv" in source_lower_rpt: source_icon = "📺"
                elif "youtube" in source_lower_rpt: source_icon = "🎥"
                elif "twitter" in source_lower_rpt: source_icon = "🐦"
                elif "facebook" in source_lower_rpt: source_icon = "📘"
                elif "rss" in source_lower_rpt: source_icon = "📰"
                else: source_icon = "📸"
                formatted_time = datetime.fromtimestamp(a["timestamp"]).strftime("%I:%M %p")
                sentiment_str = "🟢 Positivo" if a["sentimiento"] == "Positivo" else ("🔴 Negativo" if a["sentimiento"] == "Negativo" else "🔵 Neutral")
                
                report_md += f"### {source_icon} {a['source']} - {formatted_time} ({sentiment_str})\n"
                report_md += f"**Mención original:** *\"{a['text']}\"*\n\n"
                report_md += f"**Resumen de IA:** {a['resumen']}\n\n"
                
                # Fetch YouTube video_url or Instagram/RSS post_url
                alert_link = a.get("metadata", {}).get("video_url") or a.get("metadata", {}).get("post_url") or ""
                if alert_link:
                    report_md += f"**Enlace:** {alert_link}\n\n"
                
                audio_path = a.get("audio_path")
                if audio_path and os.path.exists(audio_path):
                    # Ensure metadata exists
                    if "metadata" not in a or a["metadata"] is None:
                        a["metadata"] = {}
                        
                    # Upload to cloud if not already uploaded
                    if "online_audio_url" not in a["metadata"]:
                        with st.spinner("Subiendo clip de audio de radio a la nube..."):
                            online_url = upload_to_catbox(audio_path)
                            if online_url:
                                a["metadata"]["online_audio_url"] = online_url
                                
                    online_url = a["metadata"].get("online_audio_url")
                    if online_url:
                        report_md += f"**Audio Online:** [🔗 Escuchar en Línea (Nube)]({online_url})\n\n"
                        
                    audio_uri = get_lightweight_audio_uri(audio_path)
                    if audio_uri:
                        report_md += f"**Audio Embebido:** [🎧 Escuchar Audio (Autónomo)]({audio_uri})\n\n"
                        
                video_path = a.get("video_path")
                if video_path and os.path.exists(video_path):
                    # Ensure metadata exists
                    if "metadata" not in a or a["metadata"] is None:
                        a["metadata"] = {}
                        
                    # Upload to cloud if not already uploaded
                    if "online_video_url" not in a["metadata"]:
                        with st.spinner("Subiendo clip de video de TV a la nube..."):
                            online_url = upload_to_catbox(video_path)
                            if online_url:
                                a["metadata"]["online_video_url"] = online_url
                                
                    online_url = a["metadata"].get("online_video_url")
                    if online_url:
                        report_md += f"**Video Online:** [🔗 Ver Video en Línea (Nube)]({online_url})\n\n"
                        
                report_md += "---\n\n"
                
            # 2. Compile CSV using Semicolon delimiter for Excel compatibility in Spanish locales
            import csv
            from io import StringIO
            f = StringIO()
            writer = csv.writer(f, delimiter=';', lineterminator='\n')
            writer.writerow(["Fecha/Hora", "Medio/Fuente", "Texto Original", "Resumen de IA", "Sentimiento", "Enlace de Fuente"])
            for a in st.session_state.approved_alerts:
                formatted_time = datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %I:%M:%S %p")
                link = a.get("metadata", {}).get("video_url") or a.get("metadata", {}).get("post_url") or ""
                if not link and a.get("audio_path"):
                    link = a.get("metadata", {}).get("online_audio_url") or f"static/{os.path.basename(a['audio_path'])}"
                if not link and a.get("video_path"):
                    link = a.get("metadata", {}).get("online_video_url") or f"static/{os.path.basename(a['video_path'])}"
                writer.writerow([formatted_time, a["source"], a["text"], a["resumen"], a["sentimiento"], link])
            
            # Prepend UTF-8 BOM so Excel opens it with correct encoding and handles accents (e.g. empezó, así) properly
            csv_data = "\ufeff" + f.getvalue()
            
            # Render SMTP send results if available
            if st.session_state.get("smtp_status") == "success":
                st.success("✅ ¡Reporte enviado exitosamente por correo!")
                st.session_state.smtp_status = None
            elif st.session_state.get("smtp_status") == "error":
                st.error(f"❌ Falló el envío del reporte por correo. Detalle: {st.session_state.smtp_result}")
                st.session_state.smtp_status = None

            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                st.download_button(
                     label="📥 Descargar Reporte en Markdown (.md)",
                     data=report_md,
                     file_name=f"reporte_monitoreo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                     mime="text/markdown",
                     use_container_width=True
                )
            with col_dl2:
                st.download_button(
                     label="📊 Descargar Reporte en Excel (.csv)",
                     data=csv_data,
                     file_name=f"reporte_monitoreo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                     mime="text/csv",
                     use_container_width=True
                )
            with col_dl3:
                active_client = next((c for c in clients if c["id"] == st.session_state.active_client_id), None)
                client_emails = active_client["email"] if active_client else ""
                recipient_emails = client_emails if client_emails else smtp_config.get("to", "")
                
                smtp_configured = bool(smtp_config.get("server") and smtp_config.get("user") and smtp_config.get("password") and recipient_emails)
                btn_label = "⌛ Enviando..." if st.session_state.smtp_sending else "📧 Enviar por Correo"
                if st.button(btn_label, use_container_width=True, disabled=not smtp_configured or st.session_state.smtp_sending, help="Envía este reporte diario a través de correo electrónico (SMTP) a la lista de destinatarios del cliente seleccionado."):
                    st.session_state.smtp_sending = True
                    st.session_state.smtp_status = "sending"
                    import threading
                    t = threading.Thread(
                        target=send_email_report_thread, 
                        args=(smtp_config, report_md, csv_data, st.session_state.get("ai_summary_report"), recipient_emails)
                    )
                    t.start()
                    st.rerun()
                 
            st.markdown("##### <i class='fa-solid fa-magnifying-glass-chart'></i> Vista Previa del Reporte:", unsafe_allow_html=True)
            st.code(report_md, language="markdown")
             
            st.markdown("---")
            if st.button("🧹 Limpiar Lista de Aprobados", type="secondary", use_container_width=True):
                # Clean up any approved audio and video files
                for a in st.session_state.approved_alerts:
                    ap = a.get("audio_path")
                    if ap and os.path.exists(ap):
                        try: os.remove(ap)
                        except Exception: pass
                    vp = a.get("video_path")
                    if vp and os.path.exists(vp):
                        try: os.remove(vp)
                        except Exception: pass
                database.delete_alerts_by_status('approved', st.session_state.active_client_id)
                st.session_state.approved_alerts = []
                st.session_state.ai_summary_report = None
                st.rerun()

    with tab_face:
        st.markdown("### <i class='fa-solid fa-face-viewfinder'></i> Módulo de Búsqueda Facial", unsafe_allow_html=True)
        st.markdown("Sube la imagen del rostro de una persona para identificarla en los clips de video locales (TV) o buscar noticias relacionadas en la Web (Google Cloud Vision API).")
        
        # Import face search module
        import face_search
        
        uploaded_face = st.file_uploader(
            "Cargar foto de referencia (rostro):",
            type=["jpg", "jpeg", "png"],
            key="face_search_uploader",
            help="Sube un archivo de imagen claro donde aparezca la cara de la persona."
        )
        
        if uploaded_face is not None:
            # Show the uploaded image
            st.image(uploaded_face, caption="Imagen Subida", width=200)
            
            # Options
            search_type = st.radio(
                "Tipo de Búsqueda:",
                ["🌐 Buscar en la Web (Google Cloud Vision)", "💻 Buscar en Videos Locales (Videoteca TV)"],
                index=0,
                horizontal=True
            )
            
            image_bytes = uploaded_face.getvalue()
            
            if "web" in search_type.lower():
                st.markdown("### <i class='fa-solid fa-key'></i> API Oficial: Google Cloud Vision", unsafe_allow_html=True)
                st.markdown("Busca noticias y páginas web que contengan imágenes coincidentes del rostro subido e importa los resultados directamente dentro de la aplicación. Ingresa la ruta local de tu archivo de credenciales JSON de Google Cloud Service Account:")
                
                st.text_input(
                    "Ruta al archivo JSON de credenciales:",
                    key="google_vision_credentials_val",
                    on_change=save_config,
                    args=("google_vision_credentials_val", "config_google_vision_credentials"),
                    help="Ejemplo: C:/Users/Usuario/Documents/proyecto-google-cloud-vision-12345.json"
                )
                
                # Button for Google Cloud Vision API Search
                if st.button("🚀 Buscar con Google Cloud Vision API", use_container_width=True):
                    with st.spinner("Conectando con Google Cloud Vision API y ejecutando Web Detection..."):
                        results = face_search.google_vision_web_detection(
                            image_bytes=image_bytes,
                            credentials_path=st.session_state.google_vision_credentials_val
                        )
                        
                    if not results:
                        st.info("ℹ️ No se detectaron coincidencias visuales ni entidades en portales de noticias o web con Google Cloud Vision API.")
                    elif isinstance(results, dict) and 'error' in results:
                        st.error(f"❌ Error al consultar la API: `{results['error']}`")
                        st.info("💡 Asegúrate de habilitar la 'Cloud Vision API' en tu consola de Google Cloud y que las credenciales del Service Account sean válidas.")
                    else:
                        best_guess = results.get('best_guess')
                        entities = results.get('entities', [])
                        pages = results.get('pages', [])
                        
                        # 1. Sugerencia de Identificación
                        st.markdown("#### <i class='fa-solid fa-id-card'></i> Identificación Sugerida", unsafe_allow_html=True)
                        if best_guess:
                            st.markdown(f"💡 **Etiqueta aproximada:** `{best_guess.title()}`")
                            
                        if entities:
                            st.write("🔍 **Nombres y Entidades detectadas en la Web:**")
                            for idx, ent in enumerate(entities[:5]):
                                ent_name = ent['description']
                                score_pct = int(ent['score'] * 100)
                                col_ent_lbl, col_ent_act1, col_ent_act2 = st.columns([0.5, 0.25, 0.25])
                                with col_ent_lbl:
                                    st.write(f"👤 **{ent_name}** *(Similitud: {score_pct}%)*")
                                with col_ent_act1:
                                    search_btn_key = f"web_ent_search_{idx}_{ent_name}"
                                    if st.button("➕ Keyword", key=search_btn_key, use_container_width=True, help="Añade este nombre a la lista temporal de palabras clave del cliente seleccionado."):
                                        if "temp_client_keywords" not in st.session_state:
                                            st.session_state.temp_client_keywords = []
                                        if ent_name not in st.session_state.temp_client_keywords:
                                            st.session_state.temp_client_keywords.append(ent_name)
                                            st.success(f"Añadido: {ent_name}")
                                            st.rerun()
                                with col_ent_act2:
                                    gnews_url = f"https://news.google.com/search?q={urllib.parse.quote(ent_name)}&hl=es-419&gl=DO&ceid=DO:es-419"
                                    st.link_button("📰 Google News", gnews_url, use_container_width=True)
                        else:
                            st.warning("⚠️ No se pudieron identificar nombres o entidades específicas asociadas a este rostro en la web.")
                            
                        st.markdown("---")
                        
                        # 2. Coincidencias de páginas
                        st.markdown("#### <i class='fa-solid fa-copy'></i> Coincidencias de la Imagen en Portales Web", unsafe_allow_html=True)
                        if pages:
                            st.success(f"✅ ¡Se encontraron {len(pages)} páginas web con esta foto exacta o recortada!")
                            for r in pages:
                                with st.container(border=True):
                                    col_p1, col_p2 = st.columns([0.75, 0.25])
                                    with col_p1:
                                        st.markdown(f"📰 **Título de Página:** `{r['page_title']}`")
                                        st.markdown(f"🔗 **Enlace:** [{r['url']}]({r['url']})")
                                    with col_p2:
                                        import hashlib
                                        p_hash = hashlib.sha256(r['url'].encode()).hexdigest()
                                        btn_key = f"approve_vision_page_{p_hash}"
                                        
                                        # Check if already approved
                                        is_already_approved = any(a['identifier'] == p_hash for a in st.session_state.approved_alerts)
                                        
                                        if is_already_approved:
                                            st.button("✅ Aprobado", key=btn_key, disabled=True, use_container_width=True)
                                        else:
                                            if st.button("➕ Reporte", key=btn_key, use_container_width=True, help="Agrega este resultado como una mención aprobada en el reporte diario."):
                                                new_alert = {
                                                    "identifier": p_hash,
                                                    "source": f"Búsqueda Visual ({best_guess.title()})" if best_guess else "Búsqueda Visual (Web)",
                                                    "text": r['page_title'],
                                                    "keywords": [best_guess] if best_guess else [],
                                                    "timestamp": datetime.now().isoformat(),
                                                    "sentimiento": "Neutral",
                                                    "resumen": f"Coincidencia visual de rostro detectada en portal web: {r['url']}",
                                                    "simulated": False,
                                                    "metadata": {"url": r['url']}
                                                }
                                                database.save_alert(new_alert, client_id=st.session_state.active_client_id, status='approved')
                                                st.session_state.should_reload_approved = True
                                                st.success("✅ Añadida al reporte.")
                                                st.rerun()
                        else:
                            st.info("ℹ️ No se detectaron portales de noticias o web que usen esta misma imagen.")
                        
            else:
                st.markdown("### <i class='fa-solid fa-desktop'></i> Análisis de Rostros en Videoteca Local", unsafe_allow_html=True)
                st.markdown("El sistema analizará todos los clips de video de la televisión en vivo (`static/`) para buscar rostros coincidentes.")
                
                similarity = st.slider(
                    "Umbral de Similitud Facial:",
                    min_value=0.40,
                    max_value=0.90,
                    value=0.65,
                    step=0.05,
                    help="Valores más bajos encuentran más candidatos pero con más falsos positivos. 0.65 es el recomendado."
                )
                
                # Button to start local scan
                if st.button("🚀 Iniciar Escaneo de Video", use_container_width=True):
                    # First detect face in uploaded image
                    with st.spinner("Analizando rostro de referencia..."):
                        target_face = face_search.detect_face_in_image(image_bytes)
                        
                    if target_face is None:
                        st.error("❌ No se detectó ningún rostro en la imagen subida. Por favor, sube una foto de frente con buena iluminación.")
                    else:
                        # Display cropped face to confirm
                        import cv2
                        face_rgb = cv2.cvtColor(target_face, cv2.COLOR_BGR2RGB)
                        st.image(face_rgb, caption="Rostro Detectado de Referencia", width=120)
                        
                        # Start video scan
                        project_dir = os.path.dirname(os.path.abspath(__file__))
                        static_dir = os.path.join(project_dir, "static")
                        
                        scan_bar = st.progress(0.0, text="Iniciando escaneo...")
                        
                        def progress_cb(pct, msg):
                            scan_bar.progress(pct, text=msg)
                            
                        with st.spinner("Escaneando fotogramas de la videoteca..."):
                            matches = face_search.search_local_videos(
                                target_face_bgr=target_face,
                                static_dir=static_dir,
                                similarity_threshold=similarity,
                                progress_callback=progress_cb
                            )
                            
                        if not matches:
                            st.info("ℹ️ No se encontraron coincidencias del rostro en los videos locales con el umbral seleccionado.")
                        else:
                            st.success(f"✅ ¡Se encontraron {len(matches)} coincidencias visuales en la videoteca!")
                            
                            # Render matches
                            for m in matches:
                                with st.container(border=True):
                                    col_m1, col_m2 = st.columns([0.3, 0.7])
                                    with col_m1:
                                        # Render match image
                                        match_img_path = os.path.join(static_dir, m['match_image'])
                                        if os.path.exists(match_img_path):
                                            st.image(match_img_path, use_container_width=True)
                                    with col_m2:
                                        st.markdown(f"🎬 **Video:** `{m['video_name']}`")
                                        st.markdown(f"⏱️ **Tiempo en Video:** `{m['timestamp_str']}`")
                                        st.markdown(f"🎯 **Similitud:** `{m['score']}%`")
                                        
                                        # Expander to play the video clip directly
                                        video_file_path = os.path.join(static_dir, m['video_name'])
                                        with st.expander("▶️ Reproducir Clip"):
                                            st.video(video_file_path, start_time=int(m['timestamp_sec']))

    with tab_clients:
        st.markdown("### <i class='fa-solid fa-users-gear'></i> Administración de Clientes", unsafe_allow_html=True)
        st.markdown("Configura los perfiles de tus clientes, incluyendo destinatarios de correo, palabras clave y contexto para el análisis automatizado con Inteligencia Artificial.")
        
        # Load clients
        clients = database.get_all_clients()
        
        # 2-column layout inside the tab
        col_list, col_form = st.columns([0.45, 0.55])
        
        with col_list:
            st.markdown("##### <i class='fa-solid fa-address-book'></i> Clientes Registrados", unsafe_allow_html=True)
            if not clients:
                st.info("No hay clientes registrados.")
            else:
                for c in clients:
                    is_enabled = c.get("enabled", 1) == 1
                    status_lbl = "🟢 Activo" if is_enabled else "🔴 Inactivo"
                    with st.expander(f"👤 {c['name']} ({status_lbl})"):
                        st.markdown(f"**Emails:** `{c['email'] or 'No configurados'}`")
                        st.markdown(f"**Keywords:** `{c['keywords']}`")
                        st.markdown(f"**Descripción/Contexto IA:**\n{c['description']}")
                        st.markdown("---")
                        toggle_key = f"toggle_client_enabled_{c['id']}"
                        enabled_toggle = st.toggle("Monitoreo Activo", value=is_enabled, key=toggle_key)
                        if enabled_toggle != is_enabled:
                            database.update_client_enabled(c['id'], 1 if enabled_toggle else 0)
                            st.rerun()
                        
                        # Botón para cargar este cliente directamente en el formulario de edición
                        edit_btn_key = f"edit_client_btn_{c['id']}"
                        if st.button("✏️ Editar Datos", key=edit_btn_key, use_container_width=True):
                            st.session_state.client_form_action = f"✏️ Editar: {c['name']}"
                            st.rerun()
        
        with col_form:
            st.markdown("##### <i class='fa-solid fa-user-plus'></i> Agregar / Editar Cliente", unsafe_allow_html=True)
            
            # Option to add new or select existing to edit
            form_options = ["🆕 Agregar Nuevo Cliente"] + [f"✏️ Editar: {c['name']}" for c in clients]
            if "client_form_action" not in st.session_state or st.session_state.client_form_action not in form_options:
                st.session_state.client_form_action = "🆕 Agregar Nuevo Cliente"
            selected_option = st.selectbox("Seleccione una acción:", options=form_options, key="client_form_action")
            
            # Setup form fields based on selection
            if selected_option == "🆕 Agregar Nuevo Cliente":
                edit_mode = False
                target_client = None
                default_name = ""
                default_email = ""
                default_keywords = ""
                default_desc = ""
            else:
                edit_mode = True
                client_name_to_edit = selected_option.replace("✏️ Editar: ", "")
                target_client = next(c for c in clients if c["name"] == client_name_to_edit)
                default_name = target_client["name"]
                default_email = target_client["email"]
                default_keywords = target_client["keywords"]
                default_desc = target_client["description"]
            
            # Initialize temp keywords in session state if action changed or not present
            current_action = selected_option
            if "last_form_action" not in st.session_state or st.session_state.last_form_action != current_action or "temp_client_keywords" not in st.session_state:
                if edit_mode and target_client:
                    st.session_state.temp_client_keywords = [k.strip() for k in target_client["keywords"].split(",") if k.strip()]
                else:
                    st.session_state.temp_client_keywords = []
                st.session_state.last_form_action = current_action

            # Callback to add keyword safely before widgets are instantiated on next run
            def add_keyword_callback():
                if "temp_client_keywords" not in st.session_state:
                    st.session_state.temp_client_keywords = []
                kw_raw = st.session_state.get("new_kw_input_field", "").strip()
                if kw_raw:
                    # Separar por comas si por error meten comas
                    kws_split = [k.strip() for k in kw_raw.split(",") if k.strip()]
                    for k in kws_split:
                        if k not in st.session_state.temp_client_keywords:
                            st.session_state.temp_client_keywords.append(k)
                    # Clear input safely in the callback
                    st.session_state.new_kw_input_field = ""

            def append_operator_callback(op):
                current = st.session_state.get("new_kw_input_field", "")
                if current and not current.endswith(" "):
                    st.session_state.new_kw_input_field = current + " " + op + " "
                else:
                    st.session_state.new_kw_input_field = current + op + " "

            # Form fields
            form_name = st.text_input("Nombre del Cliente", value=default_name, placeholder="Ej. Presidencia de la República")
            form_email = st.text_input("Correo(s) para Reportes (separados por comas)", value=default_email, placeholder="ejemplo1@correo.com, ejemplo2@correo.com")
            
            # Tags-style input for keywords
            st.markdown("<label style='font-size: 0.9rem; font-weight: bold;'>Palabras Clave de Monitoreo</label>", unsafe_allow_html=True)
            col_kw_in, col_kw_btn = st.columns([0.75, 0.25])
            with col_kw_in:
                st.text_input(
                    "Añadir Palabra Clave",
                    value="",
                    placeholder="Escribe y presiona Enter...",
                    label_visibility="collapsed",
                    key="new_kw_input_field",
                    on_change=add_keyword_callback
                )
            with col_kw_btn:
                st.button(
                    "➕ Añadir", 
                    use_container_width=True, 
                    key="add_kw_btn",
                    on_click=add_keyword_callback
                )
            
            # Row of boolean helper buttons
            st.markdown("<div style='margin-top: -10px; margin-bottom: 5px;'><small style='color: #a0a0a0;'>Asistente booleano (clic para insertar):</small></div>", unsafe_allow_html=True)
            col_op1, col_op2, col_op3, col_op4, col_op5 = st.columns(5)
            with col_op1:
                st.button("AND", key="btn_op_and", use_container_width=True, on_click=append_operator_callback, args=("AND",))
            with col_op2:
                st.button("OR", key="btn_op_or", use_container_width=True, on_click=append_operator_callback, args=("OR",))
            with col_op3:
                st.button("NOT", key="btn_op_not", use_container_width=True, on_click=append_operator_callback, args=("NOT",))
            with col_op4:
                st.button("(", key="btn_op_lpar", use_container_width=True, on_click=append_operator_callback, args=("(",))
            with col_op5:
                st.button(")", key="btn_op_rpar", use_container_width=True, on_click=append_operator_callback, args=(")",))
            st.caption("💡 *Ejemplo:* `(danilo OR leonel) AND NOT gobierno` *(busca menciones que contengan Danilo o Leonel, pero no gobierno)*")

            # Mostrar palabras clave actuales como chips interactivos
            if st.session_state.temp_client_keywords:
                st.markdown("<p style='font-size:0.85rem; color:#a0a0a0; margin-bottom:5px;'>Haga clic en una palabra clave para eliminarla:</p>", unsafe_allow_html=True)
                kw_cols = st.columns(4)
                for idx, kw in enumerate(st.session_state.temp_client_keywords):
                    col_idx = idx % 4
                    with kw_cols[col_idx]:
                        if st.button(f"❌ {kw}", key=f"del_kw_{idx}_{kw}", use_container_width=True):
                            st.session_state.temp_client_keywords.remove(kw)
                            st.rerun()
            else:
                st.info("💡 No hay palabras clave añadidas aún. Escribe arriba para agregar.")
                
            form_desc = st.text_area("Descripción/Contexto para la IA", value=default_desc, placeholder="Contexto de negocio o marca, temas críticos a monitorear y tono sugerido para el análisis...")
            
            # Buttons
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                submit_label = "Guardar Cambios" if edit_mode else "Crear Cliente"
                if st.button(submit_label, type="primary", use_container_width=True):
                    if not form_name.strip():
                        st.error("El nombre del cliente no puede estar vacío.")
                    elif not st.session_state.temp_client_keywords:
                        st.error("Debe ingresar al menos una palabra clave de monitoreo.")
                    else:
                        client_id = target_client["id"] if edit_mode else None
                        try:
                            # Verificar si ya existe un cliente con el mismo nombre (fácilmente prevenible antes de tocar la DB)
                            name_exists = False
                            if not edit_mode:
                                name_exists = any(c["name"].lower() == form_name.strip().lower() for c in clients)
                            else:
                                name_exists = any(c["name"].lower() == form_name.strip().lower() and c["id"] != client_id for c in clients)
                            
                            if name_exists:
                                st.error(f"❌ Ya existe un cliente con el nombre '{form_name.strip()}'. Si desea editar sus datos, selecciónelo en 'Seleccione una acción' arriba o pulse el botón '✏️ Editar Datos' de su tarjeta a la izquierda.")
                            else:
                                form_keywords_str = ",".join(st.session_state.temp_client_keywords)
                                database.save_client(client_id, form_name.strip(), form_email.strip(), form_keywords_str, form_desc.strip())
                                st.success("✅ Cliente guardado con éxito.")
                                st.session_state.client_form_action = "🆕 Agregar Nuevo Cliente"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar cliente: {e}")
            with col_b2:
                if edit_mode:
                    # Allow deletion unless it is the last client
                    if len(clients) <= 1:
                        st.button("Eliminar Cliente", type="secondary", use_container_width=True, disabled=True, help="No se puede eliminar el único cliente activo.")
                    else:
                        confirm_delete = st.checkbox("Confirmar eliminación", key=f"confirm_del_{target_client['id']}")
                        if st.button("Eliminar Cliente", type="secondary", use_container_width=True, disabled=not confirm_delete):
                            try:
                                database.delete_client(target_client["id"])
                                st.success("✅ Cliente eliminado.")
                                # If we deleted the active client, reset active client ID
                                if st.session_state.active_client_id == target_client["id"]:
                                    remaining_clients = [c for c in clients if c["id"] != target_client["id"]]
                                    st.session_state.active_client_id = remaining_clients[0]["id"]
                                st.session_state.client_form_action = "🆕 Agregar Nuevo Cliente"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al eliminar cliente: {e}")

with col_right:
    render_right_column()
