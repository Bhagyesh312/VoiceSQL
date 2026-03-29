/**
 * app.js — VoiceSQL main application
 */

// ── State ──────────────────────────────────────────────────
const state = {
  dbPath:       null,
  schema:       [],
  lastCols:     [],
  lastRows:     [],
  chartType:    "bar",
  chartVisible: false,
  queryHistory: [],
  page:         1,
  pageSize:     50,
};

// ── DOM shortcuts ──────────────────────────────────────────
const $  = id => document.getElementById(id);
const el = {
  // Sidebar
  dropZone:       $("drop-zone"),
  browseBtn:      $("browse-btn"),
  fileInput:      $("file-input"),
  uploadProgress: $("upload-progress"),
  progressBar:    $("progress-bar"),
  progressName:   $("progress-name"),
  progressPct:    $("progress-pct"),
  fileChip:       $("file-chip"),
  fileChipName:   $("file-chip-name"),
  fileChipRemove: $("file-chip-remove"),
  schemaCard:     $("schema-card"),
  schemaBadge:    $("schema-badge"),
  schemaBody:     $("schema-body"),
  suggestCard:    $("suggest-card"),
  suggestList:    $("suggest-list"),
  // Status
  statusDot:      $("status-dot"),
  statusLabel:    $("status-label"),
  // Theme
  themeToggle:    $("theme-toggle"),
  themeIconDark:  document.querySelector(".theme-icon-dark"),
  themeIconLight: document.querySelector(".theme-icon-light"),
  // Sidebar mobile
  sidebarToggle:  $("sidebar-toggle"),
  sidebarOverlay: $("sidebar-overlay"),
  sidebar:        $("sidebar"),
  welcome:        $("welcome"),
  queryPanel:     $("query-panel"),
  queryInput:     $("query-input"),
  btnMic:         $("btn-mic"),
  micDefault:     document.querySelector(".mic-default"),
  micListening:   document.querySelector(".mic-listening"),
  btnRun:         $("btn-run"),
  listeningStrip: $("listening-strip"),
  lsCancel:       $("ls-cancel"),
  sqlStrip:       $("sql-strip"),
  sqlStripCode:   $("sql-strip-code"),
  sqlStripSource: $("sql-strip-source"),
  sqlCopyBtn:     $("sql-copy-btn"),
  loaderPanel:    $("loader-panel"),
  resultsPanel:   $("results-panel"),
  resultsCountBadge: $("results-count-badge"),
  btnChart:       $("btn-chart"),
  btnExport:      $("btn-export"),
  chartPanel:     $("chart-panel"),
  chartTypeSelector: $("chart-type-selector"),
  thead:          $("thead"),
  tbody:          $("tbody"),
  errorPanel:     $("error-panel"),
  errorTitle:     $("error-title"),
  errorDesc:      $("error-desc"),
  errorChips:     $("error-chips"),
  emptyPanel:     $("empty-panel"),
  toastContainer: $("toast-container"),
  pagination:     $("pagination"),
  btnPrev:        $("btn-prev"),
  btnNext:        $("btn-next"),
  pageInfo:       $("page-info"),
};

// ── Helpers ────────────────────────────────────────────────
const show = (...els) => els.forEach(e => e?.classList.remove("hidden"));
const hide = (...els) => els.forEach(e => e?.classList.add("hidden"));

// ── Theme Toggle ───────────────────────────────────────────
const savedTheme = localStorage.getItem("voicesql-theme");
if (savedTheme === "light") applyTheme("light");

el.themeToggle.addEventListener("click", () => {
  const isLight = document.documentElement.classList.contains("light");
  applyTheme(isLight ? "dark" : "light");
});

function applyTheme(mode) {
  if (mode === "light") {
    document.documentElement.classList.add("light");
    hide(el.themeIconDark);
    show(el.themeIconLight);
  } else {
    document.documentElement.classList.remove("light");
    show(el.themeIconDark);
    hide(el.themeIconLight);
  }
  localStorage.setItem("voicesql-theme", mode);
}

// ── Mobile Sidebar ─────────────────────────────────────────
el.sidebarToggle.addEventListener("click", () => toggleSidebar());
el.sidebarOverlay.addEventListener("click", () => closeSidebar());

// Hero upload button (mobile) — opens sidebar
const heroUploadBtn = $("hero-upload-btn");
if (heroUploadBtn) heroUploadBtn.addEventListener("click", () => openSidebar());

