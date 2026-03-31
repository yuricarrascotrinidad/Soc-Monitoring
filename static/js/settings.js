const SettingsManager = {
    state: {
        users: [],
        roles: [],
        currentTab: 'users'
    },

    init: function() {
        this.loadUsers();
        this.loadRoles();
        this.setupForms();
    },

    switchTab: function(tab) {
        this.state.currentTab = tab;
        document.getElementById('section-users').style.display = tab === 'users' ? 'block' : 'none';
        document.getElementById('section-roles').style.display = tab === 'roles' ? 'block' : 'none';
        
        // Update tabs style
        const activeStyle = { background: 'var(--primary-color)', color: 'white' };
        const inactiveStyle = { background: 'var(--stat-card-bg)', color: 'var(--text-color)' };
        
        Object.assign(document.getElementById('tab-users').style, tab === 'users' ? activeStyle : inactiveStyle);
        Object.assign(document.getElementById('tab-roles').style, tab === 'roles' ? activeStyle : inactiveStyle);
    },

    loadUsers: async function() {
        try {
            const response = await fetch('/admin/users');
            if (response.ok) {
                this.state.users = await response.json();
                this.renderUsers();
            }
        } catch (error) { console.error('Error loading users:', error); }
    },

    loadRoles: async function() {
        try {
            const response = await fetch('/admin/roles');
            if (response.ok) {
                this.state.roles = await response.json();
                this.renderRoles();
                this.populateRoleSelectors();
            }
        } catch (error) { console.error('Error loading roles:', error); }
    },

    renderUsers: function() {
        const tbody = document.getElementById('users-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        this.state.users.forEach(user => {
            const tr = document.createElement('tr');
            const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || '---';
            const permsHtml = Object.entries(user.permissions || {})
                .filter(([name, enabled]) => enabled && name !== 'api_access')
                .map(([name, _]) => `<span class="perm-pill">${name}</span>`)
                .join('');
            
            tr.innerHTML = `
                <td><strong>${user.username}</strong></td>
                <td>${fullName}</td>
                <td><span class="role-badge role-${user.role}">${user.role}</span></td>
                <td>${permsHtml}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-action btn-edit" onclick="SettingsManager.editUser(${user.id})"><i class="fas fa-edit"></i></button>
                    ${user.username !== 'admin' ? `<button class="btn-action btn-delete" onclick="SettingsManager.deleteUser(${user.id})"><i class="fas fa-trash"></i></button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    renderRoles: function() {
        const tbody = document.getElementById('roles-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        this.state.roles.forEach(role => {
            const tr = document.createElement('tr');
            const permsHtml = Object.entries(role.permissions || {})
                .filter(([_, enabled]) => enabled)
                .map(([name, _]) => `<span class="perm-pill">${name}</span>`)
                .join('');
            
            tr.innerHTML = `
                <td><strong>${role.name}</strong></td>
                <td>${permsHtml}</td>
                <td>
                    <button class="btn-action btn-edit" onclick="SettingsManager.editRole(${role.id})"><i class="fas fa-edit"></i></button>
                    ${!['admin', 'soc', 'viewer'].includes(role.name) ? `<button class="btn-action btn-delete" onclick="SettingsManager.deleteRole(${role.id})"><i class="fas fa-trash"></i></button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    populateRoleSelectors: function() {
        const select = document.getElementById('role');
        if (!select) return;
        const currentVal = select.value;
        select.innerHTML = this.state.roles.map(r => `<option value="${r.name}">${r.name}</option>`).join('');
        if (currentVal) select.value = currentVal;
    },

    setupForms: function() {
        // User Form
        document.getElementById('userForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('userId').value;
            const role = document.getElementById('role').value;
            const permissions = {};
            document.querySelectorAll('#user-perms-grid input').forEach(cb => {
                permissions[cb.dataset.perm] = cb.checked;
            });

            // Handle API Access if it's a customer
            if (role === 'customer') {
                permissions.api_access = {};
                document.querySelectorAll('#api-perms-grid input').forEach(cb => {
                    permissions.api_access[cb.dataset.api] = cb.checked;
                });
            }

            const data = {
                username: document.getElementById('username').value,
                first_name: document.getElementById('first_name').value,
                last_name: document.getElementById('last_name').value,
                role: role,
                permissions: permissions
            };
            const pass = document.getElementById('password').value;
            if (pass) data.password = pass;

            const res = await fetch(id ? `/admin/users/${id}` : '/admin/users', {
                method: id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) { this.closeModal(); this.loadUsers(); }
            else { alert((await res.json()).msg); }
        });

        // Role Form
        document.getElementById('roleForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('roleId').value;
            const permissions = {};
            document.querySelectorAll('#role-perms-grid input').forEach(cb => {
                permissions[cb.dataset.perm] = cb.checked;
            });
            const data = {
                name: document.getElementById('roleName').value,
                permissions: permissions
            };

            const res = await fetch(id ? `/admin/roles/${id}` : '/admin/roles', {
                method: id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) { this.closeRoleModal(); this.loadRoles(); }
            else { alert((await res.json()).msg); }
        });
    },

    // User Modals
    openCreateModal: function() {
        this.resetUserForm();
        document.getElementById('userModal').style.display = 'flex';
    },

    editUser: function(id) {
        const user = this.state.users.find(u => u.id === id);
        if (!user) return;
        document.getElementById('modalTitle').textContent = `Edit User: ${user.username}`;
        document.getElementById('userId').value = user.id;
        document.getElementById('username').value = user.username;
        document.getElementById('username').disabled = true;
        document.getElementById('first_name').value = user.first_name || '';
        document.getElementById('last_name').value = user.last_name || '';
        document.getElementById('role').value = user.role;
        
        // Permissions
        document.querySelectorAll('#user-perms-grid input').forEach(cb => {
            cb.checked = user.permissions[cb.dataset.perm] || false;
        });

        // API Permissions
        if (user.role === 'customer' && user.permissions.api_access) {
            document.querySelectorAll('#api-perms-grid input').forEach(cb => {
                cb.checked = user.permissions.api_access[cb.dataset.api] || false;
            });
        }
        
        this.applyRoleDefaults(); // To show/hide API section
        document.getElementById('userModal').style.display = 'flex';
    },

    resetUserForm: function() {
        document.getElementById('modalTitle').textContent = 'Create New User';
        document.getElementById('userId').value = '';
        document.getElementById('username').value = '';
        document.getElementById('username').disabled = false;
        document.getElementById('first_name').value = '';
        document.getElementById('last_name').value = '';
        document.getElementById('password').value = '';
        document.getElementById('role').value = 'viewer';
        this.applyRoleDefaults();
    },

    applyRoleDefaults: function() {
        const roleName = document.getElementById('role').value;
        const role = this.state.roles.find(r => r.name === roleName);
        
        // Show/Hide API section
        const apiSection = document.getElementById('api-access-section');
        if (apiSection) apiSection.style.display = (roleName === 'customer') ? 'block' : 'none';

        if (role) {
            document.querySelectorAll('#user-perms-grid input').forEach(cb => {
                cb.checked = role.permissions[cb.dataset.perm] || false;
            });
            
            if (roleName === 'customer' && role.permissions.api_access) {
                document.querySelectorAll('#api-perms-grid input').forEach(cb => {
                    cb.checked = role.permissions.api_access[cb.dataset.api] || false;
                });
            }
        }
    },

    deleteUser: async function(id) {
        if (!confirm('Eliminar usuario?')) return;
        const res = await fetch(`/admin/users/${id}`, { method: 'DELETE' });
        if (res.ok) this.loadUsers();
    },

    // Role Modals
    openRoleModal: function() {
        document.getElementById('roleModalTitle').textContent = 'Create New Role';
        document.getElementById('roleId').value = '';
        document.getElementById('roleName').value = '';
        document.getElementById('roleName').disabled = false;
        document.querySelectorAll('#role-perms-grid input').forEach(cb => cb.checked = false);
        document.getElementById('roleModal').style.display = 'flex';
    },

    editRole: function(id) {
        const role = this.state.roles.find(r => r.id === id);
        if (!role) return;
        document.getElementById('roleModalTitle').textContent = `Edit Role: ${role.name}`;
        document.getElementById('roleId').value = role.id;
        document.getElementById('roleName').value = role.name;
        document.getElementById('roleName').disabled = ['admin', 'soc', 'viewer'].includes(role.name);
        document.querySelectorAll('#role-perms-grid input').forEach(cb => {
            cb.checked = role.permissions[cb.dataset.perm] || false;
        });
        document.getElementById('roleModal').style.display = 'flex';
    },

    deleteRole: async function(id) {
        if (!confirm('Eliminar rol?')) return;
        const res = await fetch(`/admin/roles/${id}`, { method: 'DELETE' });
        if (res.ok) {
            this.loadRoles();
            this.loadUsers(); // Users might be affected
        }
    },

    closeModal: () => document.getElementById('userModal').style.display = 'none',
    closeRoleModal: () => document.getElementById('roleModal').style.display = 'none'
};

// Global exports
window.openCreateModal = () => SettingsManager.openCreateModal();
window.closeModal = () => SettingsManager.closeModal();
window.openRoleModal = () => SettingsManager.openRoleModal();
window.closeRoleModal = () => SettingsManager.closeRoleModal();
window.applyRoleDefaults = () => SettingsManager.applyRoleDefaults();

document.addEventListener('DOMContentLoaded', () => SettingsManager.init());
