# Security Policy

## Supported versions

Security fixes are made in the latest release only. Please make sure you can reproduce an issue with the [latest release](https://github.com/royshil/scoresight/releases/latest) (or `main`) before reporting it.

| Version | Supported |
|---|---|
| Latest release | ✔ |
| Older releases | ✘ (please upgrade) |

## Reporting a vulnerability

Please **do not** report security vulnerabilities in public issues, discussions or pull requests.

1. **Preferred**: use GitHub's private vulnerability reporting. Open the repository's [**Security** tab](https://github.com/royshil/scoresight/security) and choose **Report a vulnerability** (direct link: [new security advisory](https://github.com/royshil/scoresight/security/advisories/new)).
2. If private reporting isn't available, [open an issue](https://github.com/royshil/scoresight/issues/new/choose) that **only** says you have a security issue to report and asks a maintainer to contact you privately. Don't include any details in the issue.

Please include the affected version and platform, a description of the issue and its impact, and steps to reproduce. A proof of concept helps. ScoreSight is maintained by volunteers. We'll acknowledge your report as soon as we can, keep you informed, and credit you in the release notes unless you prefer otherwise.

## Download integrity

- Official builds are published **only** on [GitHub Releases](https://github.com/royshil/scoresight/releases).
- Every release lists SHA-256 checksums (`SHA256SUMS.txt`, or the release notes for older releases). Verify your download, for example with `Get-FileHash <file> -Algorithm SHA256` (Windows), `shasum -a 256 <file>` (macOS) or `sha256sum -c SHA256SUMS.txt` (Linux).
- The former project domain **`scoresight[.]live` (including its `download.` subdomain) is no longer controlled by the project.** ScoreSight 0.1.x and older still show links to it in the About and "Update Available" dialogs. Do not download anything from that domain, and upgrade to a current release, which no longer contains those links.
- The macOS app is signed and notarized by Apple in official releases. The Windows installer is not code-signed yet, so Windows SmartScreen shows a warning. Verify the checksum before choosing **Run anyway**.

## Network exposure

ScoreSight is a desktop app, but it opens network connections. Here's what to know:

### Built-in HTTP server

- ScoreSight starts an HTTP server automatically, listening on **all network interfaces (`0.0.0.0`) on port 18099** (or the port given with `--port`).
- It has **no authentication**, and CORS allows **any origin** (`*`). Anyone who can reach the port, including web pages open in a browser on your network, can read your current scoreboard readings, box names and box positions.
- The server is **read-only** from ScoreSight 0.2.0. Version 0.1.x and older also had an unauthenticated `GET /shutdown` endpoint that let any device that could reach the port close ScoreSight. Please upgrade.

**Recommendations:**

- Allow ScoreSight through your firewall on **private/trusted networks only**. When Windows asks, don't allow it on public networks.
- On untrusted networks (venue Wi-Fi, public networks), block inbound connections to the port in your firewall, or only use the server from the same computer (`localhost`).
- Don't forward the port on your router to the internet.

### Outbound connections

ScoreSight connects only to the destinations you configure:

- **OBS** (WebSocket, port 4455 by default), **vMix** (HTTP Web API, port 8088 by default), **overlays.uno** (HTTPS) and the **outbound HTTP API** (any URL you enter).
- `http://` and `ws://` connections are **unencrypted**. Use them only on trusted local networks, and prefer `https://` endpoints on the internet.
- NDI and RTSP sources are received over the network as configured in their senders.

### Stored credentials

- The settings file `scoresight.json` (see [Settings, Files & Command Line](https://royshil.github.io/scoresight/configuration.html)) stores the **OBS WebSocket password**, the **overlays.uno control URL** (which works like a password) and **outbound API URLs** (which may contain tokens) in **plain text**. Protect your user account and don't share this file.
- **File > Export Configuration** exports boxes only, without connection settings. Still check exported files before sharing them.
- Log files can contain host names, URLs and connection details. Check them before attaching them to a public issue.

## Scope

In scope: the ScoreSight application and its official release packages, the build and release workflows in this repository, and the documentation site.

Out of scope: vulnerabilities in third-party software (OBS, vMix, NDI, Qt, Tesseract and others; please report those upstream), and issues that need an attacker who already controls your computer or user account.
