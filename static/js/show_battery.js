let allRecords = [];
let expandedSites = new Set();
let currentFilters = {
    tipo: 'todos',
    regions: [],
    status: 'all',
    search: ''
};

async function loadData() {
    const timestamp = document.getElementById('update-timestamp');
    try {
        const response = await fetch('/api/battery_show_data');
        const data = await response.json();

        allRecords = data.records;
        updateSummary(data.summary);
        renderTable();

        if (timestamp) timestamp.innerText = `Latest update: ${new Date().toLocaleString()}`;
    } catch (error) {
        console.error('Error loading battery data:', error);
    }
}

function updateSummary(summary) {
    const elements = {
        'stat-total': summary.total,
        'stat-critical': summary.critical,
        'stat-caution': summary.caution,
        'stat-normal': summary.normal,
        'stat-counts-sub': `${summary.access_count} Access - ${summary.transport_count} Transport`
    };

    for (const [id, value] of Object.entries(elements)) {
        const el = document.getElementById(id);
        if (el) el.innerText = value;
    }
}

function renderTable() {
    const body = document.getElementById('data-body');
    if (!body) return;

    const filtered = allRecords.filter(r => {
        const matchTipo = currentFilters.tipo === 'todos' || r.tipo.toLowerCase() === currentFilters.tipo;
        const matchRegion = currentFilters.regions.length === 0 || currentFilters.regions.includes(r.region);
        const matchStatus = currentFilters.status === 'all' || r.estado === currentFilters.status;
        const matchSearch = !currentFilters.search || r.sitio.toLowerCase().includes(currentFilters.search.toLowerCase());
        return matchTipo && matchRegion && matchStatus && matchSearch;
    });

    if (filtered.length === 0) {
        body.innerHTML = '<tr><td colspan="7" class="text-center">No active records found.</td></tr>';
        return;
    }

    const sitesMap = {};
    filtered.forEach(r => {
        if (!sitesMap[r.sitio]) {
            sitesMap[r.sitio] = {
                sitio: r.sitio,
                region: r.region,
                tipo_sistema: r.tipo,
                devices: []
            };
        }
        sitesMap[r.sitio].devices.push(r);
    });

    const sites = Object.values(sitesMap).sort((a, b) => a.sitio.localeCompare(b.sitio));

    body.innerHTML = '';
    sites.forEach((site, idx) => {
        const isExpanded = expandedSites.has(site.sitio);
        const avgSoc = site.devices.reduce((acc, d) => acc + (d.soc || 0), 0) / site.devices.length;
        const hasDischarging = site.devices.some(d => d.estado === 'DISCHARGING');
        const hasCharging = site.devices.some(d => d.estado === 'CHARGING');
        
        let statusLabel = "IDLE";
        let badgeClass = "badge-caution";
        if (hasDischarging) { statusLabel = "DISCHARGING"; badgeClass = "badge-critical"; }
        else if (hasCharging) { statusLabel = "CHARGING"; badgeClass = "badge-normal"; }

        const nwLabel = site.tipo_sistema === 'Access' ? 'Ax' : 'Tx';

        const tr = document.createElement('tr');
        tr.className = 'expand-row';
        tr.onclick = () => toggleDetail(idx, site.sitio);

        tr.innerHTML = `
            <td><span class="badge-nw">${nwLabel}</span></td>
            <td style="font-weight: 700;">${site.sitio}</td>
            <td>${site.region}</td>
            <td class="text-center"><span class="badge" style="background: var(--filter-group-bg); color: var(--text-muted);">${site.devices.length}</span></td>
            <td class="text-center" style="font-weight: 700;">${avgSoc.toFixed(1)}%</td>
            <td class="text-center">
                <span class="badge ${badgeClass}"><span class="dot"></span> ${statusLabel}</span>
            </td>
            <td>
                <button class="filter-btn" style="padding: 4px 8px; font-size: 0.75rem;">
                    <i class="fa-solid ${isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}"></i> ${isExpanded ? 'Hide' : 'Show'}
                </button>
            </td>
        `;
        body.appendChild(tr);

        const trDetail = document.createElement('tr');
        trDetail.className = 'detail-row';
        if (!isExpanded) trDetail.style.display = 'none';
        
        trDetail.innerHTML = `
            <td colspan="7">
                <div class="detail-inner visible">
                    <div class="battery-mini-grid">
                        ${buildDeviceCards(site.devices)}
                    </div>
                </div>
            </td>
        `;
        body.appendChild(trDetail);
    });
}

function buildDeviceCards(devices) {
    return devices.map(d => {
        const statusMap = {
            'DISCHARGING': { class: 'badge-critical', label: 'DISCHARGING' },
            'CHARGING': { class: 'badge-normal', label: 'CHARGING' },
            'IDLE': { class: 'badge-caution', label: 'IDLE' },
            'NO DATA': { class: 'badge-nodata', label: 'NO DATA' }
        };
        const info = statusMap[d.estado] || statusMap['NO DATA'];
        const isDisconnected = d.conexion === 1;
        
        return `
            <div class="battery-mini-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: 700; font-size: 0.85rem;">${isDisconnected ? '⛓️‍💥 ' : ''}${d.dispositivo}</span>
                    <span class="badge ${info.class}" style="font-size: 0.6rem; padding: 2px 6px;">${info.label}</span>
                </div>
                <div style="font-size: 1.2rem; font-weight: 800; margin-bottom: 4px;">${d.soc !== null ? d.soc.toFixed(1) + '%' : 'N/A'}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Cap: ${d.capacidad || '---'}</div>
                <div style="font-size: 0.6rem; color: var(--text-muted); margin-top: 5px;">Act: ${d.hora}</div>
            </div>
        `;
    }).join('');
}

function toggleDetail(idx, sitio) {
    if (expandedSites.has(sitio)) {
        expandedSites.delete(sitio);
    } else {
        expandedSites.add(sitio);
    }
    renderTable();
}

function resetFilters() {
    currentFilters.tipo = 'todos';
    currentFilters.regions = [];
    currentFilters.status = 'all';
    currentFilters.search = '';
    const searchInput = document.getElementById('site-search');
    if (searchInput) searchInput.value = '';
    expandedSites.clear();
    renderTable();
}

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('filter-btn') && e.target.dataset.filter) {
        const btn = e.target;
        const group = btn.dataset.filter;
        const value = btn.dataset.value;

        if (group === 'tipo') {
            document.querySelectorAll(`.filter-btn[data-filter="tipo"]`).forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilters.tipo = value;
        } else if (group === 'region') {
            if (value === 'todas') {
                currentFilters.regions = [];
                document.querySelectorAll(`.filter-btn[data-filter="region"]`).forEach(b => {
                    b.classList.toggle('active', b.dataset.value === 'todas');
                });
            } else {
                const allBtn = document.querySelector(`.filter-btn[data-filter="region"][data-value="todas"]`);
                if (allBtn) allBtn.classList.remove('active');
                if (currentFilters.regions.includes(value)) {
                    currentFilters.regions = currentFilters.regions.filter(v => v !== value);
                    btn.classList.remove('active');
                } else {
                    currentFilters.regions.push(value);
                    btn.classList.add('active');
                }
                if (currentFilters.regions.length === 0 && allBtn) allBtn.classList.add('active');
            }
        }
        renderTable();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setInterval(loadData, 30000);

    const searchInput = document.getElementById('site-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentFilters.search = e.target.value;
            renderTable();
        });
    }
});