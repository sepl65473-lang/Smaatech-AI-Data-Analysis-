# Authentication setup

The app now uses FastAPI-backed authentication with scrypt password hashes, a persistent JSON auth record protected by the existing locked atomic file store, HttpOnly session cookies, CSRF token checks, account and IP failed-attempt limits, account lockout, password recovery OTPs, password changes, session revocation, administrator account APIs and security audit events.

The auth record is stored alongside the existing session JSON data (`00000000-0000-0000-0000-000000000001.json` by default). Docker Compose already mounts that directory to its persistent `session-data` volume. Keep that volume and use one application host/replica: the JSON store does not provide distributed locking, encryption at rest, managed backups or MongoDB compatibility. Render deployments need an explicitly configured persistent disk mounted at the data directory before relying on restart recovery.

## First administrator

Set `AUTH_ADMIN_EMAIL` and `AUTH_ADMIN_PASSWORD` in the backend's secret environment, not in React or a committed `.env` file. The password must have 12–128 characters, uppercase and lowercase letters, a number and a symbol. With the backend running, fetch `/api/auth/csrf` and POST `/api/auth/bootstrap` with the returned `sepl_csrf` cookie echoed in `X-CSRF-Token`. Bootstrap is one-time; remove `AUTH_ADMIN_PASSWORD` from the running environment after it succeeds. The password provided in the conversation does not meet the minimum policy; choose a replacement before bootstrapping.

Local HTTP only: set `AUTH_COOKIE_SECURE=false`. Keep it `true` behind HTTPS in deployments. Same-origin deployments should keep `AUTH_COOKIE_SAMESITE=lax`; separately hosted Vercel/Render frontend and API may require `AUTH_COOKIE_SAMESITE=none` with Secure cookies and matching CORS origins. Verify third-party cookie behavior in the target browsers before release. Set Vercel's non-secret `VITE_API_BASE_URL` to the backend's `/api` URL when the frontend and API are on different origins. `AUTH_REQUIRED` defaults to `true`; never turn it off outside isolated legacy tests.

## SMTP recovery

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` as backend secrets. Password recovery remains unavailable until SMTP is configured. The app does not claim email delivery until the SMTP send succeeds, and the workspace has not received a real email for verification. OTPs expire after 10 minutes, are hashed, limited to five guesses, and have a 60-second resend cooldown. Recovery failure is logged without codes or credentials.

## API outline

- Public: `GET /api/auth/csrf`, `POST /api/auth/login`, one-time `POST /api/auth/bootstrap`, and recovery request/verify/reset routes.
- Signed-in: `GET /api/auth/me`, logout, password change, session listing and own-session revocation.
- Administrator-only: `/api/auth/admin/users`, account status/role changes, unlock and audit reads.
- All other `/api/*` routes require a live session. Unsafe API requests require the CSRF header.

Initial verification is limited to the local backend and frontend. No production URL, SMTP credentials, deployment secrets or official separate SEPL logo/artwork files were available in this workspace. The login page follows the supplied screenshot layout, but its CSS-rendered emblem and analytics illustration are approximations based on the screenshot, not the original image assets. No MongoDB integration is present.
