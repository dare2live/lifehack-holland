/**
 * chart.js — Result visualization for the SJT Assessment Engine.
 * Renders radar chart + bar charts for Holland and MBTI dimensions.
 * Uses Chart.js (loaded via CDN).
 */

/**
 * Render the full result page.
 * @param {Object} report - The ReportResponse from the backend
 * @param {Object} config - The dimension config from the backend
 * @param {HTMLElement} container - DOM element to render into
 */
function renderReport(report, config, container) {
    // ── Build metadata maps from config ──
    const HOLLAND_META = {};
    config.holland.dimensions.forEach(d => { HOLLAND_META[d.code] = d; });
    const MBTI_META = config.mbti.dimensions;
    const mbtiPairs = config.mbti.pairs.map(p => p.codes);

    const dimMap = {};
    for (const d of report.dimensions) {
        dimMap[d.dimension_code] = d;
    }

    let html = '';

    // ── Header ──
    html += `
    <div class="result-header">
        <div class="result-header__icon">🎯</div>
        <h1 class="result-header__title">你的测评报告</h1>
        <p class="result-header__sub">基于情境判断测试 (SJT) 的双核生涯测评结果</p>
    </div>`;

    // ── Type Badges ──
    html += '<div style="text-align:center; margin-bottom:2rem;">';
    // Holland
    if (report.holland_top3.length > 0) {
        html += `
        <div class="type-badge">
            <span class="type-badge__label">霍兰德类型</span>
            <span class="type-badge__code">${report.holland_top3.join('')}</span>
        </div> `;
    }
    // MBTI
    if (report.mbti_type) {
        html += `
        <div class="type-badge">
            <span class="type-badge__label">MBTI 偏好</span>
            <span class="type-badge__code">${report.mbti_type}</span>
        </div>`;
    }
    html += '</div>';

    // ── Radar Chart ──
    html += `
    <div class="chart-container">
        <canvas id="radar-chart"></canvas>
    </div>`;

    // ── Cross Insight ──
    if (report.cross_insight) {
        html += `
        <div class="score-section">
            <div class="score-section__title">综合倾向</div>
            <p class="insight-text">${_escapeHtml(report.cross_insight)}</p>
        </div>`;
    }

    // ── Holland Scores ──
    html += '<div class="score-section"><div class="score-section__title">霍兰德六型得分</div>';
    const hollandCodes = ['Holland_R', 'Holland_I', 'Holland_A', 'Holland_S', 'Holland_E', 'Holland_C'];
    const maxScore = Math.max(...hollandCodes.map(c => Math.abs(dimMap[c]?.final_score || 0)), 1);

    hollandCodes.forEach((code, i) => {
        const d = dimMap[code];
        const score = d ? d.final_score : 0;
        const meta = HOLLAND_META[code];
        const pct = Math.max(0, (score / (maxScore * 1.2)) * 100);
        const hasPenalty = d && d.penalty_score !== 0;

        html += `
        <div class="score-bar" style="animation-delay: ${i * 0.08}s">
            <span class="score-bar__label">${meta.icon} ${meta.name}</span>
            <div class="score-bar__track">
                <div class="score-bar__fill score-bar__fill--holland" 
                     style="width: 0%; background: ${meta.color};" 
                     data-target-width="${pct}%"></div>
            </div>
            <span class="score-bar__value">${score.toFixed(1)}${hasPenalty ? ' ⚠️' : ''}</span>
        </div>`;
    });
    html += '</div>';

    // ── MBTI Scores ──
    html += '<div class="score-section"><div class="score-section__title">MBTI 维度倾向</div>';

    mbtiPairs.forEach(([a, b], i) => {
        const scoreA = dimMap[a]?.final_score || 0;
        const scoreB = dimMap[b]?.final_score || 0;
        const metaA = MBTI_META[a];
        const metaB = MBTI_META[b];
        const total = Math.abs(scoreA) + Math.abs(scoreB) || 1;
        const pctA = (Math.abs(scoreA) / total) * 100;

        html += `
        <div class="score-bar" style="animation-delay: ${i * 0.08}s">
            <span class="score-bar__label">${metaA.name}</span>
            <div class="score-bar__track" style="position:relative;">
                <div class="score-bar__fill score-bar__fill--mbti" 
                     style="width: 0%; background: ${metaA.color};" 
                     data-target-width="${pctA}%"></div>
            </div>
            <span class="score-bar__label" style="text-align:right">${metaB.name}</span>
        </div>`;
    });
    html += '</div>';

    // ── Local Chinese Occupation Bridge ──
    if (report.recommended_cn_occupations && report.recommended_cn_occupations.length > 0) {
        html += '<div class="score-section"><div class="score-section__title">职业方向候选</div>';
        html += '<div class="occupation-list">';
        report.recommended_cn_occupations.forEach(occupation => {
            html += `
            <div class="occupation-item">
                <span class="occupation-item__code">${_escapeHtml(occupation.occupation_code || '')}</span>
                <span class="occupation-item__name">${_escapeHtml(occupation.occupation_name || '')}</span>
            </div>`;
        });
        html += '</div></div>';
    }

    // ── Holland Dimension Descriptions (Top 3) ──
    html += '<div class="score-section"><div class="score-section__title">你的核心特质解读</div>';
    report.holland_top3.forEach(code => {
        const fullCode = `Holland_${code}`;
        const meta = HOLLAND_META[fullCode];
        if (!meta) return;
        const d = dimMap[fullCode];
        const hasPenalty = d && d.penalty_score !== 0;

        html += `
        <div class="dim-desc">
            <div class="dim-desc__header">
                <div class="dim-desc__icon dim-desc__icon--${code}">${meta.icon}</div>
                <span class="dim-desc__name">${meta.name} — ${meta.full}</span>
            </div>
            <p class="dim-desc__text">${meta.desc}</p>
            ${hasPenalty ? `<p class="dim-desc__text" style="color: var(--accent-3); margin-top: 0.5rem;">
                ⚠️ 该维度检测到作答不一致，得分已被校准 (${d.penalty_score > 0 ? '+' : ''}${d.penalty_score.toFixed(1)})
            </p>` : ''}
        </div>`;
    });
    html += '</div>';

    // ── Retry Button ──
    html += `
    <div style="text-align: center; padding: 2rem 0;">
        <a href="index.html" class="btn btn--ghost">← 重新测试</a>
    </div>`;

    container.innerHTML = html;

    // ── Animate bars after render ──
    requestAnimationFrame(() => {
        setTimeout(() => {
            document.querySelectorAll('[data-target-width]').forEach(el => {
                el.style.width = el.dataset.targetWidth;
            });
        }, 100);
    });

    // ── Render radar chart ──
    _renderRadarChart(dimMap, HOLLAND_META);
}

