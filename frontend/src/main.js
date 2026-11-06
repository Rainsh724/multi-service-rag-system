import "./style.css";

const state = {
  selectedFile: null,
  documents: [],
  activeDocumentId: null,
  uploading: false,
  asking: false,
  deletingDocumentIds: new Set(),
};

const $ = (selector) => document.querySelector(selector);
const fileInput = $("#file-input");
const uploadButton = $("#upload-button");
const askButton = $("#ask-button");
const questionInput = $("#question-input");
const conversation = $("#conversation");
const documentList = $("#document-list");

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function setNotice(message, type = "info") {
  const element = $("#upload-message");
  element.textContent = message;
  element.className = `notice notice-${type}`;
}

function statusLabel(status) {
  return ({
    pending: "در صف پردازش",
    processing: "در حال پردازش",
    completed: "آماده پرسش",
    failed: "پردازش ناموفق",
  })[String(status).toLowerCase()] || status;
}

function renderDocuments() {
  if (!state.documents.length) {
    documentList.innerHTML = '<div class="empty-state">هنوز سندی در این نشست بارگذاری نشده است.</div>';
    askButton.disabled = true;
    return;
  }

  documentList.innerHTML = state.documents.map((doc) => {
    const active = doc.document_id === state.activeDocumentId;
    const status = String(doc.status).toLowerCase();
    return `
      <div class="document-row">
        <button class="document-item ${active ? "active" : ""}" data-document-id="${escapeHtml(doc.document_id)}">
          <span class="pdf-icon">PDF</span>
          <span class="document-meta"><strong>${escapeHtml(doc.filename)}</strong><small>${escapeHtml(statusLabel(status))}</small></span>
          <span class="status-indicator status-${escapeHtml(status)}"></span>
        </button>
        ${status === "completed" || status === "failed" ? `<button class="reprocess-button" data-reprocess-id="${escapeHtml(doc.document_id)}" title="پردازش مجدد با تنظیمات فعلی">↻</button>` : ""}
        <button class="delete-document-button" data-delete-id="${escapeHtml(doc.document_id)}" ${state.deletingDocumentIds.has(doc.document_id) ? "disabled" : ""} title="حذف کامل سند">${state.deletingDocumentIds.has(doc.document_id) ? "…" : "×"}</button>
      </div>`;
  }).join("");

  documentList.querySelectorAll("[data-document-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeDocumentId = button.dataset.documentId;
      renderDocuments();
      updateAskAvailability();
    });
  });

  documentList.querySelectorAll("[data-delete-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const documentId = button.dataset.deleteId;
      const doc = state.documents.find((item) => item.document_id === documentId);
      if (!doc || state.deletingDocumentIds.has(documentId)) return;

      const confirmed = window.confirm(
        `سند «${doc.filename}» و تمام متن‌های استخراج‌شده و embeddingهای آن برای همیشه حذف شوند؟ این عملیات قابل بازگشت نیست.`
      );
      if (!confirmed) return;

      state.deletingDocumentIds.add(documentId);
      renderDocuments();
      setNotice("در حال حذف سند و داده‌های وابسته...", "info");

      try {
        const response = await fetch(`/documents/${documentId}/`, {
          method: "DELETE",
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "حذف سند ناموفق بود.");
        }

        state.documents = state.documents.filter(
          (item) => item.document_id !== documentId
        );

        if (state.activeDocumentId === documentId) {
          state.activeDocumentId = null;
          conversation.innerHTML = `
            <div class="welcome-card">
              <div class="welcome-symbol">✳</div>
              <h3>سند انتخاب نشده است</h3>
              <p>برای شروع، یک سند آماده را از فهرست انتخاب کن یا فایل PDF جدیدی بارگذاری کن.</p>
            </div>`;
        }

        setNotice("سند، فایل PDF و داده‌های بازیابی‌شده آن حذف شدند.", "success");
      } catch (error) {
        setNotice(error.message || "حذف سند با خطا مواجه شد.", "error");
      } finally {
        state.deletingDocumentIds.delete(documentId);
        renderDocuments();
      }
    });
  });

  documentList.querySelectorAll("[data-reprocess-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const documentId = button.dataset.reprocessId;
      button.disabled = true;
      try {
        const response = await fetch(`/documents/${documentId}/reprocess/`, {
          method: "POST",
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "شروع پردازش مجدد ناموفق بود.");
        const doc = state.documents.find((item) => item.document_id === documentId);
        if (doc) doc.status = "pending";
        renderDocuments();
        setNotice("پردازش مجدد با پیشوندهای صحیح Embedding آغاز شد.", "info");
        await pollDocument(documentId);
      } catch (error) {
        setNotice(error.message, "error");
        button.disabled = false;
      }
    });
  });
  updateAskAvailability();
}

