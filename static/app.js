let currentSearchId = null;
let currentVideos = [];
let sortKey = 'view_count';
let sortAsc = false;
let selectedIds = new Set();

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadQuota();
    setQuickDate('thisMonth');
});

// --- Panel switching ---
function showPanel(name) {
    document.getElementById('panelSearch').style.display = name === 'search' ? 'block' : 'none';
    document.getElementById('panelHistory').style.display = name === 'history' ? 'block' : 'none';
    document.getElementById('navSearch').classList.toggle('active', name === 'search');
    document.getElementById('navHistory').classList.toggle('active', name === 'history');
    if (name === 'history') loadHistory();
}

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
        case 'allTime':
            from = new Date(2005, 1, 14);
            to = now;
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
    const channelName = document.getElementById('channelName').value;
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
                channel_name: channelName,
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
        selectedIds.clear();
        document.getElementById('tableFilter').value = '';
        document.getElementById('selectAll').checked = false;
        renderResults(data.videos, dateFrom, dateTo, data.quota_used);
        updateActionBar();
        loadQuota();
        loadHistory();
    } catch (err) {
        showError('Network error: ' + err.message);
    } finally {
        showLoading(false);
        document.getElementById('searchBtn').disabled = false;
    }
}

// --- Selection ---
function toggleSelect(videoId, checkbox) {
    if (checkbox.checked) {
        selectedIds.add(videoId);
    } else {
        selectedIds.delete(videoId);
    }
    updateActionBar();
    updateSelectAllCheckbox();
}

function toggleSelectAll(checked) {
    const filtered = getFiltered(currentVideos);
    const sorted = getSorted(filtered);
    if (checked) {
        sorted.forEach(v => selectedIds.add(v.video_id));
    } else {
        sorted.forEach(v => selectedIds.delete(v.video_id));
    }
    // Update all visible checkboxes
    document.querySelectorAll('.row-checkbox').forEach(cb => { cb.checked = checked; });
    updateActionBar();
}

function updateSelectAllCheckbox() {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    const allChecked = checkboxes.length > 0 && Array.from(checkboxes).every(cb => cb.checked);
    document.getElementById('selectAll').checked = allChecked;
}

function updateActionBar() {
    const bar = document.getElementById('actionBar');
    const count = selectedIds.size;
    bar.style.display = count > 0 ? 'flex' : 'none';
    document.getElementById('selectionCount').textContent = `${count} selected`;

    const warn = document.getElementById('selectionWarn');
    if (count > 50) {
        warn.textContent = 'NotebookLM limit: 50 sources';
        warn.style.display = 'inline';
    } else {
        warn.style.display = 'none';
    }
}

// --- NotebookLM actions ---
function copyUrlsToClipboard() {
    const urls = getSelectedVideos().map(v => v.video_url).join('\n');
    navigator.clipboard.writeText(urls).then(() => {
        const btn = event.target;
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    });
}