// ── Mobile Info Panels ─────────────────────────────────────
const mob = {
  info:          $("mobile-info"),
  fileName:      $("mobile-file-name"),
  fileRemove:    $("mobile-file-remove"),
  schemaBadge:   $("mobile-schema-badge"),
  schemaBody:    $("mobile-schema-body"),
  schemaToggle:  $("mobile-schema-toggle"),
  suggestBody:   $("mobile-suggest-body"),
  suggestToggle: $("mobile-suggest-toggle"),
};

// Accordion toggles
mob.schemaToggle.addEventListener("click", () => toggleMobileSection(mob.schemaToggle, mob.schemaBody));
mob.suggestToggle.addEventListener("click", () => toggleMobileSection(mob.suggestToggle, mob.suggestBody));

function toggleMobileSection(header, body) {
  const isOpen = !body.classList.contains("hidden");
  if (isOpen) { body.classList.add("hidden"); header.classList.remove("open"); }
  else        { body.classList.remove("hidden"); header.classList.add("open"); }
}

function renderMobileInfo(tables, suggestions, fileName) {
  // Only relevant on mobile
  if (window.innerWidth > 860) return;

  // File row
  mob.fileName.textContent = fileName;
  mob.fileRemove.onclick = resetUpload;

  // Schema
  mob.schemaBadge.textContent = `${tables.length} table${tables.length !== 1 ? "s" : ""}`;
  const schemaDiv = document.createElement("div");
  schemaDiv.className = "schema-body";
  tables.forEach(t => {
    const div = document.createElement("div");
    div.className = "schema-table";
    div.innerHTML = `
      <div class="schema-table-head">
        <span class="schema-table-name">${t.name}</span>
        <span class="schema-row-ct">${t.row_count.toLocaleString()} rows</span>
      </div>
      <div class="schema-cols">
        ${t.columns.map(c => `
          <div class="schema-col">
            <span class="schema-col-name">${c.pk ? "🔑 " : ""}${c.name}</span>
            <span class="schema-col-type">${c.type}</span>
          </div>`).join("")}
      </div>`;
    schemaDiv.appendChild(div);
  });
  mob.schemaBody.innerHTML = "";
  mob.schemaBody.appendChild(schemaDiv);
  // Auto-open schema
  mob.schemaBody.classList.remove("hidden");
  mob.schemaToggle.classList.add("open");

  // Suggestions
  const suggestDiv = document.createElement("div");
  suggestDiv.className = "suggest-list";
  suggestions.forEach(s => {
    const btn = document.createElement("button");
    btn.className = "suggest-chip";
    btn.textContent = s;
    btn.addEventListener("click", () => { el.queryInput.value = s; el.queryInput.focus(); runQuery(); });
    suggestDiv.appendChild(btn);
  });
  mob.suggestBody.innerHTML = "";
  mob.suggestBody.appendChild(suggestDiv);
  // Auto-open suggestions
  mob.suggestBody.classList.remove("hidden");
  mob.suggestToggle.classList.add("open");

  mob.info.style.display = "flex";
}
function toggleSidebar() {
  const isOpen = el.sidebar.classList.contains("open");
  isOpen ? closeSidebar() : openSidebar();
}
function openSidebar() {
  el.sidebar.classList.add("open");
  el.sidebarOverlay.classList.add("visible");
  // iOS-safe scroll lock
  document.body.style.overflow = "hidden";
  document.body.style.position = "fixed";
  document.body.style.width = "100%";
}
function closeSidebar() {
  el.sidebar.classList.remove("open");
  el.sidebarOverlay.classList.remove("visible");
  document.body.style.overflow = "";
  document.body.style.position = "";
  document.body.style.width = "";
}

// Swipe left to close sidebar on mobile
let _touchStartX = 0;
el.sidebar.addEventListener("touchstart", e => { _touchStartX = e.touches[0].clientX; }, { passive: true });
el.sidebar.addEventListener("touchend", e => {
  if (_touchStartX - e.changedTouches[0].clientX > 60) closeSidebar();
}, { passive: true });

// ── Health Check ───────────────────────────────────────────
(async () => {
  try {
    await Api.health();
    el.statusDot.classList.add("online");
    el.statusLabel.textContent = "Connected";
  } catch {
    el.statusLabel.textContent = "Offline";
  }
})();

