// Background service worker for Reddit Bias Detector

// Initialize extension on install
chrome.runtime.onInstalled.addListener((details) => {                           //Setting up listener to wait for messages
    if (details.reason === 'install') {                                         //Setting up default config for users as this is the first time it is installed
      console.log('Reddit Bias Detector installed');    
      
      chrome.storage.sync.set({
        enabled: true,
        sensitivity: 'medium',
        showNotifications: true
      });

      // chrome.tabs.create({ url: 'welcome.html' });
    } else if (details.reason === 'update') {
      console.log('Reddit Bias Detector updated');
    } else if (details.reason === 'chrome_update') { 
        console.log('Chrome Browser updated');
    }
  });
  
  // Listen for messages from content script or popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {     //Setting up listener to wait for messages
    if (request.action === 'analyzeBias') {                                     //Calls function analyzeBias from content.js 
      // Perform more complex bias analysis if needed
      const result = performAdvancedAnalysis(request.text);
      sendResponse({ result });                                                // Sends results back to user
      return true;                                                             //Keeps connection open
    }
    
    if (request.action === 'getSettings') {
      chrome.storage.sync.get(['enabled', 'sensitivity', 'showNotifications'], (data) => {
        sendResponse(data);
      });
      return true;
    }
    
    if (request.action === 'updateSettings') {
      chrome.storage.sync.set(request.settings, () => {                       //request.settings is the new settings to save
        sendResponse({ success: true });
      });
      return true;
    }
  
    if (request.action === 'biasDetected') {
      // Track statistics
      updateStatistics(request.data);
      sendResponse({ received: true });
      return true;
    }
  });
  
  // Advanced analysis function: NEED BACKEND, probably need to put analysis in here cos it a lot of computation
  function performAdvancedAnalysis(text) {
    const patterns = {
      strawman: /(?:nobody is saying|who said|no one thinks)/gi,                      //defining fallacy patterns
      appeal_to_emotion: /(?:think of the|imagine if|how would you feel)/gi,          //g-global i-Case-Sensitive
      false_dichotomy: /(?:either.*or|only two|must choose)/gi,
      ad_hominem: /(?:idiot|stupid|moron|ignorant)/gi,
      slippery_slope: /(?:next thing|leads to|where does it end)/gi
    };
  
    const detected = [];
    
    for (const [type, regex] of Object.entries(patterns)) {     //type = strawman, regex = (?:nobody....)
      if (regex.test(text)) {                                   //tests the text to see if it matches any of the patterns
        detected.push(type);                                    // pushes the type
      }
    }
  
    return {
      fallacies: detected,
      timestamp: Date.now()
    };
  }
  
  // Update statistics
  function updateStatistics(data) {
    chrome.storage.local.get(['stats'], (result) => {
      const stats = result.stats || {
        totalScanned: 0,
        biasDetected: 0,
        lastUpdate: Date.now()
      };
  
      stats.totalScanned++;
      if (data.biasScore > 0) {
        stats.biasDetected++;
      }
      stats.lastUpdate = Date.now();
  
      chrome.storage.local.set({ stats });
    });
  }
  
  // Context menu for quick actions (optional)
  chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
      id: 'analyzeBias',
      title: 'Analyze for bias',
      contexts: ['selection']
    });
  });
  
  //Still needs to be fixed
  chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'analyzeBias' && info.selectionText) {
      const result = performAdvancedAnalysis(info.selectionText);
      
      // Send result back to content script to display
      chrome.tabs.sendMessage(tab.id, {
        action: 'showAnalysis',
        result: result,
        text: info.selectionText
      });
    }
  });
  
  console.log('Reddit Bias Detector background service worker loaded');