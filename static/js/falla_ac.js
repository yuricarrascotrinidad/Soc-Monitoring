let allRecords = [];
let expandedSites = new Set();
let revisadosSites = new Set();
let currentFilters = {
    tipo: 'todos',
    regions: [],
    status: 'all'
};

// Summary counters across all battery states
function calcSummary(records) {
    const s = { total: 0, discharging: 0, idle: 0, charging: 0, access: 0, transport: 0 };
    records.forEach(r => {
        s.total++;
        if (r.tipo.toLowerCase() === 'access') s.access++;
        else s.transport++;
        (r.baterias || []).forEach(b => {
            if (b.estado === 'DISCHARGING') s.discharging++;
            else if (b.estado === 'CHARGING') s.charging++;
            else if (b.estado === 'IDLE') s.idle++;
        });
    });
    return s;
}

function updateSummary(records) {
    const s = calcSummary(records);
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set('stat-total', s.total);
    set('stat-discharging', s.discharging);
    set('stat-idle', s.idle);
    set('stat-charging', s.charging);
    set('stat-counts-sub', `${s.access} Access - ${s.transport} Transport`);
}

function toggleRevisado(sitio, checkbox) {
    if (checkbox.checked) {
        revisadosSites.add(sitio);
    } else {
        revisadosSites.delete(sitio);
    }

    // Actualizar la clase de la fila
    const row = checkbox.closest('tr');
    if (checkbox.checked) {
        row.classList.add('revisado-row');
    } else {
        row.classList.remove('revisado-row');
    }

    // Guardar en localStorage para persistencia
    localStorage.setItem('revisadosSites', JSON.stringify(Array.from(revisadosSites)));
}

function cargarRevisadosGuardados() {
    const guardados = localStorage.getItem('revisadosSites');
    if (guardados) {
        revisadosSites = new Set(JSON.parse(guardados));
    }
}

function renderTable() {
    const body = document.getElementById('data-body');
    if (!body) return;

    const filtered = allRecords.filter(r => {
        const matchTipo = currentFilters.tipo === 'todos' || r.tipo.toLowerCase() === currentFilters.tipo;
        const matchRegion = currentFilters.regions.length === 0 || currentFilters.regions.includes(r.region);

        let matchStatus = true;
        if (currentFilters.status !== 'all') {
            matchStatus = (r.baterias || []).some(b => b.estado === currentFilters.status);
        }

        return matchTipo && matchRegion && matchStatus;
    });

    updateSummary(filtered);

    if (filtered.length === 0) {
        body.innerHTML = '<tr><td colspan="9" class="text-center">No se detectaron fallas de red eléctrica activas.</td></tr>';
        return;
    }

    body.innerHTML = '';
    filtered.forEach((r, idx) => {
        const rowId = `row-${idx}`;
        const detailId = `detail-${idx}`;
        const batCount = (r.baterias || []).length;
        const isExpanded = expandedSites.has(r.sitio);
        const isRevisado = revisadosSites.has(r.sitio);

        // Main row
        const tr = document.createElement('tr');
        tr.className = `expand-row ${isRevisado ? 'revisado-row' : ''}`;
        tr.dataset.target = detailId;
        tr.innerHTML = `
            <td><i class="fa-solid fa-chevron-right expand-chevron ${isExpanded ? 'open' : ''}" id="chevron-${idx}"></i></td>
            <td>${r.hora}</td>
            <td style="font-weight: 700;">${r.sitio}</td>
            <td>${r.region}</td>
            <td>${r.tipo}</td>
            <td style="font-size:0.82rem; max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.voltaje}">${r.voltaje}</td>
            <td style="font-weight:600;">${batCount} batería${batCount !== 1 ? 's' : ''}</td>
            <td>
                <label class="checkbox-revisado" onclick="event.stopPropagation();">
                    <input type="checkbox" class="revisado-checkbox" data-site="${r.sitio}" ${isRevisado ? 'checked' : ''} onchange="toggleRevisado('${r.sitio}', this)">
                    <span class="checkmark"></span>
                    Revisado
                </label>
            </td>
            <td>
                <button class="copy-card-btn" title="Copiar como imagen" onclick="event.stopPropagation(); copyCardToClipboard(${idx})">
                    <i class="fa-solid fa-copy"></i>
                </button>
            </td>
        `;
        tr.addEventListener('click', () => toggleDetail(idx, r.sitio));
        body.appendChild(tr);

        // Detail row (hidden by default unless expanded)
        const trDetail = document.createElement('tr');
        trDetail.className = 'detail-row';
        trDetail.id = detailId;
        trDetail.innerHTML = `<td colspan="9"><div class="detail-inner ${isExpanded ? 'visible' : ''}" id="inner-${idx}">${buildBatteryCards(r.baterias, r.sitio)}</div></td>`;
        body.appendChild(trDetail);
    });
}

function toggleDetail(idx, sitio) {
    const inner = document.getElementById(`inner-${idx}`);
    const chevron = document.getElementById(`chevron-${idx}`);
    if (!inner) return;

    const isOpen = inner.classList.contains('visible');

    // Update state tracking
    if (!isOpen) {
        expandedSites.add(sitio);
    } else {
        expandedSites.delete(sitio);
    }

    inner.classList.toggle('visible', !isOpen);
    if (chevron) chevron.classList.toggle('open', !isOpen);
}