// ── Upload ─────────────────────────────────────────────────
el.browseBtn.addEventListener("click", e => { e.stopPropagation(); el.fileInput.click(); });
el.dropZone.addEventListener("click",    () => el.fileInput.click());
el.fileInput.addEventListener("change",  e => { if (e.target.files[0]) handleUpload(e.target.files[0]); });

el.dropZone.addEventListener("dragover",  e => { e.preventDefault(); el.dropZone.classList.add("dragover"); });
el.dropZone.addEventListener("dragleave", () => el.dropZone.classList.remove("dragover"));
el.dropZone.addEventListener("drop", e => {
  e.preventDefault(); el.dropZone.classList.remove("dragover");
  if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
});

el.fileChipRemove.addEventListener("click", resetUpload);

async function handleUpload(file) {
  el.progressName.textContent = file.name;
  show(el.uploadProgress);
  hide(el.fileChip);
  animateProgress(0, 35, 400);

  try {
    const data = await Api.upload(file);
    animateProgress(35, 100, 350);

    await delay(400);
    hide(el.uploadProgress);
    el.fileChipName.textContent = file.name;
    show(el.fileChip);

    state.dbPath = data.db_path;
    state.schema = data.tables;

    renderSchema(data.tables);
    show(el.schemaCard);

    await loadSuggestions(data.tables);

    hide(el.welcome);
    show(el.queryPanel);
    closeSidebar();

    // Populate mobile info panels
    const suggestionList = Array.from(el.suggestList.querySelectorAll(".suggest-chip")).map(b => b.textContent);
    renderMobileInfo(data.tables, suggestionList, file.name);

    toast(`Loaded ${data.tables.length} table(s) · ${data.tables.reduce((s,t)=>s+t.row_count,0).toLocaleString()} rows`, "success");
    el.queryInput.focus();  } catch (err) {
    hide(el.uploadProgress);
    toast(err.message || "Upload failed", "error");
  }
}

function resetUpload() {
  state.dbPath = null; state.schema = [];
  hide(el.fileChip, el.schemaCard, el.suggestCard, el.queryPanel,
       el.resultsPanel, el.errorPanel, el.emptyPanel, el.sqlStrip, el.loaderPanel);
  mob.info.style.display = "none";
  show(el.welcome);
  el.fileInput.value = "";
  el.progressBar.style.width = "0%";
  closeSidebar();
}

function animateProgress(from, to, duration) {
  const start = performance.now();
  const tick  = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const v = from + (to - from) * easeOut(t);
    el.progressBar.style.width = v + "%";
    el.progressPct.textContent = Math.round(v) + "%";
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

const easeOut = t => 1 - Math.pow(1 - t, 3);
const delay   = ms => new Promise(r => setTimeout(r, ms));

// ── Schema Render ──────────────────────────────────────────
function renderSchema(tables) {
  el.schemaBody.innerHTML = "";
  el.schemaBadge.textContent = `${tables.length} table${tables.length !== 1 ? "s" : ""}`;

  tables.forEach(t => {
    const div = document.createElement("div");
    div.className = "schema-table";
    div.innerHTML = `
      <div class="schema-table-head">
        <span class="schema-table-name">${t.name}</span>
        <span class="schema-row-ct">${t.row_count.toLocaleString()} rows</span>
      </div>
      <div class="schema-cols">
        ${t.columns.map(c => `
          <div class="schema-col">
            <span class="schema-col-name">${c.pk ? "🔑 " : ""}${c.name}</span>
            <span class="schema-col-type">${c.type}</span>
          </div>
        `).join("")}
      </div>`;
    el.schemaBody.appendChild(div);
  });
}

// ── Suggestions ────────────────────────────────────────────
async function loadSuggestions(schema) {
  try {
    const list = await Api.suggestions(schema);
    el.suggestList.innerHTML = "";
    list.forEach(s => {
      const btn = document.createElement("button");
      btn.className = "suggest-chip";
      btn.textContent = s;
      btn.addEventListener("click", () => {
        el.queryInput.value = s;
        el.queryInput.focus();
        runQuery();
      });
      el.suggestList.appendChild(btn);
    });
    show(el.suggestCard);
  } catch {}
}

// ── Query ──────────────────────────────────────────────────
el.btnRun.addEventListener("click", runQuery);
el.queryInput.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) runQuery(); });

