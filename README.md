# SecureShare Messenger

> **Project Title:** Design and Implementation of a Secure Messaging Application Using Configurable Message Fragmentation and Cryptographic Secret Sharing  
> **Application Name:** SecureShare Messenger  
> **Backend Architecture:** Python 3.13, Flask, Flask-SocketIO, MongoDB Atlas, PyMongo, Cryptography, Argon2id  
> **Frontend Architecture:** HTML5, Modern Vanilla CSS3 Design System (Light/Dark Themes), Vanilla JavaScript (ES6+), Socket.io  
> **Zero-AI Guarantee:** Completely deterministic programming, conventional cryptographic libraries, and mathematical algorithms. Zero LLMs, neural networks, or AI APIs.

---

## 1. Overview & Objectives

**SecureShare Messenger** is an academic-grade secure messaging system engineered to demonstrate defense-in-depth principles through decoupled cryptographic and algorithmic techniques:
1. **Configurable Message Fragmentation (2 to 10 parts):** Payload ciphertext is deterministically partitioned at the byte level into exactly $N \in [2, 10]$ ordered, checksummed fragments. The recipient application delays plaintext rendering until 100% of valid fragments have arrived and passed SHA-256 and GCM authentication tag verification.
2. **Cryptographic Secret Sharing (Shamir's Scheme):** Independent of payload fragmentation, symmetric encryption keys can optionally be divided into $M$ shares with a threshold $K \le M$ over the prime field $\mathbb{F}_p$ ($p = 2^{256} + 297$). The message encryption key is recovered via Lagrange interpolation only when at least $K$ distinct valid shares are available to authorized participants.
3. **Decoupled Architecture Clarification:**
   - **AES-256-GCM** encrypts and authenticates message and payload data.
   - **Shamir's Secret Sharing (SSS)** divides and recovers the 256-bit symmetric encryption key; it is *not* an alternative message encryption algorithm.
   - **Message Fragmentation** distributes ciphertext slices; fragmentation itself does not encrypt data.
   - **Network Transport Security** (TLS/WSS) protects in-transit communications.

---

## 2. Targeted Features & Capabilities

### A. Centralized Security Configuration in Settings (`Settings → Secure Protocols`)
The chat screen is kept clean and focused on messaging. All protocol controls are managed in **Settings → Secure Protocols**:
- **Automatic Mode:** For each outgoing message, the system automatically uses cryptographically secure randomness (`secrets` CSPRNG) to select a valid fragment count ($N \in [2, 10]$) and decide whether SSS is enabled. If SSS is enabled, valid parameters $M \ge 2$ and $2 \le K \le M$ are selected. The chosen configuration is immutably recorded with the message so recipients process it reliably even if settings change later.
- **Custom Mode:** Allows users to explicitly select their preferred Message Fragment Count (2–10), toggle SSS, set Total Shares ($M \ge 2$), and set Recovery Threshold ($2 \le K \le M$). Inputs are validated both on the client and backend.

### B. UI Display and Privacy Preferences
- **Fragment Telemetry Toggle:** When ON, displays fragment count information on message bubbles (`Fragments: 8`). When OFF, hides fragment-count labels. Raw encryption keys or plaintext shares are never displayed.
- **Fragment Reassembly Status Toggle:** When ON, displays live reassembly status badges (`✓ Reassembled (N/N)` or `⏳ Waiting for missing fragments...`) and telemetry inspection. When OFF, hides status indicators without disabling internal validation.
- **Private Mode Toggle:** UI privacy override that hides all fragment badges, counts, and diagnostics from the chat interface while continuing to display message text/images, timestamps, and delivery ticks. Cryptographic authentication and integrity checks remain 100% active internally.

### C. Delivery and Read Receipts
Accurate, real-time message status indicators driven by verified server-side events:
- **Single Tick (`✓`):** Message accepted and persisted by the server.
- **Double Tick (`✓✓` grey):** Recipient client has received/fetched the message.
- **Blue Double Tick (`✓✓` blue):** Recipient has opened and read the message (updated in real-time via Socket.IO `messages_read`).

### D. Secure Image Sharing
- Users can select, preview, and send images (PNG, JPEG, GIF, WEBP) up to 5MB.
- **File Validation & Storage:** Validates MIME type and magic byte headers on the server; persists outside web roots in `instance/uploads/images/` using unguessable 128-bit hex identifiers.
- **Authorization Enforcement:** Participant membership in the conversation is checked on every download request; unauthorized users are strictly denied (HTTP 403).
- **7-Day Retention Policy:** Stored images older than 7 days are automatically expired and permanently deleted from disk and database upon access or background purge.

### E. Safe Clickable Link Sharing
- Messages containing URLs beginning with `http://` or `https://` are rendered as clickable links with a Follow Link action opening in a new tab (`target="_blank" rel="noopener noreferrer"`).
- **Zero SSRF:** Links are rendered entirely on the client side without server-side link fetching or scraping.
- **XSS Immunity:** Full HTML escaping is applied before URL detection; dangerous schemes such as `javascript:` and `data:` are neutralized.

### F. Post-Reassembly Fragment Metadata Purge (Storage Optimization)
- **Zero Space Bloat:** Once a message is received, verified, and reassembled, bulky transmission metadata (`message_fragments` base64 ciphertext slices and `message_shares` transient polynomial shares) are permanently purged from MongoDB Atlas.
- **Continuous History Preservation:** The reassembled message document, delivery receipts, timestamps, and image references remain permanently visible to both sender and recipient in their chat history.

### G. Right-Click Message Deletion Context Menu
- **Interactive Deletion:** Right-clicking any message bubble (text, link, or image) opens a modern context menu providing **Delete Message** and **Copy Text** actions.
- **Hard Resource Deletion & Real-Time Sync:** Deleting a message removes the record from `mongo.messages`, cascades deletion to any remaining fragments/shares, permanently unlinks the physical image file from `instance/uploads/images/`, and broadcasts the deletion event across all active screens via Socket.IO.

---

## 3. Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | Flask 3.1.x | Python web server & REST API |
| **Real-Time Transport** | Flask-SocketIO 5.7.x | Bidirectional WebSocket communication & room broadcasting |
| **Database** | MongoDB Atlas / PyMongo | Cloud document store with unique compound indexes |
| **Cryptography** | `cryptography` (hazmat) | AES-256-GCM authenticated cipher with 12-byte random nonces |
| **Secret Sharing** | Pure-Python SSS | Prime field $\mathbb{F}_p$ arithmetic & Lagrange polynomial interpolation |
| **Password Hashing** | `argon2-cffi` | Memory-hard Argon2id key derivation |
| **Automated Testing** | `pytest` + `mongomock` | 66 comprehensive unit and integration tests (100% pass rate) |
| **Frontend** | HTML5, Vanilla CSS3, JS | Responsive WhatsApp layout, persistent chat state, right-click context menu |

---

## 4. Directory Structure

```text
INS/
├── app.py                      # Main application entry point
├── config.py                   # Environment configuration (Dev, Test, Prod)
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── Report.md                   # Comprehensive academic college project report
├── .env.example                # Environment variable template
├── app/
│   ├── __init__.py             # Flask application factory
│   ├── database/
│   │   ├── db.py               # MongoDB Atlas connection manager & indexes
│   │   └── schema.py           # Schema initialization utilities
│   ├── models/
│   │   ├── user.py             # User document model with protocol_settings
│   │   ├── conversation.py     # Conversation document model
│   │   ├── message.py          # Message model with delivery_state and image metadata
│   │   ├── message_fragment.py # MessageFragment model with compound unique index
│   │   ├── message_share.py    # MessageShare model (Shamir key shares)
│   │   └── conversation_link.py# Shareable conversation link token model
│   ├── crypto/
│   │   ├── finite_field.py     # Prime field F_p arithmetic
│   │   ├── random_source.py    # Cryptographically secure random generators
│   │   ├── interpolation.py    # Polynomial evaluation & Lagrange interpolation
│   │   ├── shamir.py           # Shamir's Secret Sharing (split & recover)
│   │   ├── encryption.py       # AES-256-GCM encryption & decryption
│   │   ├── hashing.py          # SHA-256 integrity utilities
│   │   └── key_management.py   # Key share export & parsing
│   ├── services/
│   │   ├── auth_service.py     # User registration and 3-factor login
│   │   ├── profile_service.py  # Profile updates with ID preservation
│   │   ├── user_service.py     # User lookup and handle search
│   │   ├── conversation_service.py # Direct messaging conversation management
│   │   ├── message_service.py  # Orchestrates Automatic/Custom mode, encryption, delivery
│   │   ├── image_service.py    # Image upload, magic bytes, streaming & 7-day purge
│   │   ├── fragmentation_service.py # Deterministic byte-level payload fragmentation
│   │   ├── reassembly_service.py   # Out-of-order reassembly and hash verification
│   │   ├── delivery_service.py # Incremental fragment packet delivery
│   │   ├── account_service.py  # Password changes and hard deletion cascade
│   │   └── link_service.py     # Profile and chat navigation link generation
│   ├── realtime/
│   │   ├── connection_manager.py # Active socket session registry
│   │   └── socket_events.py    # WebSocket room and message events
│   ├── security/
│   │   ├── password_security.py# Argon2id hashing & verification
│   │   ├── session_security.py # Session management and login_required decorator
│   │   ├── authorization.py    # Participant authorization verification
│   │   └── rate_limiting.py    # In-memory sliding-window brute-force defense
│   ├── routes/
│   │   ├── auth_routes.py      # Registration & authentication
│   │   ├── profile_routes.py   # User profiles & handles
│   │   ├── chat_routes.py      # Chat views
│   │   ├── message_routes.py   # Messages, images & read receipts
│   │   └── settings_routes.py  # Protocol settings & account deletion
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── chat.html           # Clean input bar, image attach & lightbox modals
│   │   ├── settings.html       # Dedicated Secure Protocols card
│   │   └── ...
│   └── static/
│       ├── css/style.css       # Delivery ticks, image bubbles, modals & safe links
│       └── js/
│           ├── chat.js         # Chat controller with linkification & image sharing
│           └── socket_client.js# WebSocket client with messages_read handler
└── tests/                      # Automated test suite (63 tests)
```

---

## 5. Local Setup and Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Internet connection (for MongoDB Atlas) or local MongoDB instance

### Installation Steps

1. **Navigate to project directory:**
   ```bash
   cd c:\Users\cheta\Downloads\hemanth\INS
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and configure your MongoDB Atlas connection:
   ```env
   SECRET_KEY=your-super-secret-random-key-here
   FLASK_ENV=development
   MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/secureshare?retryWrites=true&w=majority
   MONGO_DB_NAME=secureshare
   PORT=5000
   HOST=127.0.0.1
   ```

4. **Run the Application:**
   ```bash
   python app.py
   ```
   Open your browser at **`http://127.0.0.1:5000`**.

---

## 6. Running Automated Tests

Run the full automated test suite using pytest:

```bash
python -m pytest tests -v
```

### Test Suite Results:
- **63 Passed in 5.44s (100% Pass Rate)**
- Tests cover Automatic & Custom protocol modes, fragment validation ($2 \le N \le 10$), Shamir Secret Sharing thresholds ($2 \le K \le M$), Telemetry & Private Mode UI overrides, Delivery & Read receipt transitions (`sent` $\to$ `delivered` $\to$ `read`), secure image sharing with 5MB cap & 7-day purge, and safe client-side URL linkification.
