/* ══════════════════════════════════════════════════
   키움 관심종목 관리 시스템 — app.js
   Dark Luxury Edition
   ══════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000';

// ── 상태 ──
let allStocks = [];
let historyFilter = 'all';

// ══════════════════════════════════════════
// 페이지 라우팅
// ══════════════════════════════════════════
function navigateTo(pageId) {
    // 페이지 전환
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(`page-${pageId}`);
    if (target) target.classList.add('active');

    // 네비게이션 활성 표시
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (navItem) navItem.classList.add('active');

    // 페이지별 데이터 로드
    if (pageId === 'dashboard') loadDashboard();
    if (pageId === 'history') loadHistory();
}

// 네비게이션 이벤트
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.page));
});

// 섹션 링크
document.querySelectorAll('.section-link[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(link.dataset.page);
    });
});

// 뒤로가기
document.getElementById('btn-back-dashboard')?.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo('dashboard');
});

// ══════════════════════════════════════════
// API 호출 유틸리티
// ══════════════════════════════════════════
async function apiFetch(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('API 호출 실패:', err);
        return null;
    }
}

async function apiPost(endpoint, body) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('API POST 실패:', err);
        return null;
    }
}

async function apiDelete(endpoint) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('API DELETE 실패:', err);
        return null;
    }
}

// ══════════════════════════════════════════
// 서버 상태 확인
// ══════════════════════════════════════════
async function checkServerStatus() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('server-status-text');
    try {
        const res = await fetch(`${API_BASE}/`);
        if (res.ok) {
            dot.classList.remove('disconnected');
            text.textContent = '서버 연결됨';
        } else throw new Error();
    } catch {
        dot.classList.add('disconnected');
        text.textContent = '연결 끊김';
    }
}

// ══════════════════════════════════════════
// 대시보드
// ══════════════════════════════════════════
async function loadDashboard() {
    // 통계
    const summary = await apiFetch('/api/dashboard/summary');
    if (summary) {
        document.getElementById('stat-watching').textContent = summary.watching_count ?? 0;
        document.getElementById('stat-alerted').textContent = summary.alerted_count ?? 0;
        document.getElementById('stat-expired').textContent = summary.expired_count ?? 0;
        const total = (summary.alerted_count ?? 0) + (summary.expired_count ?? 0);
        const rate = total > 0
            ? Math.round((summary.alerted_count / total) * 100) + '%'
            : '—';
        document.getElementById('stat-rate').textContent = rate;
    }

    // 관찰 목록
    const stocks = await apiFetch('/api/watchlist?status=watching');
    allStocks = stocks || [];
    renderWatchlist(allStocks);
}

function renderWatchlist(stocks) {
    const tbody = document.getElementById('watchlist-body');
    if (!stocks || stocks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--muted-foreground); padding:40px;">등록된 관찰 종목이 없습니다</td></tr>`;
        return;
    }
    tbody.innerHTML = stocks.map(s => `
        <tr>
            <td class="stock-name-cell">${s.stock_name}</td>
            <td class="code-cell">${s.stock_code || '—'}</td>
            <td class="price-cell">${formatPrice(s.d0_low_price)}</td>
            <td class="rate-cell ${getRateClass(s.peak_rate)}">${formatRate(s.peak_rate)}</td>
            <td class="date-cell">${formatDate(s.enrolled_date)}</td>
            <td class="action-cell">
                <a class="detail-link" onclick="showDetail('${s.stock_code}')">상세 →</a>
            </td>
            <td class="action-cell">
                <button class="delete-btn" onclick="deleteStock('${s.stock_code}', '${s.stock_name}')">편출</button>
            </td>
        </tr>
    `).join('');
}

async function deleteStock(stockCode, stockName) {
    if (!confirm(`"${stockName}" 종목을 관찰 목록에서 편출하시겠습니까?\n\n편출 시 텔레그램 알림이 발송됩니다.`)) return;

    const result = await apiDelete(`/api/watchlist/${stockCode}`);
    if (result) {
        alert(`${stockName} 종목이 편출되었습니다.`);
        loadDashboard();
        loadRecentRegistrations();
    } else {
        alert('편출 처리 중 오류가 발생했습니다.');
    }
}

// ══════════════════════════════════════════
// 종목 등록
// ══════════════════════════════════════════
document.getElementById('btn-add-stock')?.addEventListener('click', async () => {
    const input = document.getElementById('input-stock-name');
    const name = input.value.trim();
    if (!name) return;

    const btn = document.getElementById('btn-add-stock');
    btn.disabled = true;
    btn.innerHTML = '처리 중…';

    const result = await apiPost('/api/watchlist', { stock_name: name });
    btn.disabled = false;
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> 등록`;

    if (result) {
        input.value = '';
        loadRecentRegistrations();
        loadDashboard();
    }
});

// 엔터키 등록
document.getElementById('input-stock-name')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('btn-add-stock')?.click();
});

async function loadRecentRegistrations() {
    const stocks = await apiFetch('/api/watchlist?status=watching');
    const container = document.getElementById('recent-registrations');
    if (!stocks || stocks.length === 0) {
        container.innerHTML = '<p style="color:var(--muted-foreground); font-size:14px;">최근 등록된 종목이 없습니다.</p>';
        return;
    }
    const recent = stocks.slice(0, 5);
    container.innerHTML = recent.map(s => `
        <div class="recent-card">
            <div class="rc-left">
                <span class="rc-name">${s.stock_name}</span>
                <span class="rc-sub">${s.stock_code || '—'} · ${formatDate(s.enrolled_date)}</span>
            </div>
            <div class="rc-right">
                <span class="rc-price">${formatPrice(s.d0_low_price)}</span>
                <span class="rc-tag">편입가</span>
            </div>
        </div>
    `).join('');
}

// ══════════════════════════════════════════
// 이력
// ══════════════════════════════════════════
async function loadHistory() {
    let endpoint = '/api/watchlist';
    if (historyFilter === 'alerted') endpoint += '?status=alerted';
    else if (historyFilter === 'expired') endpoint += '?status=expired';

    const stocks = await apiFetch(endpoint);
    renderHistory(stocks || []);
}

function renderHistory(stocks) {
    const tbody = document.getElementById('history-body');
    if (stocks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--muted-foreground); padding:40px;">이력이 없습니다</td></tr>`;
        return;
    }
    tbody.innerHTML = stocks.map(s => `
        <tr>
            <td class="stock-name-cell">${s.stock_name}</td>
            <td class="code-cell">${s.stock_code || '—'}</td>
            <td class="date-cell">${formatDate(s.enrolled_date)}</td>
            <td class="price-cell">${formatPrice(s.d0_low_price)}</td>
            <td class="rate-cell ${getRateClass(s.peak_rate)}">${formatRate(s.peak_rate)}</td>
            <td>${renderBadge(s.status)}</td>
            <td class="action-cell">
                <a class="detail-link" onclick="showDetail('${s.stock_code}')">상세 →</a>
            </td>
        </tr>
    `).join('');
}

// 필터 탭
document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        historyFilter = tab.dataset.filter;
        loadHistory();
    });
});

// ══════════════════════════════════════════
// 종목 상세
// ══════════════════════════════════════════
async function showDetail(stockCode) {
    navigateTo('detail');

    const detail = await apiFetch(`/api/watchlist/${stockCode}`);
    if (!detail) return;

    const w = detail.watchlist;
    document.getElementById('detail-name').textContent = w.stock_name;
    document.getElementById('detail-code').textContent = w.stock_code || '—';
    document.getElementById('detail-rate').textContent = formatRate(w.peak_rate);

    // 배지
    const badge = document.getElementById('detail-badge');
    badge.textContent = getStatusLabel(w.status);
    badge.className = 'badge ' + getBadgeClass(w.status);

    // 정보 카드
    document.getElementById('detail-d0-price').textContent = formatPrice(w.d0_low_price);
    document.getElementById('detail-date').textContent = formatDate(w.enrolled_date);
    const targetPrice = w.d0_low_price ? '₩' + Math.round(w.d0_low_price * 1.5).toLocaleString() : '—';
    document.getElementById('detail-target').textContent = targetPrice;

    // 일별 가격
    const prices = detail.daily_prices || [];
    const priceBody = document.getElementById('price-body');
    if (prices.length === 0) {
        priceBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--muted-foreground); padding:40px;">가격 데이터가 없습니다</td></tr>`;
    } else {
        priceBody.innerHTML = prices.map(p => `
            <tr>
                <td class="date-cell">${formatDate(p.trade_date)}</td>
                <td class="price-cell">${formatPrice(p.open_price)}</td>
                <td class="price-cell">${formatPrice(p.high_price)}</td>
                <td class="price-cell">${formatPrice(p.low_price)}</td>
                <td class="price-cell">${formatPrice(p.close_price)}</td>
                <td style="font-family:var(--font-mono); font-size:13px; color:var(--muted-foreground);">${p.volume ? p.volume.toLocaleString() : '—'}</td>
                <td class="rate-cell ${getRateClass(p.change_rate)}">${formatRate(p.change_rate)}</td>
            </tr>
        `).join('');
    }
}

// ══════════════════════════════════════════
// 유틸리티
// ══════════════════════════════════════════
function formatPrice(price) {
    if (!price && price !== 0) return '—';
    return '₩' + Math.round(price).toLocaleString();
}

function formatRate(rate) {
    if (!rate && rate !== 0) return '—';
    const val = parseFloat(rate);
    const prefix = val >= 0 ? '+' : '';
    return prefix + val.toFixed(1) + '%';
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return d.toISOString().split('T')[0].replace(/-/g, '.');
}

function getRateClass(rate) {
    if (!rate && rate !== 0) return 'neutral';
    return parseFloat(rate) >= 0 ? 'positive' : 'negative';
}

function renderBadge(status) {
    const label = getStatusLabel(status);
    const cls = getBadgeClass(status);
    return `<span class="badge ${cls}">${label}</span>`;
}

function getStatusLabel(status) {
    switch (status) {
        case 'alerted': return '달성';
        case 'expired': return '만료';
        case 'watching': return '관찰 중';
        default: return status || '—';
    }
}

function getBadgeClass(status) {
    switch (status) {
        case 'alerted': return 'badge-alerted';
        case 'expired': return 'badge-expired';
        case 'watching': return 'badge-watching';
        default: return '';
    }
}

// ══════════════════════════════════════════
// 새로고침
// ══════════════════════════════════════════
document.getElementById('btn-refresh')?.addEventListener('click', () => {
    loadDashboard();
    checkServerStatus();
});

// ══════════════════════════════════════════
// 초기화
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    checkServerStatus();
    loadDashboard();
    loadRecentRegistrations();

    // ── 공지 모달 이벤트 ──
    const modal = document.getElementById('notice-modal');
    const textarea = document.getElementById('notice-message');

    document.getElementById('btn-open-notice')?.addEventListener('click', () => {
        modal.classList.add('active');
        textarea.value = '';
        textarea.focus();
    });

    const closeModal = () => modal.classList.remove('active');
    document.getElementById('btn-close-notice')?.addEventListener('click', closeModal);
    document.getElementById('btn-cancel-notice')?.addEventListener('click', closeModal);

    // 오버레이 클릭 시 닫기
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // 전송
    document.getElementById('btn-send-notice')?.addEventListener('click', async () => {
        const message = textarea.value.trim();
        if (!message) { alert('공지 내용을 입력해주세요.'); return; }
        if (!confirm('공지를 텔레그램으로 전송하시겠습니까?')) return;

        const result = await apiPost('/api/telegram/notice', { message });
        if (result) {
            alert('✅ 공지가 전송되었습니다!');
            closeModal();
        } else {
            alert('공지 전송 중 오류가 발생했습니다.');
        }
    });
});