async function runQuery() {
  const q = el.queryInput.value.trim();
  if (!q)             { toast("Type a question first", "info"); return; }
  if (!state.dbPath)  { toast("Upload a dataset first", "info"); return; }

  hide(el.resultsPanel, el.errorPanel, el.emptyPanel);
  show(el.loaderPanel);
  el.btnRun.disabled = true;

  try {
    const data = await Api.query(q, state.dbPath, state.schema);

    // Show SQL strip
    el.sqlStripCode.textContent  = data.sql;
    el.sqlStripSource.textContent = data.source === "groq" ? "Groq AI" : data.source === "gemini" ? "Gemini AI" : "Rule-Based";
    show(el.sqlStrip);

    hide(el.loaderPanel);

    if (!data.rows || data.rows.length === 0) {
      show(el.emptyPanel);
    } else {
      state.lastCols  = data.columns;
      state.lastRows  = data.rows;
      state.chartType = data.chart_suggestion || "bar";
      state.page      = 1;

      el.resultsCountBadge.textContent = `${data.row_count.toLocaleString()} row${data.row_count !== 1 ? "s" : ""}`;
      renderPage();

      if (data.chart_suggestion) {
        ChartRenderer.render("result-chart", state.chartType, data.columns, data.rows);
        show(el.chartPanel, el.chartTypeSelector);
        el.btnChart.classList.add("active");
        state.chartVisible = true;
        // Sync chart type buttons
        syncChartTypeBtns(state.chartType);
      } else {
        hide(el.chartPanel, el.chartTypeSelector);
        ChartRenderer.destroy();
        state.chartVisible = false;
        el.btnChart.classList.remove("active");
      }
      show(el.resultsPanel);
      // Scroll results into view on mobile
      if (window.innerWidth <= 860) {
        setTimeout(() => el.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      }
    }

    state.queryHistory.unshift({ q, sql: data.sql, rows: data.row_count });

  } catch (err) {
    hide(el.loaderPanel);
    const friendly = friendlyError(err.message || "");
    el.errorTitle.textContent = friendly.title;
    el.errorDesc.textContent  = friendly.desc;

    const suggestions = err.data?.suggestions || [];
    el.errorChips.innerHTML = suggestions.map(s =>
      `<button class="error-chip" onclick="useQuery(${JSON.stringify(s)})">${s}</button>`
    ).join("");
    show(el.errorPanel);
  } finally {
    el.btnRun.disabled = false;
  }
}

window.useQuery = q => { el.queryInput.value = q; runQuery(); };

// ── Table + Pagination ─────────────────────────────────────
function renderPage() {
  const { lastCols, lastRows, page, pageSize } = state;
  const totalPages = Math.ceil(lastRows.length / pageSize);
  const start = (page - 1) * pageSize;
  const pageRows = lastRows.slice(start, start + pageSize);

  renderTable(lastCols, pageRows, start);

  if (totalPages > 1) {
    el.pageInfo.textContent = `Page ${page} of ${totalPages}`;
    el.btnPrev.disabled = page === 1;
    el.btnNext.disabled = page === totalPages;
    show(el.pagination);
  } else {
    hide(el.pagination);
  }
}

function renderTable(columns, rows, offset = 0) {
  el.thead.innerHTML = `<tr>
    <th class="row-num">#</th>
    ${columns.map(c => `<th>${c}</th>`).join("")}
  </tr>`;

  el.tbody.innerHTML = rows.map((row, i) =>
    `<tr>
      <td class="row-num">${offset + i + 1}</td>
      ${row.map(v => {
        if (v === null) return `<td class="null-val">NULL</td>`;
        const isNum = typeof v === "number";
        return `<td class="${isNum ? "num" : ""}">${isNum ? v.toLocaleString() : v}</td>`;
      }).join("")}
    </tr>`
  ).join("");
}

el.btnPrev.addEventListener("click", () => {
  if (state.page > 1) { state.page--; renderPage(); el.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" }); }
});
el.btnNext.addEventListener("click", () => {
  const totalPages = Math.ceil(state.lastRows.length / state.pageSize);
  if (state.page < totalPages) { state.page++; renderPage(); el.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" }); }
});

// ── Chart toggle ───────────────────────────────────────────
el.btnChart.addEventListener("click", () => {
  state.chartVisible = !state.chartVisible;
  if (state.chartVisible) {
    show(el.chartPanel, el.chartTypeSelector);
    ChartRenderer.render("result-chart", state.chartType, state.lastCols, state.lastRows);
    el.btnChart.classList.add("active");
  } else {
    hide(el.chartPanel, el.chartTypeSelector);
    el.btnChart.classList.remove("active");
  }
});

// ── Chart type selector ────────────────────────────────────
el.chartTypeSelector.addEventListener("click", e => {
  const btn = e.target.closest(".chart-type-btn");
  if (!btn) return;
  const type = btn.dataset.type;
  state.chartType = type;
  syncChartTypeBtns(type);
  ChartRenderer.render("result-chart", type, state.lastCols, state.lastRows);
});

function syncChartTypeBtns(type) {
  el.chartTypeSelector.querySelectorAll(".chart-type-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.type === type);
  });
}

// ── Export CSV ─────────────────────────────────────────────
el.btnExport.addEventListener("click", () => {
  if (!state.lastRows.length) return;
  const csv  = [state.lastCols.join(","), ...state.lastRows.map(r =>
    r.map(v => typeof v === "string" && v.includes(",") ? `"${v}"` : v).join(",")
  )].join("\n");
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "query_results.csv";
  a.click();
  URL.revokeObjectURL(a.href);
  toast("Exported as CSV", "success");
});

// ── Copy SQL ───────────────────────────────────────────────
el.sqlCopyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(el.sqlStripCode.textContent)
    .then(() => toast("SQL copied!", "success"));
});

