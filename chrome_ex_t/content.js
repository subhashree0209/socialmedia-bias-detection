// Content script for Reddit bias detection

// ensure we're on Reddit
if (!window.location.hostname.includes('reddit.com')) {
    console.log('Not a Reddit page - extension inactive');
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
        processedT3.clear();
        scanPosts();
      } else {
        removeAllIndicators();
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

    const API_URL = "http://127.0.0.1:8000/classify"

    async function analyzeBias(textContent) {
    try {                                                                     //want to see if we can even call the backend
       const response = await fetch(API_URL, {
       method: "POST",
       headers: {"Content-Type": "application/json"}, 
       body: JSON.stringify({text: textContent})
       });

       if (!response.ok) {
         throw new Error(`Backend returned status: ${response.status}`)
         }

       const biasLabel = await response.json()
       console.log("Backend response:", biasLabel)
       return biasLabel

       } catch (err){
          if (err.message === "Failed to Fetch") {
            console.error("Cannot call back end at all, make sure labelling.py is running")
          } else {
            console.error("Backend error: ", err)
          }
         return null
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






  // Detects whether user is on 
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
        console.log(' Content not ready yet. Waiting...');
        return; // will retry automatically via MutationObserver 
      }

      
      //analyse text and insert label   
      const biasData = await analyzeBias(fullText);
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
        const biasData = await analyzeBias(textContent);
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
       
        const biasData = await analyzeBias(textContent);
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
        const biasData = await analyzeBias(textContent);
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
  
  // Allows the content.js to be rerun when a URL changes (e.g. clicking on a post)
  let lastUrl = location.href;

  setInterval(() => {
    if (location.href !== lastUrl) {    //if url has changed
      lastUrl = location.href;
      console.log('URL changed, rescanning posts...');

      const isOpenedPostPage = location.pathname.includes('/comments/'); //checks what page user has navigated into

      if (isOpenedPostPage) {
        console.log('Opened post detected - scanning after load');
        setTimeout(scanPosts, 1500); // delay gives Reddit time to render title + body
      } else {
        // Feed or other pages
        setTimeout(scanPosts, 800);
      }
    }
  }, 500);  //every 0.5s, URL change is checked





  console.log('Reddit Bias Detector loaded');