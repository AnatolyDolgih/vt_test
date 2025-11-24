/* Chat UI: server-side storage, toolbar width aligned, voice animation/disable, responsive */
(function(){
  const STORAGE_TOPIC = 'va_topic_v1';
  const STORAGE_LANG = 'va_lang_v1';
  const API_BASE = ''; // same-origin
  const WS_URL = (location.origin.replace(/^http/, 'ws')) + '/wss/web';

  const logoutBtn = document.getElementById('logout-button');
  const chatEl = document.getElementById('chat-panel');
  const inputEl = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-button');
  const voiceBtn = document.getElementById('voice-button');
  const spinner = sendBtn.querySelector('.spinner');
  const topicEl = document.getElementById('current-topic');
  const topicBadgeEl = document.getElementById('topic-text');
  const changeTopicBtn = document.getElementById('change-topic');
  const ruBtn = document.getElementById('lang-ru');
  const enBtn = document.getElementById('lang-en');

  function setTopicText(text){
    if (topicEl) topicEl.textContent = text;        // старое место, если вернёшь левую метку
    if (topicBadgeEl) topicBadgeEl.textContent = text;  // новый бейдж справа
  }

  function num(v){ const n = parseFloat(v); return isNaN(n) ? 0 : n; }
  function getLineHeight(el){
    const s = getComputedStyle(el);
    if (s.lineHeight === 'normal'){ return Math.round(num(s.fontSize) * 1.2); }
    return num(s.lineHeight);
  }
  function getPaddingY(el){
    const s = getComputedStyle(el);
    return num(s.paddingTop) + num(s.paddingBottom);
  }
  function autosize(){
    const line = getLineHeight(inputEl);
    const padY = getPaddingY(inputEl);
    const base = Math.round(line + padY);            // 1 строка
    const maxH = Math.round(line * MAX_ROWS + padY); // до 5 строк

    inputEl.style.height = 'auto';
    let h = inputEl.scrollHeight;
    if (h < base) h = base;
    if (h > maxH) h = maxH;

    inputEl.style.height = h + 'px';
    inputEl.classList.toggle('at-max-height', h >= maxH);
  }

  inputEl.addEventListener('input', autosize);
  inputEl.addEventListener('focus', autosize);
  inputEl.addEventListener('compositionstart', ()=> composing = true);
  inputEl.addEventListener('compositionend', ()=> composing = false);
  inputEl.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && !e.shiftKey && !composing){
      e.preventDefault();
      handleSend();
    }
  });

  window.addEventListener('resize', ()=>{ autosize(); });

  if (logoutBtn){
    logoutBtn.addEventListener('click', ()=>{
      try{ localStorage.removeItem('va_topic_v1'); }catch{}
      try{ const t = document.getElementById('current-topic'); if (t) t.textContent = ''; }catch{}
      location.href = '/';
    });
  }
  // отправка: Enter без Shift, и когда не идёт IME-композиция
  inputEl.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && !e.shiftKey && !composing){
      e.preventDefault();
      handleSend();
    }
  });

  // при инициализации один раз подстроить высоту

  const uiText = {
    ru: { send:"Отправить", voice:"Голос", you:"Вы", bot:"Ассистент", hint:"Напишите сообщение…", change:"Сменить тему", none:"Тема не выбрана" },
    en: { send:"Send", voice:"Voice", you:"You", bot:"Assistant", hint:"Type a message…", change:"Change topic", none:"No topic" },
  };
  let lang = localStorage.getItem(STORAGE_LANG) || 'ru';
  function applyLang(l){
    lang = l; localStorage.setItem(STORAGE_LANG,l);
    inputEl.placeholder = uiText[l].hint;
    sendBtn.querySelector('.btn-text').textContent = uiText[l].send;
    voiceBtn.querySelector('.btn-text').textContent = uiText[l].voice;
    changeTopicBtn.textContent = uiText[l].change;
    //topicEl.textContent = currentTopic || uiText[l].none;
    setTopicText(currentTopic || uiText[lang].none);
    ruBtn.classList.toggle('active', l==='ru');
    enBtn.classList.toggle('active', l==='en');
  }
  ruBtn.addEventListener('click',()=>applyLang('ru'));
  enBtn.addEventListener('click',()=>applyLang('en'));

  // Topic syncing
  let currentTopic = localStorage.getItem(STORAGE_TOPIC) || '';
  async function refreshTopicFromServer(){
    try{
      const resp = await fetch(`${API_BASE}/get_theme`);
      if (resp.ok){
        const data = await resp.json();
        if (data && typeof data.theme === 'string' && data.theme.trim()){
          currentTopic = data.theme.trim();
          localStorage.setItem(STORAGE_TOPIC, currentTopic);
        }
      }
    }catch{}
    //topicEl.textContent = currentTopic || uiText[lang].none;
    setTopicText(currentTopic || uiText[lang].none);
  }
  changeTopicBtn.addEventListener('click', ()=> location.href = '/');

  // Server-side messages storage + local mirror fallback
  const STORAGE_CHAT = 'va_chat_messages_v1';

  let messages = [];
  function saveLocal(){ try{ localStorage.setItem(STORAGE_CHAT, JSON.stringify(messages)); }catch(e){ console.warn('Local save failed', e);} }
  function loadLocal(){ try{ return JSON.parse(localStorage.getItem(STORAGE_CHAT)||'[]'); }catch{ return []; } }

  async function loadMessages(){
    try{
      const resp = await fetch(`${API_BASE}/chat/messages`);
      if(resp.ok){
        messages = await resp.json();
        saveLocal();
        return;
      }
      // not ok -> fallback
      messages = loadLocal();
    }catch(e){
      console.warn('Server load failed, using local copy', e);
      messages = loadLocal();
    }
  }

  function appendMessage(role, text){
    const msg = { role, text, ts: Date.now() };
    messages.push(msg);
    saveLocal();
    // fire-and-forget server persist
    fetch(`${API_BASE}/chat/messages`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(msg)
    }).catch(e=> console.warn('Server save failed', e));
  }

  function messageEl(role, text, ts){
    const wrap = document.createElement('div');
    wrap.className = 'message ' + (role === 'assistant' ? 'assistant' : 'user');

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'assistant' ? 'A' : 'U';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = new Date(ts).toLocaleTimeString([], { 
      hour: '2-digit', minute: '2-digit', hour12: false 
    });

    wrap.append(avatar, bubble);
    bubble.appendChild(meta); 
    return wrap;
  }


  function render(){
    chatEl.innerHTML='';
    messages.forEach(m=> chatEl.appendChild(messageEl(m.role, m.text, m.ts)));
    chatEl.scrollTop = chatEl.scrollHeight;
    updateChatHeight();
  }

  async function sendToAgent(userText){
    // Replace with your real API call
    await new Promise(r=>setTimeout(r, 200));
    //return (currentTopic ? `По теме «${currentTopic}»: ` : '') + userText;
	return userText;
  }

  function setSending(on){
    sendBtn.disabled = on;
    if(on) sendBtn.classList.add('sending'); else sendBtn.classList.remove('sending');
  }

  

  // --- Voice press-and-hold ---
  let ws, wsReady = false;
  function connectWS(){
    try{
      ws = new WebSocket(WS_URL);
      ws.addEventListener('open', ()=>{ wsReady = true; });
      ws.addEventListener('close', ()=>{ wsReady = false; setTimeout(connectWS, 1500); });
      ws.addEventListener('error', ()=>{ wsReady = false; });
      ws.addEventListener('message', (ev)=>{
        try{
          const data = JSON.parse(ev.data);
          if (data && data.type === 'processing_done'){
            releaseVoiceProcessing();
          }
        }catch{}
      });
    }catch(e){ wsReady = false; }
  }
  connectWS();

  let holdPointerId = null;
  let processingTimer = null;
  let pollInterval = null;
  let isHolding = false;

  function startServerRecording(){
    const startPayload = JSON.stringify({ type:'voice_button', action:'start', ts: Date.now(), topic: currentTopic });
    if (wsReady){ try{ ws.send(startPayload); }catch{} }
    else { fetch('/start_recording', { method:'POST' }).catch(()=>{}); }
  }
  function stopServerRecording(){
    const stopPayload = JSON.stringify({ type:'voice_button', action:'stop', ts: Date.now(), topic: currentTopic });
    if (wsReady){ try{ ws.send(stopPayload); }catch{} }
    else { fetch('/stop_recording', { method:'POST' }).catch(()=>{}); }
  }

  function engageVoiceRecording(evt){
    if (voiceBtn.disabled) return;
    isHolding = true;
    try{ if(evt.pointerId != null) voiceBtn.setPointerCapture(evt.pointerId); }catch{}
    holdPointerId = evt.pointerId || 0;
    voiceBtn.classList.add('recording');
    startServerRecording();
  }
  function releaseVoiceRecording(){
    if (!isHolding) return;
    isHolding = false;
    voiceBtn.classList.remove('recording');
    startProcessingState();
    stopServerRecording();
  }

  function startProcessingState(){
    voiceBtn.disabled = true;
    voiceBtn.classList.add('processing');
    clearTimeout(processingTimer);
    processingTimer = setTimeout(releaseVoiceProcessing, 30000);
    clearInterval(pollInterval);
    pollInterval = setInterval(async ()=>{
      try{
        const resp = await fetch(`${API_BASE}/is_processing_done`);
        if (resp.ok){
          const data = await resp.json();
          if (data && data.done) releaseVoiceProcessing();
        }
      }catch{}
    }, 1000);
  }
  function releaseVoiceProcessing(){
    clearTimeout(processingTimer);
    clearInterval(pollInterval);
    voiceBtn.classList.remove('processing');
    voiceBtn.disabled = false;
  }

  function onPointerDown(e){
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    e.preventDefault();
    engageVoiceRecording(e);
  }
  function onPointerUp(e){
    if (!isHolding) return;
    e.preventDefault();
    releaseVoiceRecording();
  }
  function onPointerCancel(){
    if (!isHolding) return;
    releaseVoiceRecording();
  }
  voiceBtn.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerCancel);
  voiceBtn.addEventListener('lostpointercapture', onPointerCancel);
  // keyboard hold support
  voiceBtn.addEventListener('keydown', (e)=>{
    if (e.code==='Space' || e.code==='Enter'){ e.preventDefault(); if(!isHolding) engageVoiceRecording({ pointerId: 0 }); }
  });
  voiceBtn.addEventListener('keyup', (e)=>{
    if (e.code==='Space' || e.code==='Enter'){ e.preventDefault(); if(isHolding) releaseVoiceRecording(); }
  });

  // --- Autosize textarea + dynamic chat padding ---
  const MAX_ROWS = 5;
  let composing = false;

  function num(v){ const n = parseFloat(v); return isNaN(n) ? 0 : n; }
  function getLineHeight(el){
    const s = getComputedStyle(el);
    if (s.lineHeight === 'normal'){ return Math.round(num(s.fontSize) * 1.2); }
    return num(s.lineHeight);
  }
  function getPaddingY(el){
    const s = getComputedStyle(el);
    return num(s.paddingTop) + num(s.paddingBottom);
  }
  function setComposerOffset(){
    const footer = document.querySelector('.composer');
    const h = (footer && footer.offsetHeight) ? footer.offsetHeight : 112;
    //document.documentElement.style.setProperty('--composer-offset', h + 'px');
    updateChatHeight();
  }

  function updateChatHeight() {
    const topBarHeight = document.getElementById('top-bar').offsetHeight || 0;
    const toolbarHeight = document.querySelector('.chat-toolbar').offsetHeight || 0;
    const composerHeight = document.querySelector('.composer').offsetHeight || 0;
    // const chatPagePaddingTop = 16; // from .chat-page padding-top
    // const chatPagePaddingBottom = 16; // minimal reserve + var(--composer-offset) in CSS handles the rest
    // const toolbarMarginBottom = 8;
    // const margins = chatPagePaddingTop * 2 + toolbarMarginBottom + chatPagePaddingBottom; // ~ 16*2 +8 +16 =56, but dynamic
    const margins = 16 + 8;
    const maxChatHeight = `calc(100vh - ${topBarHeight + toolbarHeight + composerHeight + margins}px)`;
    chatEl.style.maxHeight = maxChatHeight;
  }

  function autosize(){
    const wasAtBottom = chatEl.scrollTop + chatEl.clientHeight >= chatEl.scrollHeight - 1;
    const line = getLineHeight(inputEl);
    const padY = getPaddingY(inputEl);
    const base = Math.round(line + padY);           // 1 строка
    const maxH = Math.round(Math.min(160, line*5 + padY)); // лимит по CSS

    inputEl.style.height = 'auto';
    let h = inputEl.scrollHeight;
    if (h < base) h = base;
    if (h > maxH) h = maxH;

    inputEl.style.height = h + 'px';
    inputEl.classList.toggle('at-max-height', h >= maxH);

    // after height change, update chat padding
    setComposerOffset();
    if (wasAtBottom) {
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  }

  // events
  inputEl.addEventListener('input', autosize);
  inputEl.addEventListener('focus', autosize);
  inputEl.addEventListener('compositionstart', ()=> composing = true);
  inputEl.addEventListener('compositionend', ()=> composing = false);
  inputEl.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && !e.shiftKey && !composing){
      e.preventDefault();
      handleSend();
    }
  });
  window.addEventListener('resize', ()=> { autosize(); updateChatHeight();});

  // --- Send handlers (restored) ---
  async function handleSend(){
    const text = inputEl.value.trim();
    if (!text) return;
    setSending(true);
    try{
      appendMessage('user', text);
      render();
      inputEl.value='';
      let reply;
      try{
        reply = await sendToAgent(text);
      }catch(e){
        console.warn('sendToAgent failed, echoing locally', e);
        reply = text;
      }
      appendMessage('assistant', reply);
      render();
      // reset composer to one line
      inputEl.value='';
      autosize();
    } finally{
      setSending(false);
    }
  }

  sendBtn.addEventListener('click', handleSend);
  inputEl.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter' && !e.shiftKey){
      e.preventDefault();
      handleSend();
    }
  });

  (async () => {
    await refreshTopicFromServer();
    applyLang(lang);
    //await loadMessages();
    render();
    autosize();
    updateChatHeight();
  })();
})();