function _escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function _renderRadarChart(dimMap, HOLLAND_META) {
    const canvas = document.getElementById('radar-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = Object.values(HOLLAND_META).map(m => m.name);
    const codes = Object.keys(HOLLAND_META);
    const data = codes.map(c => dimMap[c]?.final_score || 0);
    const baseData = codes.map(c => dimMap[c]?.base_score || 0);
    const colors = codes.map(c => HOLLAND_META[c].color);

    new Chart(canvas, {
        type: 'radar',
        data: {
            labels,
            datasets: [
                {
                    label: '最终得分',
                    data,
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    borderColor: '#6366f1',
                    borderWidth: 2,
                    pointBackgroundColor: colors,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1,
                    pointRadius: 5,
                },
                {
                    label: '基础得分 (惩罚前)',
                    data: baseData,
                    backgroundColor: 'rgba(139, 92, 246, 0.05)',
                    borderColor: 'rgba(139, 92, 246, 0.3)',
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 3,
                    pointBackgroundColor: 'rgba(139, 92, 246, 0.5)',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    angleLines: { color: 'rgba(255,255,255,0.06)' },
                    pointLabels: {
                        color: '#94a3b8',
                        font: { size: 12, family: "'Inter', 'Noto Sans SC', sans-serif" },
                    },
                    ticks: {
                        color: '#64748b',
                        backdropColor: 'transparent',
                        font: { size: 10 },
                    },
                },
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#94a3b8',
                        font: { size: 11, family: "'Inter', 'Noto Sans SC', sans-serif" },
                        usePointStyle: true,
                        pointStyle: 'circle',
                    },
                },
            },
        },
    });
}
