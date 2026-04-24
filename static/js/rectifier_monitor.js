let allRecords = [];
let expandedSites = new Set();
let currentFilters = {
    tipo: 'todos',
    regions: [],
    search: ''
};

async function loadData() {
    const timestamp = document.getElementById('update-timestamp');
    try {
        const response = await fetch('/api/rectifier_data');
        const data = await response.json();

        allRecords = data.records;
        updateSummary(data.summary);
        renderTable();

        if (timestamp) timestamp.innerText = `Latest update: ${new Date().toLocaleString()}`;
    } catch (error) {
        console.error('Error loading rectifier data:', error);
    }
}

function updateSummary(summary) {
    const elements = {
        'stat-total': summary.total,
        'stat-low-voltage': summary.low_voltage,
        'stat-counts-sub': `${summary.access} Access - ${summary.transport} Transport`
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
        const matchSearch = !currentFilters.search || r.sitio.toLowerCase().includes(currentFilters.search.toLowerCase());
        return matchTipo && matchRegion && matchSearch;
    });

    if (filtered.length === 0) {
        body.innerHTML = '<tr><td colspan="7" class="text-center">No rectifier data found.</td></tr>';
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
        const avgVolt = site.devices.reduce((acc, d) => acc + ((d.v1 || d.v2 || 0)), 0) / site.devices.length;
        const isLow = site.devices.some(d => (d.v1 !== null && d.v1 < 48) || (d.v2 !== null && d.v2 < 48));

        const nwLabel = site.tipo_sistema === 'Access' ? 'Ax' : 'Tx';

        const tr = document.createElement('tr');
        tr.className = 'expand-row';
        tr.onclick = () => toggleDetail(idx, site.sitio);

        tr.innerHTML = `
            <td><span class="badge-nw">${nwLabel}</span></td>
            <td style="font-weight: 700;">${site.sitio}</td>
            <td>${site.region}</td>
            <td class="text-center"><span class="badge" style="background: var(--filter-group-bg); color: var(--text-muted);">${site.devices.length}</span></td>
            <td class="text-center ${isLow ? 'voltage-low' : 'voltage-high'}" style="font-weight: 700;">${avgVolt.toFixed(1)} V</td>
            <td class="text-center">
                ${isLow 
                    ? '<span class="badge badge-critical"><span class="dot"></span> LOW VOLTAGE</span>' 
                    : '<span class="badge badge-normal"><span class="dot"></span> NORMAL</span>'}
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
                        ${buildRectifierCards(site.devices)}
                    </div>
                </div>
            </td>
        `;
        body.appendChild(trDetail);
    });
}

function buildRectifierCards(devices) {
    return devices.map(d => {
        const isLow1 = d.v1 !== null && d.v1 < 48;
        const isLow2 = d.v2 !== null && d.v2 < 48;
        const isOffline = d.conexion === 1;
        
        return `
            <div class="battery-mini-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: 700; font-size: 0.85rem;">${isOffline ? '⛓️‍💥 ' : ''}${d.dispositivo}</span>
                    <span class="badge ${isOffline ? 'badge-critical' : 'badge-normal'}" style="font-size: 0.6rem; padding: 2px 6px;">${isOffline ? 'OFFLINE' : 'ONLINE'}</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase;">Voltage 1</div>
                        <div class="${isLow1 ? 'voltage-low' : 'voltage-high'}" style="font-size: 1.1rem; font-weight: 800;">${d.v1 !== null ? d.v1.toFixed(1) + 'V' : '---'}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase;">Voltage 2</div>
                        <div class="${isLow2 ? 'voltage-low' : 'voltage-high'}" style="font-size: 1.1rem; font-weight: 800;">${d.v2 !== null ? d.v2.toFixed(1) + 'V' : '---'}</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div>
                        <div style="font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase;">Current 1</div>
                        <div style="font-size: 0.9rem; font-weight: 700;">${d.c1 !== null ? d.c1.toFixed(2) + 'A' : '---'}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase;">Current 2</div>
                        <div style="font-size: 0.9rem; font-weight: 700;">${d.c2 !== null ? d.c2.toFixed(2) + 'A' : '---'}</div>
                    </div>
                </div>
                <div style="font-size: 0.6rem; color: var(--text-muted); margin-top: 8px; border-top: 1px solid var(--table-border); padding-top: 5px;">Act: ${d.hora}</div>
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
    setInterval(loadData, 60000);

    const searchInput = document.getElementById('site-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentFilters.search = e.target.value;
            renderTable();
        });
    }
});
