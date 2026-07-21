document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const btnRefresh = document.getElementById('refresh-btn');
  
  // Instagram elements
  const cardInsta = document.getElementById('instagram-card');
  const statusInsta = document.getElementById('instagram-status');
  const valInsta = document.getElementById('instagram-value');
  const btnInsta = document.getElementById('copy-instagram');
  
  // Twitter elements
  const cardTwitter = document.getElementById('twitter-card');
  const statusTwitter = document.getElementById('twitter-status');
  const valTwitter = document.getElementById('twitter-value');
  const btnTwitter = document.getElementById('copy-twitter');
  
  // Facebook elements
  const cardFb = document.getElementById('facebook-card');
  const statusFb = document.getElementById('facebook-status');
  const valFb = document.getElementById('facebook-value');
  const btnFbHeader = document.getElementById('copy-facebook-header');
  const btnFbJson = document.getElementById('copy-facebook-json');

  // Helper: Mask sensitive token
  function maskToken(token) {
    if (!token) return 'No encontrado';
    if (token.length <= 10) return '••••••••';
    return `${token.substring(0, 6)}••••••••${token.substring(token.length - 4)}`;
  }

  // Helper: Copy to Clipboard with animation
  function setupCopyButton(button, textToCopy, successLabel) {
    button.onclick = async () => {
      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalHTML = button.innerHTML;
        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        button.style.borderColor = 'transparent';
        button.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
          <span>¡Copiado!</span>
        `;
        setTimeout(() => {
          button.style.background = '';
          button.style.borderColor = '';
          button.innerHTML = originalHTML;
        }, 1500);
      } catch (err) {
        console.error('Error al copiar al portapapeles:', err);
      }
    };
  }

  // Function to load all cookies
  function loadCookies() {
    // Reset views to loading
    statusInsta.className = 'dot-status';
    valInsta.textContent = 'Buscando cookie sessionid...';
    btnInsta.disabled = true;

    statusTwitter.className = 'dot-status';
    valTwitter.textContent = 'Buscando cookie auth_token...';
    btnTwitter.disabled = true;

    statusFb.className = 'dot-status';
    valFb.textContent = 'Buscando cookies de Facebook...';
    btnFbHeader.disabled = true;
    btnFbJson.disabled = true;

    // Check if chrome.cookies is available
    if (!chrome.cookies) {
      const errorMsg = 'API de Chrome Cookies no disponible. ¿Estás ejecutando esto como extensión de Chrome?';
      valInsta.textContent = errorMsg;
      valTwitter.textContent = errorMsg;
      valFb.textContent = errorMsg;
      return;
    }

    // 1. Instagram
    chrome.cookies.getAll({ url: 'https://www.instagram.com' }, (cookies) => {
      const sessionCookie = cookies.find(c => c.name === 'sessionid');
      if (sessionCookie && sessionCookie.value) {
        statusInsta.className = 'dot-status active';
        valInsta.textContent = maskToken(sessionCookie.value);
        btnInsta.disabled = false;
        setupCopyButton(btnInsta, sessionCookie.value, 'sessionid');
      } else {
        statusInsta.className = 'dot-status inactive';
        valInsta.textContent = 'Sesión no iniciada. Por favor inicia sesión en instagram.com';
        btnInsta.disabled = true;
      }
    });

    // 2. Twitter/X
    // Check twitter.com first
    chrome.cookies.getAll({ url: 'https://twitter.com' }, (cookies) => {
      let tokenCookie = cookies.find(c => c.name === 'auth_token');
      
      const processTwitterCookie = (cookie) => {
        if (cookie && cookie.value) {
          statusTwitter.className = 'dot-status active';
          valTwitter.textContent = maskToken(cookie.value);
          btnTwitter.disabled = false;
          setupCopyButton(btnTwitter, cookie.value, 'auth_token');
        } else {
          statusTwitter.className = 'dot-status inactive';
          valTwitter.textContent = 'Sesión no iniciada. Por favor inicia sesión en twitter.com o x.com';
          btnTwitter.disabled = true;
        }
      };

      if (tokenCookie) {
        processTwitterCookie(tokenCookie);
      } else {
        // Try x.com
        chrome.cookies.getAll({ url: 'https://x.com' }, (xCookies) => {
          tokenCookie = xCookies.find(c => c.name === 'auth_token');
          processTwitterCookie(tokenCookie);
        });
      }
    });

    // 3. Facebook
    chrome.cookies.getAll({ url: 'https://www.facebook.com' }, (cookies) => {
      // For facebook, we want all the session cookies or at least user & session keys (c_user, xs, atb, spin, etc.)
      // Usually, a complete serialized list of cookies is best
      if (cookies && cookies.length > 0) {
        // Filter out cookies that are empty or expired to keep it clean
        const validCookies = cookies.filter(c => c.value);
        
        if (validCookies.length > 0) {
          statusFb.className = 'dot-status active';
          
          // Show summary of found cookies
          const essentialCookies = validCookies.filter(c => ['c_user', 'xs', 'fr', 'sb'].includes(c.name)).map(c => c.name);
          valFb.textContent = `Encontradas ${validCookies.length} cookies (Esenciales: ${essentialCookies.join(', ') || 'ninguna'})`;
          
          // Formatos de copiado:
          // A. Semicolon separated string (Cookie Header style)
          const cookieHeaderStr = validCookies.map(c => `${c.name}=${c.value}`).join('; ');
          
          // B. JSON list of objects matching Playwright expectations
          const cookieJsonList = validCookies.map(c => ({
            name: c.name,
            value: c.value,
            domain: c.domain.startsWith('.') ? c.domain : `.${c.domain}`,
            path: c.path || '/',
            secure: c.secure ?? true,
            httpOnly: c.httpOnly ?? true
          }));
          const cookieJsonStr = JSON.stringify(cookieJsonList, null, 2);

          btnFbHeader.disabled = false;
          btnFbJson.disabled = false;
          
          setupCopyButton(btnFbHeader, cookieHeaderStr, 'Cabecera de Facebook');
          setupCopyButton(btnFbJson, cookieJsonStr, 'JSON de Facebook');
        } else {
          statusFb.className = 'dot-status inactive';
          valFb.textContent = 'Sesión no iniciada. Por favor inicia sesión en facebook.com';
          btnFbHeader.disabled = true;
          btnFbJson.disabled = true;
        }
      } else {
        statusFb.className = 'dot-status inactive';
        valFb.textContent = 'Sesión no iniciada. Por favor inicia sesión en facebook.com';
        btnFbHeader.disabled = true;
        btnFbJson.disabled = true;
      }
    });
  }

  // Bind refresh event
  btnRefresh.onclick = () => {
    // Add rotating animation class to refresh icon if we had one
    loadCookies();
  };

  // Initial load
  loadCookies();
});
