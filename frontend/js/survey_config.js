/**
 * survey_config.js — Dynamic survey builder using pure HTML/JS (no SurveyJS dependency).
 *
 * Fetches questions from the backend API and renders them as custom-styled cards
 * with visibleIf logic for dynamic verification questions.
 */

class SjtSurvey {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.questions = [];
        this.answers = {};
        this.currentPage = 0;
        this.pages = [];       // grouped questions per page
        this.onComplete = null;
    }

    /**
     * Load questions from backend and initialize the survey.
     */
    async init() {
        try {
            const data = await SjtApi.getQuestions();
            this.questions = data.questions;
            this._groupIntoPages();
            this._render();
        } catch (err) {
            this.container.innerHTML = `
                <div class="survey-card" style="text-align:center;">
                    <p style="color: var(--ink-2);">无法加载问卷，请确认测评服务已启动。</p>
                    <p style="color: var(--text-muted); font-size:0.85rem; margin-top:0.5rem;">${err.message}</p>
                </div>`;
        }
    }

    /**
     * Group questions into pages:
     * - Main scenario + its verification question = 1 page
     * - Standalone questions = 1 page each
     */
    _groupIntoPages() {
        const verifyMap = {};  // verify_q_id → true (these are secondary)
        const triggerMap = {}; // trigger_q_id → verify_q_id

        // Build visibility relationships
        for (const q of this.questions) {
            if (q.visibleIf) {
                // Parse: "{Q_Gala} = 'A'" → trigger_q = Q_Gala
                const match = q.visibleIf.match(/\{(\w+)\}\s*=\s*'(\w+)'/);
                if (match) {
                    verifyMap[q.name] = true;
                    triggerMap[match[1]] = q.name;
                }
            }
        }

        // Group: main + verify on same page
        const used = new Set();
        for (const q of this.questions) {
            if (used.has(q.name)) continue;
            const page = [q];
            used.add(q.name);

            if (triggerMap[q.name]) {
                const verifyQ = this.questions.find(x => x.name === triggerMap[q.name]);
                if (verifyQ) {
                    page.push(verifyQ);
                    used.add(verifyQ.name);
                }
            }
            this.pages.push(page);
        }
    }

    _render() {
        this._renderPage(this.currentPage);
        this._updateProgress();
    }

    _renderPage(pageIndex) {
        const page = this.pages[pageIndex];
        if (!page) return;

        let html = '';
        page.forEach((q, i) => {
            const isVerify = !!q.visibleIf;
            const cardClass = isVerify ? 'survey-card hidden' : 'survey-card';
            const qNum = this._getQuestionNumber(q.name);

            html += `<div class="${cardClass}" id="card-${q.name}" 
                          ${isVerify ? `data-visible-if="${q.visibleIf}"` : ''}>`;

            // Question number badge
            html += `<div class="survey-card__number">${qNum}</div>`;

            // Question text
            html += `<div class="survey-card__question">${q.title}</div>`;

            // Radio options
            html += '<div class="option-group">';
            q.choices.forEach(c => {
                const inputId = `${q.name}_${c.value}`;
                html += `
                    <div class="option-item">
                        <input type="radio" 
                               name="${q.name}" 
                               id="${inputId}" 
                               value="${c.value}"
                               onchange="survey._onAnswer('${q.name}', '${c.value}')">
                        <label class="option-item__label" for="${inputId}">
                            <span class="option-item__radio"></span>
                            <span class="option-item__key">${c.value}</span>
                            <span>${c.text}</span>
                        </label>
                    </div>`;
            });
            html += '</div></div>';
        });

        // Navigation buttons
        const isFirst = pageIndex === 0;
        const isLast = pageIndex === this.pages.length - 1;

        html += '<div class="btn-group">';
        html += isFirst
            ? '<div></div>'
            : `<button class="btn btn--ghost" onclick="survey._prevPage()">← 上一题</button>`;
        html += isLast
            ? `<button class="btn btn--primary" id="btn-submit" onclick="survey._submit()" disabled>提交问卷 →</button>`
            : `<button class="btn btn--primary" id="btn-next" onclick="survey._nextPage()" disabled>下一题 →</button>`;
        html += '</div>';

        this.container.innerHTML = html;

        // Restore previous answers if going back
        for (const q of page) {
            if (this.answers[q.name]) {
                const radio = document.getElementById(`${q.name}_${this.answers[q.name]}`);
                if (radio) {
                    radio.checked = true;
                    this._checkVisibility(q.name, this.answers[q.name]);
                }
            }
        }

        this._updateNavButton();
    }

    _onAnswer(qName, value) {
        this.answers[qName] = value;
        this._checkVisibility(qName, value);
        this._updateNavButton();
    }

    /**
     * Show/hide verification questions based on visibleIf conditions.
     */
    _checkVisibility(qName, value) {
        const page = this.pages[this.currentPage];
        for (const q of page) {
            if (!q.visibleIf) continue;
            const card = document.getElementById(`card-${q.name}`);
            if (!card) continue;

            // Parse condition: {TriggerQ} = 'TriggerVal'
            const match = q.visibleIf.match(/\{(\w+)\}\s*=\s*'(\w+)'/);
            if (match) {
                const triggerQ = match[1];
                const triggerVal = match[2];
                const shouldShow = this.answers[triggerQ] === triggerVal;

                if (shouldShow) {
                    card.classList.remove('hidden');
                    card.classList.add('fade-in');
                } else {
                    card.classList.add('hidden');
                    card.classList.remove('fade-in');
                    // Clear verification answer if hidden
                    delete this.answers[q.name];
                    const radios = card.querySelectorAll('input[type="radio"]');
                    radios.forEach(r => r.checked = false);
                }
            }
        }
    }

    _updateNavButton() {
        const page = this.pages[this.currentPage];
        const btn = document.getElementById('btn-next') || document.getElementById('btn-submit');
        if (!btn) return;

        // Check: every visible question on the page must be answered.
        const allAnswered = page.every(q => {
            const card = document.getElementById(`card-${q.name}`);
            const isHidden = card && card.classList.contains('hidden');
            if (isHidden) return true;
            return !!this.answers[q.name];
        });

        btn.disabled = !allAnswered;
    }

    _nextPage() {
        if (this.currentPage < this.pages.length - 1) {
            this.currentPage++;
            this._renderPage(this.currentPage);
            this._updateProgress();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    _prevPage() {
        if (this.currentPage > 0) {
            this.currentPage--;
            this._renderPage(this.currentPage);
            this._updateProgress();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    _updateProgress() {
        const fill = document.getElementById('progress-fill');
        const label = document.getElementById('progress-label');
        if (!fill || !label) return;

        const pct = ((this.currentPage + 1) / this.pages.length) * 100;
        fill.style.width = `${pct}%`;
        label.textContent = `${this.currentPage + 1} / ${this.pages.length}`;
    }

    async _submit() {
        const btn = document.getElementById('btn-submit');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> 提交中...';
        }

        try {
            // Get user_id (could be from a form, for now use anonymous)
            const userId = document.getElementById('user-id')?.value || 'anonymous';
            const result = await SjtApi.submitAnswers(userId, this.answers);

            // Redirect to result page
            window.location.href = `result.html?id=${result.submission_id}`;
        } catch (err) {
            alert('提交失败: ' + err.message);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '提交问卷 →';
            }
        }
    }

    _getQuestionNumber(qName) {
        let num = 0;
        for (const page of this.pages) {
            for (const q of page) {
                num++;
                if (q.name === qName) return num;
            }
        }
        return '?';
    }
}
