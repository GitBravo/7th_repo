const STORAGE_KEY = "vmc_chat_state_v1";

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("query-input");
const sendBtn = document.getElementById("send-btn");
const conversationListEl = document.getElementById("conversation-list");
const newChatBtn = document.getElementById("new-chat-btn");
const sidebarEl = document.getElementById("sidebar");
const sidebarBackdropEl = document.getElementById("sidebar-backdrop");
const sidebarToggleBtn = document.getElementById("sidebar-toggle");
const sidebarCloseBtn = document.getElementById("sidebar-close");

// ---------- 대화 이력 저장/복원 (localStorage) ----------

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { conversations: [], activeId: null };
    const parsed = JSON.parse(raw);
    return { conversations: parsed.conversations || [], activeId: parsed.activeId || null };
  } catch {
    return { conversations: [], activeId: null };
  }
}

let state = loadState();

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function getActiveConversation() {
  return state.conversations.find((c) => c.id === state.activeId) || null;
}

function sortedConversations() {
  return [...state.conversations].sort((a, b) => b.updatedAt - a.updatedAt);
}

// ---------- 사이드바 ----------

function formatTimestamp(ts) {
  const d = new Date(ts);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" });
}

function renderSidebar() {
  conversationListEl.innerHTML = "";
  const conversations = sortedConversations();

  if (!conversations.length) {
    const empty = document.createElement("p");
    empty.className = "text-xs text-zinc-600 px-2 py-3 text-center";
    empty.textContent = "아직 대화 이력이 없습니다";
    conversationListEl.appendChild(empty);
    return;
  }

  for (const conv of conversations) {
    const isActive = conv.id === state.activeId;
    const item = document.createElement("button");
    item.className =
      "conv-item group relative w-full text-left px-3 py-2.5 rounded-lg transition-colors flex flex-col gap-0.5 " +
      (isActive
        ? "bg-emerald-500/10 border border-emerald-600/60 ring-1 ring-emerald-600/20"
        : "border border-transparent hover:bg-zinc-900");

    const titleEl = document.createElement("span");
    titleEl.className = "text-sm truncate pr-6 " + (isActive ? "text-emerald-300 font-medium" : "text-zinc-200");
    titleEl.textContent = conv.title || "새 대화";

    const dateEl = document.createElement("span");
    dateEl.className = "text-[11px] text-zinc-500";
    dateEl.textContent = formatTimestamp(conv.updatedAt);

    const deleteBtn = document.createElement("span");
    deleteBtn.className =
      "absolute right-2 top-2 h-5 w-5 flex items-center justify-center rounded text-zinc-600 opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-zinc-800 transition-opacity";
    deleteBtn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"/></svg>';
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(conv.id);
    });

    item.appendChild(titleEl);
    item.appendChild(dateEl);
    item.appendChild(deleteBtn);
    item.addEventListener("click", () => selectConversation(conv.id));

    conversationListEl.appendChild(item);
  }
}

function deleteConversation(id) {
  state.conversations = state.conversations.filter((c) => c.id !== id);
  if (state.activeId === id) {
    state.activeId = null;
    clearChat();
    renderGreeting();
  }
  saveState();
  renderSidebar();
}

function selectConversation(id) {
  state.activeId = id;
  saveState();
  renderSidebar();
  const conv = getActiveConversation();
  clearChat();
  if (conv) {
    for (const msg of conv.messages) {
      if (msg.role === "user") renderUserMessage(msg.text);
      else if (msg.role === "compare") renderComparisonMessage(msg.naive, msg.advanced);
    }
  }
  closeSidebarOnMobile();
}

function startNewConversation() {
  state.activeId = null;
  saveState();
  renderSidebar();
  clearChat();
  renderGreeting();
  closeSidebarOnMobile();
  inputEl.focus();
}

// ---------- 사이드바 열기/닫기 (모바일) ----------