async function exportSelectedCSV() {
    const ids = Array.from(selectedIds);
    if (!ids.length) return;

    try {
        const res = await fetch('/api/export/selected-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_ids: ids })
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `youtube_selected_${ids.length}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showError('Export failed: ' + e.message);
    }
}

async function exportCommentsCsv() {
    const ids = Array.from(selectedIds);
    if (!ids.length) return;

    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Fetching comments...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/export/comments-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_ids: ids })
        });

        if (!res.ok) {
            const data = await res.json();
            showError(data.error || 'Export failed');
            return;
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `youtube_comments_${ids.length}videos.csv`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showError('Export failed: ' + e.message);
    } finally {
        btn.textContent = orig;
        btn.disabled = false;
    }
}

async function openNotebookLM() {
    const selected = getSelectedVideos();
    if (!selected.length) return;

    const urls = selected.map(v => v.video_url);
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Opening browser...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/notebooklm/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: urls })
        });
        const data = await res.json();

        if (data.error) {
            showError(data.error);
            return;
        }
        if (data.url) {
            window.open(data.url, '_blank');
        }
    } catch (e) {
        showError('NotebookLM failed: ' + e.message);
    } finally {
        btn.textContent = orig;
        btn.disabled = false;
    }
}

function getSelectedVideos() {
    return currentVideos.filter(v => selectedIds.has(v.video_id));
}

// --- Sort ---
function sortBy(key) {
    if (sortKey === key) {
        sortAsc = !sortAsc;
    } else {
        sortKey = key;
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

    const totalViews = videos.reduce((s, v) => s + (v.view_count || 0), 0);
    const totalLikes = videos.reduce((s, v) => s + (v.like_count || 0), 0);
    const totalComments = videos.reduce((s, v) => s + (v.comment_count || 0), 0);

    summary.textContent = `${videos.length} videos from ${dateFrom} to ${dateTo}` +
        ` | ${formatNum(totalViews)} views, ${formatNum(totalLikes)} likes, ${formatNum(totalComments)} comments` +
        (quotaUsed ? ` (${quotaUsed} quota)` : '');

    updateSortArrows();
    rebuildTable();
    section.style.display = 'block';
    const empty = document.getElementById('emptyState');
    if (empty) empty.style.display = 'none';
}

function renderRows(videos) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    // Totals row
    const totalViews = videos.reduce((s, v) => s + (v.view_count || 0), 0);
    const totalLikes = videos.reduce((s, v) => s + (v.like_count || 0), 0);
    const totalComments = videos.reduce((s, v) => s + (v.comment_count || 0), 0);
    const totalDuration = videos.reduce((s, v) => s + (v.duration_seconds || 0), 0);
    const totTr = document.createElement('tr');
    totTr.style.fontWeight = 'bold';
    totTr.style.borderBottom = '2px solid #000';
    totTr.innerHTML = `
        <td></td><td></td><td></td>
        <td>Total (${videos.length})</td>
        <td></td>
        <td class="num">${formatNum(totalViews)}</td>
        <td class="num">${formatNum(totalLikes)}</td>
        <td class="num">${formatNum(totalComments)}</td>
        <td>${formatDuration(totalDuration)}</td>
        <td></td>
    `;
    tbody.appendChild(totTr);

    videos.forEach((v, i) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = (e) => { if (e.target.type !== 'checkbox') toggleDetail(v, tr); };

        const isChecked = selectedIds.has(v.video_id);
        tr.innerHTML = `
            <td><input type="checkbox" class="row-checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleSelect('${v.video_id}', this)"></td>
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
        <td colspan="10">
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
            <div class="comments-section" id="comments-${video.video_id}">
                <dt style="margin-top:1rem">Comments</dt>
                <dd style="color:var(--muted)">Loading comments...</dd>
            </div>
        </td>
    `;
    row.after(detailTr);

    // Load comments
    loadComments(video.video_id);
}

async function loadComments(videoId) {
    const container = document.getElementById(`comments-${videoId}`);
    if (!container) return;

    try {
        const res = await fetch(`/api/video/${videoId}/comments`);
        const comments = await res.json();

        if (comments.error) {
            container.innerHTML = `<dt style="margin-top:1rem">Comments</dt><dd style="color:var(--muted)">${escHtml(comments.error)}</dd>`;
            return;
        }

        if (comments.length === 0) {
            container.innerHTML = '<dt style="margin-top:1rem">Comments</dt><dd style="color:var(--muted)">No comments or comments disabled</dd>';
            return;
        }

        const commentsHtml = comments.slice(0, 50).map(c => `
            <div class="comment-item">
                <div class="comment-header">
                    <span class="comment-author">${escHtml(c.author)}</span>
                    <span class="comment-meta">${(c.published_at || '').slice(0, 10)} | ${c.like_count} likes${c.reply_count ? ' | ' + c.reply_count + ' replies' : ''}</span>
                </div>
                <div class="comment-text">${escHtml(c.text)}</div>
            </div>
        `).join('');

        container.innerHTML = `
            <dt style="margin-top:1rem">Comments (${comments.length})</dt>
            <dd><div class="comments-list">${commentsHtml}</div></dd>
        `;
    } catch (e) {
        container.innerHTML = '<dt style="margin-top:1rem">Comments</dt><dd style="color:var(--muted)">Failed to load comments</dd>';
    }
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
        const keys = data.keys || {};
        const keyInfo = keys.total_keys > 1
            ? ` (${keys.available_keys}/${keys.total_keys} keys active)`
            : '';
        document.getElementById('quotaInfo').textContent =
            `Quota: ${formatNum(data.remaining)} / ${formatNum(data.daily_limit)} remaining today${keyInfo}`;
    } catch (e) {
        document.getElementById('quotaInfo').textContent = 'Quota info unavailable';
    }
}

// --- History ---
const langNames = {
    'en': 'English', 'zh-TW': '中文繁體', 'zh-CN': '中文简体',
    'ja': '日本語', 'ko': '한국어', 'es': 'Español', 'pt': 'Português',
    'fr': 'Français', 'de': 'Deutsch', 'hi': 'हिन्दी', 'ar': 'العربية',
    'th': 'ไทย', 'vi': 'Tiếng Việt', 'id': 'Bahasa', 'ru': 'Русский',
    'english': 'English', 'mandarin': '普通话', 'cantonese': '廣東話',
    'japanese': '日本語', 'korean': '한국어', 'spanish': 'Spanish',
    'portuguese': 'Portuguese', 'french': 'French', 'german': 'German',
    'hindi': 'Hindi', 'arabic': 'Arabic', 'thai': 'Thai',
    'vietnamese': 'Vietnamese', 'indonesian': 'Indonesian', 'russian': 'Russian'
};

async function toggleHistory() {
    loadHistory();
}

async function loadHistory() {
    const list = document.getElementById('historyList');
    try {
        const res = await fetch('/api/search/history');
        const history = await res.json();

        if (history.length === 0) {
            list.innerHTML = '<p style="color:var(--muted);font-size:0.75rem">No searches yet</p>';
            return;
        }

        list.innerHTML = history.map(h => {
            const tags = [];
            if (h.channel_name) tags.push(escHtml(h.channel_name));
            if (h.query) tags.push(`"${escHtml(h.query)}"`);
            if (h.title_lang) tags.push(`title:${langNames[h.title_lang] || h.title_lang}`);
            if (h.audio_lang) tags.push(`audio:${langNames[h.audio_lang] || h.audio_lang}`);
            if (h.pages_fetched > 1) tags.push(`${h.pages_fetched}pg`);
            const label = tags.length ? ` [${tags.join(', ')}]` : '';
            return `
                <div class="history-item" onclick="loadHistorySearch(${h.id}, '${h.published_after}', '${h.published_before}')">
                    <span>${h.published_after} to ${h.published_before}${label}</span>
                    <span class="history-meta">${h.total_results} videos &middot; ${h.searched_at}</span>
                </div>
            `}).join('');
    } catch (e) {
        list.innerHTML = '<p style="color:var(--muted)">Failed to load history</p>';
    }
}

async function loadHistorySearch(searchId, dateFrom, dateTo) {
    showPanel('search');
    showLoading(true);
    hideError();

    try {
        const res = await fetch(`/api/search/${searchId}/results`);
        const videos = await res.json();
        currentSearchId = searchId;
        currentVideos = videos;
        sortKey = 'view_count';
        sortAsc = false;
        selectedIds.clear();
        document.getElementById('tableFilter').value = '';
        document.getElementById('selectAll').checked = false;
        renderResults(videos, dateFrom, dateTo, 0);
        updateActionBar();
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
