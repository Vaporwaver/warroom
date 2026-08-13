import os
import cv2
import numpy as np
import requests
import io
import urllib.parse
import re
from PIL import Image

def scraped_web_detection(image_bytes):
    """
    Performs visual web detection by uploading the query image to a temporary host
    and scraping Bing Visual Search results without requiring Google Cloud API keys or billing.
    Returns a dictionary with 'best_guess', 'entities', 'pages', or {'error': 'msg'} on error.
    """
    try:
        from bs4 import BeautifulSoup
        
        # Step 1: Upload image to tmpfiles.org
        files = {'file': ('query_image.jpg', image_bytes, 'image/jpeg')}
        upload_resp = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=10)
        if upload_resp.status_code != 200:
            return {'error': f'Error al subir la imagen a host temporal: HTTP {upload_resp.status_code}'}
        
        data = upload_resp.json()
        upload_url = data.get('data', {}).get('url')
        if not upload_url:
            return {'error': 'No se recibió la URL de la imagen subida.'}
            
        raw_image_url = upload_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
        
        # Step 2: Scrape Bing Visual Search
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        bing_search_url = f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={urllib.parse.quote(raw_image_url)}"
        
        resp = requests.get(bing_search_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {'error': f'Error al consultar servidor visual: HTTP {resp.status_code}'}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        best_guess = ""
        entities = []
        pages = []
        
        ignore_words = [
            'ver más', 'imágenes parecidas', 'búsqueda visual', 'búsqueda por imagen', 
            'informar sobre contenido no apropiado', 'privacidad y cookies', 'términos',
            'iniciar sesión', 'filtros de búsqueda', 'configuración'
        ]
        
        # Extract best guess or titles from elements
        for tag in soup.find_all(['h2', 'h3', 'a', 'span']):
            txt = tag.text.strip()
            if txt and len(txt) > 3 and txt.lower() not in ignore_words:
                if not best_guess and len(txt) > 4 and not txt.startswith('http'):
                    best_guess = txt
                elif txt not in [e['description'] for e in entities] and not txt.startswith('http'):
                    entities.append({'description': txt, 'score': 0.85})
                    
        # Extract web pages / news matching the image
        seen_urls = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            title = a.text.strip() or a.get('title', '').strip()
            if href.startswith('http') and not re.search(r'bing\.com|microsoft\.com|live\.com|live\.net|msn\.com', href, re.I):
                if href not in seen_urls and len(title) > 4 and title.lower() not in ignore_words:
                    seen_urls.add(href)
                    pages.append({
                        'url': href,
                        'page_title': title
                    })
                    
        if not best_guess and pages:
            best_guess = pages[0]['page_title']
            
        return {
            'best_guess': best_guess or "Coincidencias encontradas en la Web",
            'entities': entities[:10],
            'pages': pages[:15]
        }
    except Exception as e:
        return {'error': f'Error en scraping visual: {str(e)}'}




def get_google_lens_link(image_bytes):
    """Uploads the image bytes to tmpfiles.org and returns a Google Lens search link."""
    try:
        files = {'file': ('query_image.jpg', image_bytes, 'image/jpeg')}
        response = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=10)
        if response.status_code == 200:
            data = response.json()
            upload_url = data.get('data', {}).get('url')
            if upload_url:
                raw_url = upload_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                return f"https://lens.google.com/uploadbyurl?url={raw_url}&hl=es"
    except Exception:
        pass
    return None

def get_yandex_link(image_bytes):
    """Uploads the image bytes to tmpfiles.org and returns a Yandex Images search link."""
    try:
        files = {'file': ('query_image.jpg', image_bytes, 'image/jpeg')}
        response = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=10)
        if response.status_code == 200:
            data = response.json()
            upload_url = data.get('data', {}).get('url')
            if upload_url:
                raw_url = upload_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                return f"https://yandex.com/images/search?rpt=imageview&url={raw_url}"
    except Exception:
        pass
    return None

