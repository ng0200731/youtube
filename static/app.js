let currentSearchId = null;
let currentVideos = [];
let sortKey = 'view_count';
let sortAsc = false;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadQuota();
    setQuickDate('thisMonth');
});

// --- Quick date presets ---
function setQuickDate(preset) {
    const now = new Date();
    let from, to;

    switch (preset) {
        case 'thisMonth':
            from = new Date(now.getFullYear(), now.getMonth(), 1);
            to = now;
            break;
        case 'lastMonth':
            from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            to = new Date(now.getFullYear(), now.getMonth(), 0);
            break;
        case 'thisYear':
            from = new Date(now.getFullYear(), 0, 1);
            to = now;
            break;
        case 'lastYear':
            from = new Date(now.getFullYear() - 1, 0, 1);
            to = new Date(now.getFullYear() - 1, 11, 31);
            break;
    }

    document.getElementById('dateFrom').value = formatDate(from);
    document.getElementById('dateTo').value = formatDate(to);
}

// --- Search ---
async function submitSearch() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    const maxPages = document.getElementById('maxPages').value;
    const query = document.getElementById('query').value;
    const titleLang = document.getElementById('titleLang').value;
    const audioLang = document.getElementById('audioLang').value;
    const honeypot = document.getElementById('website').value;

    if (!dateFrom || !dateTo) {
        showError('Please select both dates');
        return;
    }

    hideError();
    showLoading(true);
    document.getElementById('searchBtn').disabled = true;

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                published_after: dateFrom,
                published_before: dateTo,
                max_pages: parseInt(maxPages),
                query: query,
                title_lang: titleLang,
                audio_lang: audioLang,
                website: honeypot
            })
        });

        const data = await res.json();

        if (!res.ok) {
            showError(data.error || 'Search failed');
            return;
        }

        currentSearchId = data.search_id;
        currentVideos = data.videos;
        sortKey = 'view_count';
        sortAsc = false;
        document.getElementById('tableFilter').value = '';
        renderResults(data.videos, dateFrom, dateTo, data.quota_used);
        loadQuota();
    } catch (err) {
        showError('Network error: ' + err.message);
    } finally {
        showLoading(false);
        document.getElementById('searchBtn').disabled = false;
    }
}

// --- Sort ---
function sortBy(key) {
    if (sortKey === key) {
        sortAsc = !sortAsc;
    } else {
        sortKey = key;
        // Default desc for numbers, asc for text
        sortAsc = (key === 'title' || key === 'channel_title' || key === 'publish_date');
    }
    updateSortArrows();
    rebuildTable();
}

function updateSortArrows() {
    document.querySelectorAll('.sort-arrow').forEach(el => {
        el.className = 'sort-arrow';
        el.innerHTML = '';
    });
    const active = document.querySelector(`th[data-key="${sortKey}"] .sort-arrow`);
    if (active) {
        active.className = sortAsc ? 'sort-arrow sort-active-asc' : 'sort-arrow sort-active-desc';
        active.innerHTML = sortAsc ? '&#9650;' : '&#9660;';
    }
}

function getSorted(videos) {
    return [...videos].sort((a, b) => {
        let va = a[sortKey];
        let vb = b[sortKey];
        if (va == null) va = '';
        if (vb == null) vb = '';
        if (typeof va === 'string') {
            va = va.toLowerCase();
            vb = (vb || '').toLowerCase();
            return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        }
        return sortAsc ? va - vb : vb - va;
    });
}

// --- Filter ---
function filterTable() {
    rebuildTable();
}

function getFiltered(videos) {
    const q = (document.getElementById('tableFilter').value || '').toLowerCase().trim();
    if (!q) return videos;
    const terms = q.split(/\s+/);
    return videos.filter(v => {
        const text = [
            v.title, v.channel_title, v.description,
            String(v.view_count), String(v.like_count),
            (v.publish_date || '').slice(0, 10)
        ].join(' ').toLowerCase();
        return terms.every(t => text.includes(t));
    });
}

// --- Render ---
function rebuildTable() {
    const filtered = getFiltered(currentVideos);
    const sorted = getSorted(filtered);
    renderRows(sorted);
    const countEl = document.getElementById('filterCount');
    const q = (document.getElementById('tableFilter').value || '').trim();
    countEl.textContent = q ? `${sorted.length} of ${currentVideos.length}` : '';
}

function renderResults(videos, dateFrom, dateTo, quotaUsed) {
    const section = document.getElementById('resultsSection');
    const summary = document.getElementById('resultsSummary');

    summary.textContent = `${videos.length} videos from ${dateFrom} to ${dateTo}` +
        (quotaUsed ? ` (${quotaUsed} quota units used)` : '');

    updateSortArrows();
    rebuildTable();
    section.style.display = 'block';
}

