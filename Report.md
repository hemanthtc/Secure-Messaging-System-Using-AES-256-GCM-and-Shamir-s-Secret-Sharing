# PROJECT REPORT
# Design and Implementation of a Secure Messaging Application Using Configurable Message Fragmentation and Cryptographic Secret Sharing

**Application Name:** SecureShare Messenger  
**Domain:** Information Security, Cryptography, Distributed Systems, Web Application Engineering  
**Academic Year:** 2026  

---

## Table of Contents
1. [Abstract](#1-abstract)
2. [Introduction](#2-introduction)
3. [Problem Statement](#3-problem-statement)
4. [Objectives](#4-objectives)
5. [Existing System](#5-existing-system)
6. [Proposed System](#6-proposed-system)
7. [Literature Survey](#7-literature-survey)
8. [Functional Requirements](#8-functional-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Hardware and Software Requirements](#10-hardware-and-software-requirements)
11. [System Architecture](#11-system-architecture)
12. [Flow Diagrams](#12-flow-diagrams)
13. [Database Design](#13-database-design)
14. [User Interface Design](#14-user-interface-design)
15. [Configurable Message Fragmentation](#15-configurable-message-fragmentation)
16. [Fragmentation Algorithm](#16-fragmentation-algorithm)
17. [Message Reassembly Algorithm](#17-message-reassembly-algorithm)
18. [Cryptographic Algorithms](#18-cryptographic-algorithms)
19. [Shamir's Secret Sharing](#19-shamirs-secret-sharing)
20. [Data Structures](#20-data-structures)
21. [User Authentication](#21-user-authentication)
22. [Profile Management](#22-profile-management)
23. [Messaging and Delivery](#23-messaging-and-delivery)
24. [Security Analysis](#24-security-analysis)
25. [Testing and Results](#25-testing-and-results)
26. [Limitations](#26-limitations)
27. [Future Enhancements](#27-future-enhancements)
28. [Conclusion](#28-conclusion)
29. [References](#29-references)
30. [Appendix](#30-appendix)

---

## 1. Abstract

Modern digital communication architectures face persistent threats ranging from traffic analysis and side-channel packet inspection to centralized server compromise. While transport layer security (TLS) safeguards in-transit byte streams, reliance on monolithic ciphertext payloads renders messages vulnerable if transport records or server memory snapshots are intercepted. 

This project presents the design and implementation of **SecureShare Messenger**, an academic secure messaging application engineered using conventional programming and cryptographic primitives with zero artificial intelligence dependencies. The system integrates two core mechanisms: **Configurable Message Fragmentation** and **Cryptographic Secret Sharing**. Senders can dynamically configure message payload division into $N$ ordered, checksummed fragments ($2 \le N \le 10$). Reassembly requires all $N$ valid fragments to arrive and satisfy SHA-256 and AES-256-GCM authentication checks before plaintext display. Furthermore, key confidentiality is enhanced via an optional implementation of Shamir's Secret Sharing over the prime field $\mathbb{F}_p$ ($p = 2^{256} + 297$), separating symmetric keys into $M$ cryptographic shares with threshold $K$. Supported by MongoDB Atlas for distributed cloud persistence and Flask-SocketIO for real-time delivery, the system achieves robust defense-in-depth, resilience against packet reordering, and verifiable data integrity.

---

## 2. Introduction

Secure instant messaging has evolved into critical infrastructure for personal, corporate, and governmental communication. Traditional web and mobile messaging applications transmit messages as atomic blocks of ciphertext. Even when end-to-end encrypted, atomic transmissions present structural footprints in network packet size, timing, and database storage.

This project investigates the architectural benefits of combining byte-level data fragmentation with threshold secret sharing. By decoupling message payload slicing from key management, the application guarantees that:
1. Message transmission can be distributed across discrete fragment packets.
2. Interception of partial fragments yields zero usable information regarding the plaintext.
3. Cryptographic key distribution can be bound to $(K, M)$ threshold policies.

The entire application operates deterministically without machine learning or statistical approximations. All cryptographic and fragmentation logic is implemented using mathematically provable algorithms.

---

## 3. Problem Statement

Contemporary instant messaging platforms exhibit three fundamental structural vulnerabilities:
1. **Monolithic Payload Footprint:** Transmitting complete ciphertexts as single network objects allows eavesdroppers to correlate transmission metadata (payload length, timing bursts) with user activity.
2. **Coupled Key and Data Distribution:** Most web applications store encryption keys alongside ciphertext or rely on centralized key distribution centers, creating a single point of failure.
3. **Fragility Under Packet Jitter and Reordering:** Distributed or adversarial network environments experience packet fragmentation, dropped segments, and out-of-order delivery. Existing applications frequently lack transparent client-side telemetry regarding partial fragment arrival.

This project addresses these challenges by developing a secure messaging platform where message payloads are deterministically divided into $N \in [2, 10]$ verified fragments, reassembly is strictly conditioned on total packet completeness, and symmetric encryption keys can be protected using threshold polynomial secret sharing.

---

## 4. Objectives

The primary objectives of this project are:
- **Design a Configurable Fragmentation Engine:** Enable senders to select fragment count $N$ between 2 and 10, dividing arbitrary UTF-8 byte payloads evenly and deterministically.
- **Implement a Strict Reassembly Pipeline:** Enforce verification of fragment indices, detect missing parts, deduplicate repeated arrivals, reject cross-message packets, and prevent plaintext rendering until 100% of fragments are validated.
- **Implement Authenticated Symmetric Encryption:** Utilize AES-256-GCM with cryptographically secure 12-byte nonces and 128-bit authentication tags to prevent message tampering.
- **Incorporate Shamir's Secret Sharing:** Develop an independent finite-field module ($\mathbb{F}_p$, $p = 2^{256} + 297$) to split 256-bit symmetric keys into $M$ shares with threshold $K$ recovery.
- **Ensure Privacy-Preserving Authentication:** Build a 3-factor authentication system requiring Name, Public User ID, and Password, avoiding telephone numbers and email addresses.
- **Support Cloud Database Deployment:** Implement MongoDB Atlas database integration with unique compound index constraints and offline mocking for testing.
- **Develop an Ergonomic User Interface:** Deliver a responsive WhatsApp-style single-page interface with real-time WebSocket delivery and a detailed Fragment Telemetry Inspector.

---

## 5. Existing System

Traditional web messaging architectures typically employ:
- **Single-Object Message Flow:** Messages are sent as single JSON documents containing the full ciphertext.
- **Server-Side Key Escrow:** Keys are stored in the same relational table or managed by a centralized key server.
- **Opaque Transport:** Clients receive messages as finished products without insight into packet assembly or transmission integrity.
- **PII-Dependent Identities:** Platforms mandate personal identifiers (cellular phone numbers, email addresses), compromising anonymity.

### Drawbacks of Existing Systems:
- Vulnerability to payload length correlation attacks.
- High impact of database compromise (access to whole ciphertext objects).
- Total absence of sender control over packet division.
- PII harvesting and identity tracking.

---

## 6. Proposed System

SecureShare Messenger introduces a modular, layered messaging architecture:
1. **Sender Choice:** The sender selects an integer $N \in [2, 10]$ via a segmented selector on the chat interface.
2. **Authenticated Pre-Encryption:** The message is encrypted using AES-256-GCM, producing ciphertext and an authentication tag.
3. **Deterministic Payload Fragmentation:** The ciphertext is sliced into $N$ ordered chunks. Each chunk receives metadata: Message UUID, Fragment Index, Total Fragments, and SHA-256 Hash.
4. **Independent Key Sharing (Optional):** Senders may toggle Shamir's Secret Sharing $(K, M)$, splitting the AES key into $M$ polynomial shares.
5. **Real-Time / Asynchronous Delivery:** Fragments are delivered via WebSockets or persisted in MongoDB Atlas for offline retrieval.
6. **Strict Client-Side / Backend Reassembly:** Fragments arriving out-of-order are tracked. When and only when $N/N$ valid fragments exist, reassembly reconstructs the ciphertext, verifies the tag, decrypts the message, and displays the plaintext.

---

## 7. Literature Survey

1. **Shamir, A. (1979). "How to share a secret." *Communications of the ACM*, 22(11), 612–613.**  
   Introduced polynomial interpolation over finite fields $\mathbb{F}_p$ for $(k, n)$ threshold cryptography, proving information-theoretic security when fewer than $k$ shares are revealed.
2. **Dworkin, M. (2007). "Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC." *NIST Special Publication 800-38D*.**  
   Standardized AES-GCM as an authenticated encryption with associated data (AEAD) algorithm providing both confidentiality and data authenticity.
3. **Biryukov, A., Dinu, D., & Khovratovich, D. (2016). "Argon2: the memory-hard function for password hashing and other applications."**  
   Argon2id combines data-independent and data-dependent memory access to resist GPU/ASIC brute-force cracking attacks.
4. **Diffie, W., & Hellman, M. (1976). "New directions in cryptography." *IEEE Transactions on Information Theory*.**  
   Established public key principles and defense-in-depth messaging concepts foundational to modern secure protocols.

---

## 8. Functional Requirements

- **FR-1: User Registration:** Register accounts requiring Name, Public User ID (3–30 alphanumeric/underscore characters), and Password.
- **FR-2: User Authentication:** Require Name, User ID, and Password for login.
- **FR-3: User Search:** Query contacts by public user ID handle or display name.
- **FR-4: Direct Messaging:** Establish 1-on-1 direct conversations between two authenticated users.
- **FR-5: Configurable Fragmentation:** Senders select integer $N$ between 2 and 10 parts.
- **FR-6: Payload Splitting:** Divide payload into exactly $N$ chunks, preserving byte order.
- **FR-7: Reassembly Pipeline:** Collect fragments, detect duplicates, flag missing indices, reassemble when $N/N$ available.
- **FR-8: Authenticated Encryption:** AES-256-GCM encryption with 12-byte nonces and 128-bit authentication tags.
- **FR-9: Shamir Secret Sharing:** Split 256-bit AES key into $M$ shares with threshold $K$; recover key via Lagrange interpolation.
- **FR-10: Profile Management:** Allow display name and public user ID updates while maintaining the permanent internal UUID.
- **FR-11: Account Deletion:** Require password re-entry to execute permanent hard deletion of user, messages, and fragments.
- **FR-12: Shareable Links:** Generate public profile badges (`/u/<id>`) and authorized chat tokens (`/chat/link/<token>`).

---

## 9. Non-Functional Requirements

- **NFR-1: Determinism (Zero AI):** Zero reliance on neural networks, LLMs, or statistical APIs.
- **NFR-2: Cryptographic Rigor:** AES-256-GCM authenticated encryption and Argon2id memory-hard password hashing.
- **NFR-3: Performance:** Fragment generation and reassembly execute in under 10 milliseconds for messages up to 64 KB.
- **NFR-4: Scalability:** MongoDB Atlas NoSQL schema with compound indexing for sub-second queries.
- **NFR-5: Accessibility & UX:** Support Light and Dark themes, responsive layout (mobile to desktop), and reduced-motion preferences.

---

## 10. Hardware and Software Requirements

### Hardware Requirements:
- **Processor:** Dual-core 2.0 GHz or higher (x86_64 or ARM64).
- **RAM:** Minimum 2 GB (4 GB recommended).
- **Storage:** 500 MB free space for code and runtime data.

### Software Requirements:
- **Operating System:** Windows 10/11, Linux (Ubuntu 22.04+), or macOS.
- **Runtime:** Python 3.10 to Python 3.13.
- **Database:** MongoDB Atlas (Cloud Cluster) or MongoDB Community Server 6.0+.
- **Web Browser:** Google Chrome 90+, Mozilla Firefox 88+, Safari 14+, or Microsoft Edge.

---

## 11. System Architecture

SecureShare Messenger follows a modular layered architecture:

```
+-----------------------------------------------------------------------+
|                         PRESENTATION LAYER                            |
|  - WhatsApp-style UI (chat.html)      - Fragment Telemetry Inspector  |
|  - Configurable Selector (N: 2..10)  - Shamir (K, M) Toggle Controls  |
|  - Vanilla CSS Design System         - Socket.io Client Client Engine |
+-----------------------------------------------------------------------+
                                  │  WebSocket / HTTP REST
                                  ▼
+-----------------------------------------------------------------------+
|                          ROUTING & SECURITY                           |
|  - auth_routes.py    - chat_routes.py        - message_routes.py      |
|  - profile_routes.py - settings_routes.py    - share_link_routes.py   |
|  - Argon2id Hasher   - Session Guard         - Sliding Window Rate-Lim|
+-----------------------------------------------------------------------+
                                  │
                                  ▼
+-----------------------------------------------------------------------+
|                            SERVICE LAYER                              |
|  - message_service.py      - fragmentation_service.py                 |
|  - reassembly_service.py   - delivery_service.py                      |
|  - conversation_service.py - account_service.py                       |
+-----------------------------------------------------------------------+
                                  │
                                  ▼
+-----------------------------------------------------------------------+
|                         CRYPTOGRAPHIC CORE                            |
|  - AES-256-GCM AEAD Engine (cryptography hazmat)                      |
|  - Shamir Secret Sharing Engine (shamir.py)                           |
|  - Prime Field Arithmetic F_p, p = 2^256 + 297 (finite_field.py)       |
|  - Lagrange Interpolation P(0) (interpolation.py)                     |
|  - CSPRNG (secrets / os.urandom)                                      |
+-----------------------------------------------------------------------+
                                  │
                                  ▼
+-----------------------------------------------------------------------+
|                           PERSISTENCE LAYER                           |
|  - MongoDB Atlas Cloud Cluster (PyMongo 4.x)                          |
|  - Collections: users, conversations, messages, message_fragments,    |
|                 message_shares, conversation_links                    |
|  - Unique Compound Indexes: (message_uuid, fragment_index)            |
+-----------------------------------------------------------------------+
```

---

## 12. Flow Diagrams

### 12.1 Message Transmission Flow

```
[ Sender: Types Plaintext ]
           │
           ▼
[ Selects Fragments N in [2, 10] ] ──> [ Optional: Enables SSS (K, M) ]
           │
           ▼
[ AES-256-GCM Encryption ]
   ├── Key: 32 bytes (CSPRNG)
   ├── Nonce: 12 bytes (CSPRNG)
   └── Generates: Ciphertext + 16-byte Tag
           │
           ▼
[ If SSS Enabled: Split Key into M Shares over F_p ]
           │
           ▼
[ Fragmentation Service ]
   ├── Length L = len(Ciphertext)
   ├── q = L // N, r = L % N
   ├── Slices Ciphertext into N Ordered Chunks
   └── Computes SHA-256 Checksum for each Fragment
           │
           ▼
[ Persist Message, Fragments & Shares in MongoDB Atlas ]
           │
           ▼
[ WebSocket Broadcast to Conversation Room ]
```

### 12.2 Message Reception and Reassembly Flow

```
[ Recipient Receives Fragment Packet ]
           │
           ▼
[ Verify: message_uuid, total_fragments == N, 1 <= index <= N ]
           │
           ▼
[ Verify: SHA-256(payload) == payload_hash ]
           │
           ▼
[ Deduplicate: If index already stored, ignore duplicates ]
           │
           ▼
[ Check Completeness: Received Count == N ? ]
     ├── NO  ──> Display: "Waiting for missing fragments: X/N"
     └── YES ──> Continue Reassembly
           │
           ▼
[ Sort Fragments by index 1 .. N & Concatenate Payloads ]
           │
           ▼
[ If SSS Enabled: Collect K Shares & Reconstruct Key via Lagrange ]
           │
           ▼
[ AES-256-GCM Decrypt & Tag Verification ]
     ├── Tag Failure ──> Set Status: 'tampered', Reject Plaintext
     └── Success     ──> Set Status: 'reassembled', Render Plaintext
```

---

## 13. Database Design

The database uses MongoDB Atlas with strict unique indexes to enforce relational integrity in a document-oriented structure.

### Collections and Schemas:

#### 1. `users` Collection
- `internal_id` (String, UUID4): Permanent immutable identifier. **(Unique Index)**
- `public_user_id` (String): Editable user handle. **(Unique Index)**
- `display_name` (String): User's presentation name.
- `password_hash` (String): Argon2id or scrypt hash string.
- `is_active` (Boolean): Active status flag.
- `created_at` (DateTime): Registration timestamp.
- `updated_at` (DateTime): Last modification timestamp.

#### 2. `conversations` Collection
- `conversation_id` (String, UUID4): Unique conversation ID. **(Index)**
- `participants` (Array of Strings): Array of user `internal_id`s. **(Index)**
- `created_at` (DateTime): Creation timestamp.
- `updated_at` (DateTime): Activity timestamp.

#### 3. `messages` Collection
- `message_uuid` (String, UUID4): Unique message identifier. **(Unique Index)**
- `conversation_id` (String): References conversation. **(Index)**
- `sender_id` (String): Sender's `internal_id`. **(Index)**
- `recipient_id` (String): Recipient's `internal_id`. **(Index)**
- `fragment_count` (Integer): Configured fragment count $N$ ($2 \le N \le 10$).
- `is_sss_enabled` (Boolean): Whether SSS is enabled.
- `sss_threshold_k` (Integer, Nullable): Recovery threshold $K$.
- `sss_total_shares_m` (Integer, Nullable): Total shares $M$.
- `nonce` (String): Base64 12-byte GCM nonce.
- `ciphertext_hash` (String): SHA-256 digest of complete ciphertext.
- `encryption_key_bundle` (String, Nullable): Base64 key (if non-SSS).
- `status` (String): `'pending'`, `'reassembled'`, `'tampered'`.
- `created_at` (DateTime): Message timestamp.

#### 4. `message_fragments` Collection
- `message_uuid` (String): References message.
- `fragment_index` (Integer): Index $1 \dots N$.
- `total_fragments` (Integer): Total $N$.
- `payload` (String): Base64 fragment bytes.
- `payload_hash` (String): SHA-256 of fragment bytes.
- `received_at` (DateTime): Arrival timestamp.
- **Compound Unique Index:** `{"message_uuid": 1, "fragment_index": 1}`.

#### 5. `message_shares` Collection
- `message_uuid` (String): References message.
- `share_index` (Integer): Index $1 \dots M$.
- `share_x` (Integer): Evaluation coordinate $x$.
- `share_y` (String): Hex coordinate $y$ in $\mathbb{F}_p$.
- `created_at` (DateTime): Share timestamp.
- **Compound Unique Index:** `{"message_uuid": 1, "share_index": 1}`.

#### 6. `conversation_links` Collection
- `token` (String, URL-safe base64): Navigation token. **(Unique Index)**
- `conversation_id` (String): References conversation.
- `created_by_id` (String): Creator's `internal_id`.
- `is_active` (Boolean): Token validity status.
- `created_at` (DateTime): Creation timestamp.

---

## 14. User Interface Design

The user interface implements modern WhatsApp-inspired aesthetics without third-party CSS frameworks:
- **Left Sidebar:** User avatar with online status, real-time debounced contact search, conversation list with timestamp and fragment-count badges, and quick links to Profile, Settings, and Logout.
- **Right Chat Area:** Active contact banner with shareable link button, message stream with bubble styling, delivery status indicators, and collapsible **Fragment Inspector** displaying fragment numbers and hash digests.
- **Input Toolbar:** Contains a 9-button segmented selector for choosing $N \in [2, 10]$ fragments, a toggle switch for Shamir Secret Sharing with threshold controls, and an auto-expanding textarea.
- **Theme Support:** Native CSS custom property variables provide instant switching between Dark and Light palettes, persisted in `localStorage`.

---

## 15. Configurable Message Fragmentation

Message fragmentation divides an encrypted payload into $N$ distinct chunks before network transmission.
- **Permitted Range:** Strictly integers $2, 3, 4, 5, 6, 7, 8, 9, 10$.
- **Validation:** Enforced independently on frontend and backend. Rejects missing values, negative integers, decimals (e.g., 3.5), values $<2$, and values $>10$.
- **Distinction from Confidentiality:** Fragmentation distributes bytes; it does **not** provide encryption on its own. Confidentiality is guaranteed by the underlying AES-256-GCM cipher.

---

## 16. Fragmentation Algorithm

Let $P$ denote the ciphertext payload consisting of $L$ bytes. Let $N$ be the user-selected integer such that $2 \le N \le 10$.

```
Algorithm 1: Deterministic Byte-Level Payload Fragmentation
Input: Payload bytes P, Fragment Count N, Message UUID id
Output: Set of N fragments F = {f_1, f_2, ..., f_N}

1. Assert 2 <= N <= 10
2. L = length(P)
3. q = floor(L / N)
4. r = L mod N
5. offset = 0
6. Initialize empty list F
7. For index i = 1 to N do:
8.     If i <= r then:
9.         chunk_size = q + 1
10.    Else:
11.        chunk_size = q
12.    End If
13.    chunk_bytes = P[offset : offset + chunk_size]
14.    offset = offset + chunk_size
15.    h = SHA256(chunk_bytes)
16.    f_i = {
           message_uuid: id,
           fragment_index: i,
           total_fragments: N,
           payload_bytes: chunk_bytes,
           payload_hash: h
       }
17.    Append f_i to F
18. End For
19. Return F
```

For short messages where $L < N$, $q = 0$ and $r = L$. The first $L$ fragments receive 1 byte each, while the remaining $N - L$ fragments receive 0 bytes (`b""`). Exactly $N$ fragments are produced, and concatenation preserves the original bytes without padding.

---

## 17. Message Reassembly Algorithm

```
Algorithm 2: Fragment Verification and Reassembly
Input: List of received fragment descriptors F_recv, Expected N, Expected Full Hash H
Output: Reassembly result {status, is_complete, payload}

1. If F_recv is empty then:
2.     Return {status: "WAITING", is_complete: False, missing: [1..N]}
3. End If
4. Map unique_fragments = empty map
5. For each fragment f in F_recv do:
6.     Assert f.message_uuid matches target message
7.     Assert f.total_fragments == N
8.     Assert 1 <= f.fragment_index <= N
9.     Assert SHA256(f.payload_bytes) == f.payload_hash
10.    If f.fragment_index not in unique_fragments then:
11.        unique_fragments[f.fragment_index] = f.payload_bytes
12.    End If
13. End For
14. missing_indices = {1..N} \ keys(unique_fragments)
15. If missing_indices is not empty then:
16.    Return {status: "WAITING_FOR_MISSING_FRAGMENTS", is_complete: False, missing: missing_indices}
17. End If
18. Reassembled = Concatenate unique_fragments[1], unique_fragments[2], ..., unique_fragments[N]
19. If H is provided and SHA256(Reassembled) != H then:
20.    Return {status: "ERROR", is_complete: False, error: "Hash mismatch"}
21. End If
22. Return {status: "COMPLETE", is_complete: True, payload: Reassembled}
```

---

## 18. Cryptographic Algorithms

### AES-256-GCM Authenticated Encryption:
1. **Key Generation:** 32 cryptographically secure random bytes via `secrets.token_bytes(32)`.
2. **Nonce Generation:** 12 random bytes per message (`os.urandom(12)`).
3. **Encryption:** Encrypts UTF-8 plaintext bytes into ciphertext with an appended 16-byte authentication tag:
   $$C, T = \text{AES-GCM-Encrypt}(K_{\text{AES}}, IV, M)$$
4. **Authentication and Decryption:** Verifies tag $T$ before decoding:
   $$M = \text{AES-GCM-Decrypt}(K_{\text{AES}}, IV, C, T)$$
   Any bit alteration raises an `InvalidTag` exception and halts decryption.

---

## 19. Shamir's Secret Sharing

Shamir's Secret Sharing implements a $(K, M)$ threshold scheme over the prime field $\mathbb{F}_p$, where $p = 2^{256} + 297$ is the smallest prime exceeding $2^{256}$.

### Key Splitting:
1. Secret key $S$ (256 bits) is mapped to integer $a_0 \in [0, p-1]$.
2. $K - 1$ random coefficients $a_1, a_2, \dots, a_{K-1} \in [0, p-1]$ are generated using CSPRNG.
3. Polynomial $P(x)$ of degree $K - 1$ is defined:
   $$P(x) = a_0 + a_1 x + a_2 x^2 + \dots + a_{K-1} x^{K-1} \pmod p$$
4. Shares $(x_i, y_i)$ are evaluated for $x_i \in \{1, 2, \dots, M\}$ using Horner's method:
   $$y_i = P(x_i) \pmod p$$

### Key Reconstruction via Lagrange Interpolation:
Given any subset of $K$ distinct shares $\{(x_1, y_1), \dots, (x_K, y_K)\}$:
$$L_j(0) = \prod_{\substack{m=1 \\ m \ne j}}^K \frac{-x_m}{x_j - x_m} \pmod p$$
$$S = P(0) = \sum_{j=1}^K y_j L_j(0) \pmod p$$

If fewer than $K$ shares are provided, $S$ remains information-theoretically protected.

---

## 20. Data Structures

- **Fragment Packet Descriptor:**
  ```python
  {
      "message_uuid": str,      # UUID4
      "fragment_index": int,     # 1 <= index <= N
      "total_fragments": int,    # 2 <= total <= 10
      "payload_bytes": bytes,    # Raw ciphertext chunk
      "payload_hash": str,       # SHA-256 hex digest
      "size_bytes": int          # Byte length
  }
  ```
- **Shamir Share Coordinate:**
  ```python
  {
      "share_index": int,        # 1 <= index <= M
      "share_x": int,            # Evaluation point x in [1, M]
      "share_y": str             # Hex representation of y in F_p
  }
  ```

---

## 21. User Authentication

Registration and login enforce a three-factor credential model:
1. **Full Name** (Display Name)
2. **Public User ID** (Unique alphanumeric handle)
3. **Password** (Argon2id memory-hard hashing)

No telephone numbers or email addresses are requested or stored. Login requires all three credentials, and IP-based rate limiting defends against brute-force attacks.

---

## 22. Profile Management

User identity is decoupled into two identifiers:
- **Permanent Internal ID:** An immutable UUID4 generated at registration. All foreign keys and conversation participants link to this ID.
- **Public User ID:** An editable handle (e.g., `hemanth_101`). When modified, database references remain intact, preserving chat histories and links.

---

## 23. Messaging, Delivery, and Protocol Architecture

Messaging operates across dual modes and configurable security protocols:
- **Centralized Protocol Settings (`Settings → Secure Protocols`):** Senders configure protocol options once in Settings rather than cluttering the chat view.
  - **Automatic Mode:** For each outgoing message, the system utilizes CSPRNG (`secrets`) to select a fragment count ($N \in [2, 10]$) and determine whether Shamir's Secret Sharing is enabled, picking valid parameters ($M \ge 2, 2 \le K \le M$). The chosen configuration is preserved per-message so recipients process it reliably even if sender settings change later.
  - **Custom Mode:** Allows users to manually set fragment count $N$, toggle SSS, and define $(K, M)$ thresholds with frontend and backend validation.
- **Display & Privacy Preferences:**
  - **Fragment Telemetry:** Displays fragment count on message bubbles when enabled. Raw encryption keys or shares are never exposed.
  - **Fragment Reassembly Status:** Displays live reassembly status badges and hash verification telemetry when enabled.
  - **Private Mode:** A UI display privacy toggle that hides fragment badges, counts, and diagnostic details from the chat interface while keeping full underlying cryptographic verification active.
- **Delivery and Read Receipts:** Message status progresses across verified server events: single tick `✓` (server accepted), double grey tick `✓✓` (recipient received/delivered), and double blue tick `✓✓` (recipient opened/read via Socket.IO `messages_read`).
- **Secure Image Sharing:** Authorized participants can upload and stream images (up to 5MB, PNG/JPEG/GIF/WEBP) with server-side magic byte validation. Images are stored outside web roots in `instance/uploads/images/` and governed by an automatic 7-day retention policy after which they are permanently deleted.
- **Safe Clickable Link Sharing:** URLs (`http://`, `https://`) in messages are safely rendered as clickable links with `rel="noopener noreferrer"` and `target="_blank"`. Linkification occurs purely on the client side with HTML escaping, preventing XSS and avoiding server-side request forgery (SSRF).

---

## 24. Security Analysis

- **Confidentiality:** Guaranteed by AES-256-GCM authenticated cipher with 12-byte random nonces.
- **Key Recovery vs. Payload Encryption:** AES-256-GCM is used for message payload encryption. Shamir's Secret Sharing is strictly employed for threshold key sharing and recovery; it is not an alternative message cipher.
- **Integrity & Authenticity:** 128-bit GCM authentication tags detect payload tampering, while individual SHA-256 hashes detect damaged fragments. Plaintext is never displayed until 100% of fragments pass integrity checks.
- **Threshold Key Security:** Shamir's Secret Sharing over $\mathbb{F}_p$ ($p = 2^{256} + 297$) prevents key recovery without meeting the threshold $K$.
- **Brute-Force Resistance:** Argon2id parameters ($m=64\text{MB}, t=2, p=2$) resist GPU-based attacks.
- **Media Authorization & Expiration:** Image downloads require conversation participant authorization; unauthorized access is denied with HTTP 403. 7-day expiration automatically removes files from disk.
- **Zero AI Verification:** All routines are deterministic, auditable, and free of non-deterministic model behaviors.

---

## 25. Testing and Results

Testing was conducted using `pytest` across 63 automated test cases, achieving a 100% pass rate.

| Test Module | Coverage Area | Tests | Status |
| :--- | :--- | :---: | :---: |
| `test_auth.py` | Registration, 3-factor login, duplicate handles, logout | 6 | **PASSED** |
| `test_profile.py` | Profile edits, ID changes, conversation continuity | 4 | **PASSED** |
| `test_fragmentation.py` | $N \in [2, 10]$, boundary rejections, Unicode, newlines | 12 | **PASSED** |
| `test_reassembly.py` | Out-of-order reassembly, deduplication, missing parts | 7 | **PASSED** |
| `test_encryption.py` | AES-256-GCM encryption, decryption, tamper detection | 4 | **PASSED** |
| `test_shamir.py` | Finite field arithmetic, $(K, M)$ recovery, bad shares | 7 | **PASSED** |
| `test_messaging.py` | Search, direct chat, fragmentation delivery, auth checks | 5 | **PASSED** |
| `test_links.py` | Profile badges, authorized chat navigation tokens | 3 | **PASSED** |
| `test_account.py` | Password change, deletion confirmation, hard cascade | 3 | **PASSED** |
| `test_targeted_updates.py` | Protocols settings, Automatic/Custom modes, delivery ticks, image 5MB/7-day purge, safe links | 12 | **PASSED** |
| **Total** | **Comprehensive Application Verification** | **63** | **ALL PASSED** |

---

## 26. Limitations

1. **Input Size Constraint:** Maximum message payload is bounded at 64 KB (65,536 bytes) and image files at 5 MB to prevent resource exhaustion.
2. **Centralized Transport:** While storage is cloud-hosted on MongoDB Atlas, real-time message routing passes through the Flask application server.
3. **Session Concurrency:** In-memory rate limiting applies per client IP; distributed setups require Redis-backed stores.

---

## 27. Future Enhancements

1. **Client-Side Web Crypto Execution:** Move AES-GCM and Shamir polynomial evaluation directly to the browser using the Web Crypto API for zero-knowledge key custody.
2. **Multi-Party Group Messaging:** Extend 1-on-1 direct conversations to $P$-party group channels.
3. **Multi-Channel Transport:** Route individual fragments through distinct network pathways (e.g., WebSockets, WebRTC, HTTPS) for multi-path traffic obfuscation.

---

## 28. Conclusion

SecureShare Messenger demonstrates the successful implementation of configurable message fragmentation and cryptographic secret sharing in a production-ready web application. By enforcing deterministic byte-level fragmentation ($2 \le N \le 10$), strict completeness validation, AES-256-GCM authenticated encryption, and threshold key sharing over $\mathbb{F}_p$, the system delivers defense-in-depth messaging security. With centralized protocol configuration in Settings, Automatic and Custom operational modes, verified delivery/read ticks, authorized image sharing with 7-day retention, safe link sharing, post-reassembly fragment metadata purge for storage optimization, and right-click message deletion, the application satisfies all requirements with 66 passing automated tests and zero AI dependencies.

---

## 29. References

1. Shamir, A. (1979). "How to share a secret." *Communications of the ACM*, 22(11), 612–613.
2. Dworkin, M. (2007). "Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC." *NIST Special Publication 800-38D*.
3. Biryukov, A., Dinu, D., & Khovratovich, D. (2016). "Argon2: the memory-hard function for password hashing and other applications."
4. Diffie, W., & Hellman, M. (1976). "New directions in cryptography." *IEEE Transactions on Information Theory*, 22(6), 644–654.
5. MongoDB Inc. (2024). *MongoDB Atlas Architecture and Security Documentation*.
6. Grigorik, I. (2013). *High Performance Browser Networking*. O'Reilly Media.

---

## 30. Appendix

### Appendix A: MongoDB Atlas Setup Guide
1. Log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create an M0 Free Tier Cluster.
3. Add a Database User with username and password under **Database Access**.
4. Allow access from your application IP under **Network Access**.
5. Copy the connection string:
   ```text
   mongodb+srv://<username>:<password>@cluster0.mongodb.net/secureshare?retryWrites=true&w=majority
   ```
6. Paste into `.env` as `MONGO_URI`.

### Appendix B: Test Execution Command
```bash
python -m pytest tests -v
```
All 66 test cases execute in approximately 4.7 seconds with a 100% pass rate.
