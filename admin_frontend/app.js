const API_BASE = '/';
let authToken = localStorage.getItem('adminToken');

const els = {
    authContainer: document.getElementById('auth-container'),
    appContainer: document.getElementById('app-container'),
    loginForm: document.getElementById('login-form'),
    logoutBtn: document.getElementById('logout-btn'),
    navLinks: document.querySelectorAll('.nav-links li'),
    sections: document.querySelectorAll('.view-section'),
    toast: document.getElementById('toast'),
    
    // Exercises
    exForm: document.getElementById('exercise-form'),
    
    // Announcements
    annForm: document.getElementById('announcement-form'),
    annList: document.getElementById('ann-list'),
    
    // Inquiries
    inqList: document.getElementById('inq-list')
};

function showToast(msg, isError = false) {
    els.toast.textContent = msg;
    els.toast.style.borderLeft = `4px solid var(--${isError ? 'danger' : 'success'})`;
    els.toast.classList.add('show');
    setTimeout(() => els.toast.classList.remove('show'), 3000);
}

function init() {
    if (authToken) {
        els.authContainer.classList.add('hidden');
        els.appContainer.classList.remove('hidden');
        loadData('exercises');
    } else {
        els.authContainer.classList.remove('hidden');
        els.appContainer.classList.add('hidden');
    }
}

async function apiFetch(endpoint, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) options.headers['Authorization'] = `Bearer ${authToken}`;
    options.headers['Content-Type'] = 'application/json';
    
    try {
        const res = await fetch(API_BASE + endpoint, options);
        let data = {};
        try {
            data = await res.json();
        } catch (e) {}
        
        if (!res.ok) {
            throw new Error(data.message || 'Request failed');
        }
        return data;
    } catch (err) {
        showToast(err.message, true);
        if (err.message.includes('token') || err.message.includes('credentials') || err.message.includes('not valid')) {
            logout();
        }
        throw err;
    }
}

// Auth
els.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const data = await apiFetch('auth/admin/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        if (data.success && data.data && data.data.access) {
            authToken = data.data.access;
            localStorage.setItem('adminToken', authToken);
            showToast('Login successful!');
            init();
        }
    } catch (err) {}
});

function logout() {
    authToken = null;
    localStorage.removeItem('adminToken');
    init();
}

els.logoutBtn.addEventListener('click', logout);

// Navigation
els.navLinks.forEach(link => {
    link.addEventListener('click', () => {
        const view = link.dataset.view;
        els.navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        els.sections.forEach(sec => sec.classList.add('hidden'));
        document.getElementById(`view-${view}`).classList.remove('hidden');
        
        loadData(view);
    });
});

// Loaders
function loadData(view) {
    if (view === 'announcements') fetchAnnouncements();
    else if (view === 'inquiries') fetchInquiries();
}

// Exercises
els.exForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        code: document.getElementById('ex-code').value,
        name: document.getElementById('ex-name').value,
        category: document.getElementById('ex-category').value,
        target_muscle: document.getElementById('ex-muscle').value
    };
    
    try {
        await apiFetch('admin/exercises/', { method: 'POST', body: JSON.stringify(payload) });
        showToast('운동 기구가 추가되었습니다.');
        els.exForm.reset();
    } catch (err) {}
});

// Announcements
els.annForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        title: document.getElementById('ann-title').value,
        content: document.getElementById('ann-content').value
    };
    
    try {
        await apiFetch('admin/announcements/', { method: 'POST', body: JSON.stringify(payload) });
        showToast('공지사항이 등록되었습니다.');
        els.annForm.reset();
        fetchAnnouncements();
    } catch (err) {}
});

async function fetchAnnouncements() {
    try {
        const data = await apiFetch('announcements/');
        const list = data.data || [];
        if (list.length === 0) {
            els.annList.innerHTML = '<p style="color: var(--text-muted)">등록된 공지사항이 없습니다.</p>';
            return;
        }
        els.annList.innerHTML = list.map(a => `
            <div class="list-item glass">
                <div class="item-content">
                    <h3>${a.title}</h3>
                    <p style="white-space: pre-wrap;">${a.content}</p>
                    <div class="item-meta">${new Date(a.created_at).toLocaleDateString()}</div>
                </div>
                <button class="action-btn btn-danger" onclick="deleteAnnouncement(${a.id})">삭제</button>
            </div>
        `).join('');
    } catch (e) {}
}

window.deleteAnnouncement = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
        await apiFetch(`admin/announcements/${id}/`, { method: 'DELETE' });
        showToast('삭제 완료');
        fetchAnnouncements();
    } catch (err) {}
};

// Inquiries
async function fetchInquiries() {
    try {
        const data = await apiFetch('admin/inquiries/');
        const list = data.data || [];
        if (list.length === 0) {
            els.inqList.innerHTML = '<p style="color: var(--text-muted)">접수된 문의사항이 없습니다.</p>';
            return;
        }
        els.inqList.innerHTML = list.map(i => `
            <div class="list-item glass">
                <div class="item-content">
                    <h3>${i.user_email}</h3>
                    <p style="white-space: pre-wrap;">${i.content}</p>
                    <div class="item-meta">${new Date(i.created_at).toLocaleString()}</div>
                    <div style="margin-top: 8px;">
                        <span class="status-badge ${i.status === 'RESOLVED' ? 'status-resolved' : 'status-pending'}">
                            ${i.status === 'RESOLVED' ? '답변완료' : '대기중'}
                        </span>
                    </div>
                </div>
                ${i.status === 'PENDING' ? `
                    <button class="action-btn btn-success" onclick="resolveInquiry(${i.id})">답변 완료 처리</button>
                ` : ''}
            </div>
        `).join('');
    } catch (e) {}
}

window.resolveInquiry = async (id) => {
    try {
        await apiFetch(`admin/inquiries/${id}/`, { 
            method: 'PATCH', 
            body: JSON.stringify({ status: 'RESOLVED' }) 
        });
        showToast('상태 업데이트 완료');
        fetchInquiries();
    } catch (err) {}
};

init();
