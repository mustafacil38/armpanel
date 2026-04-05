/* ===== ArmPanel - Main App Controller ===== */

const App = {
    currentPage: null,
    username: null,

    async init() {
        this.bindEvents();
        const ok = await this.checkAuth();
        if (ok) {
            this.showApp();
            this.handleRoute();
        } else {
            this.showLogin();
        }
        window.addEventListener('hashchange', () => this.handleRoute());
    },

    bindEvents() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.doLogin();
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => this.doLogout());

        // Sidebar toggle (mobile)
        document.getElementById('menu-toggle').addEventListener('click', () => this.toggleSidebar());
        document.getElementById('sidebar-overlay').addEventListener('click', () => this.closeSidebar());

        // Modal close
        document.getElementById('modal-close').addEventListener('click', () => this.closeModal());
        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target === document.getElementById('modal-overlay')) this.closeModal();
        });

        // Nav links close sidebar on mobile
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => this.closeSidebar());
        });
    },

    // ── Auth ──
    async checkAuth() {
        try {
            const res = await fetch('/api/auth/check');
            const data = await res.json();
            if (data.ok) {
                this.username = data.username;
                return true;
            }
            return false;
        } catch { return false; }
    },

    async doLogin() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errEl = document.getElementById('login-error');
        errEl.textContent = '';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json();
            if (data.ok) {
                this.username = data.username;
                this.showApp();
                this.handleRoute();
            } else {
                errEl.textContent = data.error || 'Giriş başarısız';
            }
        } catch {
            errEl.textContent = 'Bağlantı hatası';
        }
    },

    async doLogout() {
        await fetch('/api/auth/logout', { method: 'POST' });
        this.username = null;
        this.showLogin();
        // Stop any polling
        if (Dashboard._interval) clearInterval(Dashboard._interval);
    },

    showLogin() {
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('app-shell').classList.add('hidden');
    },

    showApp() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('app-shell').classList.remove('hidden');
        document.getElementById('top-username').textContent = this.username;
        if (!location.hash || location.hash === '#/') {
            location.hash = '#/dashboard';
        }
    },

    // ── Routing ──
    handleRoute() {
        const hash = location.hash || '#/dashboard';
        const page = hash.replace('#/', '') || 'dashboard';

        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        this.currentPage = page;
        this.loadPage(page);
    },

    loadPage(page) {
        // Clear any existing intervals
        if (Dashboard._interval) { clearInterval(Dashboard._interval); Dashboard._interval = null; }

        const main = document.getElementById('main-content');
        main.innerHTML = '<div class="page-loading"><div class="loading-spinner"></div></div>';

        switch (page) {
            case 'dashboard': Dashboard.render(main); break;
            case 'services': Services.render(main); break;
            case 'store': Store.render(main); break;
            case 'settings': Settings.render(main); break;
            default:
                main.innerHTML = '<div class="empty-state"><i class="fa-solid fa-compass"></i><p>Sayfa bulunamadı</p></div>';
        }
    },

    // ── Sidebar ──
    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('open');
        document.getElementById('sidebar-overlay').classList.toggle('active');
    },

    closeSidebar() {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebar-overlay').classList.remove('active');
    },

    // ── Modal ──
    openModal(title, bodyHtml) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = bodyHtml;
        document.getElementById('modal-overlay').classList.remove('hidden');
    },

    closeModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    },

    // ── Toast ──
    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    // ── API Helper ──
    async api(url, options = {}) {
        try {
            if (options.body && typeof options.body === 'object') {
                options.headers = { 'Content-Type': 'application/json', ...options.headers };
                options.body = JSON.stringify(options.body);
            }
            const res = await fetch(url, options);
            return await res.json();
        } catch (e) {
            return { ok: false, error: 'Bağlantı hatası' };
        }
    },
};

// ── Helpers ──
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatUptime(seconds) {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}g ${h}s ${m}dk`;
    if (h > 0) return `${h}s ${m}dk`;
    return `${m}dk`;
}

function formatSpeed(bytesPerSec) {
    if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s';
    if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s';
    return (bytesPerSec / (1024 * 1024)).toFixed(1) + ' MB/s';
}

// SVG gradient definitions (added once to page)
function ensureSvgDefs() {
    if (document.getElementById('svg-gauge-defs')) return;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = 'svg-gauge-defs';
    svg.style.position = 'absolute';
    svg.style.width = '0';
    svg.style.height = '0';
    svg.innerHTML = `
        <defs>
            <linearGradient id="grad-cpu" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#00d4ff"/>
                <stop offset="100%" style="stop-color:#a855f7"/>
            </linearGradient>
            <linearGradient id="grad-ram" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#22c55e"/>
                <stop offset="100%" style="stop-color:#3b82f6"/>
            </linearGradient>
            <linearGradient id="grad-disk" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#f97316"/>
                <stop offset="100%" style="stop-color:#ef4444"/>
            </linearGradient>
            <linearGradient id="grad-net" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#a855f7"/>
                <stop offset="100%" style="stop-color:#ec4899"/>
            </linearGradient>
        </defs>
    `;
    document.body.appendChild(svg);
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    ensureSvgDefs();
    App.init();
});
