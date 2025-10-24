// Content script for Reddit bias detection

// Check if we're on Reddit
if (!window.location.hostname.includes('reddit.com')) {
    console.log('Not a Reddit page - extension inactive');
    // Stop execution
    throw new Error('This extension only works on Reddit pages');
  }
  
  // Global state
  let isEnabled = true;
  
  // Create toggle button
  function createToggleButton() {
    if (document.getElementById('bias-detector-toggle')) return;                            // Check if button already exists
  
    const toggleContainer = document.createElement('div');
    toggleContainer.id = 'bias-detector-toggle';
    toggleContainer.innerHTML = `
      <div class="toggle-wrapper">
        <span class="toggle-label">
            <span style="color: #4CAF50;">Vibes</span> / <span style="color: #dc3545;">Skeptical</span> Mode
        </span>    
        <label class="toggle-switch">
          <input type="checkbox" id="biasToggleCheckbox" checked>
          <span class="toggle-slider"></span>
        </label>
      </div>
    `;
  
    // Add to page
    document.body.appendChild(toggleContainer);
  
    // Add event listener
    const checkbox = document.getElementById('biasToggleCheckbox');
    checkbox.addEventListener('change', (e) => {
      isEnabled = e.target.checked;
      chrome.storage.sync.set({ biasDetectionEnabled: isEnabled });
      
      if (isEnabled) {
        scanPosts();
      } else {
        removeAllIndicators();
      }
    });
  }


  function findAvailPort(start, total=10) {
    let current = start;

    function checkPort() {
      if (current >= start + total) {
        return Promise.resolve(null);
      }

      return fetch(`http://127.0.0.1:${current}`, {
        method: 'GET',
        mode: 'no-cors'
      })
      .then(() => {
        return current
      })
      .catch(() => {
        current++;
        return checkPort();
      });
    }
    return checkPort();
  }



  function createDashboardButton() {
    if (document.getElementById('dashboard-btn')) return;


    findAvailPort(8501).then(availPort => {
        if (!availPort) {
          console.error('No free ports between port 8501-8510 for dashboard');
          return;
          }

        const btnCon = document.createElement('div');
        btnCon.id = 'dashboard-btn';
        btnCon.style.position = "fixed";
        btnCon.style.bottom = '20px';
        btnCon.style.right = '20px';
        btnCon.style.zIndex = '9999';

        btnCon.innerHTML = '<button style="padding: 10px 16px 10px 16 px; background-color: #ff4500; color: white; border-radius:6px; cursor:pointer;"> View Dashboard </button>'
        
        document.body.appendChild(btnCon)
        const button = btnCon.querySelector('button')
        button.addEventListener('click',() => {
          window.open(`http://127.0.0.1:${availPort}`, "_blank");
        });
      })
  }
  
  // Get initial state from storage
  chrome.storage.sync.get(['biasDetectionEnabled'], (result) => {
    isEnabled = result.biasDetectionEnabled !== false; // Default to true
    
    // Wait for body to exist, then create toggle button
    const waitForBody = setInterval(() => {
      if (document.body) {
        clearInterval(waitForBody);
        
        createToggleButton();
        createDashboardButton();
        
        // Update checkbox state
        const checkbox = document.getElementById('biasToggleCheckbox');
        if (checkbox) {
          checkbox.checked = isEnabled;
        }
        
        if (isEnabled) {
          scanPosts();
        }
      }
    }, 100);
  });
 
  //NEED BACKEND
  // Bias indicators - you can expand this
  const biasKeywords = {
    emotional: ['always', 'never', 'everyone', 'nobody', 'obviously', 'clearly'],
    loaded: ['radical', 'extreme', 'insane', 'crazy', 'absurd'],
    absolute: ['all', 'every', 'none', 'completely', 'totally']
    // neutral: ['reportedly', 'allegedly','suggests', 'according', 'research', 'evidence', 'data', 'study', 'research', 'seems', 'claims'],
    // rightWing: ['freedom', 'patriot', 'traditional', 'tax cuts', 'free market', 'border', 'immigrants', 'woke', 'liberal'],
    // leftWing: ['progressive', 'inclusive', 'equality', 'diversity', 'equal', 'climate', 'rights', 'public', 'renewable']
  };
  
  //NEED BACKEND: replace this
  function analyzeBias(text) {
    const lowerText = text.toLowerCase();
    let biasScore = 0;
    let detectedTypes = [];
  
    for (const [type, keywords] of Object.entries(biasKeywords)) {
      for (const keyword of keywords) {
        if (lowerText.includes(keyword)) {
          biasScore++;
          if (!detectedTypes.includes(type)) {
            detectedTypes.push(type);
          }
        }
      }
    }
  
    return { score: biasScore, types: detectedTypes };
  }
  
  function addBiasIndicator(element, biasData) {
    // Check if indicator already exists
    if (element.querySelector('.bias-indicator')) return;
  
    const indicator = document.createElement('div');
    indicator.className = 'bias-indicator';
    
    let level = 'low';
    if (biasData.score > 5) level = 'high';
    else if (biasData.score > 2) level = 'medium';
  
    indicator.classList.add(`bias-${level}`);
    indicator.innerHTML = `
      <span class="bias-badge">⚠️ Bias Level: ${level.toUpperCase()}</span>
      <span class="bias-details">${biasData.types.join(', ')}</span>
    `;
  
    element.style.position = 'relative';
    element.insertBefore(indicator, element.firstChild);
  }
  
  function scanPosts() {
    if (!isEnabled) return; // Don't scan if disabled
    
    // Reddit post selectors (works for both old and new Reddit)
    const posts = document.querySelectorAll('[data-testid="post-content"], .entry .usertext-body, shreddit-post');
    
    posts.forEach(post => {
      const textContent = post.textContent || post.innerText;
      if (textContent && textContent.length > 50) {
        const biasData = analyzeBias(textContent);
        if (biasData.score > 0) {
          addBiasIndicator(post, biasData);
        }
      }
    });
  }

