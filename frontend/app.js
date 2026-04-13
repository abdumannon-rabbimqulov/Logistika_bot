const tg = window.Telegram.WebApp;
tg.expand();

// DOM elements
const totalUsersEl = document.getElementById('total-users');
const truckTypesCountEl = document.getElementById('truck-types-count');
const usersTbody = document.getElementById('users-tbody');
const truckTypesTbody = document.getElementById('truck-types-tbody');
const adminNameEl = document.getElementById('admin-name');

// Tabs and Sections
const tabUsers = document.getElementById('tab-users');
const tabTruckTypes = document.getElementById('tab-truck-types');
const sectionUsers = document.getElementById('section-users');
const sectionTruckTypes = document.getElementById('section-truck-types');

// Modal Elements
const truckModal = document.getElementById('truck-modal');
const addTruckBtn = document.getElementById('add-truck-type-btn');
const closeModalBtn = document.getElementById('close-modal');
const truckForm = document.getElementById('truck-type-form');

// App start
function init() {
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        adminNameEl.innerText = tg.initDataUnsafe.user.first_name + ' (Admin)';
    }

    tabUsers.classList.add('active');
    fetchStats();
    fetchUsers();
    fetchTruckTypes();

    setupEventListeners();
}

function setupEventListeners() {
    // Tab switching
    tabUsers.addEventListener('click', () => switchTab('users'));
    tabTruckTypes.addEventListener('click', () => switchTab('truck-types'));

    // Refresh buttons
    document.querySelectorAll('.refresh-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            fetchStats();
            fetchUsers();
            fetchTruckTypes();
        });
    });

    // Modal
    addTruckBtn.addEventListener('click', () => truckModal.style.display = 'block');
    closeModalBtn.addEventListener('click', () => truckModal.style.display = 'none');
    window.addEventListener('click', (e) => {
        if (e.target === truckModal) truckModal.style.display = 'none';
    });

    // Form submission
    truckForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(truckForm);
        const data = Object.fromEntries(formData.entries());
        
        try {
            const response = await fetch('/api/driver/truck-type-create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) {
                tg.HapticFeedback.notificationOccurred('success');
                truckModal.style.display = 'none';
                truckForm.reset();
                fetchTruckTypes();
            }
        } catch (error) {
            console.error('Create error:', error);
            tg.HapticFeedback.notificationOccurred('error');
        }
    });
}

function switchTab(tab) {
    if (tab === 'users') {
        tabUsers.classList.add('active');
        tabTruckTypes.classList.remove('active');
        sectionUsers.style.display = 'block';
        sectionTruckTypes.style.display = 'none';
    } else {
        tabUsers.classList.remove('active');
        tabTruckTypes.classList.add('active');
        sectionUsers.style.display = 'none';
        sectionTruckTypes.style.display = 'block';
    }
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        totalUsersEl.innerText = data.total_users;
    } catch (error) {}
}

async function fetchUsers() {
    try {
        const response = await fetch('/api/users');
        const users = await response.json();
        renderUsers(users);
    } catch (error) {}
}

async function fetchTruckTypes() {
    try {
        const response = await fetch('/api/driver/truck-type-get_all');
        const types = await response.json();
        truckTypesCountEl.innerText = types.length;
        renderTruckTypes(types);
    } catch (error) {}
}

function renderUsers(users) {
    usersTbody.innerHTML = '';
    users.forEach(user => {
        const tr = document.createElement('tr');
        const statusClass = user.is_banned ? 'status-banned' : 'status-active';
        const statusText = user.is_banned ? 'Bloklangan' : 'Faol';
        const actionBtn = user.is_banned 
            ? `<button class="action-btn unban-btn" onclick="toggleBan(${user.id}, false)">🔓 O'chirish</button>`
            : `<button class="action-btn ban-btn" onclick="toggleBan(${user.id}, true)">🚫 Bloklash</button>`;

        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.full_name}</td>
            <td>@${user.username || '-'}</td>
            <td><span class="role-badge">${user.role}</span></td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td>${actionBtn}</td>
        `;
        usersTbody.appendChild(tr);
    });
}

function renderTruckTypes(types) {
    truckTypesTbody.innerHTML = '';
    types.forEach(type => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${type.id}</td>
            <td>${type.name}</td>
            <td>${type.max_weight} t</td>
            <td>${type.max_volume} m³</td>
            <td>
                <button class="action-btn ban-btn" onclick="deleteTruckType(${type.id})">🗑️ O'chirish</button>
            </td>
        `;
        truckTypesTbody.appendChild(tr);
    });
}

async function toggleBan(userId, shouldBan) {
    const endpoint = shouldBan ? `/api/users/${userId}/ban` : `/api/users/${userId}/unban`;
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        if (response.ok) {
            tg.HapticFeedback.notificationOccurred('success');
            fetchUsers();
        }
    } catch (error) {}
}

async function deleteTruckType(pk) {
    if (!confirm('Haqiqatdan ham o\'chirmoqchimisiz?')) return;
    try {
        const response = await fetch(`/api/driver/delete_truck_type/${pk}`, { method: 'DELETE' });
        if (response.ok) {
            tg.HapticFeedback.notificationOccurred('success');
            fetchTruckTypes();
        }
    } catch (error) {}
}

init();
