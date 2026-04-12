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
        body.innerHTML = '<tr><td colspan="14" class="text-center">No se detectaron fallas de red eléctrica activas.</td></tr>';
        return;
    }

    body.innerHTML = '';
    const now = new Date();

    filtered.forEach((r, idx) => {
        const detailId = `detail-${idx}`;
        const isExpanded = expandedSites.has(r.sitio);
        const isRevisado = revisadosSites.has(r.sitio);

        // NW Badge
        const nwLabel = r.tipo === 'Access' ? 'Ax' : 'Tx';

        // Status Pill
        let statusLabel = "OTHER";
        let statusClass = "other";
        if ((r.baterias || []).some(b => b.estado === 'DISCHARGING')) {
            statusLabel = "DISCHARGING";
            statusClass = "discharging";
        } else if ((r.baterias || []).some(b => b.estado === 'IDLE')) {
            statusLabel = "IDLE";
            statusClass = "idle";
        }

        // B1-B4 SOCs
        const socs = (r.baterias || []).slice(0, 4);
        const bCells = [0, 1, 2, 3].map(i => {
            if (socs[i]) {
                const isDischarging = socs[i].estado === 'DISCHARGING';
                const isCharging = socs[i].estado === 'CHARGING';
                const val = socs[i].soc !== null ? Math.round(socs[i].soc) : '';

                let color = '';
                if (isDischarging) color = 'color: #ef4444;';
                else if (isCharging) color = 'color: #22c55e;';
                else if (socs[i].estado === 'IDLE') color = ''; // No color for IDLE
                else if (socs[i].soc < 30) color = 'color: #ef4444;';
                else if (socs[i].soc < 100) color = 'color: #22c55e;';

                let arrow = '';
                if (isDischarging) arrow = '<i class="fa-solid fa-arrow-down" style="font-size:0.7rem; margin-left:2px; vertical-align:middle; color: #ef4444;"></i>';
                else if (isCharging) arrow = '<i class="fa-solid fa-arrow-up" style="font-size:0.7rem; margin-left:2px; vertical-align:middle; color: #22c55e;"></i>';

                return `<td style="text-align: center; font-weight: 700; ${color}">${val}${arrow}</td>`;
            }
            return `<td style="text-align: center; color: #94a3b8; font-size: 0.8rem;">--</td>`;
        }).join('');

        // Type Badges
        const bNames = (r.baterias || []).map(b => (b.nombre || "").toLowerCase());
        const isZte = bNames.some(n => n.includes('zte'));
        const isLitio = bNames.some(n => n.includes('litio') || n.includes('lithium') || n.includes('batería') || n.includes('batt'));
        let typeHtml = "";
        if (isLitio) typeHtml += '<span class="badge-type">Litio</span>';
        if (isZte) typeHtml += '<span class="badge-type">ZTE</span>';
        if (!typeHtml) typeHtml = '<span class="badge-type">Litio</span>';


        // Elapsed Time
        const alarmTime = new Date(r.hora);
        const elapsedMs = now - alarmTime;
        const elapsedHours = elapsedMs / (1000 * 60 * 60);
        let elapsedStr = "--";
        if (elapsedHours > 0) {
            const h = Math.floor(elapsedHours);
            const m = Math.floor((elapsedHours - h) * 60);
            elapsedStr = `${h}h ${m}m`;

            if (elapsedHours < 24) {
                const hf = Math.floor(elapsedHours);
                const mf = Math.floor((elapsedHours - hf) * 60);
                elapsedStr = `${hf}h ${mf}m`;
                if (hf === 0) elapsedStr = `${mf}m`;
            } else {
                elapsedStr = `${(elapsedHours / 24).toFixed(1)}d`;
            }
        }

        // Main row
        const tr = document.createElement('tr');
        const isGenActive = r.corriente_gen !== null && r.corriente_gen > 0;
        tr.className = `expand-row ${isRevisado ? 'revisado-row' : ''} ${isGenActive ? 'gen-active-row' : ''}`;
        tr.dataset.target = detailId;

        tr.innerHTML = `
            <td><span class="badge-nw">${nwLabel}</span></td>
            <td style="font-weight: 700;">${r.sitio}</td>
            ${bCells}
            <td>${typeHtml}</td>
            <td style="font-weight: 600;">${r.voltaje || 'N/A'}</td>
            <td style="font-weight: 700;">${r.svoltaje || '-'}</td>
            <td style="text-align: center;">${r.current1 || 0}</td>
            <td style="text-align: center;">${r.current2 || 0}</td>
            <td style="color: #22c55e; font-weight: 700;">${elapsedStr}</td>
            <td style="font-size: 0.8rem; color: #64748b;">${r.hora}</td>
            <td>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <label class="checkbox-revisado" onclick="event.stopPropagation();" title="Marcar como revisado">
                        <input type="checkbox" class="revisado-checkbox" data-site="${r.sitio}" ${isRevisado ? 'checked' : ''} onchange="toggleRevisado('${r.sitio}', this)">
                        <span class="checkmark"></span>
                    </label>
                    <button class="copy-card-btn" title="Ver Reporte" onclick="event.stopPropagation(); showReportModal('${r.sitio}', '${r.hora}')">
                        <i class="fa-solid fa-file-invoice"></i>
                    </button>
                </div>
            </td>
        `;
        tr.addEventListener('click', () => toggleDetail(idx, r.sitio));
        body.appendChild(tr);

        // Detail row (hidden by default unless expanded)
        const trDetail = document.createElement('tr');
        trDetail.className = 'detail-row';
        trDetail.id = detailId;
        trDetail.innerHTML = `<td colspan="14"><div class="detail-inner ${isExpanded ? 'visible' : ''}" id="inner-${idx}">${buildBatteryCards(r.baterias, r.sitio)}</div></td>`;
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

function buildModalBatteryCards(baterias) {
    if (!baterias || baterias.length === 0) return '';

    return baterias.map((bat, i) => {
        const soc = bat.soc !== null ? `${bat.soc.toFixed(1)}%` : 'N/A';
        let flowVal = '0.00 A';
        let flowClass = '';
        if (bat.estado === 'CHARGING') {
            flowVal = `+${(bat.carga || 0).toFixed(2)} A`;
            flowClass = 'pos';
        } else if (bat.estado === 'DISCHARGING') {
            flowVal = `-${(bat.descarga || 0).toFixed(2)} A`;
            flowClass = 'neg';
        }

        const badgeClass = bat.estado === 'DISCHARGING' ? 'badge-discharging' :
            (bat.estado === 'CHARGING' ? 'badge-charging' : 'badge-idle');

        const label = bat.estado || 'NO DATA';

        const statusCardClass = (bat.estado || 'no-data').toLowerCase();

        return `
            <div class="modal-qir-bat-card ${statusCardClass}">
                <div class="modal-qir-bat-header">
                    <span class="modal-qir-bat-name">${bat.nombre || `Batería ${i + 1}`}</span>
                    <span class="modal-qir-bat-badge ${badgeClass}"><span class="dot"></span> ${label}</span>
                </div>
                <div class="modal-qir-bat-soc">${soc}</div>
                <div class="modal-qir-bat-current ${flowClass}">${flowVal}</div>
                <div class="modal-qir-bat-update">Act: ${bat.ultimo_update || '---'}</div>
            </div>
        `;
    }).join('');
}

/**
l
 * @param {string} sitio - Nombre del sitio
 * @param {string} hora - Hora del evento
 */
async function showReportModal(sitio, hora) {
    const record = allRecords.find(r => r.sitio === sitio && r.hora === hora);
    if (!record) return;

    // --- Lógica de EBA ---
    const now = new Date();
    const alarmTime = new Date(record.hora);
    const elapsedMs = now - alarmTime;
    const elapsedHours = elapsedMs / (1000 * 60 * 60);

    const hours = Math.floor(elapsedHours);
    const minutes = Math.floor((elapsedHours - hours) * 60);
    const elapsedStr = `${hours}h ${minutes}m`;

    let currentSoc = 100;
    if (record.baterias && record.baterias.length > 0) {
        currentSoc = Math.min(...record.baterias.map(b => b.soc !== null ? b.soc : 100));
    }

    const socDrop = 100 - currentSoc;
    let ebaText = "";
    if (elapsedHours > 0.5 && socDrop > 2) {
        const dropRate = socDrop / elapsedHours;
        const remainingHours = currentSoc / dropRate;
        const h = Math.floor(remainingHours);
        const m = Math.floor((remainingHours - h) * 60);
        ebaText = `${h}h ${m}m apróx.`;
    } else if (currentSoc < 98) {
        ebaText = "Pendiente (Estabilizando)";
    } else {
        ebaText = "(Batería con carga completa)";
    }

    // Asegurar que tenemos los nombres
    const firstName = localStorage.getItem('user_first_name') || '';
    const lastName = localStorage.getItem('user_last_name') || '';
    let rawName = `${firstName} ${lastName}`.trim();
    if (!rawName) {
        syncUserInfo();
        rawName = 'Sistema';
    }

    // --- Construcción de las filas de baterías (Cards version) ---
    let batteriesHtml = '';
    if (record.baterias && record.baterias.length > 0) {
        batteriesHtml = `
            <div style="margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 20px;">
                <span style="font-weight: 800; color: #64748b; font-size: 13px; text-transform: uppercase; display: block; margin-bottom: 12px;">
                    <i class="fa-solid fa-battery-three-quarters"></i> Detalle de Baterías:
                </span>
                <div class="modal-battery-grid" style="transform: scale(0.95); transform-origin: top left;">
                    ${buildBatteryCards(record.baterias, record.sitio)}
                </div>
            </div>
        `;
    }

    // --- Construcción del Contenedor de Reporte (Harmonized Version) ---
    const modalHtml = `
        <div id="qir-capture-area" class="modal-qir-container">
            <!-- Header Section -->
            <div class="modal-qir-header">
                <span class="modal-qir-title">${record.sitio}</span>
                <span class="modal-qir-id">${record.voltaje}</span>
            </div>

            <!-- Content Body -->
            <div class="modal-qir-body">
                <div class="modal-qir-section-header">
                    <i class="fa-solid fa-microchip"></i> Rectifier Details:
                </div>

                <div class="modal-qir-info-row">
                    <div class="modal-qir-info-label">Electrical Info:</div>
                    <div class="modal-qir-info-value">
                        ${record.svoltaje !== null ? record.svoltaje + 'V' : '--- '} 
                        <span style="color: #94a3b8; margin: 0 8px;">|</span> 
                        C1: ${record.current1 || '0'}A 
                        <span style="color: #94a3b8; margin: 0 8px;">|</span> 
                        C2: ${record.current2 || '0'}A
                    </div>
                </div>

                <div class="modal-qir-section-header" style="margin-top: 24px;">
                    <i class="fa-solid fa-battery-three-quarters"></i> Battery Details:
                </div>

                <div class="modal-qir-battery-grid">
                    ${buildModalBatteryCards(record.baterias)}
                </div>

                <div class="modal-qir-footer">
                    <span><i class="fa-solid fa-user-shield"></i> Validated by YOFC NOC</span>
                    <span style="font-style: italic;"> ${rawName} | ${new Date().toLocaleString()}</span>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modal-report-content').innerHTML = modalHtml;
    const modal = document.getElementById('reportModal');

    // Configurar botón descargar
    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.onclick = async () => {
        const area = document.getElementById('qir-capture-area');
        const canvas = await html2canvas(area, { scale: 2, useCORS: true });
        const link = document.createElement('a');
        link.download = `Reporte_AC_${record.sitio}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        showNotification('✅ Imagen descargada correctamente', 'success');
    };

    modal.style.display = 'flex';

    // Manejo del resumen copiable
    const summarySection = document.getElementById('summary-copy-section');
    const summaryText = document.getElementById('summary-text');
    const isAnyDischarging = record.baterias && record.baterias.some(b => b.estado === 'DISCHARGING');

    if (isAnyDischarging) {
        summarySection.style.display = 'block';
        const lbat1 = record.current1 !== null ? `${record.current1}A` : '0.0A';
        const lbat2 = record.current2 !== null ? `${record.current2}A` : '0.0A';
        const socDetails = record.baterias.map((b, i) => `SOC${i + 1}:"${(b.soc || 0).toFixed(1)}%"`).join(' ');
        const finalSummary = `Batteries discharging due to Power AC Outage // RECT (VSyS "${record.svoltaje || '---'}V" lbat1:"${lbat1}"/lbat2:"${lbat2}". Batt% (Rem.): ${socDetails} Autonomy so far(Tot. aut...): ${elapsedStr}) ------------- support ticket: ------------- (reports no scheduled or unscheduled outages)`;
        summaryText.innerText = finalSummary;
    } else {
        summarySection.style.display = 'none';
        summaryText.innerText = '';
    }
}

function copySummaryToClipboard() {
    const text = document.getElementById('summary-text').innerText;
    navigator.clipboard.writeText(text).then(() => {
        showNotification('✅ Texto copiado al portapapeles', 'success');
    }).catch(err => {
        console.error('Error al copiar:', err);
        showNotification('❌ Error al copiar al portapapeles', 'error');
    });
}

function closeModal() {
    document.getElementById('reportModal').style.display = 'none';
}

// Cerrar modal al hacer click fuera
window.onclick = function (event) {
    const modal = document.getElementById('reportModal');
    if (event.target == modal) {
        closeModal();
    }
}

/**
 * Intenta sincronizar datos del perfil si no están en localStorage
 */
async function syncUserInfo() {
    const token = localStorage.getItem('jwt_token');
    if (!token) return;
    try {
        const resp = await fetch('/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            localStorage.setItem('user_first_name', data.first_name || '');
            localStorage.setItem('user_last_name', data.last_name || '');
            console.log('User info synced');
        }
    } catch (e) { /* silent fail */ }
}

// Intentar sincronizar al cargar la página si falta algo
document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('user_first_name') || !localStorage.getItem('user_last_name')) {
        syncUserInfo();
    }
});

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
        if (body) body.innerHTML = `<tr><td colspan="14" class="text-center" style="color:var(--critical-red);">Error al cargar los datos: ${error.message}</td></tr>`;
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

