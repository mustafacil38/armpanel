/* ===== Installer Page - Native App Store ===== */

const Installer = {
    _apps: [],
    _allApps: [],
    _installed: [],

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px; margin-bottom:20px;">
                    <div>
                        <h2><i class="fa-solid fa-store" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Uygulama Mağazası</h2>
                        <p>CasaOS AppStore'dan uygulama kurun (native)</p>
                    </div>
                    <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                        <div class="search-wrapper" style="position:relative; flex:1; max-width:300px; min-width:200px;">
                            <i class="fa-solid fa-magnifying-glass" style="position:absolute; left:15px; top:50%; transform:translateY(-50%); color:var(--text-muted); font-size:0.9rem;"></i>
                            <input type="text" id="app-search" class="form-control" placeholder="Uygulama ara..." 
                                style="padding-left:42px; border-radius:10px; background:var(--bg-input); border:1px solid var(--border-color); width:100%;"
                                oninput="Installer.filterApps(this.value)">
                        </div>
                        <button onclick="Installer.refreshApps()" title="Mağazayı yenile" style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:10px; padding:10px 14px; cursor:pointer; color:var(--text-secondary);">
                            <i class="fa-solid fa-arrows-rotate"></i>
                        </button>
                    </div>
                </div>

                <div style="display:flex; gap:8px; margin-bottom:20px;">
                    <button id="tab-store" class="installer-tab active" onclick="Installer.switchTab('store')" style="padding:8px 20px; border-radius:8px; border:1px solid var(--border-color); background:var(--bg-card); color:var(--text-secondary); cursor:pointer; font-weight:500; font-size:0.9rem;">
                        <i class="fa-solid fa-store"></i> Mağaza
                    </button>
                    <button id="tab-installed" class="installer-tab" onclick="Installer.switchTab('installed')" style="padding:8px 20px; border-radius:8px; border:1px solid var(--border-color); background:var(--bg-card); color:var(--text-secondary); cursor:pointer; font-weight:500; font-size:0.9rem;">
                        <i class="fa-solid fa-check-circle"></i> Kurulu
                    </button>
                </div>

                <div id="tab-content">
                    <div id="apps-list" class="grid-1">
                        <div class="page-loading"><div class="loading-spinner"></div></div>
                    </div>
                </div>
            </div>
        `;
        await this.fetchApps();
    },

    switchTab(tab) {
        document.querySelectorAll('.installer-tab').forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.add('active');
        if (tab === 'store') {
            this._renderList();
        } else {
            this.fetchInstalled();
        }
    },

    async refreshApps() {
        App.toast('Mağaza yenileniyor...', 'info');
        await App.api('/api/installer/refresh', { method: 'POST' });
        await this.fetchApps();
    },

    async fetchApps() {
        try {
            const data = await App.api('/api/installer/apps');
            this._allApps = Array.isArray(data) ? data : [];
            this._apps = [...this._allApps];
            this._renderList();
        } catch (e) {
            const el = document.getElementById('apps-list');
            if (el) {
                el.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-wifi"></i>
                        <p>Mağaza yüklenemedi</p>
                        <button onclick="Installer.fetchApps()" style="margin-top:12px;padding:8px 20px;border-radius:8px;background:var(--gradient-brand);color:white;border:none;cursor:pointer;">
                            <i class="fa-solid fa-arrows-rotate"></i> Tekrar Dene
                        </button>
                    </div>
                `;
            }
        }
    },

    async fetchInstalled() {
        const content = document.getElementById('tab-content');
        content.innerHTML = `<div class="page-loading"><div class="loading-spinner"></div></div>`;
        try {
            const data = await App.api('/api/installer/installed');
            this._installed = data.installed || [];
            this._renderInstalled();
        } catch (e) {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Kurulu uygulamalar alınamadı</p>
                </div>
            `;
        }
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
                    <p>Uygulama bulunamadı</p>
                </div>
            `;
            return;
        }

        el.innerHTML = `<div class="grid-2" style="gap:16px;">` + this._apps.map((app, i) => {
            const iconHtml = app.icon
                ? `<img src="${app.icon}" onerror="this.parentElement.innerHTML='<i class=\\'fa-solid fa-cube\\'></i>'" style="width:50px;height:50px;border-radius:12px;object-fit:cover;">`
                : `<i class="fa-solid fa-cube"></i>`;

            const nativeBadge = app.native_install
                ? `<span class="badge-category" style="font-size:0.65rem; background:rgba(34,197,94,0.1); color:#22c55e; padding:2px 8px; border-radius:16px; border:1px solid rgba(34,197,94,0.2); font-weight:500; white-space:nowrap;"><i class="fa-solid fa-bolt"></i> Native</span>`
                : `<span class="badge-category" style="font-size:0.65rem; background:rgba(100,130,200,0.1); color:#8892a8; padding:2px 8px; border-radius:16px; border:1px solid rgba(100,130,200,0.2); font-weight:500; white-space:nowrap;">Docker only</span>`;

            return `
            <div class="card app-card slide-up" style="animation-delay:${i * 0.03}s; padding:18px;">
                <div style="display:flex; gap:16px; align-items:flex-start;">
                    <div class="app-icon" style="flex-shrink:0; width:50px; height:50px; display:flex; align-items:center; justify-content:center; background:var(--bg-input); border-radius:12px; font-size:1.4rem; color:var(--accent-blue); overflow:hidden;">
                        ${iconHtml}
                    </div>
                    <div class="app-info" style="flex:1; min-width:0;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; flex-wrap:wrap; gap:6px;">
                            <div class="app-name" style="font-weight:600; font-size:1rem; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${app.name}</div>
                            <div style="display:flex; gap:4px;">
                                ${nativeBadge}
                                <span class="badge-category" style="font-size:0.65rem; background:rgba(0,212,255,0.1); color:#00d4ff; padding:2px 8px; border-radius:16px; border:1px solid rgba(0,212,255,0.2); font-weight:500; white-space:nowrap;">${app.category || 'Genel'}</span>
                            </div>
                        </div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:6px;">
                            ${app.port ? `Port: <span style="color:var(--accent-blue);">${app.port}</span>` : ''}
                        </div>
                        <div class="app-description" style="font-size:0.82rem; line-height:1.4; color:var(--text-secondary); margin-bottom:12px; opacity:0.8; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${app.description || 'Açıklama yok'}</div>
                        ${app.native_install
                            ? `<button class="btn-install" onclick="Installer.install('${app.id}')" style="background:var(--gradient-brand); color:white; border:none; padding:7px 16px; border-radius:8px; cursor:pointer; font-weight:500; font-size:0.85rem; display:flex; align-items:center; gap:6px; width:fit-content;">
                                   <i class="fa-solid fa-download"></i> Kur
                               </button>`
                            : `<span style="font-size:0.75rem; color:var(--text-muted);"><i class="fa-solid fa-info-circle"></i> Sadece Docker ile kurulabilir</span>`
                        }
                    </div>
                </div>
            </div>`;
        }).join('') + `</div>`;
    },

    _renderInstalled() {
        const content = document.getElementById('tab-content');
        if (!content) return;

        if (this._installed.length === 0) {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-box-open"></i>
                    <p>Henüz uygulama kurulmamış</p>
                    <p style="font-size:0.8rem;margin-top:8px;color:var(--text-muted);">Mağaza sekmesinden uygulama kurarak başlayın.</p>
                </div>
            `;
            return;
        }

        content.innerHTML = `<div class="grid-1" style="gap:12px;">` + this._installed.map(app => `
            <div class="card" style="padding:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="flex:1; min-width:0;">
                    <div style="font-weight:600; font-size:1rem; color:var(--text-primary);">${app.name}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
                        ${app.port ? `Port: ${app.port}` : ''}
                        ${app.actually_installed ? '<span style="color:var(--accent-green); margin-left:8px;"><i class="fa-solid fa-circle-check"></i> Çalışıyor</span>' : '<span style="color:var(--accent-red); margin-left:8px;"><i class="fa-solid fa-circle-xmark"></i> Durmuş</span>'}
                    </div>
                </div>
                <div style="display:flex; gap:6px;">
                    <button onclick="Installer.uninstall('${app.app_id}')" title="Kaldır" style="background:rgba(255,0,0,0.1); border:1px solid rgba(255,0,0,0.3); border-radius:8px; padding:6px 12px; cursor:pointer; color:#ff4444;">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                    ${app.port ? `<a href="http://${window.location.hostname}:${app.port}" target="_blank" style="background:rgba(0,212,255,0.1); border:1px solid rgba(0,212,255,0.3); border-radius:8px; padding:6px 12px; cursor:pointer; color:var(--accent-blue); display:flex; align-items:center; gap:4px; text-decoration:none;">
                        <i class="fa-solid fa-external-link-alt"></i> Aç
                    </a>` : ''}
                </div>
            </div>
        `).join('') + `</div>`;
    },

    async install(appId) {
        const app = this._allApps.find(a => a.id === appId);
        if (!app) return;

        const html = `
            <div style="margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                    ${app.icon ? `<img src="${app.icon}" style="width:48px;height:48px;border-radius:12px;object-fit:cover;" onerror="this.style.display='none'">` : ''}
                    <div>
                        <div style="font-weight:600; font-size:1.1rem; color:var(--text-primary);">${app.name}</div>
                        <div style="font-size:0.8rem; color:var(--accent-green);"><i class="fa-solid fa-bolt"></i> Native kurulum</div>
                    </div>
                </div>
                <div id="install-progress" style="display:none;">
                    <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:10px; padding:16px; font-family:'Courier New',monospace; font-size:0.82rem; color:var(--accent-green); max-height:250px; overflow-y:auto; white-space:pre-wrap; word-break:break-all;" id="install-log"></div>
                </div>
                <div id="install-success" style="display:none; margin-top:12px; padding:12px; background:rgba(0,212,255,0.08); border:1px solid rgba(0,212,255,0.2); border-radius:10px;">
                    <div style="color:var(--accent-green); font-weight:600; margin-bottom:6px;"><i class="fa-solid fa-check-circle"></i> Kurulum başarılı!</div>
                    <div id="install-url" style="font-size:0.9rem; color:var(--text-secondary);"></div>
                </div>
                <div style="margin-top:16px;">
                    <button id="install-btn" onclick="Installer.doInstall('${appId}')" style="padding:10px 24px; background:var(--gradient-brand); border:none; border-radius:10px; cursor:pointer; color:white; font-weight:600; font-size:0.95rem; display:flex; align-items:center; gap:8px;">
                        <i class="fa-solid fa-download"></i> Kur
                    </button>
                </div>
                <p style="color:var(--text-muted); font-size:0.78rem; margin-top:10px;">
                    <i class="fa-solid fa-circle-info"></i>
                    Native kurulum apt/pip/curl ile yapılır. Birkaç dakika sürebilir.
                </p>
            </div>
        `;

        App.openModal(`${app.name} Kurulumu`, html);
    },

    async doInstall(appId) {
        const btn = document.getElementById('install-btn');
        const progress = document.getElementById('install-progress');
        const log = document.getElementById('install-log');
        const success = document.getElementById('install-success');

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kuruluyor...';
            btn.style.opacity = '0.6';
        }
        if (progress) progress.style.display = 'block';

        if (log) log.textContent = 'Kurulum başlatılıyor...\n\n';

        try {
            const data = await App.api('/api/installer/install', {
                method: 'POST',
                body: { app_id: appId }
            });

            if (data.ok) {
                if (log) {
                    log.textContent += '\n✓ Kurulum tamamlandı!\n';
                    if (data.output) {
                        data.output.forEach(step => {
                            log.textContent += `\n[${step.ok ? 'OK' : 'FAIL'}] ${step.cmd}\n`;
                            if (step.output) log.textContent += step.output.slice(-200) + '\n';
                        });
                    }
                }
                if (success) {
                    success.style.display = 'block';
                    const urlDiv = document.getElementById('install-url');
                    if (urlDiv && data.port) {
                        const ip = data.local_ip || 'localhost';
                        urlDiv.innerHTML = `Erişim: <a href="http://${ip}:${data.port}" target="_blank" style="color:var(--accent-blue);">http://${ip}:${data.port}</a>`;
                    }
                }
                App.toast(`${data.name || appId} başarıyla kuruldu!`, 'success');
            } else {
                if (log) log.textContent += `\n✗ Hata: ${data.error}\n`;
                if (data.output) {
                    data.output.forEach(step => {
                        if (log) log.textContent += `\n[${step.ok ? 'OK' : 'FAIL'}] ${step.cmd}\n${(step.output || '').slice(-200)}\n`;
                    });
                }
                App.toast(data.error || 'Kurulum başarısız', 'error');
            }
        } catch (e) {
            if (log) log.textContent += `\n✗ Bağlantı hatası: ${e.message}\n`;
            App.toast('Kurulum sırasında hata oluştu', 'error');
        }

        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-download"></i> Kur';
            btn.style.opacity = '1';
        }
    },

    async uninstall(appId) {
        if (!confirm('Bu uygulamayı kaldırmak istediğinize emin misiniz?')) return;

        App.toast('Uygulama kaldırılıyor...', 'info');
        const res = await App.api('/api/installer/uninstall', {
            method: 'POST',
            body: { app_id: appId }
        });

        if (res.ok) {
            App.toast('Uygulama kaldırıldı', 'success');
            this.fetchInstalled();
        } else {
            App.toast(res.error || 'Kaldırma başarısız', 'error');
        }
    }
};
