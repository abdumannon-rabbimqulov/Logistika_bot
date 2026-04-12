// Mock State
let state = {
    user: {
        name: "Abdumannon",
        balance: 1250400,
        orders: []
    }
};

// Loader
window.addEventListener('load', () => {
    setTimeout(() => {
        const loader = document.getElementById('loader');
        const app = document.getElementById('app');
        if(loader) loader.style.display = 'none';
        if(app) app.style.display = 'block';
    }, 1500);
});

// View Management
function switchView(viewId) {
    const views = document.querySelectorAll('.view');
    const navItems = document.querySelectorAll('.nav-item');
    
    views.forEach(v => v.classList.remove('active'));
    navItems.forEach(n => n.classList.remove('active'));
    
    const target = document.getElementById(viewId);
    if(target) target.classList.add('active');
    
    // Simple nav mapping
    if(viewId === 'home' && navItems[0]) navItems[0].classList.add('active');
    if(viewId === 'create_order' && navItems[1]) navItems[1].classList.add('active');
    if(viewId === 'orders' && navItems[2]) navItems[2].classList.add('active');
}

// Mock Action
function mockCreateOrder() {
    const from = document.querySelector('input[placeholder="Shahar yoki viloyat"]').value;
    const to = document.querySelector('input[placeholder="Manzilni kiriting"]').value;
    const weight = document.querySelector('input[placeholder="5.0"]').value;
    const price = document.querySelector('input[placeholder="500,000"]').value;
    
    if(!from || !to || !weight || !price) {
        alert("Iltimos barcha maydonlarni to'ldiring!");
        return;
    }

    const newOrder = {
        id: Date.now(),
        from,
        to,
        weight,
        price,
        status: 'Qabul qilindi'
    };

    state.user.orders.unshift(newOrder);
    renderOrders();
    
    // Feedback
    alert("Buyurtma muvaffaqiyatli yaratildi (Mock)!");
    switchView('home');
}

function renderOrders() {
    const list = document.getElementById('user-orders-list');
    if(!list) return;
    if (state.user.orders.length === 0) {
        list.innerHTML = '<div class="empty-state">Hali buyurtmalar yo\'q</div>';
        return;
    }

    list.innerHTML = state.user.orders.map(o => `
        <div class="load-card">
            <div class="load-info">
                <strong>Yuk (${o.weight}t)</strong>
                <span>${o.from} → ${o.to}</span>
            </div>
            <div class="load-price">${o.price}</div>
        </div>
    `).join('');
}

// Initialize
renderOrders();
// Set balance
const balEl = document.getElementById('balance');
if(balEl) {
    balEl.textContent = state.user.balance.toLocaleString() + " UZS";
}
