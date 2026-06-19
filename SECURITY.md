# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v1.0.0-beta | ✅ Active |

## Reporting a Vulnerability

ErnosDecent is a cryptographic system. Security vulnerabilities are treated with the highest priority.

### How to Report

**DO NOT open a public issue for security vulnerabilities.**

Instead, email: **security@ernosdecent.org**

Include:
- **Description** of the vulnerability
- **Module** affected (e.g., `decent_id/keys.ep`, `decent_net/noise.ep`)
- **Steps to reproduce** — exact commands and inputs
- **Impact assessment** — what an attacker could achieve
- **Suggested fix** (if you have one)

### Response Timeline

- **Acknowledgement**: Within 48 hours
- **Initial assessment**: Within 7 days
- **Fix or mitigation**: Depends on severity, targeting 30 days for critical issues

### Scope

The following areas are in scope for security reports:

| Area | Priority | Examples |
|------|----------|---------|
| Cryptographic primitives | **Critical** | Key derivation flaws, nonce reuse, weak randomness |
| Identity & authentication | **Critical** | DID forgery, session token bypass, capability escalation |
| Network protocol | **High** | Noise handshake downgrade, DHT poisoning, relay deanonymisation |
| Smart contracts | **High** | State manipulation, unauthorised minting, REVERT bypass |
| Onion routing | **High** | Timing attacks, circuit correlation, exit node compromise |
| Storage | **Medium** | Hash collision exploitation, CRDT merge corruption |
| Messaging | **Medium** | Message forgery, channel key leakage |

### Responsible Disclosure

We follow a coordinated disclosure model:

1. Reporter submits vulnerability privately
2. We confirm and assess the issue
3. We develop and test a fix
4. We release the fix and credit the reporter (unless anonymity is requested)
5. Full details are published after users have had time to update

### Recognition

Security researchers who responsibly disclose vulnerabilities will be:
- Credited in the changelog and release notes (with permission)
- Added to a SECURITY_ACKNOWLEDGEMENTS.md file
- Thanked publicly in project communications

---

## Cryptographic Dependencies

ErnosDecent relies on [libsodium](https://doc.libsodium.org/) for all cryptographic primitives:

| Primitive | Algorithm | Library |
|-----------|-----------|---------|
| Signing | Ed25519 | libsodium |
| Key exchange | X25519 | libsodium |
| Symmetric encryption | XChaCha20-Poly1305 | libsodium |
| Key derivation | HKDF-SHA256 | libsodium |
| Password hashing | Argon2id | libsodium |
| Content hashing | BLAKE3 | Pure Ernos implementation |
| Wallet seed | PBKDF2-HMAC-SHA512 | Pure Ernos implementation |

No custom cryptography is used. All implementations follow published standards and use well-audited libraries.

---

*Maria Smith. Scotland. 2026.*