/**
 * Exporta los datos actuales (filtrados) a Excel siguiendo el formato solicitado
 */
function exportToExcel() {
    if (typeof XLSX === 'undefined') {
        showNotification('⚠️ Librería de exportación no cargada aún.', 'error');
        return;
    }

    // Usar registros filtrados (los mismos que se ven en la tabla)
    const filtered = allRecords.filter(r => {
        const matchTipo = currentFilters.tipo === 'todos' || r.tipo.toLowerCase() === currentFilters.tipo;
        const matchRegion = currentFilters.regions.length === 0 || currentFilters.regions.includes(r.region);
        let matchStatus = true;
        if (currentFilters.status !== 'all') {
            matchStatus = (r.baterias || []).some(b => b.estado === currentFilters.status);
        }
        return matchTipo && matchRegion && matchStatus;
    });

    if (filtered.length === 0) {
        showNotification('⚠️ No hay datos para exportar.', 'error');
        return;
    }

    const now = new Date();

    // Mapeo de datos al formato Excel
    const dataForExcel = filtered.map(r => {
        // NW (Network Type)
        const nw = r.tipo === 'Access' ? 'AX' : 'TX';

        // Batteria SOCs (B1-B4)
        const socs = (r.baterias || []).slice(0, 4);
        const b1 = socs[0] ? (socs[0].soc !== null ? socs[0].soc : '') : '';
        const b2 = socs[1] ? (socs[1].soc !== null ? socs[1].soc : '') : '';
        const b3 = socs[2] ? (socs[2].soc !== null ? socs[2].soc : '') : '';
        const b4 = socs[3] ? (socs[3].soc !== null ? socs[3].soc : '') : '';

        // Type (Litio / ZTE)
        const bNames = (r.baterias || []).map(b => (b.nombre || "").toLowerCase());
        const isZte = bNames.some(n => n.includes('zte'));
        const isLitio = bNames.some(n => n.includes('litio') || n.includes('lithium') || n.includes('batería'));
        let typeStr = "";
        if (isLitio && isZte) typeStr = "Litio/ZTE";
        else if (isZte) typeStr = "ZTE";
        else if (isLitio) typeStr = "Litio";
        else typeStr = "Litio"; // Default

        // Elapsed Time
        const alarmTime = new Date(r.hora);
        const elapsedMs = now - alarmTime;
        const elapsedHours = elapsedMs / (1000 * 60 * 60);
        let elapsedStr = "";
        if (elapsedHours > 0) {
            const h = Math.floor(elapsedHours);
            const m = Math.floor((elapsedHours - h) * 60);
            elapsedStr = `${h}h ${m}m`;
        } else {
            elapsedStr = "--";
        }

        // Status General
        let status = "OTHER";
        if ((r.baterias || []).some(b => b.estado === 'DISCHARGING')) status = "DISCHARGING";
        else if ((r.baterias || []).some(b => b.estado === 'IDLE')) status = "IDLE";


        return {
            "NW": nw,
            "SITE NAME": r.sitio,
            "B1": b1,
            "B2": b2,
            "B3": b3,
            "B4": b4,
            "TYPE": typeStr,
            "AC V": r.voltaje || 'N/A',
            "VDC": r.svoltaje || '-',
            "CUR 1": r.current1 || 0,
            "CUR 2": r.current2 || 0,
            "ELAPSED TIME": elapsedStr,
            "POWER AC OFF TIME": r.hora
        };
    });

    // Crear Workbook y Worksheet
    const worksheet = XLSX.utils.json_to_sheet(dataForExcel);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "AC Failures");

    // Ajustar anchos de columna automáticamente
    const wscols = [
        { wch: 5 },  // NW
        { wch: 25 }, // SITE NAME
        { wch: 5 },  // B1
        { wch: 5 },  // B2
        { wch: 5 },  // B3
        { wch: 5 },  // B4
        { wch: 10 }, // TYPE
        { wch: 10 }, // AC V
        { wch: 8 },  // VDC
        { wch: 8 },  // CUR 1
        { wch: 8 },  // CUR 2
        { wch: 15 }, // ELAPSED TIME
        { wch: 20 }  // POWER AC OFF TIME
    ];
    worksheet['!cols'] = wscols;

    // Descargar
    XLSX.writeFile(workbook, `Fallas_AC_${new Date().toISOString().split('T')[0]}.xlsx`);
    showNotification('✅ Excel exportado correctamente', 'success');
}