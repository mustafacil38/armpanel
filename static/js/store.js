const Store = {
    _apps: [],

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header">
                    <h2><i class="fa-solid fa-store" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Uygulama Mağazası</h2>
                    <p>Uygulamaları keşfedin, kurun ve kaldırın</p>
                </div>
                <div id="store-list" class="grid-2">
                    <div class="page-loading"><div class="loading-spinner"></div></div>
                </div>
            </div>
        `;
        await this.fetchApps();
    },

    async fetchApps() {
        const data = await App.api('/api/store');
        if (data.ok) {
            this._apps = data.apps || [];
            this._renderGrid();
        } else {
            const el = document.getElementById('store-list');
            if (el) el.innerHTML = `<div class="empty-state"><i class="fa-solid fa-cloud-arrow-down"></i><p>Mağaza yüklenemedi: ${data.error || 'Bilinmeyen hata'}</p></div>`;
        }
    },

    _renderGrid() {
        const el = document.getElementById('store-list');
        if (!el) return;

        if (this._apps.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fa-solid fa-store"></i><p>Henüz uygulama yok</p></div>';
            return;
        }

        el.innerHTML = this._apps.map((app, i) => `
            <div class="card store-card slide-up" style="animation-delay:${i * 0.05}s">
                <div class="store-icon">
                    <i class="${app.icon || 'fa-solid fa-cube'}"></i>
                </div>
                <div class="store-info">
                    <div class="store-name">${app.name}</div>
                    <div class="store-desc">${app.description || ''}</div>
                    <div class="store-port">Port: ${app.default_port || '-'}</div>
                </div>
                <div class="store-actions">
                    ${app.installed
                        ? `<button class="btn-sm btn-stop" onclick="Store.uninstall('${app.name}', event)"><i class="fa-solid fa-trash"></i> Kaldır</button>`
                        : `<button class="btn-sm btn-start" onclick="Store.install('${app.name}', event)"><i class="fa-solid fa-download"></i> Kur</button>`
                    }
                </div>
            </div>
        `).join('');
    },

    async install(name, e) {
        App.toast(`${name} kuruluyor...`, 'info');
        const btn = e.target.closest('button');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kuruluyor...';
        }

        const data = await App.api('/api/store/install', {
            method: 'POST',
            body: { name },
        });

        if (data.ok) {
            App.toast(data.message, 'success');
            await this.fetchApps();
        } else {
            App.toast(data.error || 'Kurulum başarısız', 'error');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-download"></i> Kur';
            }
        }
    },

    async uninstall(name, e) {
        if (!confirm(`${name} kaldırılacak. Emin misiniz?`)) return;

        App.toast(`${name} kaldırılıyor...`, 'info');
        const btn = e.target.closest('button');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaldırılıyor...';
        }

        const data = await App.api('/api/store/uninstall', {
            method: 'POST',
            body: { name },
        });

        if (data.ok) {
            App.toast(data.message, 'success');
            await this.fetchApps();
        } else {
            App.toast(data.error || 'Kaldırma başarısız', 'error');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-trash"></i> Kaldır';
            }
        }
    },
};
