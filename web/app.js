/**
 * 长伴 · 战略研究智能体
 */

let selectedMode = 'flow';
let pollInterval = null;
let vaultQuery = '';

function isLocalAccess() {
    const host = (location.hostname || '').toLowerCase();
    return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

document.addEventListener('DOMContentLoaded', () => {
    initEnv();
    initPresets();
    initModeSwitch();
    initActions();
    loadDeliverables();
    checkActiveJob();
});

function paintPill(id, level, text) {
    const dot = document.querySelector('#' + id + ' .dot');
    const label = document.querySelector('#' + id + ' .text');
    if (!dot || !label) return;
    dot.className = 'dot ' + (level || 'red');
    label.textContent = text;
}

function deepseekLabel(data) {
    const name = data.model_label || '模型';
    if (!data.deepseek || !data.deepseek.configured) return '推理服务未配置';
    if (data.deepseek.reachable) return name + ' · 可连通';
    return name + ' · 无法连通';
}

function searchLabel(section) {
    if (!section || !section.configured) return '搜索引擎未配置';
    if (section.reachable) return '搜索引擎 · 可连通';
    return '搜索引擎 · 无法连通';
}

// 1. 读取实际模型名，以及 DeepSeek / 搜索引擎是否已配置、能否连通
async function initEnv() {
    try {
        const res = await fetch('/api/status');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await res.json();
        paintPill('deepseekStatus', data.deepseek && data.deepseek.level, deepseekLabel(data));
        paintPill('searchStatus', data.search && data.search.level, searchLabel(data.search));
        const modelEl = document.getElementById('kpiModelName');
        if (modelEl) {
            modelEl.textContent = data.model_label || '未配置';
        }
        const note = document.getElementById('redactionNote');
        if (note) {
            note.textContent = data.redaction_enabled
                ? '外发脱敏已开启：手机号、身份证号、邮箱、银行卡号和已配置的客户企业名称会先换成占位符。'
                : '外发脱敏已关闭。课题会原样送去检索和模型。';
        }
    } catch (err) {
        paintPill('deepseekStatus', 'red', '状态读取失败');
        paintPill('searchStatus', 'red', '状态读取失败');
        console.error('Failed to init env:', err);
    }
}

// 2. 预设课题点击绑定
function initPresets() {
    const chips = document.querySelectorAll('.preset-chip');
    const input = document.getElementById('topicInput');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            input.value = chip.textContent.trim();
            input.focus();
        });
    });
}

// 3. 编排引擎切换
function initModeSwitch() {
    const modeBtns = document.querySelectorAll('.mode-btn');
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedMode = btn.dataset.mode;
        });
    });
}

