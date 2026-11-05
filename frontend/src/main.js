import "./style.css";

const HISTORY_KEY = "multi-service-rag-chat-history-v1";
const ACTIVE_DOCUMENT_KEY = "multi-service-rag-active-document";

const state = {
  selectedFile: null,
  documents: [],
  activeDocumentId: localStorage.getItem(ACTIVE_DOCUMENT_KEY),
  uploading: false,
  asking: false,
  history: loadHistory(),
  pollTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const fileInput = $("#file-input");
const uploadButton = $("#upload-button");
const askButton = $("#ask-button");
const questionInput = $("#question-input");
const conversation = $("#conversation");
const documentList = $("#document-list");

function loadHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history));
  } catch {
    setNotice("ذخیره تاریخچه در مرورگر ممکن نشد؛ فضای ذخیره‌سازی را بررسی کن.", "warning");
  }
}

function getActiveHistory() {
  if (!state.activeDocumentId) return [];
  const messages = state.history[state.activeDocumentId];
  return Array.isArray(messages) ? messages : [];
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function setNotice(message, type = "info") {
  const element = $("#upload-message");
  element.textContent = message;
  element.className = `notice notice-${type}`;
  element.classList.remove("hidden");
}

function statusLabel(status) {
  return ({
    pending: "در صف پردازش",
    processing: "در حال پردازش",
    completed: "آماده پرسش",
    failed: "پردازش ناموفق",
  })[String(status).toLowerCase()] || "وضعیت نامشخص";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

async function readResponse(response) {
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { detail: text };
  }
  if (!response.ok) {
    const detail = payload.detail || payload.message || payload.error || `خطای سرور (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

async function apiRequest(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("ارتباط با سرور برقرار نشد. از روشن بودن سرویس‌ها مطمئن شو.");
  }
  return readResponse(response);
}

function setConnection(message, online = false) {
  $("#connection-label").textContent = message;
  $(".state-dot").classList.toggle("online", online);
}

function renderDocuments() {
  if (!state.documents.length) {
    documentList.innerHTML = '<div class="empty-state">هنوز سندی بارگذاری نشده است.</div>';
    updateAskAvailability();
    return;
  }

  documentList.innerHTML = state.documents.map((doc) => {
    const active = doc.document_id === state.activeDocumentId;
    const status = String(doc.status || "").toLowerCase();
    const error = status === "failed" && doc.error_message
      ? `<small class="document-error">${escapeHtml(doc.error_message)}</small>`
      : "";
    return `
      <div class="document-row">
        <button class="document-item ${active ? "active" : ""}" data-document-id="${escapeHtml(doc.document_id)}">
          <span class="pdf-icon">PDF</span>
          <span class="document-meta">
            <strong>${escapeHtml(doc.filename)}</strong>
            <small>${escapeHtml(statusLabel(status))} · ${escapeHtml(formatDate(doc.created_at))}</small>
            ${error}
          </span>
          <span class="status-indicator status-${escapeHtml(status)}"></span>
        </button>
        ${status === "completed" || status === "failed" ? `<button class="reprocess-button" data-reprocess-id="${escapeHtml(doc.document_id)}" title="پردازش مجدد">↻</button>` : ""}
      </div>`;
  }).join("");

  documentList.querySelectorAll("[data-document-id]").forEach((button) => {
    button.addEventListener("click", () => selectDocument(button.dataset.documentId));
  });

  documentList.querySelectorAll("[data-reprocess-id]").forEach((button) => {
    button.addEventListener("click", () => reprocessDocument(button.dataset.reprocessId, button));
  });

  updateAskAvailability();
}

function selectDocument(documentId) {
  state.activeDocumentId = documentId;
  localStorage.setItem(ACTIVE_DOCUMENT_KEY, documentId);
  renderDocuments();
  renderConversation();
  updateAskAvailability();
}

function renderConversation() {
  const messages = getActiveHistory();
  if (!state.activeDocumentId) {
    conversation.innerHTML = '<div class="welcome-card"><div class="welcome-symbol">✳</div><h3>ابتدا یک سند انتخاب کن</h3><p>پس از انتخاب سند پردازش‌شده، می‌توانی سؤال‌هایت را بپرسی.</p></div>';
    return;
  }
  if (!messages.length) {
    conversation.innerHTML = '<div class="welcome-card"><div class="welcome-symbol">✳</div><h3>گفت‌وگو با این سند را شروع کن</h3><p>سؤال‌ها و پاسخ‌ها برای این سند در همین مرورگر ذخیره می‌شوند.</p></div>';
    return;
  }
  conversation.innerHTML = "";
  messages.forEach((message) => appendMessageElement(message));
  conversation.scrollTop = conversation.scrollHeight;
}

function appendMessageElement(message) {
  const article = document.createElement("article");
  article.className = `message message-${message.role}`;
  const label = message.role === "user" ? "شما" : "دستیار";
  const sources = Array.isArray(message.sources) ? message.sources : [];
  const sourceHtml = sources.length ? `
    <div class="sources"><strong>منابع پاسخ</strong>
      ${sources.map((source) => `
        <div class="source-item"><span>صفحه ${escapeHtml(source.page_number ?? "—")}</span><span>${escapeHtml(source.filename || "")}</span></div>
      `).join("")}
    </div>` : "";
  article.innerHTML = `
    <div class="message-label">${label}<time>${escapeHtml(formatDate(message.created_at))}</time></div>
    <div class="message-content"></div>
    ${message.insufficient ? '<div class="notice notice-warning">اطلاعات بازیابی‌شده برای پاسخ مطمئن کافی نبود.</div>' : ""}
    ${sourceHtml}`;
  article.querySelector(".message-content").textContent = message.content || "";
  conversation.appendChild(article);
}

function appendAndSaveMessage(message) {
  if (!state.activeDocumentId) return;
  const messages = getActiveHistory();
  messages.push(message);
  state.history[state.activeDocumentId] = messages;
  saveHistory();
  appendMessageElement(message);
  conversation.scrollTop = conversation.scrollHeight;
}

function updateAskAvailability() {
  const active = state.documents.find((doc) => doc.document_id === state.activeDocumentId);
  askButton.disabled = state.asking || !questionInput.value.trim() || !active || active.status !== "completed";
}

function setBusy(button, busy, busyText, normalText) {
  button.disabled = busy;
  button.textContent = busy ? busyText : normalText;
}

async function checkServices() {
  try {
    const results = await Promise.all([
      apiRequest("/health/documents"),
      apiRequest("/health/retrieval"),
      apiRequest("/health/rag"),
    ]);
    setConnection("سرویس‌ها در دسترس‌اند", results.every((item) => item.status === "healthy"));
  } catch {
    setConnection("برخی سرویس‌ها در دسترس نیستند", false);
  }
}

async function loadDocuments() {
  documentList.innerHTML = '<div class="empty-state">در حال دریافت فهرست اسناد...</div>';
  try {
    const documents = await apiRequest("/documents/");
    state.documents = Array.isArray(documents) ? documents : [];
    if (!state.documents.some((doc) => doc.document_id === state.activeDocumentId)) {
      state.activeDocumentId = state.documents[0]?.document_id || null;
    }
    if (state.activeDocumentId) {
      localStorage.setItem(ACTIVE_DOCUMENT_KEY, state.activeDocumentId);
    } else {
      localStorage.removeItem(ACTIVE_DOCUMENT_KEY);
    }
    renderDocuments();
    renderConversation();
    await checkServices();
    startStatusPolling();
  } catch (error) {
    documentList.innerHTML = '<div class="empty-state">دریافت فهرست اسناد ناموفق بود.</div>';
    setNotice(error.message, "error");
    setConnection("خطا در اتصال به سرویس اسناد", false);
  }
}

async function refreshDocument(documentId) {
  const latest = await apiRequest(`/documents/${documentId}/status/`);
  const index = state.documents.findIndex((doc) => doc.document_id === documentId);
  if (index >= 0) state.documents[index] = latest;
  return latest;
}

async function pollDocument(documentId) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const latest = await refreshDocument(documentId);
    renderDocuments();
    if (latest.status === "completed") {
      setNotice("پردازش سند کامل شد. حالا می‌توانی سؤال بپرسی.", "success");
      return;
    }
    if (latest.status === "failed") {
      setNotice(latest.error_message || "پردازش سند ناموفق بود. می‌توانی دوباره تلاش کنی.", "error");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  setNotice("پردازش همچنان ادامه دارد؛ وضعیت سند در فهرست به‌روزرسانی می‌شود.", "warning");
}

function startStatusPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    const pending = state.documents.filter((doc) => ["pending", "processing"].includes(String(doc.status).toLowerCase()));
    if (!pending.length) return;
    await Promise.all(pending.map(async (doc) => {
      try {
        const latest = await refreshDocument(doc.document_id);
        if (latest.status === "failed" && latest.error_message) {
          setNotice(`پردازش «${latest.filename}» ناموفق بود: ${latest.error_message}`, "error");
        }
      } catch {
        setNotice("به‌روزرسانی وضعیت بعضی اسناد ممکن نشد.", "warning");
      }
    }));
    renderDocuments();
  }, 5000);
}

async function reprocessDocument(documentId, button) {
  button.disabled = true;
  try {
    const result = await apiRequest(`/documents/${documentId}/reprocess/`, { method: "POST" });
    const doc = state.documents.find((item) => item.document_id === documentId);
    if (doc) doc.status = result.status;
    renderDocuments();
    setNotice("پردازش مجدد آغاز شد.", "info");
    await pollDocument(documentId);
  } catch (error) {
    setNotice(error.message, "error");
    button.disabled = false;
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0] || null;
  state.selectedFile = file;
  $("#selected-file").textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "";
  $("#selected-file").classList.toggle("hidden", !file);
  uploadButton.disabled = !file || state.uploading;
});

const dropzone = $("#dropzone");
dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  const file = event.dataTransfer.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setNotice("فقط فایل PDF قابل بارگذاری است.", "error");
    return;
  }
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event("change"));
});

uploadButton.addEventListener("click", async () => {
  const file = state.selectedFile;
  if (!file || state.uploading) return;
  state.uploading = true;
  setBusy(uploadButton, true, "در حال بارگذاری...", "بارگذاری و پردازش");
  setNotice("فایل در حال ارسال است...", "info");
  try {
    const form = new FormData();
    form.append("file", file);
    const result = await apiRequest("/documents/upload/", { method: "POST", body: form });
    const doc = {
      document_id: result.document_id,
      filename: result.filename,
      status: result.status,
      created_at: new Date().toISOString(),
    };
    state.documents = [doc, ...state.documents.filter((item) => item.document_id !== doc.document_id)];
    selectDocument(doc.document_id);
    fileInput.value = "";
    state.selectedFile = null;
    $("#selected-file").classList.add("hidden");
    setNotice("فایل دریافت شد؛ پردازش در پس‌زمینه انجام می‌شود.", "info");
    await pollDocument(doc.document_id);
  } catch (error) {
    setNotice(error.message || "بارگذاری فایل ناموفق بود.", "error");
  } finally {
    state.uploading = false;
    setBusy(uploadButton, false, "در حال بارگذاری...", "بارگذاری و پردازش");
    uploadButton.disabled = !state.selectedFile;
  }
});

questionInput.addEventListener("input", updateAskAvailability);

$("#question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  const active = state.documents.find((doc) => doc.document_id === state.activeDocumentId);
  if (!question || !active || active.status !== "completed" || state.asking) return;

  appendAndSaveMessage({ role: "user", content: question, created_at: new Date().toISOString() });
  questionInput.value = "";
  state.asking = true;
  updateAskAvailability();
  setBusy(askButton, true, "در حال جست‌وجو...", "ارسال پرسش ←");

  try {
    const payload = {
      question,
      top_k: Number($("#top-k").value),
      document_ids: $("#limit-to-current").checked ? [active.document_id] : null,
    };
    const result = await apiRequest("/rag/ask/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    appendAndSaveMessage({
      role: "assistant",
      content: result.answer || "پاسخی از سرویس دریافت نشد.",
      sources: result.sources || [],
      insufficient: Boolean(result.insufficient_context),
      created_at: new Date().toISOString(),
    });
  } catch (error) {
    appendAndSaveMessage({
      role: "assistant",
      content: `خطا در دریافت پاسخ: ${error.message}`,
      sources: [],
      created_at: new Date().toISOString(),
    });
    setNotice(error.message, "error");
  } finally {
    state.asking = false;
    setBusy(askButton, false, "در حال جست‌وجو...", "ارسال پرسش ←");
    updateAskAvailability();
    questionInput.focus();
  }
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.focus();
    updateAskAvailability();
  });
});

loadDocuments();
