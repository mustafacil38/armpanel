/* ===== Dashboard Page ===== */

const Dashboard = {
    _interval: null,

    async render(container) {
        container.innerHTML = `
            <div class="fade-in">
                <div class="page-header">
                    <h2><i class="fa-solid fa-gauge-high" style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"></i> Kontrol Paneli</h2>
                    <p>Sistem kaynaklarını gerçek zamanlı izleyin</p>
                </div>

                <!-- Gauges -->
                <div class="grid-2" id="gauge-grid">
                    ${this._gaugeCard('cpu', 'CPU', 0, '--')}
                    ${this._gaugeCard('ram', 'RAM', 0, '--')}
                    ${this._gaugeCard('disk', 'Disk', 0, '--')}
                    <div class="card gauge-card slide-up" style="animation-delay:0.15s">
                        <div class="card-title">Uptime</div>
                        <div class="uptime-display">
                            <div class="uptime-value" id="dash-uptime">--</div>
                        </div>
                    </div>
                </div>

                <!-- Network -->
                <div class="card slide-up" style="margin-top:16px;animation-delay:0.2s">
                    <div class="card-title"><i class="fa-solid fa-network-wired"></i> Ağ Trafiği</div>
                    <div class="net-stats">
                        <div class="net-stat">
                            <div class="net-icon up"><i class="fa-solid fa-arrow-up"></i></div>
                            <div class="net-info">
                                <div class="net-speed" id="dash-net-up">0 B/s</div>
                                <div class="net-label">Upload</div>
                            </div>
                        </div>
                        <div class="net-stat">
                            <div class="net-icon down"><i class="fa-solid fa-arrow-down"></i></div>
                            <div class="net-info">
                                <div class="net-speed" id="dash-net-down">0 B/s</div>
                                <div class="net-label">Download</div>
                            </div>
                        </div>
                    </div>
                    <div style="text-align:center;margin-top:12px;color:var(--text-muted);font-size:0.78rem;">
                        Toplam: <span id="dash-net-total-up">0 B</span> ↑ / <span id="dash-net-total-down">0 B</span> ↓
                    </div>
                </div>

                <!-- System Info -->
                <div class="card slide-up" style="margin-top:16px;animation-delay:0.25s">
                    <div class="card-title"><i class="fa-solid fa-microchip"></i> Sistem Bilgileri</div>
                    <div id="system-info-body">
                        <div class="page-loading"><div class="loading-spinner"></div></div>
                    </div>
                </div>
            </div>
        `;

        await this.fetchStats();
        await this.fetchSystemInfo();

        this._interval = setInterval(() => this.fetchStats(), 5000);
    },

    _gaugeCard(type, label, percent, sub) {
        const r = 45;
        const circ = 2 * Math.PI * r;
        return `
            <div class="card gauge-card slide-up" style="animation-delay:${type === 'cpu' ? '0' : type === 'ram' ? '0.05s' : '0.1s'}">
                <div class="gauge-wrap">
                    <svg class="gauge-svg" viewBox="0 0 110 110">
                        <circle class="gauge-bg" cx="55" cy="55" r="${r}"/>
                        <circle class="gauge-fill ${type}" cx="55" cy="55" r="${r}"
                            stroke-dasharray="${circ}"
                            stroke-dashoffset="${circ}"
                            id="gauge-${type}"/>
                    </svg>
                    <div class="gauge-value">
                        <span class="gauge-percent" id="gauge-${type}-val">${percent}%</span>
                        <span class="gauge-label-small" id="gauge-${type}-sub">${sub}</span>
                    </div>
                </div>
                <div class="card-title">${label}</div>
            </div>
        `;
    },

    _setGauge(type, percent, sub) {
        const r = 45;
        const circ = 2 * Math.PI * r;
        const offset = circ - (percent / 100) * circ;
        const el = document.getElementById(`gauge-${type}`);
        const valEl = document.getElementById(`gauge-${type}-val`);
        const subEl = document.getElementById(`gauge-${type}-sub`);
        if (el) el.setAttribute('stroke-dashoffset', offset);
        if (valEl) valEl.textContent = `${percent}%`;
        if (subEl) subEl.textContent = sub;
    },

    async fetchStats() {
        const data = await App.api('/api/dashboard/stats');
        if (!data || data.error) return;

        this._setGauge('cpu', data.cpu_percent, `${data.cpu_count} çekirdek`);
        this._setGauge('ram', data.ram_percent, `${formatBytes(data.ram_used)} / ${formatBytes(data.ram_total)}`);
        this._setGauge('disk', data.disk_percent, `${formatBytes(data.disk_used)} / ${formatBytes(data.disk_total)}`);

        const uptimeEl = document.getElementById('dash-uptime');
        if (uptimeEl) uptimeEl.textContent = formatUptime(data.uptime);

        const nuEl = document.getElementById('dash-net-up');
        const ndEl = document.getElementById('dash-net-down');
        const tnuEl = document.getElementById('dash-net-total-up');
        const tndEl = document.getElementById('dash-net-total-down');

        if (nuEl) nuEl.textContent = formatSpeed(data.net_up_speed);
        if (ndEl) ndEl.textContent = formatSpeed(data.net_down_speed);
        if (tnuEl) tnuEl.textContent = formatBytes(data.net_sent);
        if (tndEl) tndEl.textContent = formatBytes(data.net_recv);
    },

    async fetchSystemInfo() {
        const data = await App.api('/api/dashboard/system');
        const body = document.getElementById('system-info-body');
        if (!body) return;
        if (!data || data.error) {
            body.innerHTML = '<p style="color:var(--text-muted)">Sistem bilgileri alınamadı</p>';
            return;
        }

        body.innerHTML = `
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-server"></i> Hostname</span>
                <span class="stat-value">${data.hostname}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-brands fa-linux"></i> Kernel</span>
                <span class="stat-value">${data.kernel}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-brands fa-debian"></i> İşletim Sistemi</span>
                <span class="stat-value">${data.os_version}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-microchip"></i> İşlemci</span>
                <span class="stat-value">${data.processor}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-layer-group"></i> Mimari</span>
                <span class="stat-value">${data.architecture}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-cube"></i> Çekirdek (Fiziksel / Mantıksal)</span>
                <span class="stat-value">${data.cpu_physical} / ${data.cpu_cores}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-memory"></i> Toplam RAM</span>
                <span class="stat-value">${data.ram_total_gb} GB</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-hard-drive"></i> Toplam Disk</span>
                <span class="stat-value">${data.disk_total_gb} GB</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-solid fa-network-wired"></i> IP Adresi</span>
                <span class="stat-value">${data.ip_address}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label"><i class="fa-brands fa-python"></i> Python</span>
                <span class="stat-value">${data.python_version}</span>
            </div>
        `;
    },
};
