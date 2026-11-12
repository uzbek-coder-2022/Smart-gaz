// SmartGaz frontend shared utilities
const SG = {
  token: localStorage.getItem('sg_token') || null,

  async api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (this.token) headers['Authorization'] = 'Bearer ' + this.token;
    const url = path.startsWith('/auth/') ? path : '/api/v1' + path;
    const r = await fetch(url, { ...opts, headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    let data = null;
    try { data = await r.json(); } catch (e) {}
    if (!r.ok) {
      const msg = (data && data.detail) ? data.detail : ('Xato: ' + r.status);
      throw new Error(msg);
    }
    return data;
  },

  async setToken(tok, user) {
    this.token = tok;
    localStorage.setItem('sg_token', tok);
    localStorage.setItem('sg_user', JSON.stringify(user));
    // Also set an HttpOnly cookie via server endpoint so SSR sees the user
    try { await fetch('/auth/logout', { method:'POST' }); /* noop */ } catch {}
    document.cookie = `sg_token=${tok}; path=/; max-age=${60*60*24}; samesite=lax`;
  },
  getUser() { try { return JSON.parse(localStorage.getItem('sg_user')); } catch { return null; } },
  async logout() {
    localStorage.removeItem('sg_token');
    localStorage.removeItem('sg_user');
    document.cookie = 'sg_token=; path=/; max-age=0';
    try { await fetch('/auth/logout', { method:'POST' }); } catch {}
    location.href = '/';
  },
  fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('uz-UZ', { year:'numeric', month:'2-digit', day:'2-digit' });
  },
  fmtDateTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('uz-UZ', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' });
  },
  badge(status) {
    const map = {
      PENDING: ['sg-badge-pending', 'Navbatda'],
      APPROVED: ['sg-badge-approved', 'Marshrutda'],
      ON_WAY: ['sg-badge-onway', 'Yo\'lda'],
      DELIVERED: ['sg-badge-delivered', 'Topshirildi'],
      CANCELLED: ['sg-badge-cancelled', 'Bekor'],
      PLANNED: ['sg-badge-planned', 'Rejalashtirilgan'],
      IN_PROGRESS: ['sg-badge-progress', 'Davom etmoqda'],
      COMPLETED: ['sg-badge-completed', 'Yakunlandi'],
    };
    const [cls, label] = map[status] || ['sg-badge-pending', status];
    return `<span class="sg-badge ${cls}">${label}</span>`;
  },
  showAlert(msg, type='success') {
    const el = document.createElement('div');
    el.className = `sg-alert sg-alert-${type}`;
    el.textContent = msg;
    const first = document.querySelector('.sg-container');
    if (first) first.prepend(el);
    setTimeout(() => el.remove(), 5000);
  }
};

// Authenticated gate — redirect unauthenticated users away from protected pages
(function authGate() {
  const protectedPages = ['/cabinet','/driver','/dispatcher','/mfy','/admin'];
  const path = location.pathname;
  if (protectedPages.some(p => path.startsWith(p)) && !SG.token) {
    location.href = '/login?next=' + encodeURIComponent(path);
  }
})();

// FAQ toggle
document.addEventListener('click', (e) => {
  if (e.target.closest('.sg-faq-q')) e.target.closest('.sg-faq-item').classList.toggle('open');
});