function updateAskAvailability() {
  const active = state.documents.find((doc) => doc.document_id === state.activeDocumentId);
  askButton.disabled = state.asking || !questionInput.value.trim() || !active || active.status !== "completed";
}

function addMessage(role, content, sources = [], insufficient = false) {
  const article = document.createElement("article");
  article.className = `message message-${role}`;
  const label = role === "user" ? "شما" : "دستیار";
  const sourceHtml = sources.length ? `
    <div class="sources"><strong>منابع پاسخ</strong>
      ${sources.map((source) => `
        <div class="source-item"><span>صفحه ${escapeHtml(source.page_number)}</span><span>${escapeHtml(source.filename)}</span></div>
      `).join("")}
    </div>` : "";
  article.innerHTML = `<div class="message-label">${label}</div><div class="message-content"></div>${insufficient ? '<div class="notice notice-warning">اطلاعات بازیابی‌شده برای پاسخ مطمئن کافی نبود.</div>' : ""}${sourceHtml}`;
  article.querySelector(".message-content").textContent = content;
  conversation.appendChild(article);
  conversation.scrollTop = conversation.scrollHeight;
}

function setBusy(button, busy, busyText, normalText) {
  button.disabled = busy;
  button.textContent = busy ? busyText : normalText;
}

async function checkServices() {
  const label = $("#connection-label");
  try {
    const [documentHealth, retrievalHealth, ragHealth] = await Promise.all([
      fetch("/health/documents").catch(() => null),
      fetch("/health/retrieval").catch(() => null),
      fetch("/health/rag").catch(() => null),
    ]);
    const ok = Boolean(documentHealth?.ok && retrievalHealth?.ok && ragHealth?.ok);
    label.textContent = ok ? "سرویس‌ها در دسترس‌اند" : "در انتظار اتصال به سرویس‌ها";
    $(".state-dot").classList.toggle("online", ok);
  } catch {
    label.textContent = "اتصال به سرویس‌ها برقرار نیست";
  }
}

async function refreshDocument(documentId) {
  const response = await fetch(`/documents/${documentId}/status/`);
  if (!response.ok) throw new Error("دریافت وضعیت سند ناموفق بود.");
  const latest = await response.json();
  const index = state.documents.findIndex((doc) => doc.document_id === documentId);
  if (index >= 0) state.documents[index] = latest;
  renderDocuments();
  return latest;
}

async function pollDocument(documentId) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const doc = await refreshDocument(documentId);
    const status = String(doc.status).toLowerCase();
    if (status === "completed") {
      setNotice("پردازش سند کامل شد. حالا می‌توانی سؤال بپرسی.", "success");
      return;
    }
    if (status === "failed") {
      setNotice(doc.error_message || "پردازش سند با خطا مواجه شد.", "error");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  setNotice("پردازش هنوز ادامه دارد. وضعیت سند در فهرست قابل مشاهده است.", "warning");
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
    const response = await fetch("/documents/upload/", { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "بارگذاری فایل ناموفق بود.");
    const doc = { ...payload, created_at: new Date().toISOString() };
    state.documents.unshift(doc);
    state.activeDocumentId = doc.document_id;
    renderDocuments();
    setNotice("فایل دریافت شد؛ پردازش در پس‌زمینه انجام می‌شود.", "info");
    fileInput.value = "";
    state.selectedFile = null;
    $("#selected-file").classList.add("hidden");
    await pollDocument(doc.document_id);
  } catch (error) {
    setNotice(error.message || "خطای ناشناخته هنگام بارگذاری.", "error");
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

  addMessage("user", question);
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
    const response = await fetch("/rag/ask/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "اجرای پرسش ناموفق بود.");
    addMessage("assistant", result.answer, result.sources || [], result.insufficient_context);
  } catch (error) {
    addMessage("assistant", error.message || "ارتباط با سرویس پاسخ‌گویی برقرار نشد.");
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

checkServices();