// ── Voice ──────────────────────────────────────────────────
if (!Voice.isSupported) {
  el.btnMic.title   = "Voice not supported in this browser";
  el.btnMic.opacity = "0.4";
  el.btnMic.disabled = true;
}

el.btnMic.addEventListener("click", toggleVoice);
el.lsCancel.addEventListener("click", () => { Voice.stop(); setListening(false); });

function toggleVoice() {
  if (Voice.active) { Voice.stop(); setListening(false); return; }

  const started = Voice.start(
    (transcript, isFinal) => {
      el.queryInput.value = transcript;
      if (isFinal) { setListening(false); runQuery(); }
    },
    (err) => {
      setListening(false);
      if (err && err !== "no-speech") toast("Mic error: " + err, "error");
    }
  );
  if (started) setListening(true);
  else toast("Microphone not available", "error");
}

function setListening(on) {
  el.btnMic.classList.toggle("listening", on);
  if (on) { hide(el.micDefault); show(el.micListening); }
  else    { show(el.micDefault); hide(el.micListening); }
  el.listeningStrip.classList.toggle("hidden", !on);
}

// ── Friendly Error Messages ────────────────────────────────
function friendlyError(raw) {
  const r = raw.toLowerCase();
  if (r.includes("no such column") || r.includes("no such table")) {
    const match = raw.match(/no such (?:column|table): (\S+)/i);
    return {
      title: "Column or table not found",
      desc: match
        ? `"${match[1]}" doesn't exist in your dataset. Check the schema on the left for exact names.`
        : "A column or table referenced in the query doesn't exist. Check the schema panel."
    };
  }
  if (r.includes("syntax error")) {
    return {
      title: "SQL syntax error",
      desc: "The generated query had a syntax issue. Try rephrasing your question more clearly."
    };
  }
  if (r.includes("ambiguous column")) {
    return {
      title: "Ambiguous column name",
      desc: "Multiple tables have a column with the same name. Try specifying which table you mean."
    };
  }
  if (r.includes("could not understand") || r.includes("cannot generate") || r.includes("422")) {
    return {
      title: "Couldn't understand your question",
      desc: "Try rephrasing — be specific about column names, values, or conditions you want to filter by."
    };
  }
  if (r.includes("db not found") || r.includes("re-upload")) {
    return {
      title: "Dataset not found",
      desc: "Your uploaded file seems to have expired. Please re-upload your dataset."
    };
  }
  if (r.includes("network") || r.includes("failed to fetch")) {
    return {
      title: "Connection error",
      desc: "Can't reach the server. Make sure the backend is running and try again."
    };
  }
  if (r.includes("read-only") || r.includes("permission")) {
    return {
      title: "Not allowed",
      desc: "Only SELECT queries are permitted. The app is read-only for your safety."
    };
  }
  return {
    title: "Something went wrong",
    desc: raw || "An unexpected error occurred. Try a different question or re-upload your file."
  };
}

// ── Toast ──────────────────────────────────────────────────
function toast(msg, type = "info") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  el.toastContainer.appendChild(t);
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 350);
  }, 3200);
}
