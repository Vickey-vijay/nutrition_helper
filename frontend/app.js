/* NutriMind AI — single-page front-end controller */
const App = (() => {
  const $ = id => document.getElementById(id);
  const TOKEN_KEY = 'nm_token';
  // HTML-escape any user- or AI-supplied text before it goes into innerHTML —
  // reviews, tracker notes and recipe text all round-trip free-form strings
  // through here, so this is not optional.
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  let state = {
    token: localStorage.getItem(TOKEN_KEY) || null,
    user: null, profile: null, metrics: null,
    cards: [], prefsMap: {}, servings: 1, revRating: 0, health: null,
  };

  /* ---------------- API helper ---------------- */
  async function api(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
    const res = await fetch(path, {
      method, headers, body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) { doLogout(); throw new Error('Session expired'); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || ('Request failed (' + res.status + ')'));
    return data;
  }

  // `text` may intentionally contain trusted markup (e.g. a spinner span) —
  // callers are responsible for esc()-ing any untrusted value they interpolate
  // into it before calling flash().
  function flash(el, text, kind = 'err') {
    if (!text) { el.innerHTML = ''; return; }
    el.innerHTML = `<div class="msg ${kind}">${text}</div>`;
  }

  /* ---------------- Auth ---------------- */
  function showTab(which) {
    const login = which === 'login';
    $('tabLogin').classList.toggle('active', login);
    $('tabRegister').classList.toggle('active', !login);
    $('loginForm').classList.toggle('hidden', !login);
    $('registerForm').classList.toggle('hidden', login);
    flash($('authMsg'), '');
  }

  async function login(e) {
    e.preventDefault();
    try {
      const d = await api('POST', '/api/auth/login', {
        email: $('loginEmail').value.trim(), password: $('loginPassword').value });
      setSession(d.token); await boot();
    } catch (err) { flash($('authMsg'), err.message); }
    return false;
  }

  async function register(e) {
    e.preventDefault();
    try {
      const d = await api('POST', '/api/auth/register', {
        name: $('regName').value.trim(), email: $('regEmail').value.trim(),
        password: $('regPassword').value });
      setSession(d.token); await boot();
    } catch (err) { flash($('authMsg'), err.message); }
    return false;
  }

  function setSession(token) { state.token = token; localStorage.setItem(TOKEN_KEY, token); }

  function doLogout() {
    state.token = null; localStorage.removeItem(TOKEN_KEY);
    state.user = state.profile = state.metrics = null;
    $('appView').classList.add('hidden');
    $('authView').classList.remove('hidden');
  }
  async function logout() {
    try { await api('POST', '/api/auth/logout'); } catch (_) {}
    doLogout();
  }

  /* ---------------- Boot / routing ---------------- */
  async function boot() {
    try { state.health = await (await fetch('/api/health')).json(); } catch (_) {}
    if (!state.token) { $('authView').classList.remove('hidden'); $('appView').classList.add('hidden'); return; }
    let me;
    try { me = await api('GET', '/api/me'); }
    catch (_) { doLogout(); return; }
    state.user = me.user; state.profile = me.profile; state.metrics = me.metrics;
    state.prefsMap = {};
    (me.prefs.liked || []).forEach(k => state.prefsMap[k] = 'like');
    (me.prefs.disliked || []).forEach(k => state.prefsMap[k] = 'dislike');

    $('authView').classList.add('hidden'); $('appView').classList.remove('hidden');
    $('uname').textContent = state.user.name;
    $('avatar').textContent = (state.user.name[0] || 'U').toUpperCase();
    renderDashboard(me);
    fillProfileForm();
    if (!state.cards.length) loadCards();
    go('dashboard');
  }

  function go(view) {
    document.querySelectorAll('[id^="view-"]').forEach(s => s.classList.add('hidden'));
    $('view-' + view).classList.remove('hidden');
    document.querySelectorAll('.nav a').forEach(a =>
      a.classList.toggle('active', a.dataset.view === view));
    if (view === 'tracker') loadLogs();
    if (view === 'reviews') loadReviews();
    if (view === 'recipe') loadRecipes();
    if (view === 'preferences') renderPrefGrid();
  }

  /* ---------------- Dashboard ---------------- */
  function renderDashboard(me) {
    $('welcome').textContent = `Welcome, ${state.user.name.split(' ')[0]} 👋`;
    const h = state.health || {};
    const mode = h.ai_mode === 'groq_llama_langchain'
      ? `🤖 AI: Groq · ${h.model}` : '⚙️ AI: rule-based fallback';
    $('aiBadge').textContent = `${mode} · ${h.foods || ''} foods loaded`;

    const t = me.tracker || { count: 0, avg_score: 0 };
    if (state.metrics) {
      const m = state.metrics;
      $('dashStats').innerHTML = stat(m.bmi, 'BMI') + stat(m.bmi_category, 'Category')
        + stat(m.target_calories, 'Target kcal/day') + stat(t.avg_score || '–', 'Avg activity');
      $('dashNoProfile').classList.add('hidden');
      $('dashProfile').classList.remove('hidden');
      const p = state.profile;
      $('snapshot').innerHTML =
        `<div class="tags">
          <span class="pill green">${esc(p.region)} · ${esc(p.diet)}</span>
          <span class="pill orange">Goal: ${esc(p.goal)}</span>
          <span class="pill gray">${p.height_cm} cm · ${p.weight_kg} kg · age ${p.age}</span>
          <span class="pill gray">BMR ${m.bmr} · TDEE ${m.tdee} kcal</span>
        </div>
        <p class="muted" style="margin-top:10px">${t.count} tracker ${t.count === 1 ? 'entry' : 'entries'} logged.</p>`;
    } else {
      $('dashStats').innerHTML = stat('–', 'BMI') + stat('–', 'Category')
        + stat('–', 'Target kcal') + stat('–', 'Avg activity');
      $('dashNoProfile').classList.remove('hidden');
      $('dashProfile').classList.add('hidden');
    }
  }
  const stat = (v, l) => `<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`;

  /* ---------------- Profile ---------------- */
  function fillProfileForm() {
    const p = state.profile; if (!p) return;
    if (p.dob) $('pf_dob').value = p.dob;
    $('pf_sex').value = p.sex; $('pf_height').value = p.height_cm;
    $('pf_weight').value = p.weight_kg; $('pf_activity').value = p.activity;
    $('pf_goal').value = p.goal; $('pf_diet').value = p.diet;
    $('pf_region').value = p.region; $('pf_allergies').value = p.allergies || '';
  }

  async function saveProfile(e) {
    e.preventDefault();
    const body = {
      dob: $('pf_dob').value || null, sex: $('pf_sex').value,
      height_cm: +$('pf_height').value, weight_kg: +$('pf_weight').value,
      activity: $('pf_activity').value, goal: $('pf_goal').value,
      diet: $('pf_diet').value, region: $('pf_region').value,
      allergies: $('pf_allergies').value || null,
    };
    if (!body.dob) { flash($('profileMsg'), 'Please pick your date of birth.'); return false; }
    try {
      const d = await api('POST', '/api/profile', body);
      state.profile = d.profile; state.metrics = d.metrics;
      flash($('profileMsg'),
        `Saved! BMI ${d.metrics.bmi} (${d.metrics.bmi_category}), target ${d.metrics.target_calories} kcal/day.`, 'ok');
      renderDashboard({ tracker: { count: 0, avg_score: 0 } });
    } catch (err) { flash($('profileMsg'), err.message); }
    return false;
  }

  async function aiSuggestGoal() {
    const hint = $('goalHint'); hint.classList.remove('hidden');
    hint.innerHTML = '<span class="spinner" style="border-color:#ccc;border-top-color:#1f8a4c"></span>Asking AI…';
    try {
      // ensure a profile exists to base the suggestion on
      await saveProfileSilently();
      const d = await api('POST', '/api/suggest-goal');
      $('pf_goal').value = d.suggestion.goal;
      hint.innerHTML = `🤖 <b>${esc(d.suggestion.goal)}</b> — ${esc(d.suggestion.rationale)} <span class="src">(${esc(d.suggestion.source)})</span>`;
    } catch (err) { hint.textContent = err.message; }
  }
  async function saveProfileSilently() {
    const body = {
      dob: $('pf_dob').value || null, sex: $('pf_sex').value,
      height_cm: +$('pf_height').value, weight_kg: +$('pf_weight').value,
      activity: $('pf_activity').value, goal: $('pf_goal').value,
      diet: $('pf_diet').value, region: $('pf_region').value,
      allergies: $('pf_allergies').value || null,
    };
    if (!body.dob) throw new Error('Pick your date of birth first.');
    const d = await api('POST', '/api/profile', body);
    state.profile = d.profile; state.metrics = d.metrics;
  }

  /* ---------------- Meal plan ---------------- */
  async function generatePlan(regen) {
    if (!state.profile) { go('profile'); return; }
    const pill = $('planPill');
    pill.innerHTML = '<span class="pill gray"><span class="spinner" style="border-color:#bbb;border-top-color:#1f8a4c"></span>Building plan…</span>';
    try {
      const seed = regen ? Math.floor(Math.random() * 1e9) : undefined;
      const d = await api('POST', '/api/plan', { seed });
      renderPlan(d); pill.innerHTML = '';
    } catch (err) { pill.innerHTML = `<span class="pill orange">${err.message}</span>`; }
  }

  function renderPlan(d) {
    $('planResult').classList.remove('hidden');
    const m = d.metrics, pl = d.plan;
    $('planStats').innerHTML = stat(m.bmi, 'BMI') + stat(m.bmi_category, 'Category')
      + stat(pl.target_calories, 'Target kcal') + stat(pl.calorie_accuracy_pct + '%', 'Plan accuracy');
    // A meal is a plate of several dishes, so rows are grouped under their
    // slot: the slot name is printed once and the dishes listed beneath it.
    const tb = $('planTable').querySelector('tbody'); tb.innerHTML = '';
    let lastSlot = null;
    pl.meals.forEach(me => {
      const newSlot = me.slot !== lastSlot;
      lastSlot = me.slot;
      const slotCell = newSlot ? esc(me.slot) : '';
      const serving = me.pieces
        ? `${me.pieces} × <span class="muted">(${me.grams} g)</span>`
        : `${me.grams} g`;
      tb.insertAdjacentHTML('beforeend',
        `<tr${newSlot ? ' class="slot-start"' : ''}>
          <td class="slot">${slotCell}</td>
          <td>${esc(me.name)} <span class="role">${esc(me.role || '')}</span></td>
          <td>${serving}</td><td>${me.kcal}</td>
          <td>${me.protein_g}</td><td>${me.carb_g}</td><td>${me.fat_g}</td></tr>`);
    });
    $('tk').textContent = pl.totals.kcal; $('tp').textContent = pl.totals.protein_g;
    $('tc').textContent = pl.totals.carb_g; $('tf').textContent = pl.totals.fat_g;
    $('planAcc').textContent = `Plan hits ${pl.calorie_accuracy_pct}% of your ${pl.target_calories} kcal target · ${pl.region} · ${pl.diet}.`;
    $('planGuide').textContent = d.guidance.guidance;
    $('planSrc').textContent = 'Guidance source: ' + d.guidance.source;
  }

  /* ---------------- Preferences ---------------- */
  async function loadCards() {
    try { const d = await api('GET', '/api/food-cards'); state.cards = d.cards; } catch (_) {}
  }
  function renderPrefGrid() {
    if (!state.cards.length) { loadCards().then(renderPrefGrid); return; }
    $('prefGrid').innerHTML = state.cards.map(c => {
      const st = state.prefsMap[c.key];
      const cls = st === 'like' ? 'like' : st === 'dislike' ? 'dislike' : '';
      const lab = st === 'like' ? '👍 Like' : st === 'dislike' ? '👎 Avoid' : 'Neutral';
      return `<div class="foodcard ${cls}" onclick="App.cyclePref('${c.key}')">
        <span class="emo">${c.emoji}</span><div class="lab">${c.label}</div>
        <div class="state">${lab}</div></div>`;
    }).join('');
  }
  function cyclePref(key) {
    const cur = state.prefsMap[key];
    state.prefsMap[key] = cur === undefined ? 'like' : cur === 'like' ? 'dislike' : undefined;
    if (state.prefsMap[key] === undefined) delete state.prefsMap[key];
    renderPrefGrid();
  }
  async function savePrefs() {
    const liked = [], disliked = [];
    Object.entries(state.prefsMap).forEach(([k, v]) =>
      (v === 'like' ? liked : disliked).push(k));
    try {
      await api('POST', '/api/preferences', { liked, disliked });
      flash($('prefMsg'), `Saved ${liked.length} likes, ${disliked.length} avoided. Your next meal plan will use these.`, 'ok');
    } catch (err) { flash($('prefMsg'), err.message); }
  }

  /* ---------------- Recipe ---------------- */
  function bumpServings(n) {
    state.servings = Math.max(1, Math.min(12, state.servings + n));
    $('servings').textContent = state.servings;
  }
  async function makeRecipe() {
    const dish = $('recDish').value.trim();
    if (dish.length < 2) return;
    if (!state.profile) { go('profile'); return; }
    const box = $('recipeResult'); box.classList.remove('hidden');
    box.innerHTML = '<span class="spinner" style="border-color:#ccc;border-top-color:#1f8a4c"></span>Cooking up a healthy recipe…';
    try {
      const d = await api('POST', '/api/recipe', { dish, servings: state.servings });
      renderRecipe(d.recipe); loadRecipes();
    } catch (err) { box.innerHTML = `<div class="msg err">${err.message}</div>`; }
  }
  function renderRecipe(r) {
    const ing = r.ingredients.map(i => `<li>${esc(i)}</li>`).join('');
    const steps = r.steps.map(s => `<li>${esc(s)}</li>`).join('');
    const notes = r.health_notes.map(n => `<li>${esc(n)}</li>`).join('');
    $('recipeResult').innerHTML = `
      <h2>${esc(r.title)}</h2>
      <div class="tags">
        <span class="pill green">${r.servings} serving(s)</span>
        <span class="pill orange">Budget: ${r.budget_kcal_per_serving} kcal/serving (your body)</span>
        <span class="pill gray">AI estimate: ~${r.approx_calories_per_serving} kcal</span>
        <span class="pill gray">⏱ ${r.prep_time_min} min</span>
      </div>
      <h2 style="font-size:1rem;margin-top:16px">Ingredients</h2><ul class="reclist">${ing}</ul>
      <h2 style="font-size:1rem">Method</h2><ol>${steps}</ol>
      <h2 style="font-size:1rem">Health notes</h2><ul class="reclist">${notes}</ul>
      <div class="src">Source: ${esc(r.source)}</div>`;
  }
  async function loadRecipes() {
    try {
      const d = await api('GET', '/api/recipes');
      $('recentRecipes').innerHTML = d.recipes.length
        ? d.recipes.map(x => `<li><b>${esc(x.dish)}</b> · ${x.servings} serving(s)
            <span class="muted">— ${new Date(x.created + 'Z').toLocaleDateString()}</span></li>`).join('')
        : '<li class="muted">None yet.</li>';
    } catch (_) {}
  }

  /* ---------------- Tracker ---------------- */
  async function addLog() {
    const note = $('logNote').value.trim();
    if (!note) { flash($('logMsg'), 'Write a short note first.'); return; }
    flash($('logMsg'), '<span class="spinner" style="border-color:#ccc;border-top-color:#1f8a4c"></span>Summarising…', 'ok');
    try {
      const w = $('logWeight').value ? +$('logWeight').value : null;
      const d = await api('POST', '/api/log', { note_text: note, weight_kg: w });
      flash($('logMsg'),
        `${esc(d.ai.summary)} <b>Score: ${d.ai.activity_score}/10.</b> ${esc(d.ai.encouragement)}`, 'ok');
      $('logNote').value = ''; $('logWeight').value = '';
      loadLogs();
    } catch (err) { flash($('logMsg'), err.message); }
  }
  async function loadLogs() {
    try {
      const d = await api('GET', '/api/logs');
      const recent = d.stats.recent || [];
      $('trackerBars').innerHTML = recent.length
        ? recent.map(r => `<div class="bar" style="height:${(r.activity_score || 0) * 10}%">
            <span>${r.activity_score || 0}</span></div>`).join('')
        : '<p class="muted">Log a day to see your trend.</p>';
      $('trackerAvg').textContent = d.stats.count
        ? `Average activity score: ${d.stats.avg_score}/10 over ${d.stats.count} entries.` : '';
      $('logHistory').innerHTML = d.logs.length ? d.logs.map(l => `
        <div class="logitem"><div class="top">
          <span class="date">${esc(l.log_date)}${l.weight_kg ? ' · ' + l.weight_kg + ' kg' : ''}</span>
          <span class="score ${l.activity_score < 5 ? 'low' : ''}">${l.activity_score}/10</span></div>
          <div style="margin-top:6px">${esc(l.ai_summary || l.note_text)}</div></div>`).join('')
        : '<p class="muted">No entries yet.</p>';
    } catch (_) {}
  }

  /* ---------------- Reviews ---------------- */
  function renderStars() {
    $('revStars').innerHTML = [1, 2, 3, 4, 5].map(i =>
      `<span class="st ${i <= state.revRating ? 'on' : ''}" onclick="App.setRating(${i})">★</span>`).join('');
  }
  function setRating(n) { state.revRating = n; renderStars(); }
  async function addReview() {
    if (!state.revRating) { flash($('revMsg'), 'Pick a star rating.'); return; }
    try {
      await api('POST', '/api/review', {
        feature: $('revFeature').value, rating: state.revRating,
        comment: $('revComment').value.trim() });
      flash($('revMsg'), 'Thanks for your feedback! 🙏', 'ok');
      $('revComment').value = ''; state.revRating = 0; renderStars(); loadReviews();
    } catch (err) { flash($('revMsg'), err.message); }
  }
  async function loadReviews() {
    try {
      const d = await api('GET', '/api/reviews');
      $('reviewList').innerHTML = d.reviews.length ? d.reviews.map(r => `
        <div class="logitem"><div class="top">
          <span><b>${esc(r.name)}</b> · <span class="muted">${esc(r.feature)}</span></span>
          <span class="pill orange">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
        </div>${r.comment ? `<div style="margin-top:6px">${esc(r.comment)}</div>` : ''}</div>`).join('')
        : '<p class="muted">No reviews yet.</p>';
    } catch (_) {}
  }

  /* ---------------- init ---------------- */
  document.addEventListener('DOMContentLoaded', () => { renderStars(); boot(); });

  return { showTab, login, register, logout, go, saveProfile, aiSuggestGoal,
    generatePlan, savePrefs, cyclePref, bumpServings, makeRecipe,
    addLog, addReview, setRating };
})();
