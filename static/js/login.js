document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const errorMsg = document.getElementById('errorMsg');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // Limpiar errores y poner estado de carga
        errorMsg.style.display = 'none';
        loginBtn.classList.add('loading');

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                // Guardar token y datos en localStorage
                localStorage.setItem('jwt_token', data.access_token);
                localStorage.setItem('user_role', data.role);
                localStorage.setItem('user_permissions', JSON.stringify(data.permissions));
                localStorage.setItem('user_first_name', data.first_name || '');
                localStorage.setItem('user_last_name', data.last_name || '');
                
                // Redirigir al dashboard
                window.location.href = '/dashboard';
            } else {
                errorMsg.textContent = data.msg || 'Error de autenticación';
                errorMsg.style.display = 'block';
            }
        } catch (error) {
            console.error('Login error:', error);
            errorMsg.textContent = 'Error de conexión con el servidor';
            errorMsg.style.display = 'block';
        } finally {
            loginBtn.classList.remove('loading');
        }
    });
});
