const API_BASE_URL = 'http://localhost:8000';

// Утилиты
function getUserId() {
    return localStorage.getItem('user_id');
}

function getAuthHeaders() {
    return {
        'Authorization': `Bearer ${getUserId()}`,
        'Content-Type': 'application/json'
    };
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Auth функции
function handleRegister(event) {
    event.preventDefault();
    
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    
    const data = {
        email: form.email.value,
        password: form.password.value,
        name: form.name.value
    };
    
    fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Успешно! Перенаправление...', 'success');
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 1500);
        } else {
            showNotification(data.error || 'Ошибка регистрации', 'error');
            button.disabled = false;
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
        button.disabled = false;
    });
}

function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    
    const data = {
        email: form.email.value,
        password: form.password.value
    };
    
    fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.setItem('user_id', data.data.user_id);
            localStorage.setItem('user_name', data.data.name);
            showNotification('Вход выполнен!', 'success');
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        } else {
            showNotification(data.error || 'Неверный email или пароль', 'error');
            button.disabled = false;
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
        button.disabled = false;
    });
}

function handleLogout() {
    localStorage.clear();
    window.location.href = 'login.html';
}

// API Keys функции
function loadApiKeys() {
    fetch(`${API_BASE_URL}/api-keys`, {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderApiKeys(data.data);
            updateApiKeySelect(data.data);
        } else {
            showNotification(data.error || 'Ошибка загрузки ключей', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

function renderApiKeys(keys) {
    const tbody = document.getElementById('apiKeysBody');
    
    if (keys.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Нет API ключей</td></tr>';
        return;
    }
    
    tbody.innerHTML = keys.map(key => `
        <tr>
            <td>${key.id}</td>
            <td>${key.nickname}</td>
            <td>${key.exchange || 'Bybit'}</td>
            <td>
                <button class="btn btn-error btn-small" onclick="handleDeleteApiKey(${key.id})">Удалить</button>
            </td>
        </tr>
    `).join('');
}

function updateApiKeySelect(keys) {
    const select = document.getElementById('apiKeySelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Выберите ключ</option>' + 
        keys.map(key => `<option value="${key.id}">${key.nickname}</option>`).join('');
}

function handleAddApiKey(event) {
    event.preventDefault();
    
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    
    const data = {
        nickname: form.nickname.value,
        api_key: form.api_key.value,
        api_secret: form.api_secret.value
    };
    
    fetch(`${API_BASE_URL}/api-keys`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('API ключ добавлен', 'success');
            form.reset();
            loadApiKeys();
        } else {
            showNotification(data.error || 'Ошибка добавления ключа', 'error');
        }
        button.disabled = false;
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
        button.disabled = false;
    });
}

function handleDeleteApiKey(keyId) {
    if (!confirm('Удалить этот API ключ?')) return;
    
    fetch(`${API_BASE_URL}/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('API ключ удален', 'success');
            loadApiKeys();
        } else {
            showNotification(data.error || 'Ошибка удаления ключа', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

// Bots функции
let botsUpdateInterval;

function loadBots() {
    fetch(`${API_BASE_URL}/bots`, {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            renderBots(data.data);
        } else {
            showNotification(data.error || 'Ошибка загрузки ботов', 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки ботов:', error);
    });
}

function renderBots(bots) {
    const tbody = document.getElementById('botsBody');
    
    if (bots.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Нет ботов</td></tr>';
        return;
    }
    
    tbody.innerHTML = bots.map(bot => {
        const statusIcon = bot.status === 'running' ? '🟢' : '🔴';
        const statusClass = bot.status === 'running' ? 'status-running' : 'status-stopped';
        const statusText = bot.status === 'running' ? 'Running' : 'Stopped';
        
        const actionButtons = bot.status === 'running' 
            ? `<button class="btn btn-error btn-small" onclick="handleStopBot(${bot.id})">Остановить</button>`
            : `<button class="btn btn-success btn-small" onclick="handleStartBot(${bot.id})">Запустить</button>`;
        
        return `
            <tr>
                <td>${bot.id}</td>
                <td>${bot.name}</td>
                <td>${bot.trading_pair}</td>
                <td class="${statusClass}">${statusIcon} ${statusText}</td>
                <td>
                    ${actionButtons}
                    <button class="btn btn-secondary btn-small" onclick="handleShowLogs(${bot.id})">Логи</button>
                    <button class="btn btn-error btn-small" onclick="handleDeleteBot(${bot.id})">Удалить</button>
                </td>
            </tr>
        `;
    }).join('');
}

function handleCreateBot(event) {
    event.preventDefault();
    
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    
    const formData = new FormData(form);
    const data = {
        api_key_id: parseInt(formData.get('api_key_id')),
        name: formData.get('name'),
        trading_pair: formData.get('trading_pair'),
        strategy: formData.get('strategy'),
        leverage: parseInt(formData.get('leverage')),
        deposit: parseFloat(formData.get('deposit')),
        take_profit_percent: parseFloat(formData.get('take_profit_percent')),
        stop_loss_percent: parseFloat(formData.get('stop_loss_percent')),
        indicators: [
            {
                type: 'RSI',
                timeframe: formData.get('rsi_timeframe'),
                period: parseInt(formData.get('rsi_period')),
                threshold: parseFloat(formData.get('rsi_threshold')),
                direction: formData.get('rsi_direction')
            },
            {
                type: 'CCI',
                timeframe: formData.get('cci_timeframe'),
                period: parseInt(formData.get('cci_period')),
                threshold: parseFloat(formData.get('cci_threshold')),
                direction: formData.get('cci_direction')
            }
        ]
    };
    
    fetch(`${API_BASE_URL}/bots`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const botId = data.data.bot_id;
            return fetch(`${API_BASE_URL}/bots/${botId}/start`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
        } else {
            throw new Error(data.error || 'Ошибка создания бота');
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Бот создан и запущен!', 'success');
            form.reset();
            loadBots();
        } else {
            showNotification(data.error || 'Бот создан, но не запущен', 'error');
            loadBots();
        }
        button.disabled = false;
    })
    .catch(error => {
        showNotification(error.message || 'Ошибка подключения к серверу', 'error');
        button.disabled = false;
    });
}

function handleStartBot(botId) {
    fetch(`${API_BASE_URL}/bots/${botId}/start`, {
        method: 'POST',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Бот запущен', 'success');
            loadBots();
        } else {
            showNotification(data.error || 'Ошибка запуска бота', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

function handleStopBot(botId) {
    fetch(`${API_BASE_URL}/bots/${botId}/stop`, {
        method: 'POST',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Бот остановлен', 'success');
            loadBots();
        } else {
            showNotification(data.error || 'Ошибка остановки бота', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

function handleDeleteBot(botId) {
    if (!confirm('Удалить этого бота?')) return;
    
    fetch(`${API_BASE_URL}/bots/${botId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Бот удален', 'success');
            loadBots();
        } else {
            showNotification(data.error || 'Ошибка удаления бота', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

function handleShowLogs(botId) {
    fetch(`${API_BASE_URL}/bots/${botId}/logs`, {
        headers: getAuthHeaders()
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const modal = document.getElementById('logsModal');
            const logsContent = document.getElementById('logsContent');
            logsContent.textContent = data.data.logs || 'Нет логов';
            modal.style.display = 'block';
        } else {
            showNotification(data.error || 'Ошибка загрузки логов', 'error');
        }
    })
    .catch(error => {
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    const page = path.split('/').pop();
    
    // Регистрация
    if (page === 'index.html' || page === '') {
        const form = document.getElementById('registerForm');
        if (form) {
            form.addEventListener('submit', handleRegister);
        }
    }
    
    // Вход
    if (page === 'login.html') {
        const form = document.getElementById('loginForm');
        if (form) {
            form.addEventListener('submit', handleLogin);
        }
    }
    
    // Dashboard
    if (page === 'dashboard.html') {
        // Проверка авторизации
        if (!getUserId()) {
            window.location.href = 'login.html';
            return;
        }
        
        // Отображение имени пользователя
        const userName = localStorage.getItem('user_name') || 'Пользователь';
        document.getElementById('userName').textContent = `Привет, ${userName}`;
        
        // Обработчики
        document.getElementById('logoutBtn').addEventListener('click', handleLogout);
        document.getElementById('addApiKeyForm').addEventListener('submit', handleAddApiKey);
        document.getElementById('createBotForm').addEventListener('submit', handleCreateBot);
        
        // Модальное окно логов
        const modal = document.getElementById('logsModal');
        const closeBtn = document.querySelector('.close');
        closeBtn.onclick = () => modal.style.display = 'none';
        window.onclick = (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };
        
        // Загрузка данных
        loadApiKeys();
        loadBots();
        
        // Автообновление списка ботов каждые 5 секунд
        botsUpdateInterval = setInterval(loadBots, 5000);
    }
});

// Очистка интервала при закрытии страницы
window.addEventListener('beforeunload', () => {
    if (botsUpdateInterval) {
        clearInterval(botsUpdateInterval);
    }
});
