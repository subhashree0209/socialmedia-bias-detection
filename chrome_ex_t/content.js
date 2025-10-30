// Content script for Reddit bias detection

// ensure we're on Reddit
if (!window.location.hostname.includes('reddit.com')) {
    console.log('Not a Reddit page - extension inactive');
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
  
    const toggleContainer = document.createElement('div');a
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
      
      if (isEnabled) { //if toggle on,
        // Re-enable bias scanning
        processedT3.clear();
        scanPosts();
        // Recheck for bias-tagged post so the Related Posts button reappears if needed
        setTimeout(checkForBiasTaggedPost, 1000);
    
      } else {
    // Remove all bias indicators and remove related posts button 
        removeAllIndicators();
        removeRelatedPostsButton();
        processedT3.clear();
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

        btnCon.innerHTML = '<button style="padding: 10px 16px 10px 16px; background-color: #ff4500; color: white; border-radius:6px; cursor:pointer;"> View Dashboard </button>'
        
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
  // const biasKeywords = {
  //   emotional: ['always', 'never', 'everyone', 'nobody', 'obviously', 'clearly'],
  //   loaded: ['radical', 'extreme', 'insane', 'crazy', 'absurd'],
  //   absolute: ['all', 'every', 'none', 'completely', 'totally', 'most']
    // neutral: ['reportedly', 'allegedly','suggests', 'according', 'research', 'evidence', 'data', 'study', 'research', 'seems', 'claims'],
    // rightWing: ['freedom', 'patriot', 'traditional', 'tax cuts', 'free market', 'border', 'immigrants', 'woke', 'liberal'],
    // leftWing: ['progressive', 'inclusive', 'equality', 'diversity', 'equal', 'climate', 'rights', 'public', 'renewable']
  // };
  
  

  //NEED BACKEND: replace this
  // function analyzeBias(text) {
  //   const lowerText = text.toLowerCase();
  //   let biasScore = 0;
  //   let detectedTypes = [];
  
  //   for (const [type, keywords] of Object.entries(biasKeywords)) {
  //     for (const keyword of keywords) {
  //       if (lowerText.includes(keyword)) {
  //         biasScore++;
  //         if (!detectedTypes.includes(type)) {
  //           detectedTypes.push(type);
  //         }
  //       }
  //     }
  //   }
  
  //   return { score: biasScore, types: detectedTypes };
  // }

    const SINGLE_API_URL = "http://127.0.0.1:8000/classify"
    const BATCH_API_URL = "http://127.0.0.1:8000/classify_batch"

    async function analyzeBias(textContent, API_URL) {
    try {
        // For batch endpoint, send as array; for single, send as object
        const requestBody = API_URL.includes('batch') 
            ? JSON.stringify({ texts: [textContent] })  // Wrap in array for batch
            : JSON.stringify({ text: textContent });     // Single object for single classify

        const response = await fetch(API_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"}, 
            body: requestBody
        });

        if (!response.ok) {
            throw new Error(`Backend returned status: ${response.status}`);
        }

        const result = await response.json();
        
        // Handle different response formats
        if (API_URL.includes('batch')) {
            // Batch returns { results: [{ label, confidence }] }
            return result.results[0];  // Return first result since we sent one text
        } else {
            // Single returns { label, confidence }
            return result;
        }

    } catch (err) {
        if (err.message === "Failed to fetch") {
            console.error("Cannot call backend at all, make sure combined_api.py is running");
        } else {
            console.error("Backend error: ", err);
        }
        return null;
    }
}
  
  // function addBiasIndicator(element, biasData) {
  //   // Check if indicator already exists
  //   if (element.querySelector('.bias-indicator')) return;
  
  //   const indicator = document.createElement('div');
  //   indicator.className = 'bias-indicator';
    
  //   let level = 'low';
  //   if (biasData.score > 5) level = 'high';
  //   else if (biasData.score > 2) level = 'medium';
  
  //   indicator.classList.add(`bias-${level}`);
  //   indicator.innerHTML = `
  //     <span class="bias-badge">⚠️ Bias Level: ${level.toUpperCase()}</span>
  //     <span class="bias-details">${biasData.types.join(', ')}</span>
  //   `;
  
  //   element.style.position = 'relative';
  //   element.insertBefore(indicator, element.firstChild);
  // }

  function addBiasIndicator(element, biasData) {
    if (element.querySelector('.bias-indicator')) return;

    const biasIndicator = document.createElement('div');
    biasIndicator.className = 'bias-indicator';

    let label = biasData.label.toLowerCase();
    let labelClass = "bias-neutral"; 

    if (label === "left") {
      labelClass = "bias-left";
    } else if (
      label === "right") {
      labelClass = "bias-right";
    }

    element.dataset.biasLabel = label;

    biasIndicator.classList.add(labelClass);
    biasIndicator.innerHTML = `<span class="bias-badge"> ${label.toUpperCase()}</span>`;

    biasIndicator.style.display = 'block';
    biasIndicator.style.textAlign = 'center';
    biasIndicator.style.width = '15%';
    biasIndicator.style.margin = '5px 4px';
    biasIndicator.style.clear = 'both'
    // element.style.position = 'relative';
    element.appendChild(biasIndicator);
  }


  // HELPER FUNCTIONS  ===

  // keep track of posts we already processed to avoid duplicate work
  const processedT3 = new Set();

  // default way to obtain every post's unique indentifier "t3_xxx" id from its post element
  function getPostId(post) {
    if (post.matches('shreddit-post')) {
      const idAttr = post.getAttribute('id'); 
      if (idAttr) return idAttr;
      const permalink = post.getAttribute('permalink') || '';
      const m = permalink.match(/\/comments\/([a-z0-9]+)\//i);
      if (m) return `t3_${m[1]}`;
    }

    // handles case of some posts having older layouts 
    const a = post.querySelector('a[href*="/comments/"]');
    if (a) {
      const m = a.getAttribute('href')?.match(/\/comments\/([a-z0-9]+)\//i);
      if (m) return `t3_${m[1]}`;
    }

    return null;
  }

  //extract t3 id from SDUI (title-only) search tiles FOR SPECIAL CASE OF SEARCHING ONE WORD!!!! (T3 id is the unique identifier of every post)
  function getT3FromSduiUnit(unit) {
    const a = unit.querySelector('a[data-testid="post-title"][href*="/comments/"]');
    if (!a) return null;
    const m = a.getAttribute('href')?.match(/\/comments\/([a-z0-9]+)\//i);
    return m ? `t3_${m[1]}` : null;
  }




  //use the t3 id to fetch full title and post body via Reddit JSON (public) 
  //allows full content of posts to be analysed before bias labels are displayed in a feed (posts in feed usually only have title and first few lines of post body)
  async function fetchFullPost(t3id) {
    if (!t3id) return null;
    const shortId = t3id.replace(/^t3_/, '');
    const url = `https://www.reddit.com/comments/${shortId}.json?raw_json=1`;

    const res = await fetch(url, { method: 'GET', credentials: 'omit' });
    if (!res.ok) return null;

    const arr = await res.json();
    const d = arr?.[0]?.data?.children?.[0]?.data;
    if (!d) return null;

    return {
      title: d.title || '',
      selftext: d.selftext || '',   // full text body for normal posts; empty for link/image/video posts
    };
  }






  // ===== Detects what kind of page user is on (opened post, home feed, single word search results feed or >1 word search results feed) 
  // ====== and adds bias labels accordingly
  async function scanPosts() {
    if (!isEnabled) return;

    const isOpenedPostPage = location.pathname.includes('/comments/');

    // PUTING LABEL ON AN OPENED POST PAGE 
    if (isOpenedPostPage) {
      // locates the full post container by trying multiple selectors
      const openedPost = document.querySelector('[data-testid="post-container"], shreddit-post, .Post');
      if (!openedPost) {
        console.log('Opened post not found yet, waiting...');
        return; // Retry on next mutation
      }

      //  if a post is already labeled, do not rescan the post
      if (openedPost.querySelector('.bias-indicator')) {
        console.log('Bias label already present — stopping further scans.');
        return;
      }

      // locates post title by trying multiple selectors (multiple selectors to handle cases of outdated reddit pages and some webpages that follow different layouts)
      const titleElement = openedPost.querySelector(
        'h1[data-testid="post-title"], h1, h2, [data-click-id="title"]'
      );
      const title = titleElement?.innerText?.trim() || '';

      // locates post body by trying multiple selectors
      let bodyElement = openedPost.querySelector(
        'shreddit-post-text-body, [data-testid="post-content"], .usertext-body'
      );
      let body = bodyElement?.innerText?.trim() || '';

      // shadow DOM as fallback (if standard DOM didn't return enough content) 
      // - on some webpages, reddit's layouts have been changed to shadow DOM
      // if (!body || body.length < 20) {
      //   console.log('Body not found with standard DOM. Trying Shadow DOM...');
      //   body = extractTextWithShadow(openedPost);
      //   console.log('Shadow DOM extracted content length:', body.length);
      // }

      const fullText = `${title}\n${body}`.trim();

      if (fullText.length < 20) {
        return; // will retry automatically via MutationObserver 
      }

      
      
      //analyse text and insert label   
      const biasData = await analyzeBias(fullText, SINGLE_API_URL);
      if (biasData && biasData.label) {
        addBiasIndicator(openedPost, biasData);
        console.log('Bias indicator added to opened post.');
      } else {
        console.log('No bias detected in opened post.');
      }

      return; // smart stop: do not continue feed scanning
    }



    // FEED PAGE — fetch full post text via Reddit JSON API and generate labels, batching it to prevent too many request error
    const posts = Array.from(document.querySelectorAll(    //getting post containers in a feed
      'shreddit-post, shreddit-search-post, [data-testid="post-content"], [data-testid="search-post"], [role="article"], .entry .usertext-body'
    )).slice(0, 15);


    // Handle SDUI search results (only titles with no preview of post body)) 
    // {HANDLES CASE OF USER MAKING SINGLE WORD SEARCHES (e.g. "government")}
    const sduiUnits = document.querySelectorAll('[data-testid="sdui-post-unit"]');
    for (const unit of sduiUnits) {
      const t3id = getT3FromSduiUnit(unit);
      if (!t3id || processedT3.has(t3id)) continue;
      processedT3.add(t3id);

      const full = await fetchFullPost(t3id);
      if (!full) continue;

      const textContent = `${full.title}\n${full.selftext}`.trim();
      if (textContent.length > 20) {
        const biasData = await analyzeBias(textContent, BATCH_API_URL);
        if (biasData && biasData.label) {
          addBiasIndicator(unit, biasData)
        };
      }
    }

    
    // handles regular HOME FEED posts
    for (const post of posts) {
      const t3id = getPostId(post);
      if (!t3id || processedT3.has(t3id)) continue;
      processedT3.add(t3id);

      const full = await fetchFullPost(t3id);
      if (!full) continue;

      const textContent = `${full.title}\n${full.selftext}`.trim();

      if (textContent.length > 20) {
       
        const biasData = await analyzeBias(textContent, BATCH_API_URL);
        if (biasData && biasData.label) {
          addBiasIndicator(post, biasData);
        }
      }
    }

    // handles search results of >1 words (e.g. "I hate trump") 
    // such search results feed has post titles and few lines of post body displayed
    const searchResults = Array.from(document.querySelectorAll(
      '[data-testid="search-post-with-content-preview"]'
    )).slice(0, 15);

    for (const post of searchResults) {
      const t3id = getPostId(post);
      if (!t3id || processedT3.has(t3id)) continue;
      processedT3.add(t3id);

      const full = await fetchFullPost(t3id);
      if (!full) continue;

      const textContent = `${full.title}\n${full.selftext}`.trim();

      if (textContent.length > 20) {
        const biasData = await analyzeBias(textContent, BATCH_API_URL);
        if (biasData && biasData.label) {
          addBiasIndicator(post, biasData);
          console.log('Bias indicator added to SEARCH RESULT post:', t3id);
        }
      }
    }
  }



  // async function scanPosts() {
  //   if (!isEnabled) return;

  //   const posts = document.querySelectorAll('[data-testid="post-content"], .entry .usertext-body, shreddit-post');

  //   for (const post of posts) {
  //     const textContent = post.textContent || post.innerText;
  //     if (!textContent) {
  //       continue
  //     }

  //     try {
  //       const biasData = await analyzeBias(textContent);
  //       if (biasData && biasData.label) {
  //         addBiasIndicator(post, biasData);
  //         console.log("posts are labelled")
  //       } else {
  //         console.warn("Backend returned null or invalid data")
  //       }
  //     } catch (err) {
  //       console.error("Error analysing post: ", err)
  //     }
  //   }
  // }
  
  // function to remove all bias indicators
  function removeAllIndicators() {
    const indicators = document.querySelectorAll('.bias-indicator');
    indicators.forEach(indicator => indicator.remove());
  }
  
  // initial scan (wait 1s to let content load before they are scanned)
  setTimeout(scanPosts, 1000);
  
  // handles user scrolling and new posts loading
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




















// ==========================================================
//             "RELATED POSTS" BUTTON FEATURE
// - on an opened post, "Related Posts" button will open up a panel that shows posts of opposing & neutral bias
// ==========================================================

const RELATED_API = "http://127.0.0.1:8000/api/related";

let cachedRelatedPosts = null;     // panel data for current page
let lastRelatedForUrl = null;      // to prevent post views being logged multiple times

function getOpenedPostTitleAndBody() {
  const openedPost = document.querySelector("shreddit-post, [data-testid='post-container'], [data-test-id='post-content']");
  if (!openedPost) return { title: "", body: "" };

  const titleEl = openedPost.querySelector("h1[data-testid='post-title'], h1, h2, [data-click-id='title']");
  const bodyEl  = openedPost.querySelector("shreddit-post-text-body, [data-testid='post-content'], .usertext-body");

  const title = titleEl?.innerText?.trim() || "";
  const body  = bodyEl?.innerText?.trim() || "";
  return { title, body };
}

async function fetchRelatedForOpenedPost() {
  if (lastRelatedForUrl === location.href) return cachedRelatedPosts;

  const label     = getBiasLabelForOpenedPost();
  const subreddit = getOpenedPostSubredditName() || "";
  const { title, body } = getOpenedPostTitleAndBody();
  const username  = (await getRedditUsername()) || "anonymous";

  if (!label || !subreddit || (!title && !body)) {
    console.warn("[/related] Missing required fields", { label, subreddit, title, body });
    return null;
  }


  const allInfo = {
    user_id: username,
    title,
    post: body,
    label,
    subreddit
  };

  try {
    const res = await fetch(RELATED_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(allInfo)
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error("[/related] HTTP", res.status, text);
      return null;
    }
    const json = await res.json();
    cachedRelatedPosts = Array.isArray(json.related_posts) ? json.related_posts : [];
    lastRelatedForUrl = location.href;
    return cachedRelatedPosts;
  } catch (e) {
    console.error("[/related] fetch error", e);
    return null;
  }
}


function addRelatedPostsButton() {

  // if button already exists, don't make a duplicate one
  if (document.getElementById("related-posts-btn")) return;

  // Create floating button 
  const btn = document.createElement("button");
  btn.id = "related-posts-btn";
  btn.textContent = "Related Posts";
  btn.className = "related-btn";

  // Create dropdown panel container
  const panel = document.createElement("div");
  panel.id = "related-posts-panel";
  panel.className = "related-panel";
  panel.innerHTML = `<p class="loading">Loading related posts...</p>`;

  // insert the button and dropdown panel into the page
  document.body.appendChild(btn);
  document.body.appendChild(panel);

 

  //Adds the posts to the panel
  async function addPostsToPanel() {
  const posts = Array.isArray(cachedRelatedPosts) ? cachedRelatedPosts : [];
  if (!posts.length) {
    panel.innerHTML = `<div class="related-panel__header" role="heading" aria-level="2">Related Posts</div>
      <div class="related-panel__body"><div class="loading">No related posts yet.</div></div>`;
    return;
  }
  panel.innerHTML = `
    <div class="related-panel__header" role="heading" aria-level="2">Related Posts</div>
    <div class="related-panel__body">
      ${posts.map(p => `
        <a href="${p.url}" target="_blank" class="related-item ${p.leaning || p.bias || ''}" rel="noopener">
          <span class="related-title" title="${p.title}">${p.title}</span>
          <span class="related-bias">${(p.leaning || p.bias || 'neutral').toUpperCase()}</span>
        </a>
      `).join("")}
    </div>`;
}



//
btn.addEventListener("mouseenter", async () => {
  await addPostsToPanel();

  const rect = btn.getBoundingClientRect();

  // live geometry — data-driven, not hardcoded
  const panelWidth = panel.offsetWidth;
  const viewportWidth = window.innerWidth;

  // Align left edge of panel slightly left of button’s right edge,
  // but clamp within viewport
  let left = rect.right - panelWidth;  // 20px small visual gap
  left = Math.max(12, Math.min(left, viewportWidth - panelWidth - 12));

  // Position panel below the button
  const top = rect.bottom + 8;

  panel.style.position = "fixed";
  panel.style.left = `${left}px`;
  panel.style.top = `${top}px`;
  panel.classList.add("show");
});


  // when mouse leaves the button, give it short grace period to get to the pane. if it doesn't, close panel
  btn.addEventListener("mouseleave", () => {
    setTimeout(() => {
      if (!panel.matches(":hover")) panel.classList.remove("show");
    }, 150);
  });

  // when mouse leaves panel, close panel
  panel.addEventListener("mouseleave", () => panel.classList.remove("show"));

  // handles case: if browser window being resized, close the pane (when the pane is opened again, it will dynamically resize, adjusting to new window size)
  window.addEventListener("resize", () => panel.classList.remove("show"));
}


// === Ensuring Find Related Posts button only appears when user is on an OPENED and BIAS-LABELLED post ===

// Helper to remove existing Related posts button and panel 
function removeRelatedPostsButton() {
  document.getElementById("related-posts-btn")?.remove();
  document.getElementById("related-posts-panel")?.remove();
  cachedRelatedPosts = null;
  lastRelatedForUrl = null;
}



// Make Related Posts button appear on correct pages (opened & bias labelled post)
async function checkForBiasTaggedPost() {
  // check if opened post
  if (!isPostCommentsPage()) {
    removeRelatedPostsButton();
    cachedRelatedPosts = null;
    lastRelatedForUrl = null;
    return;
  }
  // check if the opened post content has loaded
  const mainPost = document.querySelector(
    "shreddit-post, [data-testid='post-container'], [data-test-id='post-content']"
  );
  if (!mainPost) {
    removeRelatedPostsButton();
    return;
  }

  const hasBias = !!mainPost.querySelector(".bias-indicator");

  // one place to collect and log everything
  const collect = async () => {
    if (lastRelatedForUrl === location.href && Array.isArray(cachedRelatedPosts)) {
    console.log("[Related] using cached", cachedRelatedPosts.length, "items");
    return;
    }
    const username  = await getRedditUsername();
    const subreddit = getOpenedPostSubredditName();
    const label     = getBiasLabelForOpenedPost();
    console.log("[Related] user:", username, "subreddit:", subreddit, "label:", label);



  // get title/body from the opened post (same selectors you use elsewhere)
    const openedPost = document.querySelector(
      "shreddit-post, [data-testid='post-container'], [data-test-id='post-content']"
    );
    const title = openedPost?.querySelector("h1[data-testid='post-title'], h1, h2, [data-click-id='title']")?.innerText?.trim() || "";
    const body  = openedPost?.querySelector("shreddit-post-text-body, [data-testid='post-content'], .usertext-body")?.innerText?.trim() || "";

    // fire request
    try {
      const res = await fetch(RELATED_API, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          user_id: username || "anonymous",
          subreddit,
          label,
          title,
          post: body
        })
      });

      if (!res.ok) {
        console.error("[Related] backend error", res.status);
        cachedRelatedPosts = [];
        lastRelatedForUrl = location.href;
        return;
      }

      const data = await res.json();
      cachedRelatedPosts = data?.related_posts || [];
      lastRelatedForUrl = location.href;

      console.log(
        "[Related] user:", username,
        "subreddit:", subreddit,
        "label:", label,
        "items:", cachedRelatedPosts.length
      );
    } catch (e) {
      console.error("[Related] fetch failed:", e);
      cachedRelatedPosts = [];
      lastRelatedForUrl = location.href;
    }
  };
    
  if (hasBias) {
    // if bias label already on screen, collect now
    await collect();
    // ensure the button exists so the hover can show related posts
    addRelatedPostsButton();
    return;
  }

  //continue checking the post in case bias label loads later (handle slow updating of bias label) 
  // if bias label appears later, collect info  
  const observer = new MutationObserver(async () => {
    if (mainPost.querySelector(".bias-indicator")) {
      await collect();
      addRelatedPostsButton();
      observer.disconnect();
    }
  });
  observer.observe(mainPost, { childList: true, subtree: true });

}

      


/////////////////////////////////////////////////////////////////////////////





//helper function to get Reddit username of post being opened
let cachedUsername = null;
async function getRedditUsername() {
  if (cachedUsername) return cachedUsername;
  try {
    const res = await fetch('https://www.reddit.com/api/me.json', {
      credentials: 'same-origin'
    });
    if (!res.ok) return null;
    const j = await res.json();
    cachedUsername = j?.data?.name || null; // e.g. "my_username"
    return cachedUsername;
  } catch {
    return null;
  }
}

// helper function for getOpenedPostSubredditName()
function deepFind(root, predicate) {
  const stack = [root];
  while (stack.length) {
    const node = stack.pop();
    if (predicate(node)) return node;
    if (node instanceof Element || node instanceof DocumentFragment) {
      if (node.shadowRoot) stack.push(node.shadowRoot);
      for (const child of node.children) stack.push(child);
    }
  }
  return null;
}


function getOpenedPostSubredditName() {
  const openedPost =
    document.querySelector('[data-testid="post-container"]') ||
    document.querySelector('shreddit-post');
  if (!openedPost) return null;

  // find the subreddit link inside the opened post
  const link = deepFind(
    openedPost,
    el => el.tagName === 'A' && /\/r\/[^/]+/i.test(el.getAttribute('href') || '')
  );
  if (!link) return null;

  const m = (link.getAttribute('href') || '').match(/\/r\/([^/]+)/i);
  return m ? m[1] : null; 
}

function getBiasLabelForOpenedPost() {
  const openedPost = document.querySelector('shreddit-post, [data-testid="post-container"]');
  return openedPost?.dataset?.biasLabel ?? null;
}







// Allow time for bias scan before deciding whether to show Related Posts button
setTimeout(() => {
  if (isPostCommentsPage()) {
    checkForBiasTaggedPost();
  } else {
    removeRelatedPostsButton();
  }
}, 2000);

// detects if user moved to a different page by checking change in URL.
// if change detected, remove everything from the pag, rescan page and add accordingly
let lastUrl = location.href;

setInterval(() => {
  if (location.href !== lastUrl) { 
    lastUrl = location.href;
    console.log('URL changed, rescanning posts...');

    cachedUsername = null;

    // Remove Related Posts button (and panel) immediately
    removeRelatedPostsButton();

    // Wait for new page load and scan page type
    const isOpenedPostPage = location.pathname.includes('/comments/');
    const delay = 1500; // give Reddit time to render

    // Add bias labels and show Related Posts button appropriately
    setTimeout(() => {
      scanPosts();                
      checkForBiasTaggedPost();    
    }, delay);
  }
}, 400); // how often to check for url changes


