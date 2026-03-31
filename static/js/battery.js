let allRecords = [];
let currentFilters = {
    tipo: 'todos',
    regions: [], // Empty means "All"
    status: 'all'
};

async function loadData() {
    const timestamp = document.getElementById('update-timestamp');
    if (!timestamp) return;

    try {
        const response = await fetch('/api/battery_data');
        const data = await response.json();

        allRecords = data.records;
        updateSummary(data.summary);
        renderTable();

        timestamp.innerText = `Latest update: ${new Date().toLocaleString()}`;
    } catch (error) {
        console.error('Error loading data:', error);
        const dataBody = document.getElementById('data-body');
        if (dataBody) {
            dataBody.innerHTML = '<tr><td colspan="6" class="text-center" style="color: red;">Error connecting to server.</td></tr>';
        }
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
        return matchTipo && matchRegion && matchStatus;
    });

    if (filtered.length === 0) {
        body.innerHTML = '<tr><td colspan="6" class="text-center">No active records found.</td></tr>';
        return;
    }

    body.innerHTML = '';
    filtered.forEach(r => {
        const tr = document.createElement('tr');

        // Map server status to badge classes
        const statusMap = {
            'DISCHARGING': { class: 'badge-critical', label: 'DISCHARGING' },
            'CHARGING': { class: 'badge-normal', label: 'CHARGING' },
            'IDLE': { class: 'badge-caution', label: 'IDLE' },
            'NO DATA': { class: 'badge-nodata', label: 'NO DATA' }
        };

        const statusInfo = statusMap[r.estado] || statusMap['NO DATA'];
        const badgeClass = statusInfo.class;
        const estadoLabel = statusInfo.label;

        // Corriente display logic
        let corrienteVal = '--';
        if (r.estado === 'CHARGING') {
            corrienteVal = `<span style="color: var(--normal-green); font-weight: 700;">${r.carga.toFixed(2)} A</span>`;
        } else if (r.estado === 'DISCHARGING') {
            corrienteVal = `<span style="color: var(--critical-red); font-weight: 700;">${r.descarga.toFixed(2)} A</span>`;
        } else if (r.estado === 'IDLE') {
            corrienteVal = '0.00 A';
        }

        const siteContent = r.sitio;

        const batteryContent = parseInt(r.conexion) === 1
            ? `<span style="color: var(--critical-red); font-weight: 800;"> ⛓️‍💥${r.dispositivo}</span>`
            : r.dispositivo;

        tr.innerHTML = `
            <td>${r.hora}</td>
            <td style="font-weight: 600;">${siteContent}</td>
            <td>${batteryContent}</td>
            <td style="font-weight: 700; font-size: 1rem;">${r.soc !== null ? r.soc.toFixed(1) + '%' : 'N/A'}</td>
            <td>${corrienteVal}</td>
            <td>
                <span class="badge ${badgeClass}"><span class="dot"></span> ${estadoLabel}</span>
            </td>
        `;
        body.appendChild(tr);
    });
}

function resetFilters() {
    currentFilters.tipo = 'todos';
    currentFilters.regions = [];
    currentFilters.status = 'all';

    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.value === 'todos' || btn.dataset.value === 'todas') btn.classList.add('active');
        else btn.classList.remove('active');
    });

    document.querySelectorAll('.summary-card').forEach(c => c.classList.remove('active-filter'));
    renderTable();
}

function filterByStatus(status) {
    currentFilters.status = status;

    // Highlight active card
    document.querySelectorAll('.summary-card').forEach(c => c.classList.remove('active-filter'));
    if (status === 'all') document.getElementById('card-total').classList.add('active-filter');
    else if (status === 'DISCHARGING') document.getElementById('card-discharging').classList.add('active-filter');
    else if (status === 'IDLE') document.getElementById('card-idle').classList.add('active-filter');
    else if (status === 'CHARGING') document.getElementById('card-charging').classList.add('active-filter');

    renderTable();
}

// Filter Button Event Listeners
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('filter-btn')) {
        const btn = e.target;
        const group = btn.dataset.filter;
        const value = btn.dataset.value;

        if (group === 'tipo') {
            // Radio behavior for Type
            document.querySelectorAll(`.filter-btn[data-filter="tipo"]`).forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilters.tipo = value;
        } else if (group === 'region') {
            // Multi-select behavior for Region
            if (value === 'todas') {
                currentFilters.regions = [];
                document.querySelectorAll(`.filter-btn[data-filter="region"]`).forEach(b => {
                    if (b.dataset.value === 'todas') b.classList.add('active');
                    else b.classList.remove('active');
                });
            } else {
                // Deselect "All"
                const allBtn = document.querySelector(`.filter-btn[data-filter="region"][data-value="todas"]`);
                if (allBtn) allBtn.classList.remove('active');

                if (currentFilters.regions.includes(value)) {
                    // Remove if already selected
                    currentFilters.regions = currentFilters.regions.filter(v => v !== value);
                    btn.classList.remove('active');
                } else {
                    // Add if not selected
                    currentFilters.regions.push(value);
                    btn.classList.add('active');
                }

                // If nothing selected, re-select "All"
                if (currentFilters.regions.length === 0) {
                    if (allBtn) allBtn.classList.add('active');
                }
            }
        }
        renderTable();
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setInterval(loadData, 5000); // Auto-refresh every minute
});
