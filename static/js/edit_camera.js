document.addEventListener('DOMContentLoaded', () => {
    let currentTab = 'access';
    let camerasData = { access: [], transport: [] };

    // Elements
    const accessBtn = document.querySelector('[data-target="access-tab"]');
    const transBtn = document.querySelector('[data-target="transport-tab"]');
    const accessTab = document.getElementById('access-tab');
    const transTab = document.getElementById('transport-tab');
    const accessBody = document.getElementById('access-table-body');
    const transportBody = document.getElementById('transport-table-body');
    
    const modal = document.getElementById('cameraModal');
    const closeModal = document.getElementById('closeModal');
    const form = document.getElementById('cameraForm');
    
    // Switch tabs
    accessBtn.addEventListener('click', () => {
        currentTab = 'access';
        accessTab.style.display = 'block';
        transTab.style.display = 'none';
        accessBtn.classList.add('active');
        accessBtn.style.background = 'var(--yofc-pink)';
        accessBtn.style.color = 'white';
        accessBtn.style.border = 'none';
        
        transBtn.classList.remove('active');
        transBtn.style.background = 'var(--card-bg)';
        transBtn.style.color = 'var(--text-color)';
        transBtn.style.border = '1px solid var(--border-color)';
    });

    transBtn.addEventListener('click', () => {
        currentTab = 'transport';
        transTab.style.display = 'block';
        accessTab.style.display = 'none';
        transBtn.classList.add('active');
        transBtn.style.background = 'var(--yofc-pink)';
        transBtn.style.color = 'white';
        transBtn.style.border = 'none';
        
        accessBtn.classList.remove('active');
        accessBtn.style.background = 'var(--card-bg)';
        accessBtn.style.color = 'var(--text-color)';
        accessBtn.style.border = '1px solid var(--border-color)';
    });

    // Load Data
    async function loadCameras() {
        try {
            const res = await fetch('/cameras', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
                }
            });
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            const data = await res.json();
            camerasData = data;
            
            // Populate Position dropdown with unique positions from DB
            const positionSelect = document.getElementById('camPosition');
            if (positionSelect && data.transport) {
                const uniquePositions = [...new Set(data.transport.map(c => c.position).filter(p => p))];
                const defaults = ['principal', 'patio', 'equipo', 'generador', 'prin'];
                const allPositions = [...new Set([...defaults, ...uniquePositions])].sort();
                
                // Clear existing and add "Select" option
                positionSelect.innerHTML = '<option value="">Seleccione posición...</option>';
                allPositions.forEach(pos => {
                    const opt = document.createElement('option');
                    opt.value = pos;
                    opt.textContent = pos.charAt(0).toUpperCase() + pos.slice(1);
                    positionSelect.appendChild(opt);
                });
            }
            
            renderTables();
        } catch (e) {
            console.error(e);
            alert('Failed to load cameras: ' + e.message + '\n\n' + e.stack);
        }
    }

    const searchInput = document.getElementById('cameraSearch');
    let searchTerm = '';

    searchInput.addEventListener('input', (e) => {
        searchTerm = e.target.value.toLowerCase();
        renderTables();
    });

    function renderTables() {
        // Filter logic
        const accFilter = camerasData.access.filter(c => 
            (c.site && c.site.toLowerCase().includes(searchTerm)) || 
            (c.ip && c.ip.toLowerCase().includes(searchTerm)) ||
            (c.id && c.id.toString().includes(searchTerm))
        );
        
        const transFilter = camerasData.transport.filter(c => 
            (c.site && c.site.toLowerCase().includes(searchTerm)) || 
            (c.ip && c.ip.toLowerCase().includes(searchTerm)) ||
            (c.id && c.id.toString().includes(searchTerm)) ||
            (c.position && c.position.toLowerCase().includes(searchTerm))
        );

        // Access Table (Optimized String Rendering)
        if (!accFilter || accFilter.length === 0) {
            accessBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px;">No access cameras found.</td></tr>';
        } else {
            const accRows = accFilter.sort((a,b)=> a.id - b.id).map(cam => `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 12px; font-weight:bold;">#${cam.id}</td>
                    <td style="padding: 12px;">${cam.site || ''}</td>
                    <td style="padding: 12px; color: var(--yofc-blue); font-weight:bold;">${cam.ip || ''}</td>
                    <td style="padding: 12px; text-align: right;">
                        <button class="btn btn-edit" data-id="${cam.id}" data-type="access" style="background:#f39c12; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-delete" data-id="${cam.id}" data-type="access" style="background:#e74c3c; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
            accessBody.innerHTML = accRows;
        }

        // Transport Table (Optimized String Rendering)
        if (!transFilter || transFilter.length === 0) {
            transportBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">No transport cameras found.</td></tr>';
        } else {
            const transRows = transFilter.sort((a,b)=> a.id - b.id).map(cam => `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 12px; font-weight:bold;">#${cam.id}</td>
                    <td style="padding: 12px;">${cam.site || ''}</td>
                    <td style="padding: 12px;">${cam.position || ''}</td>
                    <td style="padding: 12px; color: var(--yofc-blue); font-weight:bold;">${cam.ip || ''}</td>
                    <td style="padding: 12px; text-align: right;">
                        <button class="btn btn-edit" data-id="${cam.id}" data-type="transport" style="background:#f39c12; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-delete" data-id="${cam.id}" data-type="transport" style="background:#e74c3c; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
            transportBody.innerHTML = transRows;
        }
        
        attachRowListeners();
    }

    // Modal Logic
    document.querySelectorAll('.add-cam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const type = e.currentTarget.dataset.type;
            document.getElementById('modalTitle').innerText = `Add ${type === 'access' ? 'Access' : 'Transport'} Camera`;
            document.getElementById('camAction').value = 'create';
            document.getElementById('camType').value = type;
            document.getElementById('camId').value = '';
            document.getElementById('camSite').value = '';
            document.getElementById('camIp').value = '';
            
            if (type === 'transport') {
                document.getElementById('positionContainer').style.display = 'block';
                document.getElementById('camPosition').value = '';
                document.getElementById('camPosition').required = true;
            } else {
                document.getElementById('positionContainer').style.display = 'none';
                document.getElementById('camPosition').required = false;
            }
            
            modal.style.display = 'flex';
        });
    });

    closeModal.addEventListener('click', () => { modal.style.display = 'none'; });

    // Handle Edit & Delete clicks
    function attachRowListeners() {
        document.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.dataset.id);
                const type = e.currentTarget.dataset.type;
                const camList = type === 'access' ? camerasData.access : camerasData.transport;
                const cam = camList.find(c => c.id === id);
                if (!cam) return;

                document.getElementById('modalTitle').innerText = 'Edit Camera';
                document.getElementById('camAction').value = 'edit';
                document.getElementById('camType').value = type;
                document.getElementById('camId').value = cam.id;
                document.getElementById('camSite').value = cam.site;
                document.getElementById('camIp').value = cam.ip;
                
                if (type === 'transport') {
                    document.getElementById('positionContainer').style.display = 'block';
                    document.getElementById('camPosition').value = cam.position;
                    document.getElementById('camPosition').required = true;
                } else {
                    document.getElementById('positionContainer').style.display = 'none';
                    document.getElementById('camPosition').required = false;
                }
                
                modal.style.display = 'flex';
            });
        });

        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = parseInt(e.currentTarget.dataset.id);
                const type = e.currentTarget.dataset.type;
                
                const result = await Swal.fire({
                    title: 'Delete Camera?',
                    text: 'Are you sure you want to delete this camera?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#e74c3c',
                    confirmButtonText: 'Yes, delete it'
                });
                
                if (result.isConfirmed) {
                    await manageCamera({ action: 'delete', type, id });
                }
            });
        });
    }

    // Submit form
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const payload = {
            action: document.getElementById('camAction').value,
            type: document.getElementById('camType').value,
            id: document.getElementById('camId').value,
            site: document.getElementById('camSite').value,
            ip: document.getElementById('camIp').value,
            position: document.getElementById('camPosition').value
        };

        const success = await manageCamera(payload);
        if (success) {
            modal.style.display = 'none';
        }
    });

    async function manageCamera(payload) {
        try {
            const res = await fetch('/api/cameras/manage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`
                },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            
            if (res.ok && data.success) {
                Swal.fire('Success', 'Camera saved successfully', 'success');
                loadCameras();
                return true;
            } else {
                Swal.fire('Error', data.error || 'Failed to manage camera', 'error');
                return false;
            }
        } catch (e) {
            Swal.fire('Error', e.message, 'error');
            return false;
        }
    }

    // Init
    loadCameras();
});
