document.addEventListener("DOMContentLoaded", () => {
    const STORAGE_KEY = "mimar.panel.apiBase";
    const DEFAULT_POLL_MS = 12000;

    const state = {
        apiBase: resolveInitialApiBase(),
        activeTab: "dashboard",
        activeMemTab: "persona",
        activeSrcTab: "file",
        selectedFilePath: null,
        pendingActionId: null,
        hierarchy: null,
        stats: [],
        logs: [],
        skills: [],
        pendingActions: [],
        system: null,
        chart: null,
        lastSyncAt: null,
        expandedDirs: new Set(),
        heartbeatDirty: false,
        heartbeat: {
            config: null,
            status: null,
            jobs: [],
        },
        pendingUploadFile: null,
        social: {
            browser: null,
            queue: { items: [] },
            selectedQueueId: null,
            editorDirty: false,
        },
    };

    const dom = {
        navItems: [...document.querySelectorAll(".nav-item")],
        tabPanels: [...document.querySelectorAll(".tab-panel")],
        memNavItems: [...document.querySelectorAll(".mem-nav-item")],
        memPanes: [...document.querySelectorAll(".memory-pane")],
        srcTabs: [...document.querySelectorAll(".src-tab")],
        srcPanes: [...document.querySelectorAll(".src-sub-content")],
        currentTabTitle: document.getElementById("current-tab-title"),
        connectionState: document.getElementById("connection-state"),
        apiBaseInput: document.getElementById("api-base-input"),
        saveApiBase: document.getElementById("save-api-base"),
        refreshAll: document.getElementById("refresh-all"),
        sidebarSystemChip: document.getElementById("sidebar-system-chip"),
        sidebarModel: document.getElementById("sidebar-model"),
        sidebarUptime: document.getElementById("sidebar-uptime"),
        heroSystemPill: document.getElementById("hero-system-pill"),
        lastSyncLabel: document.getElementById("last-sync-label"),
        metricModel: document.getElementById("metric-model"),
        metricUptime: document.getElementById("metric-uptime"),
        metricApprovals: document.getElementById("metric-approvals"),
        summaryGrid: document.getElementById("summary-grid"),
        basemodelTools: document.getElementById("basemodel-tools"),
        submodelsContainer: document.getElementById("submodels-container"),
        liveActivity: document.getElementById("live-activity"),
        pendingActionsList: document.getElementById("pending-actions-list"),
        approvalCountBadge: document.getElementById("approval-count-badge"),
        approvalBadge: document.getElementById("approval-badge"),
        approvalModal: document.getElementById("approval-modal"),
        approvalDesc: document.getElementById("approval-desc"),
        btnApprove: document.getElementById("btn-approve"),
        btnReject: document.getElementById("btn-reject"),
        personaEditor: document.getElementById("persona-editor"),
        savePersona: document.getElementById("save-persona"),
        jsonEditor: document.getElementById("json-editor"),
        saveJson: document.getElementById("save-json"),
        memListTitle: document.getElementById("mem-list-title"),
        memTableBody: document.getElementById("mem-table-body"),
        newMemKey: document.getElementById("new-mem-key"),
        newMemVal: document.getElementById("new-mem-val"),
        btnAddMem: document.getElementById("btn-add-mem"),
        fileTree: document.getElementById("file-tree"),
        currentFileName: document.getElementById("current-file-name"),
        currentFilePath: document.getElementById("current-file-path"),
        fileViewer: document.getElementById("file-viewer"),
        btnRunCode: document.getElementById("btn-run-code"),
        terminalOutput: document.getElementById("terminal-output"),
        clearConsole: document.getElementById("clear-console"),
        btnAddSource: document.getElementById("btn-add-source"),
        refreshTree: document.getElementById("refresh-tree"),
        sourceModal: document.getElementById("source-modal"),
        closeSourceModal: document.getElementById("close-source-modal"),
        fileInput: document.getElementById("file-input"),
        dropZone: document.getElementById("drop-zone"),
        selectedFileName: document.getElementById("selected-file-name"),
        btnUpload: document.getElementById("btn-upload"),
        btnAddUrl: document.getElementById("btn-add-url"),
        btnAddText: document.getElementById("btn-add-text"),
        srcUrlName: document.getElementById("src-url-name"),
        srcUrlVal: document.getElementById("src-url-val"),
        srcTextName: document.getElementById("src-text-name"),
        srcTextVal: document.getElementById("src-text-val"),
        reloadSkills: document.getElementById("reload-skills"),
        skillsList: document.getElementById("skills-list"),
        heartbeatEditor: document.getElementById("heartbeat-editor"),
        heartbeatEnable: document.getElementById("heartbeat-enable"),
        heartbeatDisable: document.getElementById("heartbeat-disable"),
        heartbeatReload: document.getElementById("heartbeat-reload"),
        heartbeatEnabledState: document.getElementById("heartbeat-enabled-state"),
        heartbeatMeta: document.getElementById("heartbeat-meta"),
        heartbeatRunningState: document.getElementById("heartbeat-running-state"),
        heartbeatRunningMeta: document.getElementById("heartbeat-running-meta"),
        heartbeatConfigState: document.getElementById("heartbeat-config-state"),
        heartbeatConfigMeta: document.getElementById("heartbeat-config-meta"),
        heartbeatJobList: document.getElementById("heartbeat-job-list"),
        saveHeartbeat: document.getElementById("save-heartbeat"),
        launchBrowserVisible: document.getElementById("launch-browser-visible"),
        launchBrowserHeadless: document.getElementById("launch-browser-headless"),
        refreshSocial: document.getElementById("refresh-social"),
        scanSocial: document.getElementById("scan-social"),
        socialBrowserState: document.getElementById("social-browser-state"),
        socialBrowserUrl: document.getElementById("social-browser-url"),
        socialBrowserMode: document.getElementById("social-browser-mode"),
        socialQueueCount: document.getElementById("social-queue-count"),
        socialQueueUpdated: document.getElementById("social-queue-updated"),
        socialSelectedMeta: document.getElementById("social-selected-meta"),
        socialOpenLink: document.getElementById("social-open-link"),
        socialQueueList: document.getElementById("social-queue-list"),
        socialEditorTitle: document.getElementById("social-editor-title"),
        socialCommentPreview: document.getElementById("social-comment-preview"),
        socialReplyEditor: document.getElementById("social-reply-editor"),
        socialGenerateDraft: document.getElementById("social-generate-draft"),
        socialSaveDraft: document.getElementById("social-save-draft"),
        socialSkipItem: document.getElementById("social-skip-item"),
        socialSendReply: document.getElementById("social-send-reply"),
        statsChart: document.getElementById("stats-chart"),
        toastRegion: document.getElementById("toast-region"),
    };

    bindEvents();
    initializePanel();

    function resolveInitialApiBase() {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            return stored;
        }
        if (window.location.protocol.startsWith("http")) {
            return `${window.location.origin}/api`;
        }
        return "http://localhost:8001/api";
    }

    function normalizeApiBase(value) {
        let normalized = (value || "").trim();
        if (!normalized) {
            return resolveInitialApiBase();
        }
        if (normalized.startsWith("/")) {
            normalized = `${window.location.origin}${normalized}`;
        }
        normalized = normalized.replace(/\/+$/, "");
        if (!normalized.endsWith("/api")) {
            normalized = `${normalized}/api`;
        }
        return normalized;
    }

    function bindEvents() {
        dom.apiBaseInput.value = state.apiBase;

        dom.navItems.forEach((item) => {
            item.addEventListener("click", () => switchTab(item.dataset.tab));
        });

        dom.memNavItems.forEach((item) => {
            item.addEventListener("click", () => switchMemTab(item.dataset.mem));
        });

        dom.srcTabs.forEach((item) => {
            item.addEventListener("click", () => switchSourceTab(item.dataset.src));
        });

        dom.saveApiBase.addEventListener("click", connectApiBase);
        dom.apiBaseInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                connectApiBase();
            }
        });

        dom.refreshAll.addEventListener("click", async () => {
            try {
                await refreshActiveView();
                toast("Panel verileri yenilendi.", "success");
            } catch (error) {
                setConnectionState(`Yenileme başarısız: ${error.message}`, "error");
                toast(`Panel yenilenemedi: ${error.message}`, "error");
            }
        });

        dom.approvalBadge.addEventListener("click", () => {
            const current = state.pendingActions.find((item) => item.id === state.pendingActionId) || state.pendingActions[0];
            if (current) {
                openApprovalModal(current);
            }
        });

        dom.btnApprove.addEventListener("click", () => decideAction("approve"));
        dom.btnReject.addEventListener("click", () => decideAction("reject"));

        dom.savePersona.addEventListener("click", savePersona);
        dom.saveJson.addEventListener("click", saveJsonMemory);
        dom.btnAddMem.addEventListener("click", addMemoryEntry);

        dom.refreshTree.addEventListener("click", fetchWorkspaceTree);
        dom.btnRunCode.addEventListener("click", runSelectedCode);
        dom.clearConsole.addEventListener("click", clearConsole);

        dom.btnAddSource.addEventListener("click", () => dom.sourceModal.classList.remove("hidden"));
        dom.closeSourceModal.addEventListener("click", () => dom.sourceModal.classList.add("hidden"));
        dom.sourceModal.addEventListener("click", (event) => {
            if (event.target === dom.sourceModal) {
                dom.sourceModal.classList.add("hidden");
            }
        });
        dom.approvalModal.addEventListener("click", (event) => {
            if (event.target === dom.approvalModal) {
                dom.approvalModal.classList.add("hidden");
            }
        });
        dom.fileInput.addEventListener("change", syncSelectedFile);
        dom.dropZone.addEventListener("click", () => dom.fileInput.click());
        dom.dropZone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dom.dropZone.classList.add("dragover");
        });
        dom.dropZone.addEventListener("dragleave", () => dom.dropZone.classList.remove("dragover"));
        dom.dropZone.addEventListener("drop", (event) => {
            event.preventDefault();
            dom.dropZone.classList.remove("dragover");
            if (event.dataTransfer.files.length > 0) {
                state.pendingUploadFile = event.dataTransfer.files[0];
                syncSelectedFile();
            }
        });

        dom.btnUpload.addEventListener("click", uploadSelectedFile);
        dom.btnAddUrl.addEventListener("click", addUrlTarget);
        dom.btnAddText.addEventListener("click", addTextTarget);

        dom.reloadSkills.addEventListener("click", reloadSkills);
        dom.heartbeatEnable.addEventListener("click", () => toggleHeartbeat(true));
        dom.heartbeatDisable.addEventListener("click", () => toggleHeartbeat(false));
        dom.heartbeatReload.addEventListener("click", reloadHeartbeatScheduler);
        dom.saveHeartbeat.addEventListener("click", saveHeartbeatConfig);
        dom.heartbeatEditor.addEventListener("input", () => {
            state.heartbeatDirty = true;
        });
        dom.heartbeatJobList.addEventListener("click", (event) => {
            const button = event.target.closest("[data-heartbeat-action]");
            if (!button) {
                return;
            }
            handleHeartbeatJobAction(
                button.dataset.heartbeatJobId,
                button.dataset.heartbeatAction
            );
        });
        dom.launchBrowserVisible.addEventListener("click", () => launchSocialBrowser(false));
        dom.launchBrowserHeadless?.addEventListener("click", () => launchSocialBrowser(false));
        dom.refreshSocial.addEventListener("click", async () => {
            await fetchSocialSnapshot();
            toast("Sosyal kuyruk yenilendi.", "success");
        });
        dom.scanSocial.addEventListener("click", scanSocialPage);
        dom.socialGenerateDraft.addEventListener("click", generateSocialDraft);
        dom.socialSaveDraft.addEventListener("click", saveSocialDraft);
        dom.socialSkipItem.addEventListener("click", skipSocialItem);
        dom.socialSendReply.addEventListener("click", sendSocialReply);
        dom.socialReplyEditor.addEventListener("input", () => {
            state.social.editorDirty = true;
        });
        dom.socialQueueList.addEventListener("click", (event) => {
            const item = event.target.closest("[data-social-queue-id]");
            if (!item) {
                return;
            }
            selectSocialItem(item.dataset.socialQueueId);
        });

        dom.fileTree.addEventListener("click", async (event) => {
            const node = event.target.closest("[data-tree-path]");
            if (!node) {
                return;
            }

            const { treePath, treeType, treeName } = node.dataset;
            if (treeType === "directory") {
                if (state.expandedDirs.has(treePath)) {
                    state.expandedDirs.delete(treePath);
                } else {
                    state.expandedDirs.add(treePath);
                }
                await fetchWorkspaceTree({ silent: true });
                return;
            }

            await loadFile(treePath, treeName);
        });

        dom.submodelsContainer.addEventListener("click", async (event) => {
            const button = event.target.closest("[data-agent-toggle]");
            if (!button) {
                return;
            }

            await apiRequest(`/agents/${encodeURIComponent(button.dataset.agentToggle)}/toggle`, {
                method: "POST",
            });
            toast("Ajan durumu güncellendi.", "success");
            await fetchBootstrap();
        });

        document.addEventListener("click", handleToolToggle);

        dom.pendingActionsList.addEventListener("click", (event) => {
            const button = event.target.closest("[data-open-approval]");
            if (!button) {
                return;
            }
            const action = state.pendingActions.find((item) => item.id === button.dataset.openApproval);
            if (action) {
                openApprovalModal(action);
            }
        });

        dom.skillsList.addEventListener("click", async (event) => {
            const button = event.target.closest("[data-skill-toggle]");
            if (!button) {
                return;
            }
            await toggleSkill(button.dataset.skillToggle);
        });

        document.addEventListener("visibilitychange", async () => {
            if (!document.hidden) {
                await refreshActiveView({ silent: true });
            }
        });
    }

    async function initializePanel() {
        try {
            await refreshActiveView({ silent: true });
        } catch (error) {
            setConnectionState(`İlk senkron başarısız: ${error.message}`, "error");
            toast(`İlk bağlantı kurulamadı: ${error.message}`, "error");
        }
        window.setInterval(async () => {
            if (document.hidden) {
                return;
            }
            try {
                await refreshActiveView({ silent: true });
            } catch (error) {
                setConnectionState(`Arka plan senkronu başarısız: ${error.message}`, "error");
            }
        }, DEFAULT_POLL_MS);
    }

    async function connectApiBase() {
        const previous = state.apiBase;
        const nextBase = normalizeApiBase(dom.apiBaseInput.value);
        state.apiBase = nextBase;
        dom.apiBaseInput.value = nextBase;

        try {
            await fetchBootstrap();
            localStorage.setItem(STORAGE_KEY, nextBase);
            toast("API bağlantısı güncellendi.", "success");
        } catch (error) {
            state.apiBase = previous;
            dom.apiBaseInput.value = previous;
            setConnectionState(`Bağlantı başarısız: ${error.message}`, "error");
            toast(`API bağlantısı kurulamadı: ${error.message}`, "error");
        }
    }

    async function apiRequest(path, options = {}) {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), options.timeout ?? 12000);
        const headers = new Headers(options.headers || {});
        const config = {
            method: options.method || "GET",
            headers,
            signal: controller.signal,
        };

        if (options.body !== undefined) {
            if (options.body instanceof FormData) {
                config.body = options.body;
            } else if (typeof options.body === "string") {
                config.body = options.body;
                if (!headers.has("Content-Type")) {
                    headers.set("Content-Type", "text/plain;charset=UTF-8");
                }
            } else {
                config.body = JSON.stringify(options.body);
                if (!headers.has("Content-Type")) {
                    headers.set("Content-Type", "application/json");
                }
            }
        }

        try {
            const response = await fetch(`${state.apiBase}${path}`, config);
            const contentType = response.headers.get("content-type") || "";
            const payload = contentType.includes("application/json")
                ? await response.json()
                : await response.text();

            if (!response.ok) {
                const rawDetail = typeof payload === "string"
                    ? payload
                    : payload.detail ?? payload.message ?? "Bilinmeyen API hatası";
                const message = typeof rawDetail === "string"
                    ? rawDetail
                    : rawDetail.message
                        || [rawDetail.busy_owner, rawDetail.busy_label].filter(Boolean).join(" • ")
                        || JSON.stringify(rawDetail);
                throw new Error(message);
            }

            return payload;
        } catch (error) {
            if (error.name === "AbortError") {
                throw new Error("İstek zaman aşımına uğradı.");
            }
            throw error;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    async function refreshActiveView({ silent = false } = {}) {
        await fetchBootstrap({ silent });
        if (state.activeTab === "memory") {
            await loadMemoryTab({ silent: true });
        }
        if (state.activeTab === "workspace") {
            await fetchWorkspaceTree({ silent: true });
        }
        if (state.activeTab === "automation") {
            await fetchHeartbeatConfig({ silent: true });
            await fetchSocialSnapshot({ silent: true });
        }
    }

    async function fetchBootstrap({ silent = false } = {}) {
        const payload = await apiRequest("/panel/bootstrap");
        state.system = payload.system || null;
        state.hierarchy = payload.hierarchy || { tools: [], submodels: [] };
        state.logs = payload.logs || [];
        state.stats = payload.stats || [];
        state.pendingActions = payload.pending_actions || [];
        state.skills = payload.skills || [];
        state.heartbeat = {
            config: payload.heartbeat || null,
            status: payload.heartbeat_status || null,
            jobs: payload.heartbeat_jobs || [],
        };
        state.social.browser = payload.social?.browser || null;
        state.social.queue = payload.social?.queue || { items: [] };

        if (!state.heartbeatDirty && payload.heartbeat && typeof payload.heartbeat.content === "string") {
            dom.heartbeatEditor.value = payload.heartbeat.content;
        }

        renderSystem(payload.system);
        renderHierarchy(payload.hierarchy);
        renderLogs(payload.logs);
        renderPendingActions(payload.pending_actions);
        renderSummary(payload.hierarchy, payload.skills, payload.pending_actions);
        renderStatsChart(payload.stats);
        renderSkills(payload.skills);
        renderHeartbeat();
        renderSocial(payload.social || { browser: null, queue: { items: [] } });
        markSync();

        if (!silent) {
            setConnectionState("API senkronize edildi.", "success");
        }
    }

    function renderSystem(system) {
        if (!system) {
            setConnectionState("API cevap vermiyor.", "error");
            updateStatusChip(dom.sidebarSystemChip, "Offline", false);
            updateStatusChip(dom.heroSystemPill, "Offline", false);
            return;
        }

        const isOnline = system.status === "Online";
        const uptime = formatUptime(system.uptime || 0);

        updateStatusChip(dom.sidebarSystemChip, system.status, isOnline);
        updateStatusChip(dom.heroSystemPill, system.status, isOnline);
        dom.sidebarModel.textContent = system.model || "Model bilgisi yok";
        dom.sidebarUptime.textContent = `Uptime: ${uptime}`;
        dom.metricModel.textContent = system.model || "-";
        dom.metricUptime.textContent = uptime;

        setConnectionState(
            isOnline ? `Bağlı: ${state.apiBase}` : "Sistem offline görünüyor.",
            isOnline ? "success" : "warning"
        );
    }

    function renderSummary(hierarchy, skills, pendingActions) {
        const agents = hierarchy?.submodels || [];
        const rootTools = hierarchy?.tools || [];
        const allTools = rootTools.concat(...agents.map((agent) => agent.tools || []));
        const activeAgents = agents.filter((agent) => agent.active).length;
        const activeTools = allTools.filter((tool) => tool.active).length;
        const summaryItems = [
            { label: "Ajan", value: `${activeAgents}/${agents.length || 0}`, tone: "teal" },
            { label: "Aktif Tool", value: `${activeTools}/${allTools.length || 0}`, tone: "amber" },
            { label: "Skill", value: `${skills?.length || 0}`, tone: "slate" },
            { label: "Approval", value: `${pendingActions?.length || 0}`, tone: "rose" },
        ];

        dom.metricApprovals.textContent = `${pendingActions?.length || 0}`;
        dom.summaryGrid.innerHTML = "";

        summaryItems.forEach((item) => {
            const card = document.createElement("div");
            card.className = `summary-item tone-${item.tone}`;
            const label = document.createElement("span");
            label.textContent = item.label;
            const value = document.createElement("strong");
            value.textContent = item.value;
            card.append(label, value);
            dom.summaryGrid.appendChild(card);
        });
    }

    function renderHierarchy(hierarchy) {
        dom.basemodelTools.innerHTML = "";
        dom.submodelsContainer.innerHTML = "";

        (hierarchy?.tools || []).forEach((tool) => {
            dom.basemodelTools.appendChild(createToolPill(tool));
        });

        (hierarchy?.submodels || []).forEach((agent) => {
            const card = document.createElement("article");
            card.className = `agent-card ${agent.active ? "" : "is-inactive"}`;

            const head = document.createElement("div");
            head.className = "agent-card-head";

            const icon = document.createElement("span");
            icon.className = "node-mark";
            icon.textContent = resolveAgentIcon(agent.name);

            const textWrap = document.createElement("div");
            const title = document.createElement("h4");
            title.textContent = agent.name;
            const subtitle = document.createElement("p");
            subtitle.textContent = agent.active ? "Aktif durumda" : "Şu anda pasif";
            textWrap.append(title, subtitle);

            const toggle = document.createElement("button");
            toggle.className = `toggle-pill ${agent.active ? "is-active" : ""}`;
            toggle.type = "button";
            toggle.dataset.agentToggle = agent.name;
            toggle.textContent = agent.active ? "Aktif" : "Pasif";

            head.append(icon, textWrap, toggle);

            const tools = document.createElement("div");
            tools.className = "tool-cloud";
            (agent.tools || []).forEach((tool) => {
                tools.appendChild(createToolPill(tool));
            });

            card.append(head, tools);
            dom.submodelsContainer.appendChild(card);
        });
    }

    function createToolPill(tool) {
        const wrapper = document.createElement("div");
        wrapper.className = `tool-pill ${tool.active ? "" : "is-inactive"}`;

        const label = document.createElement("span");
        label.textContent = tool.name;

        const button = document.createElement("button");
        button.className = `toggle-dot ${tool.active ? "is-active" : ""}`;
        button.type = "button";
        button.dataset.toolToggle = tool.name;
        button.setAttribute("aria-label", `${tool.name} durumunu değiştir`);

        wrapper.append(label, button);
        return wrapper;
    }

    async function handleToolToggle(event) {
        const button = event.target.closest("[data-tool-toggle]");
        if (!button) {
            return;
        }
        await apiRequest(`/tools/${encodeURIComponent(button.dataset.toolToggle)}/toggle`, {
            method: "POST",
        });
        toast("Tool durumu güncellendi.", "success");
        await fetchBootstrap({ silent: true });
    }

    function renderLogs(logs) {
        dom.liveActivity.innerHTML = "";

        if (!logs || logs.length === 0) {
            dom.liveActivity.innerHTML = '<div class="empty-copy">Log akışı henüz oluşmadı.</div>';
            return;
        }

        logs.slice().reverse().forEach((log) => {
            const entry = document.createElement("div");
            entry.className = `activity-entry ${log.type || "sistem"}`;

            const meta = document.createElement("div");
            meta.className = "activity-meta";
            meta.textContent = `[${log.time || "--:--"}] ${String(log.type || "log").toUpperCase()}`;

            const body = document.createElement("p");
            body.textContent = log.message || "";

            entry.append(meta, body);
            dom.liveActivity.appendChild(entry);
        });
    }

    function renderPendingActions(actions) {
        const items = actions || [];
        state.pendingActions = items;
        state.pendingActionId = items[0]?.id || null;
        dom.approvalCountBadge.textContent = `${items.length}`;
        dom.metricApprovals.textContent = `${items.length}`;

        if (items.length === 0) {
            dom.pendingActionsList.innerHTML = '<div class="empty-copy">Bekleyen aksiyon bulunmuyor.</div>';
            dom.approvalBadge.classList.add("hidden");
            dom.approvalModal.classList.add("hidden");
            return;
        }

        dom.approvalBadge.classList.remove("hidden");
        dom.approvalBadge.textContent = `${items.length} onay bekliyor`;
        dom.pendingActionsList.innerHTML = "";

        items.forEach((action) => {
            const row = document.createElement("div");
            row.className = "stack-item";

            const content = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = action.id;
            const desc = document.createElement("p");
            desc.textContent = action.description;
            content.append(title, desc);

            const button = document.createElement("button");
            button.className = "btn ghost compact";
            button.type = "button";
            button.dataset.openApproval = action.id;
            button.textContent = "İncele";

            row.append(content, button);
            dom.pendingActionsList.appendChild(row);
        });
    }

    function openApprovalModal(action) {
        state.pendingActionId = action.id;
        dom.approvalDesc.textContent = action.description;
        dom.approvalModal.classList.remove("hidden");
    }

    async function decideAction(decision) {
        if (!state.pendingActionId) {
            return;
        }

        await apiRequest(`/actions/${encodeURIComponent(state.pendingActionId)}/${decision}`, {
            method: "POST",
        });

        dom.approvalModal.classList.add("hidden");
        toast(`İşlem ${decision === "approve" ? "onaylandı" : "reddedildi"}.`, "success");
        await fetchBootstrap({ silent: true });
    }

    function renderStatsChart(metrics) {
        const values = metrics || [];
        const labels = values.map((item) => item.time || "-");
        const durations = values.map((item) => item.duration || 0);
        const names = values.map((item) => item.name || "task");

        if (!state.chart) {
            state.chart = new Chart(dom.statsChart, {
                type: "line",
                data: {
                    labels,
                    datasets: [{
                        label: "Araç / Ajan Süresi",
                        data: durations,
                        borderColor: "#19d3c5",
                        backgroundColor: "rgba(25, 211, 197, 0.12)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: {
                                color: "#f3efe4",
                                font: { family: "Space Grotesk" },
                            },
                        },
                        tooltip: {
                            callbacks: {
                                title(context) {
                                    return `${names[context[0].dataIndex] || "Görev"} • ${labels[context[0].dataIndex] || "-"}`;
                                },
                                label(context) {
                                    return `${context.parsed.y}s`;
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            ticks: { color: "rgba(243, 239, 228, 0.65)" },
                            grid: { color: "rgba(255, 255, 255, 0.05)" },
                        },
                        y: {
                            ticks: {
                                color: "rgba(243, 239, 228, 0.65)",
                                callback(value) {
                                    return `${value}s`;
                                },
                            },
                            grid: { color: "rgba(255, 255, 255, 0.05)" },
                        },
                    },
                },
            });
            return;
        }

        state.chart.data.labels = labels;
        state.chart.data.datasets[0].data = durations;
        state.chart.update();
    }

    async function switchTab(tabId) {
        state.activeTab = tabId;

        dom.navItems.forEach((item) => item.classList.toggle("active", item.dataset.tab === tabId));
        dom.tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tabId}`));

        const activeNav = dom.navItems.find((item) => item.dataset.tab === tabId);
        dom.currentTabTitle.textContent = activeNav?.dataset.title || "Panel";

        try {
            await refreshActiveView({ silent: true });
        } catch (error) {
            setConnectionState(`Sekme verisi yüklenemedi: ${error.message}`, "error");
            toast(`Sekme yüklenemedi: ${error.message}`, "error");
        }
    }

    async function switchMemTab(memId) {
        state.activeMemTab = memId;
        dom.memNavItems.forEach((item) => item.classList.toggle("active", item.dataset.mem === memId));
        dom.memPanes.forEach((pane) => pane.classList.remove("active"));

        if (memId === "persona") {
            document.getElementById("mem-content-persona").classList.add("active");
        } else if (memId === "json") {
            document.getElementById("mem-content-json").classList.add("active");
        } else {
            document.getElementById("mem-content-list").classList.add("active");
        }

        await loadMemoryTab({ silent: true });
    }

    async function loadMemoryTab() {
        if (state.activeMemTab === "persona") {
            const data = await apiRequest("/persona");
            dom.personaEditor.value = data.content || "";
            return;
        }

        const raw = await apiRequest("/memory/raw");

        if (state.activeMemTab === "json") {
            dom.jsonEditor.value = JSON.stringify(raw, null, 2);
            return;
        }

        renderMemoryCategory(state.activeMemTab, raw);
    }

    function renderMemoryCategory(category, rawData) {
        dom.memListTitle.textContent = category.charAt(0).toUpperCase() + category.slice(1);
        dom.memTableBody.innerHTML = "";
        const items = rawData[category] || (category === "tercihler" || category === "kisiler" ? {} : []);

        if (Array.isArray(items)) {
            if (items.length === 0) {
                renderEmptyMemoryRow();
                return;
            }

            items.forEach((item) => {
                dom.memTableBody.appendChild(createMemoryRow(category, item.anahtar, item.deger));
            });
            return;
        }

        const entries = Object.entries(items);
        if (entries.length === 0) {
            renderEmptyMemoryRow();
            return;
        }

        entries.forEach(([key, value]) => {
            const normalizedValue = typeof value === "object" && value !== null ? value.deger : value;
            dom.memTableBody.appendChild(createMemoryRow(category, key, normalizedValue));
        });
    }

    function createMemoryRow(category, key, value) {
        const tr = document.createElement("tr");
        const keyCell = document.createElement("td");
        keyCell.textContent = key;
        const valueCell = document.createElement("td");
        valueCell.textContent = value;
        const actionCell = document.createElement("td");
        const button = document.createElement("button");
        button.className = "btn ghost compact";
        button.type = "button";
        button.textContent = "Sil";
        button.addEventListener("click", async () => {
            await apiRequest("/memory/delete", {
                method: "POST",
                body: { category, key },
            });
            toast("Kayıt silindi.", "success");
            await loadMemoryTab({ silent: true });
        });
        actionCell.appendChild(button);
        tr.append(keyCell, valueCell, actionCell);
        return tr;
    }

    function renderEmptyMemoryRow() {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 3;
        td.className = "empty-copy";
        td.textContent = "Bu kategoride kayıt bulunmuyor.";
        tr.appendChild(td);
        dom.memTableBody.appendChild(tr);
    }

    async function savePersona() {
        await apiRequest("/persona", {
            method: "POST",
            body: { content: dom.personaEditor.value },
        });
        toast("Persona kaydedildi.", "success");
    }

    async function saveJsonMemory() {
        let parsed;
        try {
            parsed = JSON.parse(dom.jsonEditor.value);
        } catch (error) {
            toast("JSON biçimi geçersiz.", "error");
            return;
        }

        await apiRequest("/memory/raw", {
            method: "POST",
            body: parsed,
        });
        toast("Ham bellek kaydedildi.", "success");
    }

    async function addMemoryEntry() {
        const key = dom.newMemKey.value.trim();
        const value = dom.newMemVal.value.trim();

        if (!key || !value) {
            toast("Anahtar ve değer zorunlu.", "warning");
            return;
        }

        await apiRequest("/memory/write", {
            method: "POST",
            body: { category: state.activeMemTab, key, value },
        });

        dom.newMemKey.value = "";
        dom.newMemVal.value = "";
        toast("Bellek kaydı eklendi.", "success");
        await loadMemoryTab({ silent: true });
    }

    async function fetchWorkspaceTree({ silent = false } = {}) {
        const nodes = await apiRequest("/workspace/tree");
        renderTree(nodes);
        if (!silent) {
            toast("Workspace ağacı yenilendi.", "success");
        }
    }

    function renderTree(nodes) {
        dom.fileTree.innerHTML = "";

        if (!nodes || nodes.length === 0) {
            dom.fileTree.innerHTML = '<div class="empty-copy">Workspace boş görünüyor.</div>';
            return;
        }

        const fragment = document.createDocumentFragment();
        nodes.forEach((node) => fragment.appendChild(renderTreeNode(node, 0)));
        dom.fileTree.appendChild(fragment);
    }

    function renderTreeNode(node, depth) {
        const wrapper = document.createElement("div");
        wrapper.className = "tree-node-wrapper";

        const row = document.createElement("button");
        row.type = "button";
        row.className = `tree-node ${state.selectedFilePath === node.path ? "is-selected" : ""}`;
        row.style.setProperty("--depth", depth);
        row.dataset.treePath = node.path;
        row.dataset.treeType = node.type;
        row.dataset.treeName = node.name;

        const icon = document.createElement("span");
        icon.className = "tree-icon";
        if (node.type === "directory") {
            const expanded = depth === 0 || state.expandedDirs.has(node.path);
            row.dataset.expanded = expanded ? "true" : "false";
            icon.textContent = expanded ? "▾" : "▸";
        } else {
            icon.textContent = "•";
        }

        const label = document.createElement("span");
        label.className = "tree-label";
        label.textContent = node.name;

        row.append(icon, label);
        wrapper.appendChild(row);

        if (node.type === "directory") {
            const expanded = depth === 0 || state.expandedDirs.has(node.path);
            if (expanded) {
                const children = document.createElement("div");
                children.className = "tree-children";
                (node.children || []).forEach((child) => {
                    children.appendChild(renderTreeNode(child, depth + 1));
                });
                wrapper.appendChild(children);
            }
        }

        return wrapper;
    }

    async function loadFile(path, name) {
        const data = await apiRequest(`/workspace/read?path=${encodeURIComponent(path)}`);
        state.selectedFilePath = path;
        dom.currentFileName.textContent = name;
        dom.currentFilePath.textContent = path;
        dom.fileViewer.textContent = data.content || "";
        dom.btnRunCode.classList.toggle("hidden", !name.endsWith(".py"));
        await fetchWorkspaceTree({ silent: true });
    }

    function clearConsole() {
        dom.terminalOutput.innerHTML = '<span class="term-line prompt">&gt; Bekleniyor...</span>';
    }

    function addConsoleLine(text, type = "info") {
        const line = document.createElement("span");
        line.className = `term-line ${type}`;
        line.textContent = text;
        dom.terminalOutput.appendChild(line);
        dom.terminalOutput.scrollTop = dom.terminalOutput.scrollHeight;
    }

    async function runSelectedCode() {
        if (!state.selectedFilePath) {
            toast("Önce bir Python dosyası seçin.", "warning");
            return;
        }

        addConsoleLine(`> python ${state.selectedFilePath}`, "prompt");
        dom.btnRunCode.disabled = true;

        try {
            const data = await apiRequest("/workspace/execute", {
                method: "POST",
                body: { filename: state.selectedFilePath },
                timeout: 35000,
            });

            if (data.stdout) {
                addConsoleLine(data.stdout, "info");
            }
            if (data.stderr) {
                addConsoleLine(`STDERR: ${data.stderr}`, "error");
            }
            if (data.error) {
                addConsoleLine(data.error, "error");
            }
            addConsoleLine(`Process exited with code ${data.exit_code ?? "-"}`, "prompt");
        } catch (error) {
            addConsoleLine(error.message, "error");
            toast(`Kod çalıştırılamadı: ${error.message}`, "error");
        } finally {
            dom.btnRunCode.disabled = false;
        }
    }

    function switchSourceTab(srcId) {
        state.activeSrcTab = srcId;
        dom.srcTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.src === srcId));
        dom.srcPanes.forEach((pane) => pane.classList.toggle("active", pane.id === `src-content-${srcId}`));
    }

    function syncSelectedFile() {
        state.pendingUploadFile = dom.fileInput.files?.[0] || state.pendingUploadFile;
        const file = state.pendingUploadFile;
        dom.selectedFileName.textContent = file ? file.name : "Seçili dosya yok";
    }

    async function uploadSelectedFile() {
        const file = state.pendingUploadFile || dom.fileInput.files?.[0];
        if (!file) {
            toast("Önce bir dosya seçin.", "warning");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        await apiRequest("/workspace/targets/upload", {
            method: "POST",
            body: formData,
            timeout: 30000,
        });

        dom.fileInput.value = "";
        state.pendingUploadFile = null;
        syncSelectedFile();
        dom.sourceModal.classList.add("hidden");
        toast("Dosya target klasörüne yüklendi.", "success");
        await fetchWorkspaceTree({ silent: true });
    }

    async function addUrlTarget() {
        const name = dom.srcUrlName.value.trim();
        const content = dom.srcUrlVal.value.trim();
        if (!name || !content) {
            toast("URL kaynağı için ad ve içerik zorunlu.", "warning");
            return;
        }

        await apiRequest("/workspace/targets/add", {
            method: "POST",
            body: { type: "url", name, content },
        });

        dom.srcUrlName.value = "";
        dom.srcUrlVal.value = "";
        dom.sourceModal.classList.add("hidden");
        toast("URL kaynağı eklendi.", "success");
        await fetchWorkspaceTree({ silent: true });
    }

    async function addTextTarget() {
        const name = dom.srcTextName.value.trim();
        const content = dom.srcTextVal.value.trim();
        if (!name || !content) {
            toast("Metin kaynağı için ad ve içerik zorunlu.", "warning");
            return;
        }

        await apiRequest("/workspace/targets/add", {
            method: "POST",
            body: { type: "text", name, content },
        });

        dom.srcTextName.value = "";
        dom.srcTextVal.value = "";
        dom.sourceModal.classList.add("hidden");
        toast("Metin kaynağı eklendi.", "success");
        await fetchWorkspaceTree({ silent: true });
    }

    function renderSkills(skills) {
        dom.skillsList.innerHTML = "";

        if (!skills || skills.length === 0) {
            dom.skillsList.innerHTML = '<div class="empty-copy">Yüklü skill bulunamadı.</div>';
            return;
        }

        skills.forEach((skill) => {
            const item = document.createElement("div");
            item.className = "stack-item";

            const content = document.createElement("div");
            const name = document.createElement("strong");
            name.textContent = skill.name;
            const desc = document.createElement("p");
            desc.textContent = `${skill.agent || "genel"} • ${skill.description || "Açıklama yok"}`;
            content.append(name, desc);

            const button = document.createElement("button");
            button.className = `btn ${skill.enabled ? "primary" : "ghost"} compact`;
            button.type = "button";
            button.dataset.skillToggle = skill.name;
            button.textContent = skill.enabled ? "Aktif" : "Pasif";

            item.append(content, button);
            dom.skillsList.appendChild(item);
        });
    }

    async function toggleSkill(name) {
        await apiRequest(`/skills/${encodeURIComponent(name)}/toggle`, { method: "POST" });
        toast(`Skill durumu güncellendi: ${name}`, "success");
        await fetchBootstrap({ silent: true });
    }

    async function reloadSkills() {
        await apiRequest("/skills/reload", { method: "POST" });
        toast("Skill listesi yeniden yüklendi.", "success");
        await fetchBootstrap({ silent: true });
    }

    async function fetchHeartbeatConfig() {
        const [config, status, jobs] = await Promise.all([
            apiRequest("/heartbeat/config"),
            apiRequest("/heartbeat/status"),
            apiRequest("/heartbeat/jobs"),
        ]);

        state.heartbeat = {
            config,
            status,
            jobs: Array.isArray(jobs) ? jobs : [],
        };

        if (!state.heartbeatDirty) {
            dom.heartbeatEditor.value = config.content || "";
        }
        renderHeartbeat();
    }

    async function saveHeartbeatConfig() {
        await apiRequest("/heartbeat/config", {
            method: "POST",
            body: { content: dom.heartbeatEditor.value },
        });
        state.heartbeatDirty = false;
        await fetchHeartbeatConfig();
        toast("Heartbeat config kaydedildi.", "success");
    }

    async function reloadHeartbeatScheduler() {
        await apiRequest("/heartbeat/reload", { method: "POST" });
        await fetchHeartbeatConfig();
        toast("Heartbeat scheduler yenilendi.", "success");
    }

    function renderHeartbeat() {
        const config = state.heartbeat?.config || {};
        const status = state.heartbeat?.status || {};
        const jobs = Array.isArray(state.heartbeat?.jobs) ? state.heartbeat.jobs : [];
        const enabled = Boolean(config?.enabled);
        const interval = config?.interval_minutes ?? "-";
        const taskCount = config?.task_count ?? 0;
        const activeJobName = status?.active_job_name || status?.active_job_id || "Yok";
        const configValid = Boolean(config?.valid);

        dom.heartbeatEnabledState.textContent = enabled ? "Aktif" : "Kapalı";
        dom.heartbeatMeta.textContent = `${taskCount} görev • legacy ${interval} dk`;
        dom.heartbeatRunningState.textContent = status?.running
            ? `Çalışıyor • ${activeJobName}`
            : (status?.ready ? "Beklemede" : "Hazır değil");
        dom.heartbeatRunningMeta.textContent = status?.last_reload_at
            ? `Son yenileme: ${formatDateTime(status.last_reload_at)}`
            : "Scheduler henüz yüklenmedi";
        dom.heartbeatConfigState.textContent = configValid ? "Geçerli" : "Hatalı";
        dom.heartbeatConfigMeta.textContent = configValid
            ? `${status?.scheduled_job_count ?? 0} zamanlı job • ${jobs.length} toplam`
            : (config?.validation_error || "Config doğrulanamadı");

        dom.heartbeatEnable.classList.toggle("primary", enabled);
        dom.heartbeatEnable.classList.toggle("ghost", !enabled);
        dom.heartbeatDisable.classList.toggle("primary", !enabled);
        dom.heartbeatDisable.classList.toggle("ghost", enabled);

        dom.heartbeatJobList.innerHTML = "";
        if (jobs.length === 0) {
            dom.heartbeatJobList.innerHTML = '<div class="empty-copy">Tanımlı heartbeat görevi yok.</div>';
            return;
        }

        jobs.forEach((job) => {
            const item = document.createElement("div");
            item.className = `stack-item heartbeat-job-item status-${job.last_status || "idle"}`;

            const top = document.createElement("div");
            top.className = "heartbeat-job-top";

            const head = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = job.name || job.job_id;
            const meta = document.createElement("p");
            meta.textContent = `${job.job_id} • ${job.cron || "manual"}`;
            head.append(title, meta);

            const badge = document.createElement("span");
            badge.className = `queue-badge status-${job.last_status || "idle"}`;
            badge.textContent = resolveHeartbeatJobStatusLabel(job);
            top.append(head, badge);

            const info = document.createElement("p");
            info.className = "heartbeat-job-copy";
            info.textContent = [
                `Next: ${formatDateTime(job.next_run_at)}`,
                `Last: ${formatDateTime(job.last_run_at)}`,
                `Run count: ${job.run_count ?? 0}`,
            ].join(" • ");

            const error = document.createElement("p");
            error.className = "heartbeat-job-error";
            error.textContent = job.last_error || "Son hata yok";

            const actions = document.createElement("div");
            actions.className = "toolbar-actions heartbeat-job-actions";

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "btn ghost";
            toggle.dataset.heartbeatAction = job.paused ? "resume" : "pause";
            toggle.dataset.heartbeatJobId = job.job_id;
            toggle.textContent = job.paused ? "Resume" : "Pause";
            toggle.disabled = !job.enabled && !job.paused;

            const run = document.createElement("button");
            run.type = "button";
            run.className = "btn ghost";
            run.dataset.heartbeatAction = "run";
            run.dataset.heartbeatJobId = job.job_id;
            run.textContent = "Şimdi Çalıştır";
            run.disabled = Boolean(job.running);

            actions.append(toggle, run);
            item.append(top, info, error, actions);
            dom.heartbeatJobList.appendChild(item);
        });
    }

    async function toggleHeartbeat(enabled) {
        dom.heartbeatEnable.disabled = true;
        dom.heartbeatDisable.disabled = true;
        dom.heartbeatReload.disabled = true;

        try {
            await apiRequest("/heartbeat/toggle", {
                method: "POST",
                body: { enabled },
            });
            await fetchHeartbeatConfig();
            toast(`Heartbeat ${enabled ? "açıldı" : "kapatıldı"}.`, "success");
        } catch (error) {
            toast(`Heartbeat durumu değiştirilemedi: ${error.message}`, "error");
        } finally {
            dom.heartbeatEnable.disabled = false;
            dom.heartbeatDisable.disabled = false;
            dom.heartbeatReload.disabled = false;
        }
    }

    async function handleHeartbeatJobAction(jobId, action) {
        if (!jobId || !action) {
            return;
        }

        const endpointMap = {
            pause: `/heartbeat/jobs/${encodeURIComponent(jobId)}/pause`,
            resume: `/heartbeat/jobs/${encodeURIComponent(jobId)}/resume`,
            run: `/heartbeat/jobs/${encodeURIComponent(jobId)}/run`,
        };

        const endpoint = endpointMap[action];
        if (!endpoint) {
            return;
        }

        try {
            await apiRequest(endpoint, { method: "POST", timeout: 20000 });
            await fetchHeartbeatConfig();
            if (action === "run") {
                toast(`Job tetiklendi: ${jobId}`, "success");
            } else {
                toast(`Job güncellendi: ${jobId}`, "success");
            }
        } catch (error) {
            toast(`Heartbeat job işlemi başarısız: ${error.message}`, "error");
        }
    }

    async function fetchSocialSnapshot({ silent = false } = {}) {
        const [browser, queue] = await Promise.all([
            apiRequest("/social/browser/status"),
            apiRequest("/social/x/queue"),
        ]);
        state.social.browser = browser || null;
        state.social.queue = queue || { items: [] };
        renderSocial({ browser, queue });
        if (!silent) {
            setConnectionState("Sosyal inbox senkronize edildi.", "success");
        }
    }

    function renderSocial(snapshot) {
        const browser = snapshot?.browser || state.social.browser || { ready: false, error: "Tarayıcı bağlı değil." };
        const queue = snapshot?.queue || state.social.queue || { items: [] };
        const items = Array.isArray(queue.items) ? queue.items : [];
        const pending = items.filter((item) => item.status !== "sent" && item.status !== "skipped").length;

        state.social.browser = browser;
        state.social.queue = queue;

        dom.socialBrowserState.textContent = browser.ready
            ? `Hazır • ${browser.title || "Aktif sekme"}`
            : "Bağlı değil";
        dom.socialBrowserUrl.textContent = browser.ready
            ? (browser.url || "Tarayıcı sekmesi algılandı")
            : (browser.error || "Tarayıcı oturumu başlatılmalı");
        dom.socialBrowserMode.textContent = browser.ready
            ? `Mod: ${browser.visibility_label || (browser.headless ? "Headless" : "Görünür")}`
            : `Son tercih: ${browser.visibility_label || (browser.preferred_headless ? "Headless" : "Görünür")}`;
        dom.socialQueueCount.textContent = `${pending} aktif • ${items.length} toplam`;
        dom.socialQueueUpdated.textContent = queue.updated_at
            ? `Son güncelleme: ${formatDateTime(queue.updated_at)}`
            : "Henüz tarama yapılmadı";
        syncSocialBrowserButtons(browser);

        const selectedStillExists = items.some((item) => item.queue_id === state.social.selectedQueueId);
        if (!selectedStillExists) {
            const nextItem = items.find((item) => !["sent", "skipped"].includes(item.status)) || items[0] || null;
            state.social.selectedQueueId = nextItem?.queue_id || null;
            state.social.editorDirty = false;
        }

        dom.socialQueueList.innerHTML = "";
        if (items.length === 0) {
            dom.socialQueueList.innerHTML = '<div class="empty-copy">Tarama sonrası yorumlar burada görünecek.</div>';
        } else {
            items.forEach((item) => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = `queue-item ${item.queue_id === state.social.selectedQueueId ? "is-active" : ""}`;
                button.dataset.socialQueueId = item.queue_id;

                const top = document.createElement("div");
                top.className = "queue-item-top";

                const author = document.createElement("strong");
                author.textContent = item.author_handle ? `@${item.author_handle}` : (item.author_name || "Bilinmeyen kullanıcı");

                const badge = document.createElement("span");
                badge.className = `queue-badge status-${item.status || "new"}`;
                badge.textContent = resolveQueueStatusLabel(item.status);

                top.append(author, badge);

                const text = document.createElement("p");
                text.className = "queue-item-text";
                text.textContent = item.text || "Yorum metni okunamadı.";

                const meta = document.createElement("div");
                meta.className = "queue-item-meta";
                meta.textContent = [item.author_name, item.time_label].filter(Boolean).join(" • ") || "Yeni yorum";

                button.append(top, text, meta);
                dom.socialQueueList.appendChild(button);
            });
        }

        const selected = getSelectedSocialItem();
        if (!selected) {
            dom.socialSelectedMeta.textContent = "Henüz seçim yok";
            dom.socialOpenLink.classList.add("hidden");
            dom.socialEditorTitle.textContent = "Yorum seçin";
            dom.socialCommentPreview.textContent = "Tarayıcı açıkken ilgili X sayfasını tarayarak yorumları sıraya alabilirsiniz.";
            if (!state.social.editorDirty) {
                dom.socialReplyEditor.value = "";
            }
            dom.socialReplyEditor.dataset.queueId = "";
            updateSocialComposerActions(false);
            return;
        }

        dom.socialSelectedMeta.textContent = `${selected.author_handle ? `@${selected.author_handle}` : (selected.author_name || "Yorum")} • ${resolveQueueStatusLabel(selected.status)}`;
        if (selected.tweet_url) {
            dom.socialOpenLink.href = selected.tweet_url;
            dom.socialOpenLink.classList.remove("hidden");
        } else {
            dom.socialOpenLink.classList.add("hidden");
        }

        dom.socialEditorTitle.textContent = selected.author_name || (selected.author_handle ? `@${selected.author_handle}` : "Seçili yorum");
        dom.socialCommentPreview.textContent = selected.text || "Yorum metni bulunamadı.";

        if (!state.social.editorDirty || dom.socialReplyEditor.dataset.queueId !== selected.queue_id) {
            dom.socialReplyEditor.value = selected.draft_reply || "";
            dom.socialReplyEditor.dataset.queueId = selected.queue_id;
            state.social.editorDirty = false;
        }

        updateSocialComposerActions(true);
    }

    function getSelectedSocialItem() {
        const items = state.social.queue?.items || [];
        return items.find((item) => item.queue_id === state.social.selectedQueueId) || null;
    }

    function syncSocialBrowserButtons(browser) {
        const effectiveHeadless = Boolean(browser?.headless ?? browser?.preferred_headless);

        dom.launchBrowserVisible.classList.toggle("primary", !effectiveHeadless);
        dom.launchBrowserVisible.classList.toggle("ghost", effectiveHeadless);
        dom.launchBrowserHeadless.classList.toggle("primary", effectiveHeadless);
        dom.launchBrowserHeadless.classList.toggle("ghost", !effectiveHeadless);
    }

    function selectSocialItem(queueId) {
        if (!queueId || queueId === state.social.selectedQueueId) {
            return;
        }
        state.social.selectedQueueId = queueId;
        state.social.editorDirty = false;
        renderSocial({ browser: state.social.browser, queue: state.social.queue });
    }

    function updateSocialComposerActions(enabled) {
        [
            dom.socialGenerateDraft,
            dom.socialSaveDraft,
            dom.socialSkipItem,
            dom.socialSendReply,
            dom.socialReplyEditor,
        ].forEach((element) => {
            element.disabled = !enabled;
        });
    }

    async function scanSocialPage() {
        dom.scanSocial.disabled = true;
        try {
            const payload = await apiRequest("/social/x/scan", {
                method: "POST",
                body: { limit: 25 },
                timeout: 30000,
            });
            state.social.browser = payload.browser || state.social.browser;
            state.social.queue = payload.queue || state.social.queue;
            renderSocial({ browser: state.social.browser, queue: state.social.queue });
            toast(`${payload.new_items || 0} yeni yorum bulundu.`, "success");
        } finally {
            dom.scanSocial.disabled = false;
        }
    }

    async function launchSocialBrowser(headless) {
        const modeLabel = "görünür";
        dom.launchBrowserVisible.disabled = true;
        if (dom.launchBrowserHeadless) {
            dom.launchBrowserHeadless.disabled = true;
        }

        try {
            const payload = await apiRequest("/social/browser/launch", {
                method: "POST",
                body: {
                    headless: false,
                    restart_if_needed: true,
                },
                timeout: 35000,
            });
            state.social.browser = payload.browser || state.social.browser;
            renderSocial({ browser: state.social.browser, queue: state.social.queue });
            toast(payload.message || `Tarayıcı ${modeLabel} modda hazır.`, "success");
        } catch (error) {
            toast(`Tarayıcı ${modeLabel} modda başlatılamadı: ${error.message}`, "error");
        } finally {
            dom.launchBrowserVisible.disabled = false;
            if (dom.launchBrowserHeadless) {
                dom.launchBrowserHeadless.disabled = false;
            }
        }
    }

    async function generateSocialDraft() {
        const selected = getSelectedSocialItem();
        if (!selected) {
            toast("Önce kuyruktan bir yorum seçin.", "warning");
            return;
        }

        dom.socialGenerateDraft.disabled = true;
        try {
            const payload = await apiRequest(`/social/x/queue/${encodeURIComponent(selected.queue_id)}/draft`, {
                method: "POST",
                body: { tone: "samimi, kısa ve doğal" },
                timeout: 35000,
            });
            dom.socialReplyEditor.value = payload.draft || "";
            state.social.editorDirty = false;
            await fetchSocialSnapshot({ silent: true });
            toast("Taslak üretildi.", "success");
        } finally {
            dom.socialGenerateDraft.disabled = false;
        }
    }

    async function saveSocialDraft() {
        const selected = getSelectedSocialItem();
        if (!selected) {
            toast("Önce kuyruktan bir yorum seçin.", "warning");
            return;
        }

        await apiRequest(`/social/x/queue/${encodeURIComponent(selected.queue_id)}/update`, {
            method: "POST",
            body: { text: dom.socialReplyEditor.value },
        });
        state.social.editorDirty = false;
        await fetchSocialSnapshot({ silent: true });
        toast("Taslak kaydedildi.", "success");
    }

    async function skipSocialItem() {
        const selected = getSelectedSocialItem();
        if (!selected) {
            toast("Önce kuyruktan bir yorum seçin.", "warning");
            return;
        }

        await apiRequest(`/social/x/queue/${encodeURIComponent(selected.queue_id)}/status`, {
            method: "POST",
            body: { status: "skipped", note: "Panelden gecildi" },
        });
        state.social.editorDirty = false;
        await fetchSocialSnapshot({ silent: true });
        toast("Yorum kuyruktan pas geçildi.", "success");
    }

    async function sendSocialReply() {
        const selected = getSelectedSocialItem();
        if (!selected) {
            toast("Önce kuyruktan bir yorum seçin.", "warning");
            return;
        }

        const text = dom.socialReplyEditor.value.trim();
        if (!text) {
            toast("Gönderilecek cevap boş olamaz.", "warning");
            return;
        }

        dom.socialSendReply.disabled = true;
        try {
            await apiRequest(`/social/x/queue/${encodeURIComponent(selected.queue_id)}/send`, {
                method: "POST",
                body: { text },
                timeout: 35000,
            });
            state.social.editorDirty = false;
            await fetchSocialSnapshot({ silent: true });
            toast("Yorum cevabı tarayıcı üzerinden gönderildi.", "success");
        } finally {
            dom.socialSendReply.disabled = false;
        }
    }

    function resolveQueueStatusLabel(status) {
        const labels = {
            new: "Yeni",
            drafted: "Taslak",
            approved: "Onaylı",
            pending_verify: "Dogrulaniyor",
            sent: "Gönderildi",
            skipped: "Geçildi",
            error: "Hata",
        };
        return labels[status] || "Yeni";
    }

    function resolveHeartbeatJobStatusLabel(job) {
        if (!job) {
            return "Beklemede";
        }
        if (!job.enabled) {
            return "Disabled";
        }
        if (job.running) {
            return "Çalışıyor";
        }
        if (job.paused) {
            return "Paused";
        }

        const labels = {
            idle: "Beklemede",
            success: "Başarılı",
            skipped: "Atlandı",
            error: "Hata",
            disabled: "Disabled",
            paused: "Paused",
            running: "Çalışıyor",
        };
        return labels[job.last_status] || "Beklemede";
    }

    function formatDateTime(value) {
        if (!value) {
            return "-";
        }
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }
        return parsed.toLocaleString("tr-TR");
    }

    function setConnectionState(message, tone = "neutral") {
        dom.connectionState.textContent = message;
        dom.connectionState.dataset.tone = tone;
    }

    function updateStatusChip(element, text, isOnline) {
        element.textContent = text;
        element.classList.toggle("online", isOnline);
        element.classList.toggle("offline", !isOnline);
    }

    function markSync() {
        state.lastSyncAt = new Date();
        dom.lastSyncLabel.textContent = `Son senkron: ${state.lastSyncAt.toLocaleTimeString("tr-TR")}`;
    }

    function formatUptime(totalSeconds) {
        const seconds = Number(totalSeconds || 0);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}s ${minutes}dk`;
        }
        return `${minutes}dk`;
    }

    function resolveAgentIcon(name) {
        if (name.includes("browser")) {
            return "🌐";
        }
        if (name.includes("vlm")) {
            return "📸";
        }
        if (name.includes("sistem")) {
            return "🛠";
        }
        if (name.includes("arastirma")) {
            return "🔎";
        }
        return "🤖";
    }

    function toast(message, tone = "info") {
        const item = document.createElement("div");
        item.className = `toast ${tone}`;
        item.textContent = message;
        dom.toastRegion.appendChild(item);

        window.setTimeout(() => {
            item.classList.add("is-leaving");
            window.setTimeout(() => item.remove(), 300);
        }, 2800);
    }
});
