/* ===== Installer Page ===== */

const Installer = {
    _apps: [],

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header">
                    <h2><i class="fa-solid fa-download" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Uygulama Yükleyici</h2>
                    <p>apps.txt dosyasındaki uygulamaları kurun</p>
                </div>
                <div id="apps-list" class="grid-1">
                    <div class="page-loading"><div class="loading-spinner"></div></div>
                </div>
            </div>
        `;
        await this.fetchApps();
    },

    async fetchApps() {
        const data = await App.api('/api/installer/apps');
        this._apps = Array.isArray(data) ? data : [];
        this._renderList();
    },

    _renderList() {
        const el = document.getElementById('apps-list');
        if (!el) return;

        if (this._apps.length === 0) {
            el.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-box-open"></i>
                    <p>apps.txt dosyasında uygulama bulunamadı</p>
                    <p style="font-size:0.8rem;margin-top:8px;color:var(--text-muted);">
                        apps.txt dosyasını düzenleyerek uygulama ekleyin
                    </p>
                </div>
            `;
            return;
        }

        const icons = ['fa-solid fa-globe', 'fa-brands fa-node-js', 'fa-solid fa-database', 'fa-brands fa-python',
                        'fa-solid fa-code', 'fa-solid fa-box', 'fa-solid fa-rocket'];

        el.innerHTML = this._apps.map((app, i) => `
            <div class="card app-card slide-up" style="animation-delay:${i * 0.05}s">
                <div class="app-icon">
                    <i class="${icons[i % icons.length]}"></i>
                </div>
                <div class="app-info">
                    <div class="app-name">${app.name}</div>
                    <div class="app-version">v${app.version}</div>
                </div>
                <button class="btn-install" onclick="Installer.install('${app.name.replace(/'/g, "\\'")}')">
                    <i class="fa-solid fa-download"></i> Kur
                </button>
            </div>
        `).join('');
    },

    async install(name) {
        const data = await App.api(`/api/installer/install/${encodeURIComponent(name)}`, { method: 'POST' });

        if (!data.ok) {
            App.toast(data.error || 'Kurulum başlatılamadı', 'error');
            return;
        }

        // Open ttyd in modal
        const app = data.app;
        const ttydUrl = data.ttyd_url;

        const html = `
            <div style="margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <span style="font-weight:600;font-size:1rem;">${app.name}</span>
                    <span style="color:var(--text-secondary);font-size:0.85rem;">v${app.version}</span>
                </div>
                <div style="padding:10px 14px;background:var(--bg-input);border:1px solid var(--border-color);border-radius:var(--radius-sm);font-family:'Courier New',monospace;font-size:0.8rem;color:var(--accent-green);margin-bottom:12px;word-break:break-all;">
                    $ ${app.command}
                </div>
                <p style="color:var(--text-secondary);font-size:0.82rem;">
                    <i class="fa-solid fa-info-circle"></i>
                    Kurulum komutu ttyd terminalinde çalıştırılacak. Aşağıdaki terminalde işlemi izleyebilirsiniz.
                </p>
            </div>
            <iframe src="${ttydUrl}" class="ttyd-frame" id="install-ttyd-frame"></iframe>
        `;

        App.openModal(`${app.name} Kurulumu`, html);
    },
};