function renderRows(videos) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    videos.forEach((v, i) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => toggleDetail(v, tr);
        tr.innerHTML = `
            <td>${i + 1}</td>
            <td><img class="thumb" src="${escHtml(v.thumbnail_url)}" alt="" loading="lazy"></td>
            <td><a class="video-link" href="${escHtml(v.video_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${escHtml(v.title)}</a></td>
            <td>${escHtml(v.channel_title || '')}</td>
            <td class="num">${formatNum(v.view_count)}</td>
            <td class="num">${formatNum(v.like_count)}</td>
            <td class="num">${formatNum(v.comment_count)}</td>
            <td>${formatDuration(v.duration_seconds)}</td>
            <td>${(v.publish_date || '').slice(0, 10)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Toggle detail row ---
function toggleDetail(video, row) {
    const next = row.nextElementSibling;
    if (next && next.classList.contains('detail-row')) {
        next.remove();
        return;
    }

    let tags = video.tags || '[]';
    if (typeof tags === 'string') {
        try { tags = JSON.parse(tags); } catch (e) { tags = []; }
    }

    const detailTr = document.createElement('tr');
    detailTr.classList.add('detail-row');
    detailTr.innerHTML = `
        <td colspan="9">
            <div class="detail-content">
                <div>
                    <dt>Description</dt>
                    <dd>${escHtml((video.description || '').slice(0, 500))}${(video.description || '').length > 500 ? '...' : ''}</dd>
                </div>
                <div>
                    <dt>Tags</dt>
                    <dd>
                        <div class="tags-list">
                            ${tags.map(t => `<span class="tag">${escHtml(t)}</span>`).join('')}
                            ${tags.length === 0 ? '<span style="color:var(--muted)">No tags</span>' : ''}
                        </div>
                    </dd>
                    <dt style="margin-top:0.5rem">Category ID</dt>
                    <dd>${video.category_id || 'N/A'}</dd>
                    <dt style="margin-top:0.5rem">Channel ID</dt>
                    <dd>${escHtml(video.channel_id || 'N/A')}</dd>
                </div>
            </div>
        </td>
    `;
    row.after(detailTr);
}

// --- CSV export ---
function downloadCSV() {
    if (!currentSearchId) return;
    window.location.href = `/api/export/csv?search_id=${currentSearchId}`;
}

// --- Quota ---
async function loadQuota() {
    try {
        const res = await fetch('/api/quota');
        const data = await res.json();
        document.getElementById('quotaInfo').textContent =
            `Quota: ${formatNum(data.remaining)} / ${formatNum(data.daily_limit)} remaining today`;
    } catch (e) {
        document.getElementById('quotaInfo').textContent = 'Quota info unavailable';
    }
}

// --- History ---
let historyVisible = false;

async function toggleHistory() {
    const list = document.getElementById('historyList');
    historyVisible = !historyVisible;
    list.style.display = historyVisible ? 'block' : 'none';

    if (historyVisible) {
        try {
            const res = await fetch('/api/search/history');
            const history = await res.json();

            if (history.length === 0) {
                list.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">No searches yet</p>';
                return;
            }

            list.innerHTML = history.map(h => `
                <div class="history-item" onclick="loadHistorySearch(${h.id}, '${h.published_after}', '${h.published_before}')">
                    <span>${h.published_after} to ${h.published_before} &mdash; ${h.total_results} videos</span>
                    <span class="history-meta">${h.searched_at}</span>
                </div>
            `).join('');
        } catch (e) {
            list.innerHTML = '<p style="color:var(--muted)">Failed to load history</p>';
        }
    }
}

async function loadHistorySearch(searchId, dateFrom, dateTo) {
    showLoading(true);
    hideError();

    try {
        const res = await fetch(`/api/search/${searchId}/results`);
        const videos = await res.json();
        currentSearchId = searchId;
        currentVideos = videos;
        sortKey = 'view_count';
        sortAsc = false;
        document.getElementById('tableFilter').value = '';
        renderResults(videos, dateFrom, dateTo, 0);
    } catch (e) {
        showError('Failed to load search results');
    } finally {
        showLoading(false);
    }
}

// --- Helpers ---
function formatNum(n) {
    return (n || 0).toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function formatDate(d) {
    return d.toISOString().slice(0, 10);
}

function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

function showError(msg) {
    const el = document.getElementById('errorMsg');
    el.textContent = msg;
    el.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMsg').style.display = 'none';
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}