def detect_face_in_image(image_bytes):
    """Detects the largest face in the provided image bytes. Returns the cropped face image (BGR) or None."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
            
        if not hasattr(cv2, 'CascadeClassifier'):
            print("WARNING: cv2.CascadeClassifier is missing. OpenCV installation might be broken. Returning original image.")
            return img
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return img
            
        # Pick the largest face by area
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        face_crop = img[y:y+h, x:x+w]
        return face_crop
    except Exception as e:
        print(f"Error in detect_face_in_image: {e}")
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

def compare_faces(target_face, test_face):
    """Compares two BGR face crops and returns a similarity score from 0.0 to 1.0."""
    try:
        # Resize to standard size
        t_face = cv2.resize(target_face, (80, 80))
        o_face = cv2.resize(test_face, (80, 80))
        
        # Convert to grayscale
        t_gray = cv2.cvtColor(t_face, cv2.COLOR_BGR2GRAY)
        o_gray = cv2.cvtColor(o_face, cv2.COLOR_BGR2GRAY)
        
        # Equalize hist to handle illumination variations
        t_gray = cv2.equalizeHist(t_gray)
        o_gray = cv2.equalizeHist(o_gray)
        
        # Compare using normalized cross correlation
        res = cv2.matchTemplate(t_gray, o_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        # matchTemplate returns score in [-1, 1]. Shift to [0, 1]
        score = float((max_val + 1) / 2)
        return score
    except Exception:
        return 0.0

def search_local_videos(target_face_bgr, static_dir, similarity_threshold=0.65, progress_callback=None):
    """
    Scans all .mp4 files in static_dir.
    Detects faces in video frames and compares them to target_face_bgr.
    Saves matching frames as JPG files and returns a list of matches.
    """
    matches = []
    if target_face_bgr is None:
        return matches
        
    # Get all .mp4 videos in the directory
    videos = [f for f in os.listdir(static_dir) if f.endswith('.mp4') and not f.startswith('match_')]
    
    if hasattr(cv2, 'CascadeClassifier'):
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
    else:
        face_cascade = None
        print("WARNING: cv2.CascadeClassifier is missing. Video face search will be bypassed.")
    
    total_videos = len(videos)
    
    for idx, video_file in enumerate(videos):
        video_path = os.path.join(static_dir, video_file)
        if progress_callback:
            progress_callback(idx / total_videos, f"Escaneando {video_file}...")
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            continue
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
            
        # Sample 1 frame per second (step = fps)
        step = int(fps)
        if step <= 0:
            step = 30
            
        frame_num = 0
        match_in_video_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_num % step == 0 and face_cascade is not None:
                # Detect faces in this frame
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                for face_idx, (x, y, w, h) in enumerate(faces):
                    test_face_crop = frame[y:y+h, x:x+w]
                    score = compare_faces(target_face_bgr, test_face_crop)
                    
                    if score >= similarity_threshold:
                        # Save matching frame to static/
                        match_filename = f"match_{video_file[:-4]}_{frame_num}_{face_idx}.jpg"
                        match_path = os.path.join(static_dir, match_filename)
                        
                        # Draw a bounding box on the frame
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        # Save it
                        cv2.imwrite(match_path, frame)
                        
                        timestamp_sec = frame_num / fps
                        minutes = int(timestamp_sec // 60)
                        seconds = int(timestamp_sec % 60)
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        
                        matches.append({
                            'video_name': video_file,
                            'match_image': match_filename,
                            'timestamp_str': time_str,
                            'timestamp_sec': timestamp_sec,
                            'score': int(score * 100)
                        })
                        match_in_video_count += 1
                        # Avoid saving too many matches from the same second/video to prevent flooding
                        if match_in_video_count >= 10:
                            break
                            
            frame_num += 1
            
        cap.release()
        
    if progress_callback:
        progress_callback(1.0, "Escaneo completado.")
        
    # Sort matches by score descending
    matches.sort(key=lambda m: m['score'], reverse=True)
    return matches
