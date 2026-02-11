const API_BASE = window.location.origin + '/api';

document.addEventListener('DOMContentLoaded', () => { loadAll(); });

async function loadAll() {
    await Promise.all([loadSummary(), loadWatching(), loadHistory(), checkHealth()]);
}

async function checkHealth() {
    const dot = document.querySelector('.status-dot');
    const label = dot.parentElement.querySelector('span:last-child');
    try {
        const resp = await fetch(`${API_BASE}/health`);
        if (resp.ok) { dot.className = 'status-dot online'; label.textContent = '서버 연결됨'; }
        else { throw new Error(); }
    } catch { dot.className = 'status-dot offline'; label.textContent = '서버 연결 실패'; }
}

async function loadSummary() {
    try {
        const resp = await fetch(`${API_BASE}/dashboard/summary`);
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        document.getElementById('watchingCount').textContent = data.watching_count;
        document.getElementById('alertedCount').textContent = data.alerted_count;
        document.getElementById('expiredCount').textContent = data.expired_count;
        document.getElementById('successRate').textContent = data.alert_success_rate !== null ? `${data.alert_success_rate}%` : '-';
    } catch (e) { console.error('요약 로드 오류:', e); }
}

async function loadWatching() {
    const container = document.getElementById('watchingList');
    const badge = document.getElementById('watchingBadge');
    try {
        const resp = await fetch(`${API_BASE}/watchlist?status=watching`);
        if (!resp.ok) throw new Error();
        const stocks = await resp.json();
        badge.textContent = stocks.length;
        if (stocks.length === 0) { container.innerHTML = '<div class="empty-state"><span class="empty-icon">📭</span><p>관찰 중인 종목이 없습니다</p></div>'; return; }
        container.innerHTML = stocks.map(stock => renderStockItem(stock, true)).join('');
    } catch (e) { console.error('관찰 목록 오류:', e); }
}

let currentHistoryFilter = 'all';
async function loadHistory(filter) {
    if (filter) currentHistoryFilter = filter;
    const container = document.getElementById('historyList');
    try {
        let url = `${API_BASE}/dashboard/history`;
        if (currentHistoryFilter !== 'all') url += `?status=${currentHistoryFilter}`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error();
        const stocks = await resp.json();
        if (stocks.length === 0) { container.innerHTML = '<div class="empty-state"><span class="empty-icon">📋</span><p>이력이 없습니다</p></div>'; return; }
        container.innerHTML = stocks.map(stock => renderStockItem(stock, false, true)).join('');
    } catch (e) { console.error('이력 로드 오류:', e); }
}

function filterHistory(filter, tabEl) {
    document.querySelectorAll('.filter-tabs .tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
    loadHistory(filter);
}

function renderStockItem(stock, showActions, showHistoryDelete = false) {
    const statusIcon = { watching: '👀', alerted: '🚀', expired: '⏰' }[stock.status] || '📌';
    const rateClass = stock.peak_rate >= 0 ? 'rate-positive' : 'rate-negative';
    const rateSign = stock.peak_rate >= 0 ? '+' : '';
    const barWidth = Math.min((stock.peak_rate / 50) * 100, 100);
    const barClass = stock.peak_rate >= 50 ? 'achieved' : '';
    const enrolledDate = new Date(stock.enrolled_date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
    let metaHtml = `<span>편입: ${enrolledDate}</span><span>D-0 저가: ${formatPrice(stock.d0_low_price)}원</span>`;
    if (stock.alert_day) metaHtml += `<span>D+${stock.alert_day} 달성</span>`;
    let actionsHtml = '';
    if (showActions) actionsHtml = `<div class="stock-actions"><button class="btn btn-danger" onclick="event.stopPropagation(); removeStock('${stock.stock_code}')">삭제</button></div>`;
    else if (showHistoryDelete) actionsHtml = `<div class="stock-actions"><button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteHistory(${stock.id})">🗑</button></div>`;
    return `<div class="stock-item" onclick="showDetail('${stock.stock_code}')"><span class="stock-status-icon">${statusIcon}</span><div class="stock-info"><div class="stock-name-row"><span class="stock-name">${stock.stock_name}</span><span class="stock-code">${stock.stock_code}</span></div><div class="stock-meta">${metaHtml}</div></div><div class="stock-rate"><span class="rate-value ${rateClass}">${rateSign}${stock.peak_rate.toFixed(1)}%</span><div class="rate-bar"><div class="rate-bar-fill ${barClass}" style="width: ${barWidth}%"></div></div></div>${actionsHtml}</div>`;
}

async function addStock(event) {
    event.preventDefault();
    const input = document.getElementById('stockNameInput');
    const btn = document.getElementById('addBtn');
    const msgEl = document.getElementById('addMessage');
    const stockName = input.value.trim();
    if (!stockName) return;
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 등록 중...';
    msgEl.className = 'message hidden';
    try {
        const resp = await fetch(`${API_BASE}/watchlist`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stock_name: stockName }) });
        const data = await resp.json();
        if (resp.ok) { msgEl.className = 'message success'; msgEl.textContent = `✅ ${data.stock_name}(${data.stock_code}) 등록 완료! D-0 저가: ${formatPrice(data.d0_low_price)}원`; input.value = ''; await loadAll(); }
        else { msgEl.className = 'message error'; msgEl.textContent = `❌ ${data.detail || '등록 실패'}`; }
    } catch (e) { msgEl.className = 'message error'; msgEl.textContent = '❌ 서버와 통신할 수 없습니다'; }
    finally { btn.disabled = false; btn.innerHTML = '<span class="btn-icon">📌</span> 등록'; setTimeout(() => { msgEl.className = 'message hidden'; }, 5000); }
}

