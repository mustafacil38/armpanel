/* ===== Installer Page ===== */

const Installer = {
    _apps: [],
    _allApps: [],

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                    <div>
                        <h2><i class="fa-solid fa-download" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Uygulama Mağazası</h2>
                        <p>Mağazadan tercih ettiğiniz uygulamaları kurun</p>
                    </div>
                    <div class="search-wrapper" style="position:relative; flex:1; max-width:350px; min-width:200px;">
                        <i class="fa-solid fa-magnifying-glass" style="position:absolute; left:15px; top:50%; transform:translateY(-50%); color:var(--text-muted); font-size:0.9rem;"></i>
                        <input type="text" id="app-search" class="form-control" placeholder="Uygulama ara..." 
                            style="padding-left:42px; border-radius:10px; background:var(--bg-input); border:1px solid var(--border-color); width:100%; transition:border-color 0.2s;"
                            oninput="Installer.filterApps(this.value)">
                    </div>
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
        this._allApps = Array.isArray(data) ? data : [];
        this._apps = [...this._allApps];
        this._renderList();
    },

    filterApps(query) {
        const q = query.toLowerCase().trim();
        if (!q) {
            this._apps = [...this._allApps];
        } else {
            this._apps = this._allApps.filter(app => 
                app.name.toLowerCase().includes(q) || 
                (app.description && app.description.toLowerCase().includes(q)) ||
                (app.category && app.category.toLowerCase().includes(q))
            );
        }
        this._renderList();
    },

    _renderList() {
        const el = document.getElementById('apps-list');
        if (!el) return;

        if (this._apps.length === 0) {
            el.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-box-open"></i>
                    <p>Uygulama mağazası listesi yüklenemedi</p>
                    <p style="font-size:0.8rem;margin-top:8px;color:var(--text-muted);">
                        Lütfen internet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.
                    </p>
                </div>
            `;
            return;
        }

        const icons = ['fa-solid fa-globe', 'fa-brands fa-node-js', 'fa-solid fa-database', 'fa-brands fa-python',
            'fa-solid fa-code', 'fa-solid fa-box', 'fa-solid fa-rocket'];

        el.innerHTML = this._apps.map((app, i) => `
            <div class="card app-card slide-up" style="animation-delay:${i * 0.05}s; padding: 20px;">
                <div style="display:flex; gap:20px; align-items:flex-start;">
                    <div class="app-icon" style="flex-shrink:0; width:50px; height:50px; display:flex; align-items:center; justify-content:center; background:var(--bg-input); border-radius:12px; font-size:1.5rem; color:var(--accent-blue);">
                        <i class="${icons[i % icons.length]}"></i>
                    </div>
                    <div class="app-info" style="flex:1;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
                            <div class="app-name" style="font-weight:600; font-size:1.1rem; color:var(--text-primary);">${app.name}</div>
                            <span class="badge-category" style="font-size:0.7rem; background:rgba(0, 212, 255, 0.1); color:#00d4ff; padding:3px 10px; border-radius:20px; border:1px solid rgba(0, 212, 255, 0.2); font-weight:500;">${app.category}</span>
                        </div>
                        <div class="app-version" style="font-size:0.8rem; color:var(--text-muted); margin-bottom:10px;">Versiyon: <span style="color:var(--text-secondary)">v${app.version}</span></div>
                        <div class="app-description" style="font-size:0.9rem; line-height:1.5; color:var(--text-secondary); margin-bottom:15px; opacity:0.85;">${app.description}</div>
                        <button class="btn-install" onclick="Installer.install('${app.name.replace(/'/g, "\\'")}')" style="background:var(--gradient-brand); color:white; border:none; padding:8px 20px; border-radius:8px; cursor:pointer; font-weight:500; display:flex; align-items:center; gap:8px; width:fit-content; transition:transform 0.2s;">
                            <i class="fa-solid fa-download"></i> Hemen Kur
                        </button>
                    </div>
                </div>
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
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:15px; flex-wrap:wrap; gap:10px;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span style="font-weight:600;font-size:1.1rem;color:var(--text-primary);">${app.name}</span>
                        <span style="color:var(--text-secondary);font-size:0.85rem;">v${app.version}</span>
                    </div>
                    <button class="btn-primary" onclick="Installer.sendToTerminal('${app.command.replace(/'/g, "\\'")}')" 
                        style="padding:8px 18px; font-size:0.9rem; background:var(--gradient-brand); border:none; border-radius:8px; cursor:pointer; color:white; font-weight:600; display:flex; align-items:center; gap:8px; box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);">
                        <i class="fa-solid fa-play"></i> Kurulumu Başlat
                    </button>
                </div>
                <div class="install-cmd-box" style="position:relative;padding:12px 16px;background:var(--bg-input);border:1px solid var(--border-color);border-radius:10px;font-family:'Courier New',monospace;font-size:0.85rem;color:var(--accent-green);margin-bottom:15px;padding-right:50px;">
                    <div id="install-cmd-text" style="word-break:break-all;">${app.command}</div>
                    <button class="btn-copy-cmd" onclick="Installer.copyCommand()" 
                        style="position:absolute;right:10px;top:50%;transform:translateY(-50%);background:transparent;border:none;color:var(--text-secondary);cursor:pointer;padding:8px;transition:color 0.2s;">
                        <i class="fa-regular fa-copy"></i>
                    </button>
                </div>
                <p style="color:var(--text-secondary);font-size:0.85rem; background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; border-left:4px solid var(--accent-blue);">
                    <i class="fa-solid fa-circle-info" style="color:var(--accent-blue); margin-right:5px;"></i>
                    <b>Kurulumu Başlat</b> butonu komutu terminale anında iletir. İsterseniz komutu kopyalayıp manuel olarak da yapıştırabilirsiniz.
                </p>
            </div>
            <iframe src="${ttydUrl}" class="ttyd-frame" id="install-ttyd-frame" style="border:1px solid var(--border-color); border-radius:12px; height:400px; width:100%;"></iframe>
        `;

        App.openModal(`${app.name} Kurulumu`, html);
    },

    async sendToTerminal(command) {
        App.toast('Komut terminale gönderiliyor...', 'info');
        const res = await App.api('/api/installer/send-command', {
            method: 'POST',
            body: { command }
        });

        if (res.ok) {
            App.toast('Kurulum başlatıldı!', 'success');
        } else {
            App.toast(res.error || 'Komut gönderilemedi', 'error');
        }
    },

    copyCommand() {
        const cmd = document.getElementById('install-cmd-text').innerText;
        navigator.clipboard.writeText(cmd).then(() => {
            const btn = document.querySelector('.btn-copy-cmd i');
            btn.className = 'fa-solid fa-check';
            btn.style.color = 'var(--accent-green)';
            App.toast('Komut kopyalandı', 'success');
            setTimeout(() => {
                btn.className = 'fa-regular fa-copy';
                btn.style.color = '';
            }, 2000);
        });
    }
};
