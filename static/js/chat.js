/**
 * SecureShare Messenger - Chat Application Controller
 * Handles active conversations, message sending with automatic or custom protocol modes,
 * real-time receipt updates, image preview/sharing, clickable link sanitization, and delivery ticks.
 */

document.addEventListener("DOMContentLoaded", async () => {
  let activeConversationId = null;
  let currentUserId = null;
  const renderedMessageUuids = new Set();
  let userProtocolSettings = {
    mode: "custom",
    fragment_count: 3,
    is_sss_enabled: false,
    sss_threshold_k: 3,
    sss_total_shares_m: 5,
    fragment_telemetry: true,
    fragment_reassembly_status: true,
    private_mode: false,
  };

  // DOM Elements
  const conversationListEl = document.getElementById("conversationList");
  const chatMessagesEl = document.getElementById("chatMessages");
  const emptyStateEl = document.getElementById("emptyState");
  const activeChatEl = document.getElementById("activeChat");
  const chatPeerNameEl = document.getElementById("chatPeerName");
  const chatPeerIdEl = document.getElementById("chatPeerId");
  const chatInputEl = document.getElementById("chatInput");
  const sendBtnEl = document.getElementById("sendBtn");
  const userSearchInput = document.getElementById("userSearchInput");
  const searchResultsDropdown = document.getElementById("searchResultsDropdown");
  const shareConvBtn = document.getElementById("shareConvBtn");

  // Multi-Screen Responsive Layout Elements
  const sidebarEl = document.getElementById("sidebar");
  const chatPanelEl = document.getElementById("chatPanel");
  const mobileBackBtn = document.getElementById("mobileBackBtn");

  function handleResponsiveLayout() {
    const isMobile = window.innerWidth <= 900;
    if (!isMobile) {
      if (sidebarEl) sidebarEl.classList.remove("mobile-hidden");
      if (chatPanelEl) chatPanelEl.classList.remove("mobile-hidden");
      if (mobileBackBtn) mobileBackBtn.style.display = "none";
    } else {
      if (activeConversationId) {
        if (sidebarEl) sidebarEl.classList.add("mobile-hidden");
        if (chatPanelEl) chatPanelEl.classList.remove("mobile-hidden");
        if (mobileBackBtn) mobileBackBtn.style.display = "inline-flex";
      } else {
        if (sidebarEl) sidebarEl.classList.remove("mobile-hidden");
        if (chatPanelEl) chatPanelEl.classList.add("mobile-hidden");
        if (mobileBackBtn) mobileBackBtn.style.display = "none";
      }
    }
  }

  if (mobileBackBtn) {
    mobileBackBtn.addEventListener("click", () => {
      if (activeConversationId && window.socketClient) {
        window.socketClient.leaveConversation(activeConversationId);
      }
      activeConversationId = null;
      sessionStorage.removeItem("active_conversation_id");
      window.history.replaceState({}, "", window.location.pathname);
      document.querySelectorAll(".conversation-item").forEach((el) => {
        el.classList.remove("active");
      });
      if (sidebarEl) sidebarEl.classList.remove("mobile-hidden");
      if (chatPanelEl) chatPanelEl.classList.add("mobile-hidden");
      if (mobileBackBtn) mobileBackBtn.style.display = "none";
    });
  }

  window.addEventListener("resize", handleResponsiveLayout);

  // Image Upload Elements
  const attachBtn = document.getElementById("attachBtn");
  const imageFileInput = document.getElementById("imageFileInput");
  const imagePreviewModal = document.getElementById("imagePreviewModal");
  const imagePreviewImg = document.getElementById("imagePreviewImg");
  const imagePreviewDetails = document.getElementById("imagePreviewDetails");
  const cancelImageBtn = document.getElementById("cancelImageBtn");
  const cancelPreviewCloseBtn = document.getElementById("cancelPreviewCloseBtn");
  const confirmSendImageBtn = document.getElementById("confirmSendImageBtn");

  // Lightbox Elements
  const imageViewModal = document.getElementById("imageViewModal");
  const fullImageViewImg = document.getElementById("fullImageViewImg");
  const imageViewTitle = document.getElementById("imageViewTitle");
  const closeImageViewBtn = document.getElementById("closeImageViewBtn");
  const downloadImageBtn = document.getElementById("downloadImageBtn");

  // Context Menu Elements (Right-Click Message Actions)
  const messageContextMenu = document.getElementById("messageContextMenu");
  const ctxCopyText = document.getElementById("ctxCopyText");
  const ctxDeleteForMe = document.getElementById("ctxDeleteForMe");
  const ctxDeleteForEveryone = document.getElementById("ctxDeleteForEveryone");
  let contextMenuTargetUuid = null;
  let contextMenuTargetText = null;

  function hideContextMenu() {
    if (messageContextMenu) messageContextMenu.style.display = "none";
    contextMenuTargetUuid = null;
    contextMenuTargetText = null;
  }

  document.addEventListener("click", hideContextMenu);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideContextMenu();
  });

  function removeMessageBubbleFromDom(messageUuid) {
    const row = document.querySelector(`[data-message-uuid="${messageUuid}"]`);
    if (row) {
      row.classList.add("message-deleting");
      setTimeout(() => {
        row.remove();
        renderedMessageUuids.delete(messageUuid);
        if (chatMessagesEl && chatMessagesEl.children.length === 0) {
          chatMessagesEl.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); font-size: 0.85rem; margin: auto;">
              This conversation is secure. Messages are encrypted and fragmented before delivery.
            </div>
          `;
        }
      }, 250);
    }
  }

  if (ctxCopyText) {
    ctxCopyText.addEventListener("click", async (e) => {
      e.stopPropagation();
      const textToCopy = contextMenuTargetText;
      hideContextMenu();
      if (textToCopy) {
        await Utils.copyToClipboard(textToCopy, "Message text copied to clipboard!");
      }
    });
  }

  async function deleteMessageAction(mode) {
    const targetUuid = contextMenuTargetUuid;
    hideContextMenu();
    if (!targetUuid) return;

    const confirmPrompt = mode === "for_everyone"
      ? "Delete this message for everyone in this conversation?"
      : "Delete this message for you? The other user will still see it.";

    if (!confirm(confirmPrompt)) return;

    try {
      const res = await Utils.apiFetch(`/api/messages/${targetUuid}?mode=${mode}`, {
        method: "DELETE",
      });
      if (res.success) {
        removeMessageBubbleFromDom(targetUuid);
        loadConversations();
        Utils.showToast(mode === "for_everyone" ? "Message deleted for everyone." : "Message deleted for you.", "success");
      }
    } catch (err) {
      Utils.showToast("Failed to delete message: " + err.message, "error");
    }
  }

  if (ctxDeleteForMe) {
    ctxDeleteForMe.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteMessageAction("for_me");
    });
  }

  if (ctxDeleteForEveryone) {
    ctxDeleteForEveryone.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteMessageAction("for_everyone");
    });
  }

  let pendingImageFile = null;

  // Retrieve current user internal ID from page
  const appContainer = document.querySelector(".messenger-container");
  if (appContainer && appContainer.dataset.userInternalId) {
    currentUserId = appContainer.dataset.userInternalId;
  }

  // 1. Fetch User's Secure Protocol Settings
  async function loadProtocolSettings() {
    try {
      const res = await Utils.apiFetch("/api/settings/protocols");
      if (res.success && res.protocols) {
        userProtocolSettings = res.protocols;
      }
    } catch (err) {
      console.warn("Could not load protocol settings; using defaults:", err);
    }
  }
  await loadProtocolSettings();

  // 2. Safe Linkification Helper
  function renderSafeTextWithLinks(text) {
    if (!text) return "";
    const escaped = Utils.escapeHtml(text);
    // Strict URL regex matching only http:// or https://
    const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;
    return escaped.replace(urlRegex, (matched) => {
      let cleanUrl = matched;
      let trailing = "";
      while (cleanUrl.length > 0 && /[.,!?;:)\]]$/.test(cleanUrl)) {
        trailing = cleanUrl.slice(-1) + trailing;
        cleanUrl = cleanUrl.slice(0, -1);
      }
      if (!/^https?:\/\//i.test(cleanUrl)) {
        return matched;
      }
      return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="chat-link" title="Open external URL">${cleanUrl}</a><a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="follow-link-btn" title="Follow link in new tab">↗</a>${trailing}`;
    });
  }

  // 3. Delivery Ticks Helper
  function getTickIndicator(msg) {
    if (msg.sender_id !== currentUserId) return "";
    const state = msg.delivery_state || "sent";
    if (state === "read") {
      return `<span class="tick-indicator tick-read" title="Read by recipient">✓✓</span>`;
    } else if (state === "delivered") {
      return `<span class="tick-indicator tick-delivered" title="Delivered to recipient">✓✓</span>`;
    } else {
      return `<span class="tick-indicator tick-sent" title="Accepted by server">✓</span>`;
    }
  }

  // 4. Initialize Real-Time Socket Connection
  if (window.socketClient) {
    window.socketClient.connect();

    window.socketClient.onNewMessage(async (msgData) => {
      if (activeConversationId && msgData.conversation_id === activeConversationId) {
        // If recipient receives an incoming message that has not yet been reassembled in client, fetch reassembly
        if (msgData.sender_id !== currentUserId && msgData.status !== "reassembled") {
          try {
            const reassembledRes = await Utils.apiFetch(`/api/messages/${msgData.message_uuid}/reassemble`);
            if (reassembledRes && reassembledRes.message) {
              msgData = reassembledRes.message;
            }
          } catch (_) {}
        }
        appendMessageBubble(msgData);
        scrollToBottom();
        // Acknowledge read if recipient receives in active conversation
        if (msgData.sender_id !== currentUserId) {
          markActiveConversationRead();
        }
      }
      loadConversations();
    });

    window.socketClient.onConversationUpdated(() => {
      loadConversations();
    });

    window.socketClient.onMessagesRead((readData) => {
      if (activeConversationId && readData.conversation_id === activeConversationId) {
        if (readData.read_by_id !== currentUserId) {
          // Update outgoing ticks to read (blue double-tick)
          document.querySelectorAll(".message-row.outgoing .tick-indicator").forEach((el) => {
            el.className = "tick-indicator tick-read";
            el.textContent = "✓✓";
            el.title = "Read by recipient";
          });
        }
      }
    });

    window.socketClient.onMessageDeleted((delData) => {
      if (activeConversationId && delData.conversation_id === activeConversationId) {
        removeMessageBubbleFromDom(delData.message_uuid);
      }
      loadConversations();
    });
  }

  // 5. Image Lightbox Setup
  window.openImageLightbox = function (imageUrl, title) {
    if (!imageViewModal || !fullImageViewImg) return;
    fullImageViewImg.src = imageUrl;
    if (imageViewTitle) imageViewTitle.textContent = title || "Shared Image";
    if (downloadImageBtn) downloadImageBtn.href = `${imageUrl}?download=true`;
    imageViewModal.style.display = "flex";
  };

  if (closeImageViewBtn) {
    closeImageViewBtn.addEventListener("click", () => {
      if (imageViewModal) imageViewModal.style.display = "none";
    });
  }

  if (imageViewModal) {
    imageViewModal.addEventListener("click", (e) => {
      if (e.target === imageViewModal) {
        imageViewModal.style.display = "none";
      }
    });
  }

  // 6. Image Attachment & Preview Handlers
  if (attachBtn && imageFileInput) {
    attachBtn.addEventListener("click", () => {
      if (!activeConversationId) {
        Utils.showToast("Select a conversation before sending an image.", "error");
        return;
      }
      imageFileInput.click();
    });

    imageFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // 5MB Limit validation
      if (file.size > 5 * 1024 * 1024) {
        Utils.showToast("Image size exceeds 5MB limit. Please select a smaller file.", "error");
        imageFileInput.value = "";
        return;
      }

      if (!file.type.startsWith("image/")) {
        Utils.showToast("Only image files (PNG, JPEG, GIF, WEBP) are supported.", "error");
        imageFileInput.value = "";
        return;
      }

      pendingImageFile = file;
      const reader = new FileReader();
      reader.onload = (event) => {
        if (imagePreviewImg) imagePreviewImg.src = event.target.result;
        if (imagePreviewDetails) {
          const sizeKb = Math.round(file.size / 1024);
          imagePreviewDetails.textContent = `${file.name} (${sizeKb} KB)`;
        }
        if (imagePreviewModal) imagePreviewModal.style.display = "flex";
      };
      reader.readAsDataURL(file);
    });
  }

  function closeImagePreview() {
    if (imagePreviewModal) imagePreviewModal.style.display = "none";
    if (imageFileInput) imageFileInput.value = "";
    pendingImageFile = null;
  }

  if (cancelImageBtn) cancelImageBtn.addEventListener("click", closeImagePreview);
  if (cancelPreviewCloseBtn) cancelPreviewCloseBtn.addEventListener("click", closeImagePreview);

  if (confirmSendImageBtn) {
    confirmSendImageBtn.addEventListener("click", async () => {
      if (!pendingImageFile || !activeConversationId) return;

      confirmSendImageBtn.disabled = true;
      confirmSendImageBtn.textContent = "Encrypting & Sending...";

      const formData = new FormData();
      formData.append("image", pendingImageFile);
      formData.append("conversation_id", activeConversationId);

      try {
        const res = await fetch("/api/messages/image/upload", {
          method: "POST",
          body: formData,
          headers: {
            Accept: "application/json",
          },
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          throw new Error(data.error || "Image upload failed");
        }

        closeImagePreview();
        if (data.message) {
          const existingBubble = document.querySelector(`[data-message-uuid="${data.message.message_uuid}"]`);
          if (!existingBubble) {
            appendMessageBubble(data.message);
            scrollToBottom();
          }
        }
        loadConversations();
        Utils.showToast("Image shared securely!", "success");
      } catch (err) {
        Utils.showToast(err.message, "error");
      } finally {
        confirmSendImageBtn.disabled = false;
        confirmSendImageBtn.textContent = "Send Image ➤";
      }
    });
  }

  // 7. User Search Functionality
  let searchTimeout = null;
  if (userSearchInput) {
    userSearchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      const query = e.target.value.trim();
      if (!query) {
        searchResultsDropdown.style.display = "none";
        return;
      }

      searchTimeout = setTimeout(async () => {
        try {
          const res = await Utils.apiFetch(`/api/users/search?q=${encodeURIComponent(query)}`);
          renderSearchResults(res.users);
        } catch (err) {
          console.error("Search failed:", err);
        }
      }, 250);
    });

    document.addEventListener("click", (e) => {
      if (!userSearchInput.contains(e.target) && !searchResultsDropdown.contains(e.target)) {
        searchResultsDropdown.style.display = "none";
      }
    });
  }

  function renderSearchResults(users) {
    searchResultsDropdown.innerHTML = "";
    if (!users || users.length === 0) {
      searchResultsDropdown.innerHTML = `
        <div style="padding: 0.75rem 1rem; color: var(--text-muted); font-size: 0.85rem;">
          No matching users found.
        </div>
      `;
      searchResultsDropdown.style.display = "block";
      return;
    }

    users.forEach((user) => {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.innerHTML = `
        <div>
          <div style="font-weight: 600; font-size: 0.9rem;">${Utils.escapeHtml(user.display_name)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">@${Utils.escapeHtml(user.public_user_id)}</div>
        </div>
        <button class="btn btn-primary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Chat</button>
      `;

      item.addEventListener("click", async () => {
        searchResultsDropdown.style.display = "none";
        userSearchInput.value = "";
        try {
          const res = await Utils.apiFetch("/api/conversations/direct", {
            method: "POST",
            body: JSON.stringify({ target_public_id: user.public_user_id }),
          });
          if (res.conversation) {
            await loadConversations();
            selectConversation(res.conversation.id);
          }
        } catch (err) {
          Utils.showToast(err.message, "error");
        }
      });

      searchResultsDropdown.appendChild(item);
    });
    searchResultsDropdown.style.display = "block";
  }

  // 8. Conversation Loading & Selection
  async function loadConversations() {
    try {
      const res = await Utils.apiFetch("/api/conversations");
      renderConversationList(res.conversations);
    } catch (err) {
      console.error("Error loading conversations:", err);
    }
  }

  function renderConversationList(conversations) {
    if (!conversationListEl) return;
    conversationListEl.innerHTML = "";

    if (!conversations || conversations.length === 0) {
      conversationListEl.innerHTML = `
        <li style="padding: 2rem 1rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          No conversations yet.<br>Search a contact above to start chatting!
        </li>
      `;
      return;
    }

    conversations.forEach((conv) => {
      const li = document.createElement("li");
      li.className = `conversation-item ${conv.id === activeConversationId ? "active" : ""}`;
      li.dataset.conversationId = conv.id;

      const peerName = conv.peer ? conv.peer.display_name : "Deleted User";
      const lastMsg = conv.last_message;
      let snippet = "No messages yet";
      if (lastMsg) {
        if (lastMsg.message_type === "image") {
          snippet = "📷 Image";
        } else {
          snippet = "Encrypted message";
        }
      }
      const timeStr = lastMsg ? Utils.formatTime(lastMsg.created_at) : "";

      li.innerHTML = `
        <div class="avatar">${peerName.charAt(0).toUpperCase()}</div>
        <div class="conversation-details">
          <div class="conversation-top">
            <span class="conversation-name">${Utils.escapeHtml(peerName)}</span>
            <span class="conversation-time">${timeStr}</span>
          </div>
          <div class="conversation-bottom">
            <span class="conversation-snippet">${Utils.escapeHtml(snippet)}</span>
          </div>
        </div>
      `;

      li.addEventListener("click", () => selectConversation(conv.id));
      conversationListEl.appendChild(li);
    });
  }

  async function markActiveConversationRead() {
    if (!activeConversationId) return;
    try {
      await Utils.apiFetch(`/api/messages/conversation/${activeConversationId}/read`, {
        method: "POST",
      });
    } catch (err) {
      console.debug("mark_read notice:", err);
    }
  }

  async function selectConversation(conversationId) {
    if (!conversationId) return;

    if (activeConversationId && activeConversationId !== conversationId && window.socketClient) {
      window.socketClient.leaveConversation(activeConversationId);
    }

    activeConversationId = conversationId;
    if (window.socketClient) {
      window.socketClient.joinConversation(conversationId);
    }

    // Persist active conversation across reloads
    sessionStorage.setItem("active_conversation_id", conversationId);
    const newUrl = `${window.location.pathname}?conv=${encodeURIComponent(conversationId)}`;
    if (window.location.search !== `?conv=${encodeURIComponent(conversationId)}`) {
      window.history.replaceState({ conv: conversationId }, "", newUrl);
    }

    // Refresh protocol settings on conversation change
    await loadProtocolSettings();

    document.querySelectorAll(".conversation-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.conversationId === conversationId);
    });

    if (emptyStateEl) emptyStateEl.style.display = "none";
    if (activeChatEl) activeChatEl.style.display = "flex";

    handleResponsiveLayout();

    try {
      const res = await Utils.apiFetch(`/api/messages/conversation/${conversationId}`);

      const convRes = await Utils.apiFetch("/api/conversations");
      const currentConv = convRes.conversations.find((c) => c.id === conversationId);
      if (currentConv && currentConv.peer) {
        if (chatPeerNameEl) chatPeerNameEl.textContent = currentConv.peer.display_name;
        if (chatPeerIdEl) chatPeerIdEl.textContent = `@${currentConv.peer.public_user_id}`;
      } else {
        if (chatPeerNameEl) chatPeerNameEl.textContent = "Deleted User";
        if (chatPeerIdEl) chatPeerIdEl.textContent = "";
      }

      renderMessageHistory(res.messages);
      scrollToBottom();

      // Automatically mark incoming messages as read
      markActiveConversationRead();
    } catch (err) {
      Utils.showToast("Failed to load messages: " + err.message, "error");
    }
  }

  // 9. Message History Rendering with Protocol Preferences
  function renderMessageHistory(messages) {
    if (!chatMessagesEl) return;
    chatMessagesEl.innerHTML = "";
    renderedMessageUuids.clear();

    if (!messages || messages.length === 0) {
      chatMessagesEl.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); font-size: 0.85rem; margin: auto;">
          This conversation is secure. Messages are encrypted and fragmented before delivery.
        </div>
      `;
      return;
    }

    messages.forEach((msg) => appendMessageBubble(msg));
  }

  function appendMessageBubble(msg) {
    if (!chatMessagesEl || !msg || !msg.message_uuid) return;

    // Check if message is already rendered; reconcile delivery state or reassembled content if changed
    const existingRow = document.querySelector(`[data-message-uuid="${msg.message_uuid}"]`);
    if (existingRow) {
      // If message transitioned from waiting/pending to reassembled, update its body content
      const contentEl = existingRow.querySelector(".message-content");
      if (contentEl && (msg.status === "reassembled" || msg.plaintext || msg.display_text)) {
        if (contentEl.querySelector("em") || contentEl.textContent.includes("Waiting for")) {
          const textToShow = msg.display_text || msg.plaintext;
          if (textToShow && !textToShow.startsWith("Waiting for")) {
            contentEl.innerHTML = renderSafeTextWithLinks(textToShow);
            const statusPill = existingRow.querySelector(".status-pill");
            if (statusPill) {
              statusPill.className = "status-pill status-reassembled";
              statusPill.textContent = "✓ Reassembled";
            }
          }
        }
      }

      const tickContainer = existingRow.querySelector(".tick-indicator");
      const expectedTickHtml = getTickIndicator(msg);
      if (tickContainer && expectedTickHtml) {
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = expectedTickHtml;
        const newTick = tempDiv.firstElementChild;
        if (newTick && tickContainer.className !== newTick.className) {
          tickContainer.className = newTick.className;
          tickContainer.textContent = newTick.textContent;
          tickContainer.title = newTick.title;
        }
      }
      return;
    }

    renderedMessageUuids.add(msg.message_uuid);

    const emptyNotice = chatMessagesEl.querySelector("div[style*='text-align: center']");
    if (emptyNotice) emptyNotice.remove();

    const isOutgoing = msg.sender_id === currentUserId;
    const row = document.createElement("div");
    row.className = `message-row ${isOutgoing ? "outgoing" : "incoming"}`;
    row.dataset.messageUuid = msg.message_uuid;

    const timeStr = Utils.formatTime(msg.created_at);
    const isReassembled = msg.status === "reassembled" || (isOutgoing && (msg.display_text || msg.plaintext));

    // Privacy & Telemetry Preference Checks
    const isPrivate = Boolean(userProtocolSettings.private_mode);
    const showTelemetry = !isPrivate && (userProtocolSettings.fragment_telemetry !== false);
    const showReassemblyStatus = !isPrivate && (userProtocolSettings.fragment_reassembly_status !== false);

    // Build Message Body (Text or Image)
    let bodyHtml = "";
    if (msg.message_type === "image" && msg.image_id) {
      const imgUrl = `/api/messages/images/${encodeURIComponent(msg.image_id)}`;
      const altText = Utils.escapeHtml(msg.image_filename || "Shared Image");
      bodyHtml = `
        <div class="chat-image-wrap">
          <img
            class="chat-image"
            src="${imgUrl}"
            alt="${altText}"
            loading="lazy"
            onclick="window.openImageLightbox('${imgUrl}', '${altText}')"
            onerror="this.parentElement.innerHTML='<div class=\\'chat-image-expired\\'>⚠️ Image expired (7-day retention policy)</div>';"
          >
        </div>
      `;
    } else {
      const hasText = msg.display_text || msg.plaintext;
      if (isReassembled || (hasText && !hasText.startsWith("Waiting for"))) {
        bodyHtml = `<div class="message-content">${renderSafeTextWithLinks(hasText)}</div>`;
      } else {
        bodyHtml = `<div class="message-content"><em>${Utils.escapeHtml(hasText || "Waiting for missing fragments...")}</em></div>`;
      }
    }

    // Telemetry Inspector (Shown only if permitted and not in Private Mode)
    let fragmentsHtml = "";
    if (showReassemblyStatus && msg.fragments && msg.fragments.length > 0) {
      const chips = msg.fragments
        .map(
          (f) => `
        <span class="fragment-chip" title="SHA-256: ${f.payload_hash}">
          Part ${f.fragment_index}/${f.total_fragments}
          <span class="mono" style="font-size: 0.65rem; color: var(--text-muted);">${f.payload_hash.substring(0, 6)}…</span>
        </span>
      `
        )
        .join("");

      fragmentsHtml = `
        <details class="fragment-inspector">
          <summary style="cursor: pointer; font-weight: 600; color: var(--text-secondary);">
            Telemetry: ${msg.received_fragments_count || msg.fragments.length}/${msg.fragment_count} Fragments Verified
          </summary>
          <div class="fragment-chips-grid">${chips}</div>
        </details>
      `;
    }

    // Metadata Badges (SSS, Fragment Count, Status, Delivery Ticks)
    let sssBadgeHtml = "";
    if (showTelemetry && msg.is_sss_enabled) {
      sssBadgeHtml = `
        <span class="status-pill sss-badge">
          🛡️ SSS: K=${msg.sss_threshold_k}/M=${msg.sss_total_shares_m}
        </span>
      `;
    }

    let statusPillHtml = "";
    if (showReassemblyStatus) {
      statusPillHtml = `
        <span class="status-pill ${isReassembled ? "reassembled" : "waiting"}">
          ${isReassembled ? `✓ Reassembled (${msg.fragment_count}/${msg.fragment_count})` : `⏳ Fragments: ${msg.received_fragments_count || 0}/${msg.fragment_count}`}
        </span>
      `;
    } else if (showTelemetry) {
      statusPillHtml = `
        <span class="status-pill reassembled">
          Fragments: ${msg.fragment_count}
        </span>
      `;
    }

    const tickHtml = getTickIndicator(msg);

    row.innerHTML = `
      <div class="message-bubble">
        ${bodyHtml}
        ${fragmentsHtml}
      </div>
      <div class="message-meta">
        ${sssBadgeHtml}
        ${statusPillHtml}
        <span>${timeStr}</span>
        ${tickHtml}
      </div>
    `;

    // Right-Click Context Menu Trigger
    row.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      e.stopPropagation();

      contextMenuTargetUuid = msg.message_uuid;
      contextMenuTargetText = msg.plaintext || msg.display_text || "";
      const isSender = (msg.sender_id === currentUserId);

      if (ctxCopyText) {
        if (msg.message_type === "image" && !contextMenuTargetText) {
          ctxCopyText.style.display = "none";
        } else {
          ctxCopyText.style.display = "flex";
        }
      }

      if (ctxDeleteForMe) {
        ctxDeleteForMe.style.display = "flex";
      }

      if (ctxDeleteForEveryone) {
        // Only the sender can delete for everyone
        ctxDeleteForEveryone.style.display = isSender ? "flex" : "none";
      }

      if (messageContextMenu) {
        messageContextMenu.style.display = "flex";
        const menuWidth = 200;
        const menuHeight = isSender ? 130 : 90;
        let x = e.clientX;
        let y = e.clientY;
        if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 10;
        if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 10;
        messageContextMenu.style.left = `${Math.max(10, x)}px`;
        messageContextMenu.style.top = `${Math.max(10, y)}px`;
      }
    });

    chatMessagesEl.appendChild(row);
  }

  function scrollToBottom() {
    if (chatMessagesEl) {
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    }
  }

  // 10. Send Text Message Action
  async function sendMessage() {
    if (!activeConversationId) {
      Utils.showToast("Please select a conversation first.", "error");
      return;
    }

    const content = chatInputEl.value.trim();
    if (!content) return;

    chatInputEl.value = "";
    chatInputEl.style.height = "auto";

    try {
      // Backend automatically applies sender's configured mode (Automatic vs Custom)
      const res = await Utils.apiFetch("/api/messages/send", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: activeConversationId,
          content: content,
        }),
      });

      if (res.success && res.message) {
        if (!res.message.display_text && !res.message.plaintext) {
          res.message.display_text = content;
          res.message.plaintext = content;
        }
        res.message.status = "reassembled";
        appendMessageBubble(res.message);
        scrollToBottom();
        loadConversations();
      }
    } catch (err) {
      Utils.showToast(err.message, "error");
    }
  }

  if (sendBtnEl) {
    sendBtnEl.addEventListener("click", sendMessage);
  }

  if (chatInputEl) {
    chatInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    chatInputEl.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });
  }

  // 11. Share Conversation Link
  if (shareConvBtn) {
    shareConvBtn.addEventListener("click", async () => {
      if (!activeConversationId) return;
      try {
        const res = await Utils.apiFetch(`/api/links/conversation/${activeConversationId}`, {
          method: "POST",
        });
        if (res.share_url) {
          await Utils.copyToClipboard(res.share_url, "Conversation navigation link copied to clipboard!");
        }
      } catch (err) {
        Utils.showToast("Failed to generate link: " + err.message, "error");
      }
    });
  }

  // 12. Continuous Reactive Reconcile Loop (Every 3.5s)
  // Ensures real-time continuous rendering even during network blips or mobile switches
  setInterval(async () => {
    if (!activeConversationId) return;
    try {
      const res = await Utils.apiFetch(`/api/messages/conversation/${activeConversationId}`);
      if (res.success && Array.isArray(res.messages)) {
        let hasNew = false;
        res.messages.forEach((msg) => {
          if (!renderedMessageUuids.has(msg.message_uuid)) {
            appendMessageBubble(msg);
            hasNew = true;
          } else {
            // Reconcile message content (e.g. from pending to reassembled) and tick state
            appendMessageBubble(msg);
          }
        });
        if (hasNew) {
          scrollToBottom();
          markActiveConversationRead();
        }
      }
    } catch (_) {
      // Silent catch for background reconcile loop
    }
  }, 3500);

  // Background sidebar conversation list update (Every 8s)
  setInterval(async () => {
    try {
      await loadConversations();
    } catch (_) {}
  }, 8000);

  // Query parameter & sessionStorage handling for preselected / restored conversation
  const urlParams = new URLSearchParams(window.location.search);
  const targetConvId = urlParams.get("conv") || sessionStorage.getItem("active_conversation_id");

  loadConversations().then(() => {
    handleResponsiveLayout();
    if (targetConvId) {
      selectConversation(targetConvId);
    }
  });
});