async function removeStock(stockCode) {
    if (!confirm('이 종목의 관찰을 종료하시겠습니까?')) return;
    try { const resp = await fetch(`${API_BASE}/watchlist/${stockCode}`, { method: 'DELETE' }); if (resp.ok) await loadAll(); else { const data = await resp.json(); alert(data.detail); } } catch { alert('서버와 통신할 수 없습니다'); }
}

async function deleteHistory(recordId) {
    if (!confirm('이 이력을 영구 삭제하시겠습니까? 복구할 수 없습니다.')) return;
    try { const resp = await fetch(`${API_BASE}/history/${recordId}`, { method: 'DELETE' }); if (resp.ok) await loadAll(); else { const data = await resp.json(); alert(data.detail); } } catch { alert('서버와 통신할 수 없습니다'); }
}

async function showDetail(stockCode) {
    const modal = document.getElementById('detailModal');
    const body = document.getElementById('modalBody');
    body.innerHTML = '<div style="text-align:center;padding:40px"><span class="spinner"></span><p style="margin-top:12px;color:var(--text-muted)">로딩 중...</p></div>';
    modal.classList.remove('hidden');
    try {
        const resp = await fetch(`${API_BASE}/watchlist/${stockCode}`);
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        const stock = data.watchlist;
        const prices = data.daily_prices;
        const statusLabel = { watching: '👀 관찰 중', alerted: '🚀 50% 달성', expired: '⏰ 만료' }[stock.status];
        let timelineHtml = prices.length > 0 ? `<div class="price-timeline"><h3>📊 일별 가격 변동</h3>${prices.map(p => { const rc = p.change_rate >= 0 ? 'rate-positive' : 'rate-negative'; const rs = p.change_rate >= 0 ? '+' : ''; return `<div class="timeline-item"><span class="timeline-day">D+${p.day_index}</span><span class="timeline-date">${new Date(p.trade_date).toLocaleDateString('ko-KR')}</span><span class="timeline-price">${formatPrice(p.close_price)}원</span><span class="timeline-rate ${rc}">${rs}${p.change_rate.toFixed(2)}%</span></div>`; }).join('')}</div>` : '<p style="color:var(--text-muted);text-align:center;padding:16px">아직 수집된 가격 데이터가 없습니다</p>';
        body.innerHTML = `<h2 class="modal-title">${stock.stock_name} <span style="color:var(--text-muted);font-size:14px">${stock.stock_code}</span></h2><div class="detail-grid"><div class="detail-item"><div class="detail-label">상태</div><div class="detail-value">${statusLabel}</div></div><div class="detail-item"><div class="detail-label">편입일</div><div class="detail-value">${new Date(stock.enrolled_date).toLocaleDateString('ko-KR')}</div></div><div class="detail-item"><div class="detail-label">D-0 저가</div><div class="detail-value">${formatPrice(stock.d0_low_price)}원</div></div><div class="detail-item"><div class="detail-label">최고 상승률</div><div class="detail-value rate-positive">+${stock.peak_rate.toFixed(2)}%</div></div></div>${timelineHtml}`;
    } catch (e) { body.innerHTML = '<div class="empty-state"><p>상세 정보를 불러올 수 없습니다</p></div>'; }
}

function closeModal() { document.getElementById('detailModal').classList.add('hidden'); }
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
function formatPrice(price) { if (price == null) return '-'; return price.toLocaleString('ko-KR'); }
