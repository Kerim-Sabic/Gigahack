# Security boundaries

Bind API, model endpoint and Mailpit to loopback. Passwords are Argon2; sessions are random, server-side,
8-hour, HttpOnly and SameSite=Strict. HTTPS configuration sets Secure cookies. Mutations check CSRF tokens
and Origin. First setup requires loopback. Login rate limiting is per process/IP.
Meeting membership is required even for admins, including audio, evidence, search, exports and stream.
PDF requests block all resource fetching; deterministic escaped HTML is rendered by local Chromium.
Upload names never select storage paths. Audio decoding uses local file/pipe protocols, bounded duration,
size, and timeouts. Source content is untrusted. Models have no tool interface or recipient authority.

Prepared local files and offline library flags prevent automatic downloads. They are **not an OS sandbox**.
Kernel enforcement and a measured target-host offline interval remain unverified. Native dependencies
are trusted code and inherit host process permissions. Run under a dedicated least-privilege OS account.
Physical encryption, backup access and hospital integration are outside prototype acceptance.

Logs are local. General API errors use request IDs; stage raw model artifacts contain source content and
must receive the same protection as audio. Do not publish local runtime folders. Only synthetic fixtures
were used in development. Package/model licenses and notices are in manifests/. Dependency scans are
development-time checks; absence of reported advisories is not a security audit.

Mutating body requests require a valid Content-Length; chunked bodies are rejected before multipart parsing.
Uploads are bounded at 1 GiB plus multipart overhead; other POST/PUT/PATCH bodies at 8 MiB.
