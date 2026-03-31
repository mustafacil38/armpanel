/* ===== Services Page ===== */

const Services = {
    _services: [],

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header">
                    <h2><i class="fa-solid fa-cubes" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Servis Yönetimi</h2>
                    <p>Sistem servislerini izleyin ve yönetin</p>
                </div>
                <div id="services-list" class="grid-1">
                    <div class="page-loading"><div class="loading-spinner"></div></div>
                </div>
            </div>
        `;
        await this.fetchServices();
    },

    async fetchServices() {
        const data = await App.api('/api/services');
        this._services = Array.isArray(data) ? data : [];
        this._renderList();
    },

    _getIconClass(name) {
        const n = name.toLowerCase();
        if (n.includes('nginx')) return 'nginx';
        if (n.includes('ttyd')) return 'ttyd';
        if (n.includes('php')) return 'php';
        if (n.includes('file')) return 'filebrowser';
        return 'default';
    },

    _renderList() {
        const el = document.getElementById('services-list');
        if (!el) return;

        if (this._services.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fa-solid fa-cubes"></i><p>Henüz servis bulunamadı</p></div>';
            return;
        }

        el.innerHTML = this._services.map((svc, i) => `
            <div class="card service-card slide-up" style="animation-delay:${i * 0.05}s">
                <div class="svc-icon ${this._getIconClass(svc.name)}">
                    <i class="${svc.icon}"></i>
                </div>
                <div class="svc-info">
                    <div class="svc-name">${svc.name}</div>
                    <div class="svc-desc">${svc.description} — Port: ${svc.default_port}</div>
                    <div class="svc-actions">
                        ${svc.is_running
                            ? `<button class="btn-sm btn-stop" onclick="Services.action(${svc.id},'stop')"><i class="fa-solid fa-stop"></i> Durdur</button>
                               <button class="btn-sm btn-restart" onclick="Services.action(${svc.id},'restart')"><i class="fa-solid fa-rotate"></i> Yeniden</button>`
                            : `<button class="btn-sm btn-start" onclick="Services.action(${svc.id},'start')"><i class="fa-solid fa-play"></i> Başlat</button>`
                        }
                        ${svc.config_files ? `<button class="btn-sm btn-config" onclick="Services.openConfig(${svc.id})"><i class="fa-solid fa-file-code"></i> Config</button>` : ''}
                        <button class="btn-sm btn-settings" onclick="Services.openSettings(${svc.id})"><i class="fa-solid fa-gear"></i> Ayarlar</button>
                        
                        <!-- Auto Start Toggle -->
                        <div class="auto-start-control" style="margin-left:auto;" title="Açılışta otomatik başlat">
                            <label class="switch">
                                <input type="checkbox" ${svc.is_autostart ? 'checked' : ''} 
                                    onchange="Services.toggleAutoStart(${svc.id}, this)">
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
                <div class="svc-status ${svc.is_running ? 'running' : 'stopped'}">
                    <span class="dot"></span>
                    ${svc.is_running ? 'Çalışıyor' : 'Durduruldu'}
                </div>
            </div>
        `).join('');
    },

    async action(id, act) {
        App.toast(`İşlem yapılıyor...`, 'info');
        const data = await App.api(`/api/services/${id}/${act}`, { method: 'POST' });
        if (data.ok) {
            App.toast(data.message, 'success');
            setTimeout(() => this.fetchServices(), 1500);
        } else {
            App.toast(data.error || 'Hata oluştu', 'error');
        }
    },

    // ── Config Editor Modal ──
    async openConfig(id) {
        const data = await App.api(`/api/services/${id}/config`);
        if (!data.ok) {
            App.toast(data.error || 'Config yüklenemedi', 'error');
            return;
        }

        const configs = data.configs || {};
        const files = Object.keys(configs);

        if (files.length === 0) {
            App.toast('Bu servis için config dosyası bulunamadı', 'info');
            return;
        }

        let html = `
            <div class="config-editor-wrap">
                <div class="config-tabs" id="config-tabs">
                    ${files.map((f, i) => `
                        <button class="config-tab ${i === 0 ? 'active' : ''}"
                            onclick="Services._switchConfigTab(this, '${f.replace(/'/g, "\\'")}')"
                            data-file="${f}">${f.split('/').pop()}</button>
                    `).join('')}
                </div>
                <textarea class="form-control" id="config-editor" rows="20">${this._escHtml(configs[files[0]])}</textarea>
                <input type="hidden" id="config-current-file" value="${files[0]}">
                <input type="hidden" id="config-service-id" value="${id}">
                <div class="config-actions">
                    <button class="btn-primary" onclick="Services.saveConfig()">
                        <i class="fa-solid fa-floppy-disk"></i> Kaydet
                    </button>
                    <button class="btn-secondary" onclick="Services.saveAndRestart()">
                        <i class="fa-solid fa-rotate"></i> Kaydet & Yeniden Başlat
                    </button>
                </div>
            </div>
        `;

        // Store configs data
        this._configData = configs;
        App.openModal(`${data.service_name} — Yapılandırma`, html);
    },

    _configData: {},

    _switchConfigTab(btn, file) {
        document.querySelectorAll('#config-tabs .config-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');

        // Save current content
        const editor = document.getElementById('config-editor');
        const curFile = document.getElementById('config-current-file').value;
        this._configData[curFile] = editor.value;

        // Load new
        editor.value = this._configData[file] || '';
        document.getElementById('config-current-file').value = file;
    },

    async saveConfig() {
        const file = document.getElementById('config-current-file').value;
        const content = document.getElementById('config-editor').value;
        const sid = document.getElementById('config-service-id').value;

        const data = await App.api(`/api/services/${sid}/config`, {
            method: 'POST',
            body: { file_path: file, content },
        });

        if (data.ok) {
            App.toast('Yapılandırma kaydedildi', 'success');
        } else {
            App.toast(data.error || 'Kaydetme hatası', 'error');
        }
    },

    async saveAndRestart() {
        await this.saveConfig();
        const sid = document.getElementById('config-service-id').value;
        await this.action(parseInt(sid), 'restart');
    },

    // ── Settings Modal ──
    async openSettings(id) {
        const data = await App.api(`/api/services/${id}/settings`);
        if (!data.ok) {
            App.toast('Ayarlar yüklenemedi', 'error');
            return;
        }

        const svc = data.service;
        const name = svc.name.toLowerCase();
        let extraHtml = '';

        // Service-specific settings
        if (name.includes('nginx')) {
            extraHtml = this._nginxSettings(svc);
        } else if (name.includes('ttyd')) {
            extraHtml = this._ttydSettings(svc);
        } else if (name.includes('php')) {
            extraHtml = this._phpSettings(svc);
        } else if (name.includes('file')) {
            extraHtml = this._fileBrowserSettings(svc);
        }

        const html = `
            <div id="svc-settings-form" data-id="${svc.id}">
                <div class="setting-section-title"><i class="fa-solid fa-circle-info"></i> Genel Ayarlar</div>
                <div class="form-group">
                    <label>Açıklama</label>
                    <input type="text" class="form-control" id="svc-desc" value="${this._escAttr(svc.description)}">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Varsayılan Port</label>
                        <input type="text" class="form-control" id="svc-port" value="${svc.default_port}"
                            oninput="Services._syncCommands(this.value)">
                    </div>
                </div>
                <div class="form-group">
                    <label>Başlatma Komutu</label>
                    <input type="text" class="form-control" id="svc-cmd-start" value="${this._escAttr(svc.command_start)}">
                </div>
                <div class="form-group">
                    <label>Durdurma Komutu</label>
                    <input type="text" class="form-control" id="svc-cmd-stop" value="${this._escAttr(svc.command_stop)}">
                </div>
                <div class="form-group">
                    <label>Yeniden Başlatma Komutu</label>
                    <input type="text" class="form-control" id="svc-cmd-restart" value="${this._escAttr(svc.command_restart)}">
                </div>
                <div class="form-group">
                    <label>Config Dosyaları (virgülle ayırın)</label>
                    <input type="text" class="form-control" id="svc-configs" value="${this._escAttr(svc.config_files)}">
                </div>

                ${extraHtml}

                <div style="margin-top:20px;">
                    <button class="btn-primary" onclick="Services.saveSettings()">
                        <i class="fa-solid fa-check"></i> Kaydet
                    </button>
                </div>
            </div>
        `;

        App.openModal(`${svc.name} — Ayarlar`, html);
    },

    _nginxSettings(svc) {
        return `
            <div class="setting-section-title"><i class="fa-solid fa-server"></i> Nginx Ayarları</div>
            <div class="form-group">
                <label>Dinleme Portu</label>
                <input type="number" class="form-control" id="nginx-listen-port" 
                    value="${svc.default_port}" placeholder="${svc.default_port}"
                    oninput="document.getElementById('svc-port').value = this.value; Services._syncCommands(this.value)">
            </div>
            <div class="form-group">
                <label>Server Name (Domain)</label>
                <input type="text" class="form-control" id="nginx-server-name" value="${this._escAttr(svc.server_name || 'localhost')}">
            </div>
            <div class="form-group">
                <label>Root Dizin</label>
                <input type="text" class="form-control" id="nginx-root-dir" value="${this._escAttr(svc.root_dir || '/var/www/html')}">
            </div>
            <div class="form-group">
                <label>Worker Processes</label>
                <input type="text" class="form-control" id="nginx-workers" value="${this._escAttr(svc.worker_processes || 'auto')}">
            </div>
            <div class="form-group">
                <label>Client Max Body Size</label>
                <input type="text" class="form-control" id="nginx-client-body" value="${this._escAttr(svc.client_max_body_size || '50M')}">
            </div>
        `;
    },

    _ttydSettings(svc) {
        return `
            <div class="setting-section-title"><i class="fa-solid fa-terminal"></i> ttyd Ayarları</div>
            <div class="form-group">
                <label>Dinleme Portu</label>
                <input type="number" class="form-control" id="ttyd-port" value="${svc.default_port}" placeholder="1570">
            </div>
            <div class="form-group">
                <label>Shell Komutu</label>
                <input type="text" class="form-control" value="bash" placeholder="bash">
            </div>
            <div class="form-group">
                <label>Yazılabilir Mod (-W)</label>
                <select class="form-control">
                    <option value="1" selected>Evet</option>
                    <option value="0">Hayır</option>
                </select>
            </div>
            <div class="form-group">
                <label>Kimlik Doğrulama</label>
                <select class="form-control" id="ttyd-auth">
                    <option value="0" selected>Kapalı</option>
                    <option value="1">Açık</option>
                </select>
            </div>
            <div class="form-group" id="ttyd-cred-group" style="display:none;">
                <label>Kullanıcı Adı:Şifre</label>
                <input type="text" class="form-control" placeholder="admin:password">
            </div>
        `;
    },

    _phpSettings(svc) {
        return `
            <div class="setting-section-title"><i class="fa-brands fa-php"></i> PHP-FPM Ayarları</div>
            <div class="form-group">
                <label>Dinleme Portu / Soket</label>
                <input type="text" class="form-control" id="php-listen" 
                    value="${svc.default_port}" placeholder="9000"
                    oninput="document.getElementById('svc-port').value = this.value">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>upload_max_filesize</label>
                    <input type="text" class="form-control" id="php-upload-limit" value="${svc.upload_max_filesize || '2M'}">
                </div>
                <div class="form-group">
                    <label>post_max_size</label>
                    <input type="text" class="form-control" id="php-post-limit" value="${svc.post_max_size || '8M'}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>memory_limit</label>
                    <input type="text" class="form-control" id="php-mem-limit" value="${svc.memory_limit || '128M'}">
                </div>
                <div class="form-group">
                    <label>max_execution_time</label>
                    <input type="number" class="form-control" id="php-exec-time" value="${svc.max_execution_time || '30'}">
                </div>
            </div>
            <div class="setting-section-title"><i class="fa-solid fa-water"></i> FPM Havuz Ayarları</div>
            <div class="form-row">
                <div class="form-group">
                    <label>pm (Process Manager)</label>
                    <input type="text" class="form-control" id="php-pm" value="${svc.pm || 'dynamic'}">
                </div>
                <div class="form-group">
                    <label>pm.max_children</label>
                    <input type="number" class="form-control" id="php-pm-max" value="${svc['pm.max_children'] || '5'}">
                </div>
            </div>
        `;
    },

    _fileBrowserSettings(svc) {
        return `
            <div class="setting-section-title"><i class="fa-solid fa-folder-open"></i> File Browser Ayarları</div>
            <div class="form-group">
                <label>Dinleme Portu</label>
                <input type="number" class="form-control" value="${svc.default_port}" placeholder="8080">
            </div>
            <div class="form-group">
                <label>Root Dizin</label>
                <input type="text" class="form-control" value="/" placeholder="/">
            </div>
            <div class="form-group">
                <label>Dinleme Adresi</label>
                <input type="text" class="form-control" value="0.0.0.0" placeholder="0.0.0.0">
            </div>
            <div class="form-group">
                <label>Veritabanı Dosyası</label>
                <input type="text" class="form-control" value="/etc/filebrowser/filebrowser.db" placeholder="/etc/filebrowser/filebrowser.db">
            </div>
        `;
    },

    _addDomain() {
        const input = document.getElementById('new-domain');
        const val = input.value.trim();
        if (!val) return;
        const list = document.getElementById('domain-list');
        const item = document.createElement('div');
        item.className = 'domain-item';
        item.innerHTML = `
            <span class="domain-name">${val}</span>
            <button class="btn-remove" onclick="this.parentElement.remove()"><i class="fa-solid fa-xmark"></i></button>
        `;
        list.appendChild(item);
        input.value = '';
    },

    async saveSettings() {
        const form = document.getElementById('svc-settings-form');
        const id = form.dataset.id;
        
        // Ana ayarlar (Her zaman var olanlar)
        const data = {
            description: document.getElementById('svc-desc')?.value || '',
            default_port: document.getElementById('svc-port')?.value || '',
            command_start: document.getElementById('svc-cmd-start')?.value || '',
            command_stop: document.getElementById('svc-cmd-stop')?.value || '',
            command_restart: document.getElementById('svc-cmd-restart')?.value || '',
            config_files: document.getElementById('svc-configs')?.value || '',
        };

        // Servis spesifik ayarlar (Sadece ekranda varsa ekle)
        const nginxServerName = document.getElementById('nginx-server-name');
        if (nginxServerName) {
            data.server_name = nginxServerName.value;
            data.root_dir = document.getElementById('nginx-root-dir')?.value || '';
            data.worker_processes = document.getElementById('nginx-workers')?.value || '';
            data.client_max_body_size = document.getElementById('nginx-client-body')?.value || '';
        }

        const phpUpload = document.getElementById('php-upload-limit');
        if (phpUpload) {
            data.upload_max_filesize = phpUpload.value;
            data.post_max_size = document.getElementById('php-post-limit')?.value || '';
            data.memory_limit = document.getElementById('php-mem-limit')?.value || '';
            data.max_execution_time = document.getElementById('php-exec-time')?.value || '';
            data.pm = document.getElementById('php-pm')?.value || '';
            data['pm.max_children'] = document.getElementById('php-pm-max')?.value || '';
        }

        const result = await App.api(`/api/services/${id}/settings`, {
            method: 'POST',
            body: data,
        });

        if (result.ok) {
            App.toast('Ayarlar kaydedildi', 'success');
            App.closeModal();
            this.fetchServices();
        } else {
            App.toast(result.error || 'Kaydetme hatası', 'error');
        }
    },

    _syncCommands(newPort) {
        const start = document.getElementById('svc-cmd-start');
        const restart = document.getElementById('svc-cmd-restart');
        const stop = document.getElementById('svc-cmd-stop');
        
        // Update -p port in commands
        if (start) start.value = start.value.replace(/(-p\s+)\d+/, `$1${newPort}`);
        if (restart) restart.value = restart.value.replace(/(-p\s+)\d+/, `$1${newPort}`);
        // Also update service-specific ports if they exist
        const nginxPort = document.getElementById('nginx-listen-port');
        if (nginxPort) nginxPort.value = newPort;
        const phpListen = document.getElementById('php-listen');
        if (phpListen) phpListen.value = newPort;
    },

    _escHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    },

    _escAttr(str) {
        return (str || '').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    async toggleAutoStart(sid, checkbox) {
        try {
            const res = await fetch(`/api/services/${sid}/autostart`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_autostart: checkbox.checked })
            });
            const data = await res.json();
            if (data.ok) {
                App.toast(data.message, 'success');
            } else {
                checkbox.checked = !checkbox.checked;
                App.toast(data.error || 'Hata oluştu', 'error');
            }
        } catch (e) {
            checkbox.checked = !checkbox.checked;
            App.toast('Bağlantı hatası', 'error');
        }
    }
};
