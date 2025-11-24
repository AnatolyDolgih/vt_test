(function(){
  const STORAGE_TOPIC = 'va_topic_v1';
  const input = document.getElementById('topic-input');
  const btn = document.getElementById('continue-button');

  async function saveThemeToServer(topic){
    try{
      const resp = await fetch('/set_theme',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ topic })
      });
      // ignore body; server returns {"theme": "..."} on success
    }catch(e){
      console.warn('Failed to save theme to server, using localStorage only', e);
    }
  }

  async function go(){
    const topic = input.value.trim();
    if (topic){
      localStorage.setItem(STORAGE_TOPIC, topic); // keep local persistence
      await saveThemeToServer(topic);             // sync to FastAPI global
    }
    // FastAPI serves /essay_editor -> static/index.html
    location.href = '/essay_editor';
  }
  btn.addEventListener('click', go);
  input.addEventListener('keydown', (e)=>{
    if (e.key === 'Enter') go();
  });

  // Prefill if exists
  const current = localStorage.getItem(STORAGE_TOPIC);
  if (current) input.value = current;

  const STORAGE_LANG = 'va_lang_v1';

  const ruBtn = document.getElementById('lang-ru');
  const enBtn = document.getElementById('lang-en');

  const titleEl = document.getElementById('sel-title');
  const inputEl = document.getElementById('topic-input');
  const goBtn   = document.getElementById('continue-button');
  const tipEl   = document.getElementById('sel-tip');

  function applyLang(lang){
    // 1) html lang
    document.documentElement.setAttribute('lang', lang);

    // 2) визуальное состояние кнопок
    if (ruBtn) ruBtn.classList.toggle('active', lang === 'ru');
    if (enBtn) enBtn.classList.toggle('active', lang === 'en');

    // 3) тексты из data-атрибутов
    if (titleEl && titleEl.dataset[lang]) titleEl.textContent = titleEl.dataset[lang];
    if (tipEl && tipEl.dataset[lang])     tipEl.textContent   = tipEl.dataset[lang];
    if (goBtn && goBtn.dataset[lang])     goBtn.textContent   = goBtn.dataset[lang];
    if (inputEl && inputEl.dataset[lang]) inputEl.setAttribute('placeholder', inputEl.dataset[lang]);
  }

  function setLang(lang){
    try { localStorage.setItem(STORAGE_LANG, lang); } catch{}
    applyLang(lang);
  }

  // начальное состояние
  const initial = (()=>{
    try { return localStorage.getItem(STORAGE_LANG) || 'ru'; } catch { return 'ru'; }
  })();
  applyLang(initial);

  // обработчики
  if (ruBtn) ruBtn.addEventListener('click', ()=> setLang('ru'));
  if (enBtn) enBtn.addEventListener('click', ()=> setLang('en'));
  
})();