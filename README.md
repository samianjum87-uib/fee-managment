---
title: AXIS School System
emoji: 🏫
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# AXIS School Management System

Multi‑tenant school fee management portal.

- **Dashboard** – view collections and pending fees
- **Student Management** – add, edit, view students
- **Fee Collection** – record payments, generate receipts
- **Reports** – financial analytics and defaulter lists

Built with Django + PostgreSQL.
## WebAuthn / biometric passkey setup

The staff portal uses WebAuthn for device-bound biometric authentication. For production, configure a secure origin and RP ID matching your deployed domain.

Required environment variables:

```bash
export WEBAUTHN_RP_ID="axis.example.com"
export WEBAUTHN_ORIGIN="https://axis.example.com"
export WEBAUTHN_RP_NAME="AXIS School Portal"
export WEBAUTHN_ALLOWED_ORIGINS="https://axis.example.com,https://www.axis.example.com"
```

Notes:

- Use HTTPS in production; localhost is accepted for local development only.
- The RP ID must be the effective domain, without protocol or port.
- The origin must include the full scheme, domain, and port.
- Browsers will reject passkey registration or login if the origin does not exactly match the expected WebAuthn origin.

The backend enforces platform authenticators and user verification for staff passkeys.
