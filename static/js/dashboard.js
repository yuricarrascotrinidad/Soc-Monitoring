const DashboardManager = {
    // Estado interno
    state: {
        lastUpdate: new Date(),
        currentModule: 'dashboard',
        currentTheme: 'light',
        refreshInterval: null,
        timestampInterval: null,
        lastDataHash: null, // Track data changes
        shownErrors: new Set() // Track shown connection alerts
    },

    // Inicialización principal
    init: function () {
        this.loadSavedTheme();
        this.setupEventListeners();
        this.loadData();
        this.updateTimestamp();

        // Configurar intervalos - Vuelto a 10s para estabilizar recursos
        this.state.refreshInterval = setInterval(() => this.refreshData(), 10000);
        this.state.timestampInterval = setInterval(() => this.updateTimestamp(), 1000);
    },

    // LocalStorage helpers para eventos marcados
    getCheckedEvents: function (type) {
        const key = `soc_checked_events_${type}`;
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : [];
    },

    setCheckedEvent: function (type, sitio, checked) {
        const key = `soc_checked_events_${type}`;
        let checkedEvents = this.getCheckedEvents(type);

        if (checked) {
            if (!checkedEvents.includes(sitio)) {
                checkedEvents.push(sitio);
            }
        } else {
            checkedEvents = checkedEvents.filter(s => s !== sitio);
        }

        localStorage.setItem(key, JSON.stringify(checkedEvents));
    },

    isEventChecked: function (type, sitio) {
        return this.getCheckedEvents(type).includes(sitio);
    },

    syncCheckedEvents: function (accessEvents, transportEvents) {
        const activeAccessNames = accessEvents.map(e => e.sitio);
        const activeTransportNames = transportEvents.map(e => e.sitio);

        // Prune access
        let checkedAccess = this.getCheckedEvents('access');
        const initialAccessCount = checkedAccess.length;
        checkedAccess = checkedAccess.filter(site => activeAccessNames.includes(site));
        if (checkedAccess.length !== initialAccessCount) {
            localStorage.setItem('soc_checked_events_access', JSON.stringify(checkedAccess));
        }

        // Prune transport
        let checkedTransport = this.getCheckedEvents('transport');
        const initialTransportCount = checkedTransport.length;
        checkedTransport = checkedTransport.filter(site => activeTransportNames.includes(site));
        if (checkedTransport.length !== initialTransportCount) {
            localStorage.setItem('soc_checked_events_transport', JSON.stringify(checkedTransport));
        }
    },

    toggleEventChecked: function (type, sitio, checkbox) {
        const checked = checkbox.checked;
        this.setCheckedEvent(type, sitio, checked);

        // Re-renderizar eventos para aplicar el ordenamiento
        this.loadData();
    },


    // Gestión de temas
    toggleTheme: function () {
        if (this.state.currentTheme === 'light') {
            document.body.classList.add('dark-theme');
            document.getElementById('themeIcon').textContent = '☀️';
            this.state.currentTheme = 'dark';
        } else {
            document.body.classList.remove('dark-theme');
            document.getElementById('themeIcon').textContent = '🌙';
            this.state.currentTheme = 'light';
        }
        localStorage.setItem('dashboard-theme', this.state.currentTheme);
        this.updateTimestamp();
    },

    loadSavedTheme: function () {
        const savedTheme = localStorage.getItem('dashboard-theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            document.getElementById('themeIcon').textContent = '☀️';
            this.state.currentTheme = 'dark';
        } else {
            document.body.classList.remove('dark-theme');
            document.getElementById('themeIcon').textContent = '🌙';
            this.state.currentTheme = 'light';
        }
    },

    // Gestión de tiempo
    updateTimestamp: function () {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        const dateStr = now.toLocaleDateString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });

        const timestampEl = document.getElementById('timestamp');
        const footerTimestampEl = document.getElementById('footer-timestamp');

        if (timestampEl) timestampEl.textContent = `Latest update: ${timeStr} - ${dateStr}`;
        if (footerTimestampEl) footerTimestampEl.textContent = `System active - ${timeStr}`;
    },

    // Navegación de módulos
    changeModule: function (moduleId) {
        document.querySelectorAll('.module-item').forEach(item => {
            item.classList.remove('active');
        });

        const activeModule = document.querySelector(`[data-module="${moduleId}"]`);
        if (activeModule) {
            activeModule.classList.add('active');
        }

        this.state.currentModule = moduleId;

        const dashboardContent = document.getElementById('dashboard-content');
        const otherContent = document.getElementById('other-modules-content');
        const contentGrid = document.querySelector('.content-grid');

        if (moduleId === 'dashboard') {
            if (dashboardContent) dashboardContent.style.display = 'block';
            if (otherContent) otherContent.style.display = 'none';
            if (contentGrid) contentGrid.style.display = 'grid';
        } else {
            if (dashboardContent) dashboardContent.style.display = 'none';
            if (otherContent) otherContent.style.display = 'block';
            if (contentGrid) contentGrid.style.display = 'none';
            this.updateModuleContent(moduleId);
        }
    },

    updateModuleContent: function (moduleId) {
        const moduleTitle = document.getElementById('module-title');
        const moduleDetails = document.getElementById('module-details');

        const moduleContents = {
            'access-alarms': { title: '🏢 Alarmas Access', content: '<p>Cargando información de alarmas Access...</p>' },
            'transport-alarms': { title: '🚚 Alarmas Transport', content: '<p>Cargando información de alarmas Transport...</p>' },
            'anomalies': { title: '⚠️ Anomalías Detectadas', content: '<p>Cargando información de anomalías...</p>' },
            'camera-list': { title: '📋 Lista de Cámaras', content: '<p>Redirigiendo a la lista de cámaras...</p>' },
            'access-cameras': { title: '🏢 Cámaras Access', content: '<p>Cargando información de cámaras Access...</p>' },
            'transport-cameras': { title: '🚚 Cámaras Transport', content: '<p>Cargando información de cámaras Transport...</p>' },
            'region-ancash': { title: '⛰️ Región Ancash', content: '<p>Cargando información de la región Ancash...</p>' },
            'region-arequipa': { title: '🌋 Región Arequipa', content: '<p>Cargando información de la región Arequipa...</p>' },
            'region-la-libertad': { title: '🏛️ Región La Libertad', content: '<p>Cargando información de la región La Libertad...</p>' },
            'region-san-martin': { title: '🌿 Región San Martín', content: '<p>Cargando información de la región San Martín...</p>' },
            'system-status': { title: '📈 Estado del Sistema', content: '<p>Cargando estado del sistema...</p>' },
            'logs': { title: '📝 Logs y Eventos', content: '<p>Cargando logs del sistema...</p>' },
            'reports': { title: '📊 Reportes', content: '<p>Cargando reportes del sistema...</p>' },
            'settings': { title: '⚙️ Configuración', content: '<p>Cargando configuración del sistema...</p>' }
        };

        if (moduleContents[moduleId]) {
            if (moduleTitle) moduleTitle.textContent = moduleContents[moduleId].title;
            if (moduleDetails) moduleDetails.innerHTML = moduleContents[moduleId].content;

            if (moduleId === 'camera-list') {
                setTimeout(() => window.location.href = '/camera_list', 500);
            } else if (moduleId === 'system-status') {
                setTimeout(() => window.open('/estado', '_blank'), 500);
            }
        }
    },

    // Carga de datos optimizada
    loadData: async function () {
        try {
            const response = await fetch('/api/dashboard_state');
            const data = await response.json();

            // Check for connection errors
            if (data.connection_errors) {
                for (const [url, error] of Object.entries(data.connection_errors)) {
                    const errorKey = url + (error || '');
                    if (error && !this.state.shownErrors.has(errorKey)) {
                        alert(error);
                        // Clean up previous errors for this URL to keep Set small
                        this.state.shownErrors.forEach(key => {
                            if (key.startsWith(url)) this.state.shownErrors.delete(key);
                        });
                        this.state.shownErrors.add(errorKey);
                    } else if (!error) {
                        // Clear all errors for this URL if it's now successful
                        this.state.shownErrors.forEach(key => {
                            if (key.startsWith(url)) this.state.shownErrors.delete(key);
                        });
                    }
                }
            }

            // Hash simple para detectar cambios antes de renderizar (Optimización de CPU)
            const dataStr = JSON.stringify({
                access: data.access,
                transport: data.transport,
                ac: data.ac_failures_count,
                bat: data.battery_alerts_count
            });

            if (this.state.lastDataHash === dataStr) {
                // Los datos son idénticos, no re-renderizamos (evita "flicker" y uso de CPU)
                this.state.lastUpdate = new Date();
                this.updateTimestamp();
                return;
            }
            this.state.lastDataHash = dataStr;

            const accessEvents = data.access.eventos.length;
            const accessAnomalies = data.access.anomalias.length;
            const transportEvents = data.transport.eventos.length;
            const transportAnomalies = data.transport.anomalias.length;

            this.updateElementText('access-events-count', accessEvents);
            this.updateElementText('access-anomalies-count', accessAnomalies);
            this.updateElementText('transport-events-count', transportEvents);
            this.updateElementText('transport-anomalies-count', transportAnomalies);

            this.updateElementText('total-alarms', accessEvents + transportEvents);
            this.updateElementText('access-alarms-count', accessEvents);
            this.updateElementText('transport-alarms-count', transportEvents);
            this.updateElementText('anomalies-count', accessAnomalies + transportAnomalies);
            this.updateElementText('ac-failures-count', data.ac_failures_count || 0);

            // Cámaras (ya vienen en el state consolidado)
            const accessCamerasCount = data.cameras.access.length;
            const transportCamerasCount = data.cameras.transport.length;
            const totalCameras = accessCamerasCount + transportCamerasCount;

            this.updateElementText('cameras-access-count', accessCamerasCount);
            this.updateElementText('cameras-transport-count', transportCamerasCount);
            this.updateElementText('total-cameras', totalCameras);
            this.updateElementText('access-cameras-count', accessCamerasCount);
            this.updateElementText('transport-cameras-count', transportCamerasCount);

            this.syncCheckedEvents(data.access.eventos, data.transport.eventos);

            this.renderEvents('access', data.access.eventos);
            this.renderAnomalies('access', data.access.anomalias);
            this.renderEvents('transport', data.transport.eventos);
            this.renderAnomalies('transport', data.transport.anomalias);

            // Batería count (ya viene en el state)
            this.updateElementText('battery-alerts-count', data.battery_alerts_count);
            this.updateElementText('hvac-alerts-count', data.hvac_total_count || 0);

            const batteryBadge = document.getElementById('battery-alerts-count');
            if (batteryBadge) {
                batteryBadge.style.backgroundColor = ''; // Reset to CSS default
                batteryBadge.style.color = '';
            }

            this.state.lastUpdate = new Date();
            this.updateTimestamp();
        } catch (error) {
            console.error('Error cargando datos dashboard:', error);
        }
    },

    updateElementText: function (id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    },

    refreshData: function () {
        this.loadData();
    },

    // Renderizado
    renderEvents: function (type, eventos) {
        const container = document.getElementById(`${type}-events`);
        if (!container) return;

        if (!eventos || eventos.length === 0) {
            container.innerHTML = '<div class="no-data">No hay eventos activos</div>';
            return;
        }

        // Ordenar eventos: no marcados primero, luego por hora descendente (más nuevos arriba)
        const sortedEventos = eventos.sort((a, b) => {
            const aChecked = this.isEventChecked(type, a.sitio);
            const bChecked = this.isEventChecked(type, b.sitio);

            if (aChecked !== bChecked) {
                return aChecked ? 1 : -1; // Checked events go to the end
            }

            // Si tienen el mismo estado de "revisado", ordenar por hora (más nuevo primero)
            return b.ultima_hora.localeCompare(a.ultima_hora);
        });

        container.innerHTML = '';
        sortedEventos.forEach(evento => {
            const eventDiv = document.createElement('div');
            const isChecked = this.isEventChecked(type, evento.sitio);
            eventDiv.className = `event-item ${this.getEventSeverity(evento.eventos)}${isChecked ? ' checked' : ''}`;

            let cameraButtons = '';
            if (type === 'access') {
                if (evento.cameras.has_camera) {
                    cameraButtons = `
                        <button class="camera-btn" 
                                onclick="DashboardManager.openCamera('${evento.sitio}', 'access', 'principal')">
                            <span class="camera-icon"></span> Ver Cámara
                        </button>`;
                } else {
                    cameraButtons = `
                        <button class="camera-btn disabled" title="No hay cámara disponible para este sitio">
                            <span class="camera-icon"></span> Sin Cámara
                        </button>`;
                }
            } else {
                if (evento.cameras.has_camera) {
                    cameraButtons = '<div class="camera-buttons-group">';
                    evento.cameras.available_positions.forEach(position => {
                        const positionNames = {
                            'principal': '🏢 Principal',
                            'patio': '🅿️ Patio',
                            'equipo': '🔌 Equipo',
                            'generador': '⚡ Generador'
                        };
                        const displayName = positionNames[position] || position;
                        cameraButtons += `
                            <button class="camera-btn" 
                                    onclick="DashboardManager.openCamera('${evento.sitio}', 'transport', '${position}')">
                                ${displayName}
                            </button>`;
                    });
                    cameraButtons += '</div>';
                } else {
                    cameraButtons = `
                        <button class="camera-btn disabled" title="No hay cámaras disponibles para este sitio">
                            <span class="camera-icon"></span> Sin Cámaras
                        </button>`;
                }
            }

            const perms = JSON.parse(localStorage.getItem('user_permissions') || '{}');
            const canInteract = perms.can_interact !== false; // Default to true if not set (for admin)

            eventDiv.innerHTML = `
                <input type="checkbox" 
                        class="event-checkbox" 
                        onchange="DashboardManager.toggleEventChecked('${type}', '${evento.sitio}', this)"
                        ${isChecked ? 'checked' : ''}
                        ${!canInteract ? 'disabled' : ''}
                        title="${!canInteract ? 'Sin permisos para editar' : 'Marcar como revisado'}">

                <div class="event-content">
                    <div class="site-name">${evento.sitio}</div>

                    <div class="event-types">
                    ${evento.eventos.join(', ')}

                    <button class="external-link-btn"
                            onclick="window.open(
                                'https://localizador-comi.onrender.com/?nodo=${encodeURIComponent(evento.sitio)}',
                                '_blank',
                                'width=1000,height=700,resizable=yes,scrollbars=yes'
                            )"
                            title="Police">
                        <i class="fas fa-shield-alt"></i> Police
                    </button>

                    ${cameraButtons}
                    </div>
                </div>
                `;
            container.appendChild(eventDiv);
        });


    },


    renderAnomalies: function (type, anomalias) {
        const container = document.getElementById(`${type}-anomalies`);
        if (!container) return;

        if (!anomalias || anomalias.length === 0) {
            container.innerHTML = '<div class="no-data">No hay anomalías detectadas</div>';
            return;
        }

        // Ordenar anomalías por última ocurrencia (más reciente arriba)
        const sortedAnomalias = [...anomalias].sort((a, b) => {
            return b.ultima_vez.localeCompare(a.ultima_vez);
        });

        container.innerHTML = '';
        sortedAnomalias.forEach(anomalia => {
            const anomalyDiv = document.createElement('div');
            anomalyDiv.className = 'anomaly-item';

            let cameraButtons = '';
            if (type === 'access') {
                if (anomalia.cameras.has_camera) {
                    cameraButtons = `
                        <button class="camera-btn" 
                                onclick="DashboardManager.openCamera('${anomalia.sitio}', 'access', 'principal')">
                            <span class="camera-icon"></span> Ver Cámara
                        </button>`;
                } else {
                    cameraButtons = `
                        <button class="camera-btn disabled" title="No hay cámara disponible para este sitio">
                            <span class="camera-icon"></span> Sin Cámara
                        </button>`;
                }
            } else {
                if (anomalia.cameras.has_camera) {
                    cameraButtons = '<div class="camera-buttons-group">';
                    anomalia.cameras.available_positions.forEach(position => {
                        const positionNames = {
                            'principal': '🏢 Principal',
                            'patio': '🅿️ Patio',
                            'equipo': '🔌 Equipo',
                            'generador': '⚡ Generador'
                        };
                        const displayName = positionNames[position] || position;
                        cameraButtons += `
                            <button class="camera-btn" 
                                    onclick="DashboardManager.openCamera('${anomalia.sitio}', 'transport', '${position}')">
                                ${displayName}
                            </button>`;
                    });
                    cameraButtons += '</div>';
                } else {
                    cameraButtons = `
                        <button class="camera-btn disabled" title="No hay cámaras disponibles para este sitio">
                            <span class="camera-icon"></span> Sin Cámaras
                        </button>`;
                }
            }

            anomalyDiv.innerHTML = `
                <div class="site-name">${anomalia.sitio}</div>
                <div class="anomaly-detail">
                    <strong>${anomalia.categoria}</strong>: ${anomalia.alarmameta}
                    <br>
                    <small>Repeticiones: ${anomalia.veces} veces</small>
                    ${cameraButtons}
                </div>`;
            container.appendChild(anomalyDiv);
        });


    },

    getEventSeverity: function (eventos) {
        const eventosStr = eventos.join(',');
        if (eventosStr.includes('🚨🚨')) return 'danger';
        if (eventosStr.includes('🚨')) return 'warning';
        if (eventosStr.includes('🚪')) return 'success';
        return '';
    },

    // Camera Status Checking
    checkAllCameraStatus: async function () {
        const buttons = document.querySelectorAll('.camera-btn[data-site]:not(.disabled)');
        const camerasToCheck = [];
        const buttonMap = new Map(); // Map key to button element

        // Collect all cameras to check
        for (const button of buttons) {
            const site = button.dataset.site;
            const type = button.dataset.type;
            const position = button.dataset.position || 'principal';

            if (site && type) {
                const key = `${site}|${type}|${position}`;
                camerasToCheck.push({ site, type, position });
                buttonMap.set(key, button);
                button.classList.add('status-checking');
            }
        }

        if (camerasToCheck.length === 0) return;

        try {
            // Send batch request
            const response = await fetch('/api/camera_status/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cameras: camerasToCheck })
            });
            const data = await response.json();

            // Process results
            if (data.results) {
                data.results.forEach(res => {
                    const key = `${res.site}|${res.type}|${res.position}`;
                    const button = buttonMap.get(key);
                    const statusData = res.status;

                    if (button) {
                        // Remove status classes
                        button.classList.remove('status-checking', 'status-online', 'status-no-config');

                        // Add new status
                        button.classList.add(`status-${statusData.status}`);
                        button.title = statusData.message || statusData.status;

                        if (statusData.status === 'no_config') {
                            button.disabled = true;
                            button.onclick = null;
                        }
                    }
                });
            }

        } catch (error) {
            console.error('Error checking camera batch status:', error);
            // Revert status on error
            buttonMap.forEach(button => {
                button.classList.remove('status-checking');
                button.classList.add('status-no-config');
            });
        }
    },

    checkCameraStatus: async function (button, site, type, position) {
        // Keep individual check for single updates if needed, logic is fine to leave as is
        // or could use batch endpoint 1 item.
        // ... existing implementation if needed ... or just remove if unused.
        // Keeping it for safety but checkAllCameraStatus is the main one.
        try {
            const response = await fetch(`/api/camera_status?site=${encodeURIComponent(site)}&type=${type}&position=${position}`);
            const data = await response.json();

            button.classList.remove('status-checking', 'status-online', 'status-no-config');
            button.classList.add(`status-${data.status}`);
            button.title = data.message || data.status;

            if (data.status === 'no_config') {
                button.disabled = true;
                button.onclick = null;
            }
        } catch (error) {
            console.error(`Error checking camera status for ${site}:`, error);
        }
    },

    // Modales y Cámaras
    openCamera: function (siteName, cameraType = "access", position = "principal") {
        const modal = document.getElementById('cameraModal');
        const modalTitle = document.getElementById('modalTitle');
        const cameraStream = document.getElementById('cameraStream');

        if (!modal || !modalTitle || !cameraStream) return;

        const positionNames = {
            'principal': 'Principal',
            'patio': 'Patio',
            'equipo': 'Equipo',
            'generador': 'Generador'
        };

        const displayPosition = positionNames[position] || position;

        if (cameraType === 'access') {
            modalTitle.textContent = `Cámara de Acceso - ${siteName}`;
            cameraStream.src = `/video_feed/${siteName}`;
        } else {
            modalTitle.textContent = `Cámara de Transporte - ${siteName} (${displayPosition})`;
            cameraStream.src = `/video_feed/transport/${siteName}/${position}`;
        }

        modal.style.display = 'flex';
    },

    closeCameraModal: function () {
        const modal = document.getElementById('cameraModal');
        const cameraStream = document.getElementById('cameraStream');

        if (cameraStream) cameraStream.src = '';
        if (modal) modal.style.display = 'none';
    },

    // Exportación
    exportarExcel: async function (tipo) {
        try {
            const buttons = document.querySelectorAll('.export-btn');
            let targetButton = null;

            if (tipo === 'access') {
                targetButton = buttons[0];
            } else {
                targetButton = buttons[1];
            }

            if (targetButton) {
                const originalHTML = targetButton.innerHTML;
                targetButton.innerHTML = '<span class="spinner"></span> Generando...';
                targetButton.disabled = true;

                const timeout = setTimeout(() => {
                    targetButton.innerHTML = originalHTML;
                    targetButton.disabled = false;
                }, 10000);

                try {
                    const response = await fetch(`/exportar/${tipo}`);
                    clearTimeout(timeout);

                    if (!response.ok) throw new Error(`Error ${response.status}`);

                    const blob = await response.blob();
                    if (blob.size === 0) throw new Error('Archivo vacío');

                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;

                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
                    a.download = `${tipo}_report_${timestamp}.xlsx`;

                    document.body.appendChild(a);
                    a.click();

                    setTimeout(() => {
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    }, 100);

                } catch (error) {
                    clearTimeout(timeout);
                    console.error(error);
                    alert(`Error exportando: ${error.message}`); // Fallback simple alert
                } finally {
                    targetButton.innerHTML = originalHTML;
                    targetButton.disabled = false;
                }
            }
        } catch (error) {
            console.error('Error exportando Excel:', error);
        }
    },

    setupEventListeners: function () {
        // Event Listeners
        const mainThemeToggle = document.getElementById('mainThemeToggle');
        const sidebarThemeToggle = document.getElementById('sidebarThemeToggle');

        if (mainThemeToggle) mainThemeToggle.addEventListener('click', () => this.toggleTheme());
        if (sidebarThemeToggle) sidebarThemeToggle.addEventListener('click', () => this.toggleTheme());

        document.querySelectorAll('.module-item').forEach(item => {
            item.addEventListener('click', () => {
                const moduleId = item.getAttribute('data-module');
                this.changeModule(moduleId);
            });
        });

        // Modal triggers
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeCameraModal();
        });

        const modal = document.getElementById('cameraModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'cameraModal') this.closeCameraModal();
            });
        }

        // Exponer funciones necesarias globalmente para los onclick del HTML
        // No ideal, pero necesario para compatibilidad con onclicks existentes si no se refactorizan
        // Exponer funciones necesarias globalmente para los onclick del HTML
        // No ideal, pero necesario para compatibilidad con onclicks existentes si no se refactorizan
        window.openCamera = (site, type, pos) => this.openCamera(site, type, pos);
        window.closeCameraModal = () => this.closeCameraModal();
        window.refreshData = () => this.refreshData();
        // Corregir referencia a exportarExcel que no es método de window sino del objeto
        window.exportarExcel = (t) => this.exportarExcel(t);

        // Lógica de colapsables del sidebar
        document.querySelectorAll('.module-group-title').forEach(title => {
            title.addEventListener('click', () => {
                const group = title.parentElement;
                group.classList.toggle('collapsed');
            });
        });

        // Highlight active module based on URL (Moved from base.html inline script)
        const currentPath = window.location.pathname;
        document.querySelectorAll('.module-item').forEach(item => {
            item.classList.remove('active');
            if (currentPath === '/' && item.dataset.module === 'dashboard') {
                item.classList.add('active');
            } else if (currentPath === '/camera_list' && item.dataset.module === 'camera-list') {
                item.classList.add('active');
            }
        });
    },
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    DashboardManager.init();
});
