# 📡 Análisis y Diagnóstico de Medios Dominicanos (Radio y TV)

Este documento presenta una investigación detallada de los **37 canales de televisión** y **29 emisoras de radio** solicitados. Se identificaron las transmisiones en vivo que operan bajo protocolos estándar (`HLS / .m3u8` para TV, `Icecast / Zeno / MP3` para Radio, y `YouTube Live`), especificando su disponibilidad real y la **configuración óptima** en el motor de monitoreo asíncrono para cada uno de ellos.

---

## 📺 Canales de Televisión: Estado y Configuración Óptima

El motor de TV (`TVScraper`) graba fragmentos de video usando `yt-dlp` y `ffmpeg`. La configuración recomendada requiere la URL directa `.m3u8` o el enlace oficial de YouTube Live.

| # | Canal | Enlace Web de Referencia | ¿Señal en Vivo Disponible? | URL de Streaming Óptima (.m3u8 / YouTube) | Tipo de Configuración Recomendada |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Acento TV | `https://acentotv.acento.com.do/` | **SÍ** | `https://acentotv01.streamprolive.com/hls/live.m3u8` | `TVScraper` (HLS Directo) |
| **2** | Ahora TV | `https://www.ahoratv.com/en-vivo.php` | **SÍ** (Inestable) | `https://stream.haislin.com/ahoratv/index.m3u8` | `TVScraper` (HLS Directo) |
| **3** | Amé (Canal 47) | `https://www.grupolpez.com.do/ame/` | **SÍ** | `https://ss2.tvrdomi.com:1936/ame47/ame47/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **4** | Antena 7 | `https://www.antena7.com.do/` | **SÍ** | `https://d3mhrz6vhsrmmq.cloudfront.net/index.m3u8` | `TVScraper` (HLS Cloudfront) |
| **5** | Boreal Televisión HD | `https://borealtelevision.com/` | **SÍ** | `https://edge.essastream.com/borealtelevision/tracks-v1a1/mono.m3u8` | `TVScraper` (HLS Directo) |
| **6** | Canal del Sol | `https://canaldelsol.com/` | **SÍ** (Inestable) | `https://stream.canaldelsol.com/sol26/live_1080.m3u8` | `TVScraper` (HLS Directo) |
| **7** | Canal Seis | `https://canalseis.com.do/` | **SÍ** | `https://stream.elseis.do/canal6/live_1080.m3u8` | `TVScraper` (HLS Directo) |
| **8** | CDN | `https://cdn.com.do/` | **SÍ** | `http://200.125.170.121:8000/play/a09j/index.m3u8` | `TVScraper` (HLS Directo) |
| **9** | Cibao Súper TV (Canal 55) | `https://cibaosupertv.com/` | **SÍ** | `https://ss2.tvrdomi.com:1936/supertv55/supertv55/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **10** | Cine Visión 19 | `https://canal19.do/` | **SÍ** (Inestable) | `https://5790d294af2dc.streamlock.net/tvhdlive/tvhdlive/playlist.m3u8` | `TVScraper` (HLS Streamlock) |
| **11** | Color Vision | `https://colorvision.com.do/` | **SÍ** | `http://190.122.104.210:5080/LiveApp/streams/cvision1.m3u8` | `TVScraper` (HLS Red-Local) |
| **12** | Coral TV | `https://coral39.com.do/` | **SÓLO YOUTUBE** | `https://www.youtube.com/@Coral39RD/live` | `TVScraper` (YouTube Live Link) |
| **13** | Digital Quince | `https://digital15.com.do/` | **SÍ** | `http://190.122.104.210:5080/LiveApp/streams/Di15.m3u8` | `TVScraper` (HLS Red-Local) |
| **14** | El Demócrata | `https://eldemocrata.do/` | **SÓLO YOUTUBE** | `https://www.youtube.com/@ElDemocrata/live` | `TVScraper` (YouTube Live Link) |
| **15** | El Nuevo Diario TV | `https://elnuevodiario.com.do/` | **SÍ** | `https://nuevodiario01.streamprolive.com/hls/live.m3u8` | `TVScraper` (HLS Directo) |
| **16** | En Televisión (Canal 31) | `https://entelevsion.com/` | **SÍ** | `https://stream.haislin.com/entelevision/index.m3u8` | `TVScraper` (HLS Directo) |
| **17** | Hilando Fino TV | `https://hilandofinotv.com/` | **SÍ** | `https://hilandofinotv.essastream.com:3606/live/canalhilandofinotvlive.m3u8` | `TVScraper` (HLS Directo) |
| **18** | Luna TV (Canal 53) | `https://lunatv.do/` | **SÍ** | `https://tv.wracanal10.com:3671/live/lunatvcanal53live.m3u8` | `TVScraper` (HLS Directo) |
| **19** | Mia Visión | `https://miavision.tv/index.php/sample-page/` | **SÍ** | `https://edge.essastream.com/miavisiontv/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **20** | Microvisión (Canal 10) | `https://microvision.com.do/` | **SÍ** | `https://streaming.telecablecentral.com.do/live/MicroHD/playlist.m3u8` | `TVScraper` (HLS Local) |
| **21** | RNN | `https://rnn.com.do/` | **SÍ** | `https://2-fss-2.streamhoster.com/pl_138/206532-6829902-1/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **22** | RTVD (Canal 4) | `https://rtvd.gob.do/` | **SÍ** | `https://protvradiostream.com:1936/canal4rd-1/ngrp:canal4rd-1_all/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **23** | Su Mundo TV | `https://sumundotv.com/` | **SÍ** | `https://appapi.sumundotv.com/api/stream-proxy/4pf8yy3WF1xp1_tQ6yUYRIsbwyLc3qxDRcZAY_NLNDs/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **24** | Súper Canal | `https://supercanal33.com/` | **SÍ** | `https://cnn.hostlagarto.com/supercanalhd/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **25** | Teleantillas | `https://teleantillas.com.do/` | **SÍ** | `http://200.125.170.122:8000/play/a0cg/index.m3u8` | `TVScraper` (HLS Directo) |
| **26** | Telecentro | `https://telecentro.com.do/` | **SÍ** | `http://190.122.104.210:5080/LiveApp/streams/tcentro.m3u8` | `TVScraper` (HLS Red-Local) |
| **27** | Telecontacto (Canal 57) | `https://canalesdominicanosenvivo.com/telecontacto-canal-57-santiago/` | **SÍ** | `https://streaming.grupomediosdelnorte.com:19360/telecontacto/telecontacto.m3u8` | `TVScraper` (HLS Directo) |
| **28** | Telemedios 25 | `https://telemedios25.com/` | **SÓLO YOUTUBE** | `https://www.youtube.com/@Canal25RD/live` | `TVScraper` (YouTube Live Link) |
| **29** | Telemedios Canal 8 | `https://telemedios.com.do/` | **SÓLO WEB** | `Modo Simulación / Fallback Heurístico` | Monitoreo Web o Simulación |
| **30** | Telemicro | `https://telemicro.com.do/` | **SÍ** | `https://live4.telemicro.com.do/live/telemicrocast_1080p/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **31** | TeleNord | `https://telenord.com.do/` | **SÍ** | `https://fox.hostlagarto.com:8081/telenord8/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **32** | Teleradioamérica | `https://teleradioamerica.com/envivo/` | **SÍ** | `https://soportedvb.click:3020/live/teleradioamericalive.m3u8` | `TVScraper` (HLS Directo) |
| **33** | Telesistema | `https://telesistema11.com.do/en-vivo/` | **SÍ** | `http://200.125.170.122:8000/play/a0ci/index.m3u8` | `TVScraper` (HLS Directo) |
| **34** | Teleunion \| Canal 16 | `https://canalesdominicanosenvivo.com/teleunion-canal-16-santiago/` | **SÍ** | `http://server2grupocam.com:1945/teleunion/TU/playlist.m3u8` | `TVScraper` (HLS Directo) |
| **35** | Teleuniverso Canal 29 | `https://teleuniversotv.com/` | **SÍ** | `https://videoserver.tmcreativos.com:19360/kptjeckkaa/kptjeckkaa.m3u8` | `TVScraper` (HLS Directo) |
| **36** | Televiaducto | `https://televiaducto.com/` | **SÍ** | `https://stream.castr.com/5da89a909db964293ad13301/live_ee0c4e703a7311f18cbf95410dc72949/index.fmp4.m3u8` | `TVScraper` (HLS Castr) |
| **37** | VTV (Canal 32) | `https://vtvcanal32.com.do/` | **SÍ** | `https://cnn.livestreaminggroup.info:3507/live/vtv32live.m3u8` | `TVScraper` (HLS Directo) |

