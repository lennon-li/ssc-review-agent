// App State
let state = {
    sessionId: null,
    files: [],
    evaluation: null,
    statusLog: ["System Ready. Pure Python Backend Initialized. Please upload application files."]
};

// DOM Elements
const navSetup = document.getElementById('nav-setup');
const navReview = document.getElementById('nav-review');
const tabSetup = document.getElementById('tab-setup');
const tabReview = document.getElementById('tab-review');
const uploadBox = document.getElementById('upload-box');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const btnRun = document.getElementById('btn-run');
const activityLog = document.getElementById('activity-log');
const loadingOverlay = document.getElementById('loading-overlay');
const loaderText = document.getElementById('loader-text');

// Initialize
function init() {
    // Navigation
    navSetup.addEventListener('click', () => switchTab('setup'));
    navReview.addEventListener('click', () => switchTab('review'));

    // Upload
    uploadBox.addEventListener('click', () => fileInput.click());
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.style.backgroundColor = '#e1e1e1';
    });
    uploadBox.addEventListener('dragleave', () => {
        uploadBox.style.backgroundColor = '#fafafa';
    });
    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.style.backgroundColor = '#fafafa';
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));

    // Run Assessment
    btnRun.addEventListener('click', runEvaluation);

    // Results Sub-tabs
    document.querySelectorAll('.tab-nav button').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-nav button').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.report-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });

    // Exports
    document.getElementById('export-html').addEventListener('click', () => exportReport('html'));
    document.getElementById('export-docx').addEventListener('click', () => exportReport('docx'));
    document.getElementById('export-md').addEventListener('click', () => exportReport('markdown'));
    
    // Filters
    document.getElementById('filter-attention').addEventListener('change', renderCriteria);
}

function switchTab(tab) {
    if (tab === 'setup') {
        navSetup.classList.add('active');
        navReview.classList.remove('active');
        tabSetup.classList.add('active');
        tabReview.classList.remove('active');
    } else {
        navSetup.classList.remove('active');
        navReview.classList.add('active');
        tabSetup.classList.remove('active');
        tabReview.classList.add('active');
    }
}

function log(msg) {
    const time = new Date().toLocaleTimeString();
    state.statusLog.push(`[${time}] ${msg}`);
    activityLog.innerText = state.statusLog.join('\n');
    activityLog.scrollTop = activityLog.scrollHeight;
}

async function handleFiles(files) {
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    log(`Uploading ${files.length} files...`);
    btnRun.disabled = true;

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        state.sessionId = data.session_id;
        state.files = data.files;
        
        renderFileList();
        log(`Upload successful. Ready for evaluation.`);
        btnRun.disabled = false;
    } catch (err) {
        log(`Error: ${err.message}`);
    }
}

function renderFileList() {
    fileList.innerHTML = state.files.map(f => `
        <div class="file-item">
            <span><i class="fa-solid fa-file"></i> ${f}</span>
            <i class="fa-solid fa-check-circle text-success"></i>
        </div>
    `).join('');
}

async function runEvaluation() {
    if (!state.sessionId) return;
    
    loadingOverlay.classList.remove('hidden');
    loaderText.innerText = "Evaluating via App Builder... This typically takes 20-40 seconds.";
    log("Connecting to Enterprise Search Engine...");

    try {
        const response = await fetch('/api/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId, evaluator_type: 'vertex' })
        });
        
        if (!response.ok) throw new Error(await response.text());
        
        const data = await response.json();
        state.evaluation = data;
        
        log("App Builder Evaluation complete. Processing results...");
        renderResults();
        navReview.disabled = false;
        
        setTimeout(() => {
            switchTab('review');
            loadingOverlay.classList.add('hidden');
            log("Review dashboard ready.");
        }, 800);
        
    } catch (err) {
        log(`❌ Evaluation failed: ${err.message}`);
        log(`💡 AI processes can occasionally time out or misformat responses. Please click "Run AI Assessment" to try again.`);
        loadingOverlay.classList.add('hidden');
        btnRun.disabled = false; // Re-enable the button so they can retry easily
        alert(`AI Error: ${err.message}\n\nThis is normal with heavy AI workloads (e.g. timeouts or JSON formatting errors). Please click "Run AI Assessment" to try again.`);
    }
}

function renderResults() {
    const eval = state.evaluation;
    
    // Profile
    document.getElementById('applicant-name').innerText = eval.applicant_id || "Unknown Applicant";
    const badge = document.getElementById('consensus-badge');
    if (eval.ready_for_human_review) {
        badge.innerText = "Ready for Approval";
        badge.className = "badge badge-success";
    } else {
        badge.innerText = "Review Required";
        badge.className = "badge badge-warning";
    }

    // Photo
    if (eval.photo_url) {
        document.getElementById('applicant-photo').innerHTML = `<img src="${eval.photo_url}" alt="Applicant">`;
    }

    // Summary
    document.getElementById('summary-text').innerText = eval.overall_summary || "No summary provided.";

    // Course Table
    const tableBody = document.querySelector('#courses-table tbody');
    tableBody.innerHTML = (eval.course_checklist || []).map(item => `
        <tr>
            <td>${item.module}</td>
            <td>${item.course_code}</td>
            <td>${item.is_satisfied ? '<span class="text-success">✅ Satisfied</span>' : '<span class="text-danger">❌ Missing/Fail</span>'}</td>
        </tr>
    `).join('');

    // Preview HTML
    document.getElementById('preview-container').innerHTML = eval.report_html || "<p>Preview not available.</p>";

    // Criteria
    renderCriteria();
}

function renderCriteria() {
    const showOnlyFlagged = document.getElementById('filter-attention').checked;
    let criteria = state.evaluation.criteria || [];
    
    if (showOnlyFlagged) {
        criteria = criteria.filter(c => c.needs_human_attention);
    }

    const list = document.getElementById('criteria-list');
    list.innerHTML = criteria.map(c => `
        <div class="criterion-card ${c.needs_human_attention ? 'flagged' : ''}">
            <div class="criterion-header">
                <span>${c.criterion_name}</span>
                <span>${c.needs_human_attention ? '⚠️ Attention Needed' : '✅ Satisfied'}</span>
            </div>
            <div class="criterion-body">
                <p>${c.supporting_evidence}</p>
            </div>
        </div>
    `).join('');
    
    if (criteria.length === 0) {
        list.innerHTML = `<p class="text-center">No criteria to display.</p>`;
    }
}

async function exportReport(fmt) {
    if (!state.sessionId) return;
    window.location.href = `/api/session/${state.sessionId}/export/${fmt}`;
}

init();
