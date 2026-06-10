import os
import sys
import time
from datetime import datetime
import streamlit as st
import queue
import textwrap

# Import scrapers backend
import scrapers
import subprocess
import tempfile
import base64

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
            
        temp_mp3 = os.path.join(tempfile.gettempdir(), f"temp_report_{int(time.time())}.mp3")
        
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

# Premium Custom CSS Styles
st.markdown("""
<style>
    /* Styling for Alert Cards */
    .pr-card {
        background-color: rgba(255, 255, 255, 0.04);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #95a5a6;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .pr-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
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
        background-color: rgba(255, 255, 255, 0.06);
        border-left: 4px solid #7f8c8d;
        padding: 12px 18px;
        border-radius: 4px;
        margin: 10px 0px 15px 0px;
        font-size: 0.95rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Variables
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "system_logs" not in st.session_state:
    st.session_state.system_logs = []
if "approved_count" not in st.session_state:
    st.session_state.approved_count = 0
if "approved_alerts" not in st.session_state:
    st.session_state.approved_alerts = []
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
    # Default to simulation if dependencies are missing, to guarantee smooth demo out-of-the-box
    st.session_state.force_simulation = missing_deps

# --- SIDEBAR: Configuration & Control ---
st.sidebar.image("https://img.icons8.com/nolan/128/war.png", width=80)
st.sidebar.markdown("<h2 style='margin-top:0;'>Centro de Control</h2>", unsafe_allow_html=True)

# Main Engine Controls
if not st.session_state.monitoring_active:
    if st.sidebar.button("🚀 INICIAR MONITOREO", use_container_width=True, type="primary"):
        # Parse keywords from the visible text input in the configuration section
        kws_str = st.session_state.get("keywords_input_state", "gobierno, economía, política, presidente")
        st.session_state.keywords_str = kws_str
        kws = [k.strip() for k in kws_str.split(",") if k.strip()]
        
        # Parse Radio channels
        radio_lines = st.session_state.get("radio_channels_val", "").split("\n")
        radio_list = []
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
            
        # Parse YouTube channels
        yt_lines = st.session_state.get("youtube_channels_val", "").split("\n")
        youtube_list = [line.strip() for line in yt_lines if line.strip()]
        
        # Parse Instagram usernames
        ig_lines = st.session_state.get("instagram_users_val", "").split("\n")
        instagram_list = [line.strip() for line in ig_lines if line.strip()]
        
        # Parse RSS feeds
        rss_lines = st.session_state.get("rss_feeds_val", "").split("\n")
        rss_list = [line.strip() for line in rss_lines if line.strip()]
        
        # Instantiate and run engine
        st.session_state.engine = scrapers.MonitoringEngine(
            keywords=kws,
            radio_channels=radio_list,
            youtube_channels=youtube_list,
            instagram_channels=instagram_list,
            rss_feeds=rss_list,
            scan_interval=st.session_state.get("scan_interval_val", 30),
            force_simulation=st.session_state.force_simulation,
            whisper_model=st.session_state.get("whisper_model_val", "tiny"),
            ollama_model=st.session_state.get("ollama_model_val", "gemma:2b"),
            instagram_sessionid=st.session_state.get("instagram_sessionid_val", "")
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
st.sidebar.subheader("⚙️ Configuración del Motor")

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
    "Modelo Whisper (Audio local)",
    options=["tiny", "base"],
    index=0,
    key="whisper_model_val",
    disabled=st.session_state.monitoring_active or st.session_state.force_simulation,
    help="Modelos más pesados incrementan el uso de CPU/RAM."
)

# Fetch active models for selection if Ollama is running
ollama_options = ["gemma:2b", "gemma:7b"]
if sys_status["ollama_models"]:
    for m in sys_status["ollama_models"]:
        if m not in ollama_options:
            ollama_options.append(m)

st.sidebar.selectbox(
    "Modelo Ollama (IA local)",
    options=ollama_options,
    index=0,
    key="ollama_model_val",
    disabled=st.session_state.monitoring_active,
    help="Modelo local de Ollama cargado a través de localhost:11434"
)

st.sidebar.text_input(
    "Instagram sessionid (Cookie)",
    type="password",
    key="instagram_sessionid_val",
    help="Opcional. Si deseas hacer scraping real de Instagram sin ser bloqueado, ingresa tu cookie 'sessionid'.",
    disabled=st.session_state.monitoring_active
)

# Text area for keywords and channels shown dynamically if not monitoring
if not st.session_state.monitoring_active:
    st.sidebar.text_input(
        "Palabras Clave",
        value="gobierno, economía, política, presidente",
        key="keywords_input_state",
        help="Menciones con estas palabras clave activarán alertas de IA."
    )
    st.session_state.keywords_str = st.session_state.keywords_input_state
    
    st.sidebar.text_area(
        "Emisoras de Radio (Nombre | URL)",
        value="Z101 | https://tunein.com/radio/Z101FM-1013-s102394/\nLa Bakana | https://tunein.com/radio/La-Bakana-1057-s102393/",
        key="radio_channels_val",
        help="Ingresa Nombre | URL de streaming de audio por línea."
    )
    st.sidebar.text_area(
        "Canales de YouTube (URLs)",
        value="https://www.youtube.com/@nuriapiera/videos",
        key="youtube_channels_val",
        help="Ingresa una URL de canal por línea."
    )
    st.sidebar.text_area(
        "Usuarios de Instagram",
        value="nuriapiera",
        key="instagram_users_val",
        help="Ingresa un usuario por línea (sin @)."
    )
    st.sidebar.text_area(
        "Feeds RSS (URLs)",
        value="https://somospueblo.com/feed/\nhttps://listindiario.com/rss/",
        key="rss_feeds_val",
        help="Ingresa una URL de feed RSS por línea."
    )
else:
    st.sidebar.info(f"🔍 **Buscando:** `{st.session_state.get('keywords_str', 'gobierno, economía, política, presidente')}`")
    
    # Format active lists
    engine = st.session_state.get("engine")
    if engine:
        st.sidebar.markdown("**Canales Activos:**")
        r_names = [f"📻 {r['name']}" for r in engine.radio_channels]
        st.sidebar.caption(" / ".join(r_names))
        
        yt_names = [f"🎥 {scrapers.extract_youtube_channel_name(url)}" for url in engine.youtube_channels]
        st.sidebar.caption(" / ".join(yt_names))
        
        ig_names = [f"📸 @{user}" for user in engine.instagram_channels]
        st.sidebar.caption(" / ".join(ig_names))
        
        rss_names = [f"📰 {scrapers.extract_rss_domain(url)}" for url in engine.rss_feeds]
        st.sidebar.caption(" / ".join(rss_names))

st.sidebar.markdown("---")

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

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Actualizaciones")
if st.sidebar.button("🔄 Buscar Actualizaciones", use_container_width=True):
    with st.spinner("Buscando e instalando actualizaciones desde el repositorio..."):
        try:
            import subprocess
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
                # If git is not configured or failed, offer manual help
                st.sidebar.error(f"Error al conectar con el repositorio. Detalle: {res.stderr[:100]}")
        except Exception as e:
            st.sidebar.error(f"Error de Git: {e}. Asegúrate de tener Git instalado.")



# --- CENTRAL PANEL: Dashboard Visuals ---
st.markdown("<h1 class='main-title'>War Room - Demo de Monitoreo con IA</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#a0a0a0; font-size:1.1rem; margin-bottom:25px;'>Monitoreo local en vivo de Radio, YouTube e Instagram con procesamiento lingüístico inteligente local.</p>", unsafe_allow_html=True)

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
    tab_validation, tab_report = st.tabs(["📥 Bandeja de Validación", "📝 Generador de Reportes"])
    
    with tab_validation:
    
        # Process queue if active
        if st.session_state.monitoring_active and "engine" in st.session_state and st.session_state.engine:
            engine = st.session_state.engine
            new_alerts_added = False
            new_logs_added = False
            
            while not engine.alerts_queue.empty():
                try:
                    alert = engine.alerts_queue.get_nowait()
                    # Check for duplicates in local display state
                    if alert["identifier"] not in [a["identifier"] for a in st.session_state.alerts]:
                        st.session_state.alerts.insert(0, alert)  # Add at top of the inbox
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
                    
            if new_alerts_added:
                # Memory leak protection: Limit live list size
                if len(st.session_state.alerts) > 100:
                    st.session_state.alerts = st.session_state.alerts[:100]
                    
            if len(st.session_state.system_logs) > 300:
                st.session_state.system_logs = st.session_state.system_logs[:300]
                
            if new_alerts_added or new_logs_added:
                st.rerun()
    
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
        else:
            # Loop through alerts in session state
            for idx, alert in enumerate(st.session_state.alerts):
                # Select icon
                source_lower = alert["source"].lower()
                if "radio" in source_lower: source_icon = "📻"
                elif "youtube" in source_lower: source_icon = "🎥"
                elif "rss" in source_lower: source_icon = "📰"
                else: source_icon = "📸"
                
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
                                
                        # Render RSS specific details and external link button
                        elif "rss" in source_lower:
                            post_url = metadata.get("post_url")
                            title = metadata.get("title", "Artículo de RSS")
                            st.markdown(f"📰 **Artículo:** `{title}`")
                            if post_url:
                                st.link_button("📰 Leer Artículo en Somos Pueblo", post_url)
                                
                        # Render st.audio player if audio path exists for this mention and toggle is active
                        audio_path = alert.get("audio_path")
                        if audio_path and os.path.exists(audio_path):
                            audio_key = f"play_audio_{alert['identifier']}"
                            if audio_key not in st.session_state:
                                st.session_state[audio_key] = False
                            
                            btn_label = "🔇 Ocultar Reproductor" if st.session_state[audio_key] else "🎧 Escuchar Audio"
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
                    with col_btn:
                        # Provide vertical spacer aligning button
                        st.write("")
                        st.write("")
                        st.write("")
                        if st.button("Aprobar", key=f"aprov_{alert['identifier']}", use_container_width=True):
                            # Action: pop alert from list, save it, increment counters
                            approved_alert = st.session_state.alerts.pop(idx)
                            if "approved_alerts" not in st.session_state:
                                st.session_state.approved_alerts = []
                            st.session_state.approved_alerts.append(approved_alert)
                            st.session_state.approved_count += 1
                            st.rerun()
                        
    with tab_report:
        st.subheader("📝 Reporte Ejecutivo de Monitoreo")
        
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
            st.markdown("#### 🤖 Síntesis Consolidada por IA")
            
            # Button to trigger AI summary using Ollama
            if st.button("🤖 Generar Resumen por IA", use_container_width=True):
                with st.spinner("Ollama local analizando menciones y redactando el reporte ejecutivo..."):
                    # Compile text blocks
                    text_blocks = ""
                    for idx, a in enumerate(st.session_state.approved_alerts):
                        text_blocks += f"[{idx+1}] Fuente: {a['source']} | Sentimiento: {a['sentimiento']}\nContenido: {a['text']}\nResumen: {a['resumen']}\n\n"
                        
                    prompt = (
                        "Eres un analista experto de PR y monitoreo de medios. "
                        "A continuación tienes una lista de menciones de prensa aprobadas hoy. "
                        "Redacta un reporte ejecutivo consolidado de un máximo de dos párrafos en español, resumiendo los temas clave tratados, la distribución del sentimiento y cualquier alerta de crisis o tendencia relevante. Usa un tono formal y corporativo.\n\n"
                        f"Menciones:\n{text_blocks}"
                    )
                    
                    try:
                        # Call Ollama local
                        import scrapers
                        analyzer = scrapers.OllamaAnalyzer(st.session_state.get("ollama_model_val", "gemma:2b"))
                        import ollama
                        client = ollama.Client(host='http://localhost:11434', timeout=30.0)
                        response = client.chat(
                            model=analyzer.model_name,
                            messages=[
                                {'role': 'system', 'content': 'Eres un analista de PR que redacta reportes consolidados corporativos.'},
                                {'role': 'user', 'content': prompt}
                            ]
                        )
                        st.session_state.ai_summary_report = response['message']['content']
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
            st.markdown("#### 📥 Descargar Reportes")
            
            # 1. Compile Markdown
            report_md = f"# REPORTE DIARIO DE MONITOREO DE MEDIOS\n"
            report_md += f"**Fecha de Emisión:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
            report_md += f"**Total Menciones Aprobadas:** {len(st.session_state.approved_alerts)}\n\n"
            
            if st.session_state.get("ai_summary_report"):
                report_md += f"## 🤖 RESUMEN EJECUTIVO (IA)\n{st.session_state.ai_summary_report}\n\n"
                
            report_md += "## 📋 DETALLE DE MENCIONES ENCONTRADAS\n\n"
            for a in st.session_state.approved_alerts:
                source_icon = "📻" if "radio" in a["source"].lower() else ("🎥" if "youtube" in a["source"].lower() else ("📰" if "rss" in a["source"].lower() else "📸"))
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
                        
                report_md += "---\n\n"
                
            # 2. Compile CSV
            import csv
            from io import StringIO
            f = StringIO()
            writer = csv.writer(f)
            writer.writerow(["Fecha/Hora", "Medio/Fuente", "Texto Original", "Resumen de IA", "Sentimiento", "Enlace de Fuente"])
            for a in st.session_state.approved_alerts:
                formatted_time = datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %I:%M:%S %p")
                link = a.get("metadata", {}).get("video_url") or a.get("metadata", {}).get("post_url") or ""
                if not link and a.get("audio_path"):
                    link = a.get("metadata", {}).get("online_audio_url") or f"media/{os.path.basename(a['audio_path'])}"
                writer.writerow([formatted_time, a["source"], a["text"], a["resumen"], a["sentimiento"], link])
            csv_data = f.getvalue()
            
            col_dl1, col_dl2 = st.columns(2)
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
                 
            st.markdown("##### Vista Previa del Reporte:")
            st.code(report_md, language="markdown")
             
            st.markdown("---")
            if st.button("🧹 Limpiar Lista de Aprobados", type="secondary", use_container_width=True):
                # Clean up any approved audio files
                for a in st.session_state.approved_alerts:
                    ap = a.get("audio_path")
                    if ap and os.path.exists(ap):
                        try: os.remove(ap)
                        except Exception: pass
                st.session_state.approved_alerts = []
                st.session_state.ai_summary_report = None
                st.rerun()

with col_right:
    st.subheader("📊 Métricas de Medios")
    
    # Graphic: Distribution by source
    sources = [a["source"] for a in st.session_state.alerts]
    radio_cnt = sum(1 for s in sources if "Radio" in s)
    yt_cnt = sum(1 for s in sources if "YouTube" in s)
    ig_cnt = sum(1 for s in sources if "Instagram" in s)
    rss_cnt = sum(1 for s in sources if "RSS" in s)
    
    st.markdown("##### Volumen por Canal")
    st.progress(radio_cnt / total_mentions if total_mentions > 0 else 0.0, text=f"📻 Radio ({radio_cnt})")
    st.progress(yt_cnt / total_mentions if total_mentions > 0 else 0.0, text=f"🎥 YouTube ({yt_cnt})")
    st.progress(ig_cnt / total_mentions if total_mentions > 0 else 0.0, text=f"📸 Instagram ({ig_cnt})")
    st.progress(rss_cnt / total_mentions if total_mentions > 0 else 0.0, text=f"📰 RSS ({rss_cnt})")
    
    st.markdown("---")
    
    # System Diagnostic Logs Panel
    st.subheader("📝 Bitácora del Sistema")
    with st.container(height=300):
        if not st.session_state.system_logs:
            st.caption("No hay eventos registrados en la bitácora aún. Inicia el motor para ver trazas de depuración.")
        else:
            for log in st.session_state.system_logs:
                st.markdown(log)

# --- AUTO-REFRESH TRIGGER ---
# If monitoring is active, trigger page rerun after 2 seconds to poll the background thread queue and render new alerts
if st.session_state.monitoring_active:
    time.sleep(2)
    st.rerun()