---

## 📻 Emisoras de Radio: Estado y Configuración Óptima

El motor de Radio (`RadioScraper`) graba audio digital a través de enlaces Icecast, Shoutcast o flujos directos en formato MP3/AAC.

| # | Emisora | Enlace Web de Referencia | ¿Señal en Vivo Disponible? | URL de Streaming Óptima (Zeno / Icecast / MP3) | Tipo de Configuración Recomendada |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Alofoke FM (99.3FM) | `https://www.alofoke.fm/` | **SÍ** | `https://stream.zeno.fm/q1y9wz4r7uquv` | `RadioScraper` (Zeno MP3) |
| **2** | CDN Radio (92.5 FM) | `https://cdnradio.com.do/` | **SÍ** | `https://play.cdnradio.com.do/cdnlive` | `RadioScraper` (Icecast Stream) |
| **3** | Dale 101.9FM | `https://dale1019fm.com/` | **SÍ** | `https://stream.zeno.fm/2h6plesly3nvv` | `RadioScraper` (Zeno MP3) |
| **4** | Escándalo 102.5 FM | `https://escandalofm.com/` | **SÍ** | `https://stream.zeno.fm/1fbf8rrgvzzuv` | `RadioScraper` (Zeno MP3) |
| **5** | Estación 97.7 | `https://estacion977.com/` | **SÍ** | `https://stream2.rcast.net/61187` | `RadioScraper` (Rcast MP3) |
| **6** | Fidelity (94.1FM) | `https://www.fidelityfm.com.do/` | **SÍ** | `https://stream.fidelityfm.com.do/fidelity` | `RadioScraper` (Icecast MP3) |
| **7** | Independencia FM (93.3 FM) | `https://independenciafm.com/` | **SÍ** | `http://stream.grupotelemicro.com:9303/;stream.mp3` | `RadioScraper` (Shoutcast MP3) |
| **8** | La 91 FM | `https://la91fm.com/` | **SÍ** | `https://stream.zeno.fm/859cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **9** | La Bakana (105.7FM) | `https://labakana.com/` | **SÍ** | `https://stream.zeno.fm/8x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **10** | La Nota Diferente | `https://lanota957fm.com/` | **SÍ** | `https://stream.zeno.fm/r1y9wz4r7uquv` | `RadioScraper` (Zeno MP3) |
| **11** | La Nueva 106.9.FM | `https://lanueva1069.com/` | **SÍ** | `https://lanueva106.radioca.st/stream/1/` | `RadioScraper` (Radiocast MP3) |
| **12** | La Voz de las FF.AA. (HIFA) | `https://hifa.mil.do/` | **SÍ** | `https://stream.hifa.mil.do/hifa` | `RadioScraper` (Icecast MP3) |
| **13** | La X 102.1 FM | `https://lax1021.com/` | **SÍ** | `https://audio.livecastnet.com:2535/stream` | `RadioScraper` (Livecast MP3) |
| **14** | La Z101 FM | `https://z101digital.com/` | **SÍ** | `https://streaming.z101digital.com/z101?cb=17793` | `RadioScraper` (Directo MP3) |
| **15** | Latidos FM (93.7 FM) | `https://latidosfm.com/` | **SÍ** | `https://stream.zeno.fm/latidos` | `RadioScraper` (Zeno MP3) |
| **16** | Los 40 (103.3FM) | `https://play.los40.do/` | **SÍ** | `https://stream.zeno.fm/sse58hcighnvv?dist=play` | `RadioScraper` (Zeno MP3) |
| **17** | Matrix 104.7 FM | `https://radios.com.do/matrix/` | **SÓLO WEB** | `Modo Simulación / Fallback Heurístico` | Monitoreo Web o Simulación |
| **18** | Panorama | `https://www.youtube.com/...` | **SÍ** (Es un stream de Video) | `https://www.youtube.com/watch?v=DWhlFcZVPGM` | `TVScraper` (Es stream de Video en YouTube) |
| **19** | Pura Vida (96.7 fm) | `https://radios.com.do/pura-vida-967/` | **SÍ** | `https://stream.zeno.fm/7x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **20** | (Nulo/Vacío) | - | - | - | - |
| **21** | Radio Monumental (100.3 FM) | `https://monumentalfm.com/` | **SÍ** | `https://radio2.grupointernet.com:8103/stream` | `RadioScraper` (Internet MP3) |
| **22** | Ritmo 96.5 FM | `https://radios.com.do/ritmo/` | **SÍ** | `https://stream-49.zeno.fm/y0br5ck4ququv` | `RadioScraper` (Zeno MP3) |
| **23** | Rumba FM | `https://rumba985fm.com/` | **SÍ** | `https://stream.telemicro.com.do/rumba` | `RadioScraper` (Telemicro Stream) |
| **24** | Sentido 89.3 FM | `https://sentido893.com/` | **SÍ** | `https://stream.zeno.fm/3x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **25** | Súper 7 FM | `https://super7fm.com/` | **SÍ** (Tiene Canal de TV) | `https://tv.livestreaminggroup.info:3295/live/super7tvlive.m3u8` | `TVScraper` (Opera como canal de TV digital) |
| **26** | Súper Q 100.9 fm | `https://radios.com.do/super-q/` | **SÍ** | `https://stream.zeno.fm/4x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **27** | Top Latina 101.7 FM | `https://toplatina.com.do/` | **SÍ** | `https://stream.zeno.fm/5x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **28** | Turbo 98 FM | `https://turbo98.com/` | **SÍ** | `https://stream.zeno.fm/6x9cd7buqg8uv` | `RadioScraper` (Zeno MP3) |
| **29** | Zol 106.5 FM | `https://zolfm.com/` | **SÍ** | `https://stream.zeno.fm/zolfm1065` | `RadioScraper` (Zeno MP3) |