// ============================================================
// 📌 MODAL POPUP CODE (Added Section)
// ============================================================

// CHANGED SELECTOR to match Reddit's current DOM
document.addEventListener('click', (event) => {
  const post = event.target.closest('[data-testid="post-container"], shreddit-post, [data-testid="post-content"]'); 
  if (post) {
    console.log('✅ Reddit post clicked:', post);
    const postTitle = post.querySelector('h3')?.innerText || "Untitled Post"; 
    const postId = post.id || "unknown";
    createOverlayPopup();
  }
});

// Function to create and display modal overlay (Reddit-style)
function createOverlayPopup() {
  if (document.getElementById('overlay-popup')) return;

  const audio = new Audio(chrome.runtime.getURL('sounds/sound1.mp3'));

  audio.play().catch((error) => {
    console.log("Error playing sound: ", error, audio);
  })

  // Overlay (dimmed background)
  const overlay = document.createElement('div');
  overlay.id = 'overlay-popup';
  overlay.style.position = 'fixed';
  overlay.style.top = 0;
  overlay.style.left = 0;
  overlay.style.width = '100vw';
  overlay.style.height = '100vh';
  overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.4)';
  overlay.style.backdropFilter = 'blur(3px)'; // 🔹 soft blur
  overlay.style.zIndex = '2147483647';
  overlay.style.display = 'flex';
  overlay.style.justifyContent = 'center';
  overlay.style.alignItems = 'center';
  overlay.style.opacity = '0';
  overlay.style.transition = 'opacity 0.25s ease';

  // Modal box
  const popupContent = document.createElement('div');
  popupContent.style.backgroundColor = '#FF5700';
  popupContent.style.borderRadius = '20px';
  popupContent.style.padding = '24px 28px';
  popupContent.style.width = '600px';
  popupContent.style.maxWidth = '90%';
  popupContent.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2)';
  popupContent.style.fontFamily = 'sans-serif';
  popupContent.style.color = 'white';
  popupContent.style.lineHeight = '1.6';
  popupContent.style.transform = 'scale(0.95)';
  popupContent.style.transition = 'transform 0.25s ease';

