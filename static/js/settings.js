/* ===== Settings Page ===== */

const Settings = {
    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header">
                    <h2><i class="fa-solid fa-gear" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Ayarlar</h2>
                    <p>Panel ve sistem ayarlarını yönetin</p>
                </div>

                <!-- User Settings -->
                <div class="settings-section">
                    <div class="card slide-up">
                        <div class="card-title"><i class="fa-solid fa-user-gear"></i> Kullanıcı Ayarları</div>
                        <div class="form-group">
                            <label>Kullanıcı Adı</label>
                            <input type="text" class="form-control" id="set-username" value="">
                        </div>
                        <div class="form-group">
                            <label>Yeni Şifre (boş bırakırsanız değişmez)</label>
                            <input type="password" class="form-control" id="set-password" placeholder="••••••••">
                        </div>
                        <div class="form-group">
                            <label>Yeni Şifre (Tekrar)</label>
                            <input type="password" class="form-control" id="set-password2" placeholder="••••••••">
                        </div>
                        <button class="btn-primary" onclick="Settings.saveUser()">
                            <i class="fa-solid fa-check"></i> Kaydet
                        </button>
                    </div>
                </div>

                <!-- Cloudflare Tunnel -->
                <div class="settings-section">
                    <div class="card slide-up" style="animation-delay:0.05s">
                        <div class="card-title"><i class="fa-solid fa-cloud"></i> Cloudflare Tunnel</div>
                        <div id="cf-status" class="cf-status stopped">
                            <i class="fa-solid fa-circle-xmark"></i> Kontrol ediliyor...
                        </div>
                        <div class="form-group">
                            <label>Tunnel Token</label>
                            <input type="text" class="form-control" id="cf-token" placeholder="eyJhIjoiN...">
                        </div>
                        <div class="cf-actions">
                            <button class="btn-primary" onclick="Settings.saveCfToken()">
                                <i class="fa-solid fa-floppy-disk"></i> Token Kaydet
                            </button>
                            <button class="btn-secondary" id="cf-start-btn" onclick="Settings.cfStart()">
                                <i class="fa-solid fa-play"></i> Başlat
                            </button>
                            <button class="btn-danger" id="cf-stop-btn" onclick="Settings.cfStop()">
                                <i class="fa-solid fa-stop"></i> Durdur
                            </button>
                        </div>
                    </div>
                </div>

                <!-- GitHub Update -->
                <div class="settings-section">
                    <div class="card slide-up" style="animation-delay:0.1s">
                        <div class="card-title"><i class="fa-brands fa-github"></i> Proje Güncellemesi</div>
                        <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">
                            <i class="fa-solid fa-code-branch"></i>
                            <a href="https://github.com/mustafacil38/armpanel" target="_blank"
                               style="color:var(--accent-cyan);text-decoration:underline;">
                                mustafacil38/armpanel
                            </a> deposundan güncelleyin.
                        </p>
                        <button class="btn-primary" id="update-btn" onclick="Settings.githubUpdate()">
                            <i class="fa-solid fa-cloud-arrow-down"></i> Güncelle
                        </button>
                        <div id="update-output" class="update-output hidden"></div>
                    </div>
                </div>
            </div>
        `;

        await this.loadUser();
        await this.loadCloudflare();
    },

    async loadUser() {
        const data = await App.api('/api/settings/user');
        if (data.ok) {
            document.getElementById('set-username').value = data.username || '';
        }
    },

    async saveUser() {
        const username = document.getElementById('set-username').value.trim();
        const password = document.getElementById('set-password').value;
        const password2 = document.getElementById('set-password2').value;

        if (!username) {
            App.toast('Kullanıcı adı boş olamaz', 'error');
            return;
        }

        if (password && password !== password2) {
            App.toast('Şifreler eşleşmiyor', 'error');
            return;
        }

        const body = { username };
        if (password) body.password = password;

        const data = await App.api('/api/settings/user', { method: 'POST', body });
        if (data.ok) {
            App.toast('Kullanıcı bilgileri güncellendi', 'success');
            document.getElementById('top-username').textContent = username;
            document.getElementById('set-password').value = '';
            document.getElementById('set-password2').value = '';
        } else {
            App.toast(data.error || 'Kaydetme hatası', 'error');
        }
    },

    async loadCloudflare() {
        const data = await App.api('/api/settings/cloudflare');
        if (data.ok) {
            document.getElementById('cf-token').value = data.token || '';
            const statusEl = document.getElementById('cf-status');
            if (data.is_running) {
                statusEl.className = 'cf-status running';
                statusEl.innerHTML = '<i class="fa-solid fa-circle-check"></i> Tunnel Çalışıyor';
            } else {
                statusEl.className = 'cf-status stopped';
                statusEl.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Tunnel Durduruldu';
            }
        }
    },

    async saveCfToken() {
        const token = document.getElementById('cf-token').value.trim();
        const data = await App.api('/api/settings/cloudflare', {
            method: 'POST',
            body: { token },
        });
        if (data.ok) {
            App.toast('Cloudflare token kaydedildi', 'success');
        } else {
            App.toast(data.error || 'Kaydetme hatası', 'error');
        }
    },

    async cfStart() {
        const data = await App.api('/api/settings/cloudflare/start', { method: 'POST' });
        if (data.ok) {
            App.toast(data.message, 'success');
            setTimeout(() => this.loadCloudflare(), 2000);
        } else {
            App.toast(data.error || 'Başlatma hatası', 'error');
        }
    },

    async cfStop() {
        const data = await App.api('/api/settings/cloudflare/stop', { method: 'POST' });
        if (data.ok) {
            App.toast(data.message, 'success');
            setTimeout(() => this.loadCloudflare(), 1000);
        } else {
            App.toast(data.error || 'Durdurma hatası', 'error');
        }
    },

    async githubUpdate() {
        const btn = document.getElementById('update-btn');
        const output = document.getElementById('update-output');

        btn.disabled = true;
        btn.innerHTML = '<div class="loading-spinner"></div> Güncelleniyor...';
        output.classList.remove('hidden');
        output.textContent = 'Git pull işlemi başlatılıyor...\n';

        const data = await App.api('/api/settings/update', { method: 'POST' });

        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Güncelle';

        if (data.ok) {
            output.textContent = data.output || 'Güncelleme tamamlandı!';
            output.style.color = 'var(--accent-green)';
            App.toast('Proje güncellendi', 'success');
        } else {
            output.textContent = data.output || data.error || 'Güncelleme başarısız';
            output.style.color = 'var(--accent-red)';
            App.toast(data.error || 'Güncelleme başarısız', 'error');
        }
    },
};
