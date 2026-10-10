---
title: Installation
parent: Getting Started
nav_order: 1
description: "Download and install ScoreSight on Windows, macOS and Linux, verify the download, and grant permissions."
---

# Installation
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Download

Official builds are published **only** on the GitHub Releases page:

**[github.com/royshil/scoresight/releases/latest](https://github.com/royshil/scoresight/releases/latest)**

Under **Assets**, pick the file for your computer:

| Your computer | Download the file whose name contains |
|---|---|
| Windows 10/11, 64-bit | `windows` (installer `.exe`, or a `.zip` that contains the installer) |
| Mac with Apple Silicon (M1, M2, M3, M4...) | `macos-arm64` (`.dmg`) |
| Mac with an Intel processor | `macos-x64` or `macos-x86` (`.dmg`) |
| Linux, 64-bit x86_64 | `linux` (`.tar.gz` or `.tar`) |

{: .warning }
Do not download ScoreSight from any other website. The project's former website domain (`scoresight[.]live`) is **no longer controlled by the project**. ScoreSight 0.1.x and older still show links to it in the About and Update dialogs. Ignore those links.

Not sure which Mac you have? Open the Apple menu > **About This Mac**. If you see **Chip: Apple M...**, download `macos-arm64`. If you see **Processor: ... Intel**, download the Intel build.

## Verify your download (recommended)

Every release lists a SHA-256 checksum for each file (in `SHA256SUMS.txt` among the assets, or in the release notes of older releases). Compare it with the checksum of the file you downloaded:

Windows (PowerShell):
```powershell
Get-FileHash .\scoresight-*-windows*.exe -Algorithm SHA256
```

macOS:
```bash
shasum -a 256 ~/Downloads/scoresight-*.dmg
```

Linux (from the folder where you saved both the archive and `SHA256SUMS.txt`):
```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

If the checksum does not match, delete the file and download it again from the Releases page.

## Windows

1. Download the Windows installer from the [latest release](https://github.com/royshil/scoresight/releases/latest). If you downloaded a `.zip`, open it and extract `scoresight-setup.exe` first.

   ![The Windows .zip contains the installer, scoresight-setup.exe](image-5.png)

2. Run the installer. ScoreSight installs to `C:\Program Files\ScoreSight` by default and adds a Start menu shortcut.
3. **SmartScreen**: the installer is not code-signed yet, so Windows may show "Windows protected your PC". Click **More info** > **Run anyway**. Do this only for a file you downloaded from the GitHub Releases page and verified.
4. **Windows Firewall**: the first time ScoreSight starts, Windows may ask whether to allow it on the network. ScoreSight runs a small [HTTP server](http_server.md) on port 18099 that browsers and other software can read. Allow it on **Private networks** only, unless you need access from a public network. See [SECURITY.md](https://github.com/royshil/scoresight/blob/main/SECURITY.md).

### If your browser or antivirus blocks the download

ScoreSight is packaged with PyInstaller, and unsigned PyInstaller apps are sometimes flagged by antivirus heuristics as false positives:

![A browser reporting "Couldn't download - Virus detected"](image.png)

Do **not** turn off your antivirus or SmartScreen globally. Instead:

1. Make sure you downloaded the file from the [GitHub Releases page](https://github.com/royshil/scoresight/releases/latest) and that its [checksum matches](#verify-your-download-recommended).
2. In **Windows Security** > **Virus & threat protection** > **Protection history**, find the blocked item and choose **Restore** (or **Allow on device**) for that specific file only.
3. Report the false positive to Microsoft at [microsoft.com/wdsi/filesubmission](https://www.microsoft.com/wdsi/filesubmission) so future releases are not flagged.

### Uninstall (Windows)

Use **Settings** > **Apps** > **Installed apps** > **ScoreSight** > **Uninstall**. Your settings are kept. Delete the [settings folder](configuration.md#where-scoresight-keeps-its-files) too for a completely clean removal.

## macOS

1. Download the `.dmg` for your Mac (Apple Silicon or Intel, see [Download](#download)).
2. Double-click the `.dmg` and drag the ScoreSight app into **Applications**:

   ![Drag the ScoreSight app to the Applications folder](image-7.png)

3. Eject the disk image and start ScoreSight from **Applications** or Launchpad.

### Gatekeeper

Official releases are signed and notarized by Apple, so macOS opens them normally. If you run a build that is not notarized (for example a test build from a pull request) and macOS says it "cannot be opened because Apple cannot check it for malicious software":

1. Open **System Settings** > **Privacy & Security**.
2. Scroll down to the message about ScoreSight and click **Open Anyway**, then confirm.

Only do this for builds you trust.

### Permissions

macOS asks for permission the first time ScoreSight uses a protected feature. If you clicked **Don't Allow** by mistake, you can change it later in **System Settings** > **Privacy & Security**:

| Feature | Permission | Where to change it |
|---|---|---|
| USB cameras and capture cards | **Camera** | Privacy & Security > **Camera** > enable ScoreSight |
| Screen / window capture | **Screen Recording** | Privacy & Security > **Screen & System Audio Recording** (named **Screen Recording** on older macOS) > enable ScoreSight, then **quit and restart** ScoreSight |
| NDI sources, OBS/vMix on other computers | **Local Network** | Privacy & Security > **Local Network** > enable ScoreSight |

{: .tip }
If a camera shows a black picture or screen capture shows only the desktop wallpaper, a missing permission is almost always the cause.

### Apple Silicon vs Intel

The Apple Silicon (`arm64`) build runs natively on M-series Macs and is much faster there. The Intel build also runs on Apple Silicon through Rosetta 2, but more slowly. Install the one that matches your Mac.

### Uninstall (macOS)

Drag ScoreSight from **Applications** to the Trash. To also remove settings and logs, delete `~/Library/Application Support/scoresight` and `~/Library/Logs/scoresight`.

## Linux

1. Download the `linux` archive from the [latest release](https://github.com/royshil/scoresight/releases/latest) and extract it:

   ```bash
   mkdir -p ~/Applications && cd ~/Applications
   tar -xf ~/Downloads/scoresight-*linux*.tar*
   ```

2. Run the `scoresight` executable from the extracted files. Depending on the release, it is either `./scoresight/scoresight` (a folder) or `./scoresight` (a single file):

   ```bash
   ./scoresight/scoresight   # or: ./scoresight
   ```

3. **Cameras**: your user must be allowed to open `/dev/video*` devices. On most distributions that means being in the `video` group:

   ```bash
   sudo usermod -aG video "$USER"   # then log out and back in
   ```

4. **Qt platform plugin errors**: if ScoreSight exits with "Could not load the Qt platform plugin xcb", install the missing X11/xcb runtime libraries. On Debian/Ubuntu:

   ```bash
   sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1
   ```

{: .note }
Screen capture is not available on Linux. Use a capture card, NDI, or OBS's virtual camera to bring a screen into ScoreSight. See [Video Sources](sources.md).

## Upgrading

Install the new version over the old one (Windows), replace the app in Applications (macOS), or extract the new archive (Linux). Your boxes and settings live in a separate settings folder, so they carry over. See [Settings, Files & Command Line](configuration.md#where-scoresight-keeps-its-files).

{: .new }
ScoreSight 0.2.0 automatically moves a saved vMix port of `8099` to `8088`, the port of vMix's Web API. If you deliberately use a different port, check it in the **VMix** tab after upgrading.

## Next step

Continue with the [Quickstart](quickstart.md).