popupContent.innerHTML = `
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <h2 style="margin:0;font-size:20px;font-weight:700;color:white;">
      You're at a risk of falling into an Echo Chamber! <br>
      Try reading some alternative perspectives:
    </h2>
  </div>

  <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px;">
    <!-- Post 1 -->
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e0e0e0;padding-bottom:12px;">
      <a href="https://www.reddit.com/r/example1" target="_blank" class="modal-link"
         style="color:white;text-decoration:underline;font-size:16px;font-weight:500;word-wrap:break-word;">
         Noem Approves Spending $200 Million to Buy Jets During Shutdown
      </a>
      <span style="background-color:#2F66B2;color:white;font-size:12px;font-weight:600;padding:6px 12px;border-radius:5px;box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);width:auto;min-width:65px;text-align:center;">
        Left Wing
      </span>
    </div>

    <!-- Post 2 -->
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e0e0e0;padding-bottom:12px;">
      <a href="https://www.reddit.com/r/example2" target="_blank" class="modal-link"
         style="color:white;text-decoration:underline;font-size:16px;font-weight:500;word-wrap:break-word;">
         Stacey Abrams' Group Closes After Campaign Finance Crimes
      </a>
      <span style="background-color:#696969;color:white;font-size:12px;font-weight:600;padding:6px 12px;border-radius:5px;box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);width:auto;min-width:65px;text-align:center;">
        Neutral
      </span>
    </div>

    <!-- Post 3 -->
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e0e0e0;padding-bottom:12px;">
      <a href="https://www.reddit.com/r/example3" target="_blank" class="modal-link"
         style="color:white;text-decoration:underline;font-size:16px;font-weight:500;word-wrap:break-word;">
         Dem Thug Who Yelled "Grab a Gun and Shoot ICE" at Chicago Rally Gets FAFO Lesson Hard!
      </a>
      <span style="background-color:#e80c25;color:white;font-size:12px;font-weight:600;padding:6px 12px;border-radius:5px;box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);width:auto;min-width:65px;text-align:center;">
        Right Wing
      </span>
    </div>
  </div>

  <div style="display:flex;justify-content:center;align-items:center;margin-top:20px;">
    <button id="ok-button" style="
      background-color:rgba(0,0,0,0.2);
      color:white;
      padding:10px 18px;
      border:none;
      border-radius:60px;
      font-family:sans-serif;
      font-weight:600;
      display:flex;
      justify-content:center;
      align-items:center;
      cursor:pointer;
      transition:all 0.2s ease;
    ">No thanks!</button>
  </div>
`;


  overlay.appendChild(popupContent);
  document.body.appendChild(overlay);

  // Animate in
  requestAnimationFrame(() => {
    overlay.style.opacity = '1';
    popupContent.style.transform = 'scale(1)';
  });

  // Close logic
  const close = () => {
    overlay.style.opacity = '0';
    popupContent.style.transform = 'scale(0.95)';
    setTimeout(() => overlay.remove(), 250);
  };

  // Close button
  document.getElementById('ok-button').addEventListener('click', close);

  // ✅ NEW: Close when clicking any post link
  const modalLinks = popupContent.querySelectorAll('.modal-link');
  modalLinks.forEach(link => {
    link.addEventListener('click', () => {
      close();
    });
  });
}


// ============================================================

  // Function to remove all bias indicators
  function removeAllIndicators() {
    const indicators = document.querySelectorAll('.bias-indicator');
    indicators.forEach(indicator => indicator.remove());
  }
  
  // Initial scan
  setTimeout(scanPosts, 1000);
  
  // Observe for dynamically loaded content
  const observer = new MutationObserver(() => {
    if (isEnabled) {
      scanPosts();
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Listen for toggle messages from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'toggleBiasDetection') {
      isEnabled = request.enabled;
      
      if (isEnabled) {
        scanPosts();
      } else {
        removeAllIndicators();
      }
      
      sendResponse({ status: 'success' });
    }
    
    if (request.action === 'rescan') {
      if (isEnabled) {
        scanPosts();
      }
      sendResponse({ status: 'complete' });
    }
  });
  
  console.log('Reddit Bias Detector loaded');