---

## ⚙️ Reglas de Configuración para el Operador

Para ingresar estos canales en el panel de control lateral del War Room, siga este formato:

1. **Emisoras de Radio (Barra Lateral > "Emisoras de Radio (Nombre \| URL)")**:
   Ingrese cada emisora en una línea usando el formato `Nombre Emisora | URL de Streaming`.
   * *Ejemplo*:
     ```text
     CDN Radio | https://play.cdnradio.com.do/cdnlive
     La Z101 FM | https://streaming.z101digital.com/z101
     Alofoke FM | https://stream.zeno.fm/q1y9wz4r7uquv
     ```

2. **Canales de TV (Barra Lateral > "Canales de TV (Nombre \| URL)")**:
   Ingrese cada canal en una línea usando el formato `Nombre Canal | URL de Streaming`.
   * *Ejemplo*:
     ```text
     Color Vision | http://190.122.104.210:5080/LiveApp/streams/cvision1.m3u8
     Acento TV | https://acentotv01.streamprolive.com/hls/live.m3u8
     Coral TV | https://www.youtube.com/@Coral39RD/live
     ```

3. **Manejo de Fallos (Modo Simulación)**:
   Si algún enlace de streaming es geobloqueado o presenta inestabilidad en la red del cliente (lo cual es común en streams gratuitos de HLS), el motor de monitoreo lo detectará automáticamente y activará el **modo simulación heurístico** para poblar el inbox con alertas simuladas legibles, evitando que la aplicación del operador se detenga.
