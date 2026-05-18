/**
 * api.js — Frontend API client for SJT Assessment Engine.
 * Handles communication with the FastAPI backend.
 */

const API_BASE = window.SJT_API_BASE || `${window.location.origin}/api`;

const SjtApi = {
    /**
     * Fetch questions from the backend for SurveyJS rendering.
     * @returns {Promise<{questions: Array, total: number}>}
     */
    async getQuestions() {
        const res = await fetch(`${API_BASE}/questions`);
        if (!res.ok) throw new Error(`Failed to fetch questions: ${res.status}`);
        return res.json();
    },

    /**
     * Submit a completed survey.
     * @param {string} userId - Student identifier
     * @param {Object} answers - Flat key-value map {question_id: selected_option}
     * @returns {Promise<{submission_id: string, message: string}>}
     */
    async submitAnswers(userId, answers, context = {}) {
        const res = await fetch(`${API_BASE}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                answers,
                core_case_id: context.core_case_id || '',
                return_url: context.return_url || '',
                source: context.source || '',
            }),
        });
        if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
        return res.json();
    },

    /**
     * Get the scoring report for a submission.
     * @param {string} submissionId - UUID of the submission
     * @returns {Promise<Object>} Full report with dimensions, holland_top3, mbti_type
     */
    async getReport(submissionId) {
        const res = await fetch(`${API_BASE}/report/${submissionId}`);
        if (!res.ok) throw new Error(`Report failed: ${res.status}`);
        return res.json();
    },

    /**
     * Get UI configuration (dimensions, metadata).
     * @returns {Promise<Object>}
     */
    async getConfig() {
        const res = await fetch(`${API_BASE}/config`);
        if (!res.ok) throw new Error(`Config failed: ${res.status}`);
        return res.json();
    },

    /**
     * Health check.
     * @returns {Promise<{status: string}>}
     */
    async health() {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    },
};
