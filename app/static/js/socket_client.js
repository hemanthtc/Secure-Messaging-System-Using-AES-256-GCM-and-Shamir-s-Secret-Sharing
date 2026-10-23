/**
 * SecureShare Messenger - Socket.io Real-time Client Module
 * Manages WebSocket connection lifecycle and event dispatching.
 */

class SocketClient {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.currentRoom = null;
    this.pendingRooms = new Set();
    this.messageCallbacks = [];
    this.conversationUpdateCallbacks = [];
    this.messagesReadCallbacks = [];
    this.messageDeletedCallbacks = [];
  }

  connect() {
    if (typeof io === "undefined") {
      console.warn("Socket.io library not loaded; falling back to HTTP polling.");
      return;
    }

    this.socket = io({
      transports: ["polling", "websocket"],
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 1000,
    });

    this.socket.on("connect", () => {
      this.connected = true;
      console.log("[Socket] Connected to SecureShare Messenger real-time server.");

      // Automatically join current active room or flush pending rooms
      if (this.currentRoom) {
        this.socket.emit("join_conversation", { conversation_id: this.currentRoom });
      }
      this.pendingRooms.forEach((convId) => {
        this.socket.emit("join_conversation", { conversation_id: convId });
      });
      this.pendingRooms.clear();
    });

    this.socket.on("disconnect", () => {
      this.connected = false;
      console.log("[Socket] Disconnected from server.");
    });

    this.socket.on("new_message", (messageData) => {
      this.messageCallbacks.forEach((cb) => cb(messageData));
    });

    this.socket.on("conversation_updated", (updateData) => {
      this.conversationUpdateCallbacks.forEach((cb) => cb(updateData));
    });

    this.socket.on("messages_read", (readData) => {
      this.messagesReadCallbacks.forEach((cb) => cb(readData));
    });

    this.socket.on("message_deleted", (delData) => {
      this.messageDeletedCallbacks.forEach((cb) => cb(delData));
    });
  }

  joinConversation(conversationId) {
    if (!conversationId) return;
    this.currentRoom = conversationId;
    if (this.socket && this.connected) {
      this.socket.emit("join_conversation", { conversation_id: conversationId });
    } else {
      this.pendingRooms.add(conversationId);
    }
  }

  leaveConversation(conversationId) {
    if (this.currentRoom === conversationId) {
      this.currentRoom = null;
    }
    this.pendingRooms.delete(conversationId);
    if (this.socket && this.connected) {
      this.socket.emit("leave_conversation", { conversation_id: conversationId });
    }
  }

  onNewMessage(callback) {
    this.messageCallbacks.push(callback);
  }

  onConversationUpdated(callback) {
    this.conversationUpdateCallbacks.push(callback);
  }

  onMessagesRead(callback) {
    this.messagesReadCallbacks.push(callback);
  }

  onMessageDeleted(callback) {
    this.messageDeletedCallbacks.push(callback);
  }
}

window.socketClient = new SocketClient();

