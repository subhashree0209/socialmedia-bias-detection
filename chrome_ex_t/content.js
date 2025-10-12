// Content script for Reddit bias detection

// Check if we're on Reddit
if (!window.location.hostname.includes('reddit.com')) {
    console.log('Not a Reddit page - extension inactive');
    // Stop execution
    throw new Error('This extension only works on Reddit pages');
  }
  
  // Global state
  let isEnabled = true;

  function isPostCommentsPage(href = location.href) {
  // Matches: /r/<sub>/comments/<postId>/...
  return /^https?:\/\/(www\.)?reddit\.com\/r\/[^/]+\/comments\/[a-z0-9]+/i.test(href);
  }

  
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
        // Re-enable bias scanning
        scanPosts();
        // Recheck for bias-tagged post so the button reappears if needed
        setTimeout(checkForBiasTaggedPost, 1000);
    
      } else {
    // Remove all bias indicators and also remove related posts button
        removeAllIndicators();
        removeRelatedPostsButton();
      }
    });
  }

  function createDashboardButton() {
    if (document.getElementById('dashboard-btn')) return;

    const btnCon = document.createElement('div');
    btnCon.id = 'dashboard-btn';
    btnCon.style.position = "fixed";
    btnCon.style.bottom = '20px';
    btnCon.style.right = '20px';
    btnCon.style.zIndex = '9999';

    btnCon.innerHTML = '<button style="padding: 10px 16px 10px 16 px; background-color: #ff4500; color: white; border-radius:6px; cursor:pointer;"> EchoBreak </button>'

    document.body.appendChild(btnCon)

    const button = btnCon.querySelector('button')
    button.addEventListener('click',() => {
      window.open('http://192.168.28.19:8501', "_blank");
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




















// === RELATED POSTS FEATURE  ===
function addRelatedPostsButton() {
  // Prevent duplicates
  if (document.getElementById("find-related-btn")) return;

  // Create floating button (position set via CSS on #find-related-btn)
  const btn = document.createElement("button");
  btn.id = "find-related-btn";
  btn.textContent = "Find Related Posts";
  btn.className = "related-btn";

  // Create dropdown panel container
  const panel = document.createElement("div");
  panel.id = "related-posts-panel";
  panel.className = "related-panel";
  panel.innerHTML = `<p class="loading">Loading related posts...</p>`;

  // Mount to BODY (NOT the header)
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  // --- Placeholder: fetch top 5 related posts (replace with your backend) ---  #need to write the endpoints
  // how it'll work: when  user opens a post, send post content to backend for backend to find related posts and then filter out top 5 opposite slant or neutral posts. titles, urls and bias tags of these posts will be sent to front end to be displayed in pane 
  async function fetchRelatedPosts() {
    return [
      { title: "Policy implications overview", url: "https://www.reddit.com/r/example1", bias: "neutral" },
      { title: "Debate on policy",            url: "https://www.reddit.com/r/example2", bias: "opposite" },
      { title: "Historical background context of policies in the US constitution and their effects",     url: "https://www.reddit.com/r/example3", bias: "neutral" },
      { title: "Why this policy works",url: "https://www.reddit.com/r/example4", bias: "opposite" },
      { title: "Global policies and the influence of US politics on global markets",    url: "https://www.reddit.com/r/example5", bias: "neutral" }
    ];
  }

  async function populatePanel() {
    const posts = await fetchRelatedPosts();
    panel.innerHTML = `
      <h4>Related Posts</h4>
      ${posts.map(p => `
        <a href="${p.url}" target="_blank" class="related-item ${p.bias}" rel="noopener">
          <span class="related-title" title="${p.title}">${p.title}</span>
          <span class="related-bias">${p.bias.toUpperCase()}</span>
        </a>
      `).join("")}
    `;
  }

btn.addEventListener("mouseenter", async () => {
  await populatePanel();

  const rect = btn.getBoundingClientRect();

  // Compute live geometry — data-driven, not hardcoded
  const panelWidth = panel.offsetWidth;
  const panelHeight = panel.offsetHeight;
  const viewportWidth = window.innerWidth;

  // Align left edge of panel slightly left of button’s right edge,
  // but clamp within viewport
  let left = rect.right - panelWidth;  // 20px small visual gap
  left = Math.max(12, Math.min(left, viewportWidth - panelWidth - 12));

  // Position below the button
  const top = rect.bottom + 8;

  panel.style.position = "fixed";
  panel.style.left = `${left}px`;
  panel.style.top = `${top}px`;
  panel.classList.add("show");
});


  // Hide when leaving button (allow time to move into panel)
  btn.addEventListener("mouseleave", () => {
    setTimeout(() => {
      if (!panel.matches(":hover")) panel.classList.remove("show");
    }, 150);
  });

  // Hide when leaving the panel itself
  panel.addEventListener("mouseleave", () => panel.classList.remove("show"));

  // If window is resized, just hide the panel (it will re-open in the right place)
  window.addEventListener("resize", () => panel.classList.remove("show"));
}


// === Find Related Posts button only appears when user opens a bias-tagged Reddit post ===

// Helper to remove any existing button/panel cleanly
function removeRelatedPostsButton() {
  document.getElementById("find-related-btn")?.remove();
  document.getElementById("related-posts-panel")?.remove();
}

// Check whether we’re currently viewing a *bias-tagged post*
function checkForBiasTaggedPost() {
  // Only on a single-post comments page
  if (!isPostCommentsPage()) {
    removeRelatedPostsButton();
    return;
  }

  // Find the opened post’s main container
  const mainPost =
    document.querySelector("shreddit-post") ||
    document.querySelector('[data-test-id="post-content"]');

  if (!mainPost) {
    removeRelatedPostsButton();
    return;
  }

  // Require a bias indicator inside THIS post
  const hasBias = !!mainPost.querySelector(".bias-indicator");

  if (hasBias) {
    if (!document.getElementById("find-related-btn")) {
      addRelatedPostsButton();
    }
  } else {
    removeRelatedPostsButton();

    // Watch this post for a bias indicator appearing later
    const observer = new MutationObserver(() => {
      if (mainPost.querySelector(".bias-indicator")) {
        addRelatedPostsButton();
        observer.disconnect();
      }
    });
    observer.observe(mainPost, { childList: true, subtree: true });
  }
}


// Run initial check after bias scan finishes
setTimeout(checkForBiasTaggedPost, 2000);

// Watch for client-side navigation (Reddit SPA changes URL without reload)
let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    removeRelatedPostsButton();          // clean up immediately on nav
    setTimeout(checkForBiasTaggedPost, 400); // short settle time
  }
}, 300);