function openSidebarOnMobile() {
  sidebarEl.classList.remove("-translate-x-full");
  sidebarEl.classList.add("translate-x-0");
  sidebarBackdropEl.classList.remove("hidden");
}

function closeSidebarOnMobile() {
  sidebarEl.classList.add("-translate-x-full");
  sidebarEl.classList.remove("translate-x-0");
  sidebarBackdropEl.classList.add("hidden");
}

sidebarToggleBtn.addEventListener("click", openSidebarOnMobile);
sidebarCloseBtn.addEventListener("click", closeSidebarOnMobile);
sidebarBackdropEl.addEventListener("click", closeSidebarOnMobile);

// ---------- 채팅 렌더링 ----------

function scrollToBottom() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

function clearChat() {
  chatEl.innerHTML = "";
}

function renderGreeting() {
  const wrap = document.createElement("div");
  wrap.className = "msg-in flex justify-start";
  wrap.innerHTML = `
    <div class="max-w-[85%] rounded-2xl rounded-tl-sm bg-zinc-900 border border-zinc-800 px-4 py-3 text-sm text-zinc-300">
      안녕하세요! 병무청 보도자료를 바탕으로 질문에 답해드립니다. 질문 하나당 <span class="text-zinc-300 font-medium">Naive RAG</span>와
      <span class="text-emerald-400 font-medium">Advanced RAG</span>(질의 확장) 답변을 나란히 비교해서 보여드려요.
      예: <span class="text-emerald-400">"사회복무요원 관련 새로운 지원 제도가 있어?"</span>
    </div>`;
  chatEl.appendChild(wrap);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderUserMessage(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg-in flex justify-end";

  const bubble = document.createElement("div");
  bubble.className =
    "max-w-[85%] rounded-2xl rounded-tr-sm bg-emerald-500 text-zinc-950 px-4 py-3 text-sm font-medium whitespace-pre-wrap";
  bubble.textContent = text;

  wrap.appendChild(bubble);
  chatEl.appendChild(wrap);
  scrollToBottom();
}

function renderLoading() {
  const wrap = document.createElement("div");
  wrap.id = "loading-msg";
  wrap.className = "msg-in flex justify-start";
  wrap.innerHTML = [
    '<div class="max-w-[85%] rounded-2xl rounded-tl-sm bg-zinc-900 border border-zinc-800 px-4 py-3 flex gap-1.5 items-center">',
    '<span class="dot h-1.5 w-1.5 rounded-full bg-zinc-400"></span>',
    '<span class="dot h-1.5 w-1.5 rounded-full bg-zinc-400"></span>',
    '<span class="dot h-1.5 w-1.5 rounded-full bg-zinc-400"></span>',
    "</div>",
  ].join("");
  chatEl.appendChild(wrap);
  scrollToBottom();
}

function removeLoading() {
  document.getElementById("loading-msg")?.remove();
}

function buildSourcesElement(sources) {
  const details = document.createElement("details");
  details.className = "mt-3 group";

  const items = sources
    .map(
      (s) => `
      <div class="rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2">
        <p class="text-xs font-semibold text-emerald-400">${escapeHtml(s.document_title || "")}${s.press_date ? ` · ${escapeHtml(s.press_date)}` : ""}</p>
        <p class="text-xs text-zinc-500 mt-0.5">${escapeHtml(s.section_heading || "")}</p>
        <p class="text-xs text-zinc-400 mt-1 line-clamp-3">${escapeHtml(s.content.slice(0, 160))}${s.content.length > 160 ? "…" : ""}</p>
      </div>`
    )
    .join("");

  details.innerHTML = `<summary class="cursor-pointer text-xs text-zinc-400 hover:text-emerald-400 select-none flex items-center gap-1"><svg class="w-3 h-3 transition-transform group-open:rotate-90" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z" clip-rule="evenodd"></path></svg>참고 자료 (${sources.length})</summary><div class="mt-2 space-y-2">${items}</div>`;

  return details;
}

function buildQueryVariantsElement(variants) {
  const wrap = document.createElement("div");
  wrap.className = "mt-3 flex flex-wrap gap-1.5";
  wrap.innerHTML =
    `<span class="text-xs text-zinc-500 mr-1">확장 질의:</span>` +
    variants
      .map(
        (v) =>
          `<span class="text-xs bg-sky-950/60 text-sky-300 border border-sky-900 rounded-full px-2 py-0.5">${escapeHtml(v)}</span>`
      )
      .join("");
  return wrap;
}

function buildRagCard(label, badgeClass, result) {
  const card = document.createElement("div");
  card.className = "rounded-2xl bg-zinc-900 border border-zinc-800 px-4 py-3 flex-1 min-w-0";

  const badge = document.createElement("span");
  badge.className = `inline-block text-[11px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 mb-2 ${badgeClass}`;
  badge.textContent = label;
  card.appendChild(badge);

  const answerEl = document.createElement("div");
  answerEl.className = "text-sm text-zinc-100 whitespace-pre-wrap";
  answerEl.textContent = result.answer;
  card.appendChild(answerEl);

  if (result.query_variants && result.query_variants.length) {
    card.appendChild(buildQueryVariantsElement(result.query_variants));
  }

  if (result.sources && result.sources.length) {
    card.appendChild(buildSourcesElement(result.sources));
  }

  return card;
}

function renderComparisonMessage(naive, advanced) {
  const wrap = document.createElement("div");
  wrap.className = "msg-in flex justify-start w-full";

  const grid = document.createElement("div");
  grid.className = "grid grid-cols-1 md:grid-cols-2 gap-3 w-full";
  grid.appendChild(buildRagCard("Naive RAG", "bg-zinc-800 text-zinc-300", naive));
  grid.appendChild(buildRagCard("Advanced RAG", "bg-emerald-900/60 text-emerald-300", advanced));

  wrap.appendChild(grid);
  chatEl.appendChild(wrap);
  scrollToBottom();
}

function renderError(message) {
  const wrap = document.createElement("div");
  wrap.className = "msg-in flex justify-start";

  const bubble = document.createElement("div");
  bubble.className =
    "max-w-[85%] rounded-2xl rounded-tl-sm bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300";
  bubble.textContent = `오류가 발생했습니다: ${message}`;

  wrap.appendChild(bubble);
  chatEl.appendChild(wrap);
  scrollToBottom();
}

// ---------- 메시지 전송 ----------

function makeConversationTitle(query) {
  return query.length > 40 ? query.slice(0, 40) + "…" : query;
}

async function sendQuery(query) {
  let conv = getActiveConversation();
  if (!conv) {
    conv = {
      id: crypto.randomUUID(),
      title: makeConversationTitle(query),
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [],
    };
    state.conversations.unshift(conv);
    state.activeId = conv.id;
  }

  conv.messages.push({ role: "user", text: query });
  conv.updatedAt = Date.now();
  saveState();
  renderSidebar();

  renderUserMessage(query);
  renderLoading();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const data = await res.json();
    removeLoading();
    renderComparisonMessage(data.naive, data.advanced);

    conv.messages.push({ role: "compare", naive: data.naive, advanced: data.advanced });
    conv.updatedAt = Date.now();
    saveState();
    renderSidebar();
  } catch (err) {
    removeLoading();
    renderError(err.message);
  } finally {
    sendBtn.disabled = false;
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const query = inputEl.value.trim();
  if (!query) return;
  inputEl.value = "";
  inputEl.style.height = "auto";
  sendQuery(query);
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    formEl.requestSubmit();
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px";
});

newChatBtn.addEventListener("click", startNewConversation);

// ---------- 초기화 ----------

renderSidebar();
const initialConv = getActiveConversation();
if (initialConv) {
  for (const msg of initialConv.messages) {
    if (msg.role === "user") renderUserMessage(msg.text);
    else if (msg.role === "compare") renderComparisonMessage(msg.naive, msg.advanced);
  }
} else {
  renderGreeting();
}