// 4. 用户交互与事件绑定
function initActions() {
    const launchBtn = document.getElementById('launchBtn');
    const input = document.getElementById('topicInput');

    launchBtn.addEventListener('click', () => startResearch());
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            startResearch();
        }
    });

    // 只有通过本机地址打开页面时才提供“在 PPT 中打开”
    const btnOpenPptx = document.getElementById('btnOpenPptx');
    if (!isLocalAccess()) {
        btnOpenPptx.hidden = true;
    }
    btnOpenPptx.addEventListener('click', async () => {
        try {
            btnOpenPptx.textContent = '唤起中...';
            const res = await fetch('/api/open-pptx', { method: 'POST' });
            if (res.ok) {
                btnOpenPptx.textContent = '已在 PPT 打开';
            } else {
                btnOpenPptx.textContent = '打开失败';
            }
            setTimeout(() => {
                btnOpenPptx.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg> 在 PPT 中打开`;
            }, 3000);
        } catch (e) {
            alert('唤起本地 PowerPoint 失败: ' + e);
        }
    });

    // 图表灯箱
    const btnPreviewChart = document.getElementById('btnPreviewChart');
    const chartModal = document.getElementById('chartModal');
    const closeChartBtn = document.getElementById('closeChartBtn');
    btnPreviewChart.addEventListener('click', () => {
        const img = document.getElementById('chartLightboxImg');
        img.src = '/api/deliverables/download/chart?t=' + Date.now();
        chartModal.classList.add('active');
    });
    closeChartBtn.addEventListener('click', () => {
        chartModal.classList.remove('active');
    });

    // 历史智库弹窗
    const openVaultBtn = document.getElementById('openVaultBtn');
    const vaultModal = document.getElementById('vaultModal');
    const closeVaultBtn = document.getElementById('closeVaultBtn');
    openVaultBtn.addEventListener('click', () => {
        loadArchives();
        vaultModal.classList.add('active');
    });
    closeVaultBtn.addEventListener('click', () => {
        vaultModal.classList.remove('active');
    });
    const vaultSearch = document.getElementById('vaultSearch');
    vaultSearch.addEventListener('input', () => {
        vaultQuery = vaultSearch.value.trim();
        loadArchives();
    });

    // 复制全文
    const copyBtn = document.getElementById('copyReportBtn');
    copyBtn.addEventListener('click', () => {
        const text = document.getElementById('reportPreviewContent').innerText;
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = '已复制！';
            setTimeout(() => copyBtn.textContent = '复制全文', 2000);
        });
    });

    // 点击滚动到研报
    document.getElementById('btnReadMd').addEventListener('click', () => {
        document.getElementById('readerSection').scrollIntoView({ behavior: 'smooth' });
    });
}

// 5. 启动研究任务
async function startResearch() {
    const input = document.getElementById('topicInput');
    const topic = input.value.trim();
    if (!topic) {
        alert('请输入或选择需要深度研究的课题');
        return;
    }

    const launchBtn = document.getElementById('launchBtn');
    launchBtn.disabled = true;
    launchBtn.querySelector('.btn-label').textContent = '研究调度中...';

    try {
        const res = await fetch('/api/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, mode: selectedMode })
        });

        if (!res.ok) {
            const err = await res.json();
            alert('启动失败: ' + (err.detail || '未知错误'));
            launchBtn.disabled = false;
            launchBtn.querySelector('.btn-label').textContent = '启动全流程战略研究';
            return;
        }

        // 展开流水线面板并开始轮询
        document.getElementById('pipelineSection').style.display = 'block';
        document.getElementById('pipelineSection').scrollIntoView({ behavior: 'smooth' });
        startPolling();

    } catch (e) {
        alert('网络请求异常: ' + e);
        launchBtn.disabled = false;
        launchBtn.querySelector('.btn-label').textContent = '启动全流程战略研究';
    }
}

// 6. 检查是否存在运行中的任务
async function checkActiveJob() {
    try {
        const res = await fetch('/api/job-status');
        const data = await res.json();
        if (data.is_running) {
            document.getElementById('pipelineSection').style.display = 'block';
            startPolling();
        }
    } catch (e) {
        console.error('Job check failed:', e);
    }
}

// 7. 轮询流水线状态与日志
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/job-status');
            const data = await res.json();
            updatePipelineUI(data);

            if (!data.is_running && data.stage === 'done') {
                clearInterval(pollInterval);
                pollInterval = null;
                resetLaunchBtn();
                loadDeliverables();
            } else if (!data.is_running && data.stage === 'error') {
                clearInterval(pollInterval);
                pollInterval = null;
                resetLaunchBtn();
                alert('任务遇到错误: ' + data.error);
            }
        } catch (e) {
            console.error('Poll failed:', e);
        }
    }, 1200);
}

function resetLaunchBtn() {
    const launchBtn = document.getElementById('launchBtn');
    launchBtn.disabled = false;
    launchBtn.querySelector('.btn-label').textContent = '启动全流程战略研究';
}

// 8. 实时更新流水线 UI
function updatePipelineUI(job) {
    document.getElementById('progressFill').style.width = job.progress + '%';
    document.getElementById('progressPercent').textContent = job.progress + '%';

    const statusTextMap = {
        'idle': '系统就绪',
        'scout': '检索员正在搜集公开资料并保留来源链接...',
        'gate': '质量门禁：正在检查链接数量和篇幅...',
        'analyst': '分析员正在根据检索底稿整理判断...',
        'multimodal': '正在整理 Word、幻灯片、图表和 Markdown...',
        'done': '全流程完成：多模态战略交付物已全部生成！',
        'error': '运行异常中断'
    };
    document.getElementById('pipelineStatusText').textContent = statusTextMap[job.stage] || '任务执行中...';

    // 节点亮起状态
    const stepScout = document.getElementById('stepScout');
    const stepGate = document.getElementById('stepGate');
    const stepAnalyst = document.getElementById('stepAnalyst');
    const stepMultimodal = document.getElementById('stepMultimodal');

    [stepScout, stepGate, stepAnalyst, stepMultimodal].forEach(el => {
        el.className = 'step-node';
    });

    if (job.stage === 'scout') {
        stepScout.className = 'step-node active';
    } else if (job.stage === 'gate') {
        stepScout.className = 'step-node done';
        stepGate.className = 'step-node active';
    } else if (job.stage === 'analyst') {
        stepScout.className = 'step-node done';
        stepGate.className = 'step-node done';
        stepAnalyst.className = 'step-node active';
    } else if (job.stage === 'multimodal') {
        stepScout.className = 'step-node done';
        stepGate.className = 'step-node done';
        stepAnalyst.className = 'step-node done';
        stepMultimodal.className = 'step-node active';
    } else if (job.stage === 'done') {
        stepScout.className = 'step-node done';
        stepGate.className = 'step-node done';
        stepAnalyst.className = 'step-node done';
        stepMultimodal.className = 'step-node done';
    }

    // 滚动更新日志
    if (job.logs && job.logs.length > 0) {
        const logBox = document.getElementById('logStream');
        logBox.innerHTML = job.logs.map(line => `<div class="log-line">${escapeHtml(line)}</div>`).join('');
        logBox.scrollTop = logBox.scrollHeight;
    }
}

// 9. 加载交付物信息与报告预览
async function loadDeliverables() {
    try {
        const res = await fetch('/api/deliverables');
        const data = await res.json();
        const files = data.deliverables;

        if (files.docx && files.docx.exists) {
            document.getElementById('sizeDocx').textContent = files.docx.size_kb + ' KB';
        }
        if (files.pptx && files.pptx.exists) {
            document.getElementById('sizePptx').textContent = files.pptx.size_kb + ' KB';
        }
        if (files.chart && files.chart.exists) {
            document.getElementById('sizeChart').textContent = files.chart.size_kb + ' KB';
        }
        if (files.md && files.md.exists) {
            document.getElementById('sizeMd').textContent = files.md.size_kb + ' KB';
        }

        if (data.markdown_preview) {
            renderMarkdown(data.markdown_preview);
        }
    } catch (e) {
        console.error('Failed to load deliverables:', e);
    }
}

// 10. 极简安全 Markdown 渲染器
function renderMarkdown(md) {
    const box = document.getElementById('reportPreviewContent');
    if (!md.trim()) {
        box.innerHTML = '<div class="empty-state">暂无最新研报内容</div>';
        return;
    }

    let html = escapeHtml(md)
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        .replace(/`([^`]+)`/gim, '<code>$1</code>')
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/\n\n/gim, '</p><p>');

    box.innerHTML = '<p>' + html + '</p>';
}

// 11. 加载历史智库列表
async function loadArchives() {
    const list = document.getElementById('vaultList');
    list.innerHTML = '<div class="loading-spinner">正在调取档案数据...</div>';

    try {
        const res = await fetch('/api/archives?q=' + encodeURIComponent(vaultQuery));
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await res.json();

        if (!data.archives || data.archives.length === 0) {
            list.innerHTML = '<div class="empty-state">' + (vaultQuery ? '没有匹配的历史课题' : '智库暂无历史研报档案') + '</div>';
            return;
        }

        list.innerHTML = data.archives.map(item => `
            <div class="vault-item" onclick="openArchive('${encodeURIComponent(item.filename)}')">
                <div>
                    <div class="vault-topic">${escapeHtml(item.topic)}</div>
                    <div class="vault-meta">日期: ${escapeHtml(item.date)} · 文件体积: ${item.size_kb} KB</div>
                </div>
                <div class="vault-actions">
                    <button type="button" class="read-md-btn">调取研报</button>
                    <button type="button" class="danger-btn" onclick="deleteArchive(event, '${encodeURIComponent(item.filename)}')">删除</button>
                </div>
            </div>
        `).join('');

    } catch (e) {
        list.innerHTML = '<div class="empty-state">读取档案失败: ' + escapeHtml(String(e)) + '</div>';
    }
}

async function deleteArchive(event, filename) {
    event.stopPropagation();
    const decoded = decodeURIComponent(filename);
    if (!confirm('确认删除这条历史课题？对应的 Word、幻灯片、图表和 Markdown 会一起删除，且不能恢复。')) {
        return;
    }
    try {
        const res = await fetch('/api/archives/' + filename, { method: 'DELETE' });
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert('删除失败: ' + (err.detail || res.status));
            return;
        }
        loadArchives();
    } catch (e) {
        alert('删除失败: ' + e);
    }
}

// 调取特定归档
async function openArchive(filename) {
    try {
        const res = await fetch('/api/archives/content/' + filename);
        const data = await res.json();
        renderMarkdown(data.content);
        document.getElementById('vaultModal').classList.remove('active');
        document.getElementById('readerSection').scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
        alert('读取归档失败: ' + e);
    }
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