function buildBatteryCards(baterias, sitio) {
    if (!baterias || baterias.length === 0) {
        return `<div class="no-batteries"><i class="fa-solid fa-circle-info"></i> No se encontraron datos de baterías para ${sitio}.</div>`;
    }

    const statusMap = {
        'DISCHARGING': { class: 'badge-critical', label: 'DISCHARGING' },
        'CHARGING': { class: 'badge-normal', label: 'CHARGING' },
        'IDLE': { class: 'badge-caution', label: 'IDLE' },
        'NO DATA': { class: 'badge-nodata', label: 'NO DATA' }
    };

    let html = '<div class="battery-mini-grid">';
    baterias.forEach((bat, i) => {
        const soc = bat.soc !== null ? `${bat.soc.toFixed(1)}%` : 'N/A';
        let flowVal = '0.00 A';
        let flowColor = 'var(--text-muted)';
        if (bat.estado === 'CHARGING') {
            flowVal = `+${(bat.carga || 0).toFixed(2)} A`;
            flowColor = 'var(--normal-green)';
        } else if (bat.estado === 'DISCHARGING') {
            flowVal = `-${(bat.descarga || 0).toFixed(2)} A`;
            flowColor = 'var(--critical-red)';
        }

        const info = statusMap[bat.estado] || statusMap['NO DATA'];
        const isDisconnected = parseInt(bat.conexion) === 1;

        const batteryNameContent = isDisconnected
            ? `<span style="color: var(--critical-red); font-weight: 800;">⛓️‍💥 ${bat.nombre || `Batería ${i + 1}`}</span>`
            : (bat.nombre || `Batería ${i + 1}`);

        html += `
            <div class="battery-mini-card ${isDisconnected ? 'disconnected-warning' : ''}">
                <div class="battery-mini-header">
                    <span style="display: flex; align-items: center; gap: 4px;">
                        ${batteryNameContent}
                    </span>
                    <span class="badge ${info.class}"><span class="dot"></span> ${info.label}</span>
                </div>
                <div class="battery-mini-soc">${soc}</div>
                <div class="battery-mini-flow" style="color: ${flowColor}; font-weight: 700;">${flowVal}</div>
                <div class="battery-mini-update">Act: ${bat.ultimo_update || '---'}</div>
            </div>
        `;
    });
    html += '</div>';
    return html;
}

async function copyCardToClipboard(rowIdx) {
    const record = allRecords[rowIdx];
    const inner = document.getElementById(`inner-${rowIdx}`);

    if (!inner) {
        showNotification('❌ No se encontró el detalle de la batería', 'error');
        return;
    }

    try {
        // Crear un contenedor temporal para la captura
        const tempDiv = document.createElement('div');
        tempDiv.style.cssText = `
            position: fixed;
            top: -9999px;
            left: -9999px;
            width: 650px;
            background: white;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.2);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        `;

        // Construir el contenido a capturar
        const fechaActual = new Date().toLocaleString();
        const isRevisado = revisadosSites.has(record.sitio);

        tempDiv.innerHTML = `
            <div style="border-bottom: 2px solid #e5e7eb; padding-bottom: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0; color: #dc2626; font-size: 1.8rem; display: flex; align-items: center; gap: 10px;">
                        <span>⚡ Falla AC</span>
                        ${isRevisado ? '<span style="font-size: 1rem; background: #22c55e; color: white; padding: 4px 12px; border-radius: 20px;">✓ REVISADO</span>' : ''}
                    </h2>
                    <span style="background: #fee2e2; color: #dc2626; padding: 6px 16px; border-radius: 9999px; font-size: 0.9rem; font-weight: 600;">
                        ${record.hora}
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 16px; background: #f8fafc; padding: 16px; border-radius: 12px;">
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Sitio</div>
                        <div style="color: #0f172a; font-weight: 700; font-size: 1.1rem;">${record.sitio}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Región</div>
                        <div style="color: #0f172a; font-weight: 600;">${record.region}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Tipo</div>
                        <div style="color: #0f172a; font-weight: 600;">${record.tipo}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-size: 0.8rem;">Voltaje</div>
                        <div style="color: #0f172a; font-weight: 600;">${record.voltaje}</div>
                    </div>
                </div>
            </div>
            ${inner.innerHTML}
            <div style="border-top: 1px solid #e5e7eb; margin-top: 20px; padding-top: 16px; display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-size: 0.8rem;">
                <span>Reporte generado: ${fechaActual}</span>
                <span>Sistema de Monitoreo de Baterías</span>
            </div>
        `;

        document.body.appendChild(tempDiv);

        // Usar html2canvas para capturar
        const canvas = await html2canvas(tempDiv, {
            scale: 2,
            backgroundColor: '#ffffff',
            logging: false,
            allowTaint: true,
            useCORS: true,
            windowWidth: 650
        });

        // Convertir a blob y copiar al portapapeles
        canvas.toBlob(async (blob) => {
            try {
                await navigator.clipboard.write([
                    new ClipboardItem({
                        [blob.type]: blob
                    })
                ]);

                showNotification('✅ Imagen copiada al portapapeles', 'success');
            } catch (err) {
                console.error('Error al copiar:', err);
                showNotification('❌ Error al copiar la imagen', 'error');
            } finally {
                // Limpiar
                document.body.removeChild(tempDiv);
            }
        }, 'image/png');

    } catch (error) {
        console.error('Error al generar la imagen:', error);
        showNotification('❌ Error al generar la imagen', 'error');
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

async function loadData() {
    const timestamp = document.getElementById('update-timestamp');
    try {
        const response = await fetch('/api/ac_data');
        const data = await response.json();

        allRecords = data.records || [];
        renderTable();

        if (timestamp) timestamp.innerText = `Última actualización: ${new Date().toLocaleString()}`;
    } catch (error) {
        console.error('Error loading AC data:', error);
        const body = document.getElementById('data-body');
        if (body) body.innerHTML = `<tr><td colspan="9" class="text-center" style="color:var(--critical-red);">Error al cargar los datos: ${error.message}</td></tr>`;
    }
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
    cargarRevisadosGuardados();
    loadData();
    setInterval(loadData, 5000);
});