---
title: Keyboard & Mouse
parent: Reference
nav_order: 3
description: "All mouse and keyboard controls in ScoreSight's viewer, field list and Training Dojo."
---

# Keyboard & Mouse

## Viewer

| Action | Control |
|---|---|
| Zoom in / out | **Ctrl + mouse wheel** (**⌘ Cmd + mouse wheel** on macOS), or **Ctrl+=** and **Ctrl+-**, up to 400% |
| Fit picture to window | **Fit**, or **Ctrl+0** |
| Scroll | Mouse wheel; scroll bars when zoomed in |
| Pan | Hold the **middle mouse button** and drag |
| Select a box | **Left-click** the box |
| Move a box | **Left-drag** the box |
| Resize a box | **Left-drag** an edge or a corner handle of the selected box |
| Nudge the selected box | **Arrow keys**: 1 pixel; **Shift + arrow keys**: 10 pixels (the viewer must have the keyboard: click the picture or the box) |
| Deselect | **Left-click** empty space, or press **Esc** |
| Set 4-corner points | After clicking **4-corner** (or **Redo corners…** in its menu), **left-click** four corners. **Esc** cancels and keeps the previous correction |
| Add a per-character sub-box | With **Composite (Per-Character)** on, click the green **+** in the box (experimental) |

Box positions and sizes are saved automatically.

## Field list

| Action | Control |
|---|---|
| Select a field (and its box) | Click its name or its value |
| Rename a custom field | Double-click its name |
| Add a custom field | **+** |
| Remove the selected custom field | **-** |
| Put the selected field on the picture | **Add to Scene ->** |
| Take the selected field off the picture | **Remove Selected** |
| Deselect | **Esc** |

## Main window shortcuts

On macOS, use **⌘ Cmd** wherever this table says **Ctrl**. The tooltips of the buttons show their shortcut.

| Key | Action |
|---|---|
| **Ctrl + Shift + P** | Pause outputs / Resume outputs |
| **Ctrl + B** | Binary View on or off (once a source is open) |
| **Ctrl + 0** | Fit the picture to the window (the **Fit** button) |
| **Ctrl + =** / **Ctrl + -** | Zoom in / out |
| **F5** | Reload the sources (cameras and NDI) |
| **Esc** | Cancel picking 4-corner points, or deselect the box |

## Training Dojo

On macOS, use **⌘ Cmd** wherever this table says **Ctrl**. The shortcuts work while you type in the annotation box.

| Key | Action |
|---|---|
| **Enter** | Approve and go to the next image |
| **Shift + Enter** | Previous image |
| **Up** / **Down** | Previous / next image |
| **Ctrl + Up** / **Ctrl + Down** | Previous / next unapproved image |
| **Ctrl + N** / **Ctrl + B** | Next / back |
| **Ctrl + U** | Remove the approval |

See [OCR Training Data](data_annotation.md).

## Menus

On Windows and Linux, the menus are at the top of the main window. On macOS they are in the system menu bar. Menu items show their shortcuts.

**File**:

- **Check for Updates** (asks GitHub for the latest release and always shows the result), **About**
- **View Current Log**
- **Import Configuration**, **Export Configuration**, **Open Configuration Folder**
- **Language**: each language is listed in its own language: English (US), Français, Español, Deutsch, Italiano, 日本語, 한국어, Nederlands, Polski, Português (Brasil), Português (Portugal), Русский and 简体中文. The current one is ticked, and the choice is remembered
- **Appearance**: System, Light or Dark colour scheme. The choice is remembered

**View**: **Binary View** (Ctrl+B), **Statistics overlay**, **Fit picture to window** (Ctrl+0), **Zoom in** (Ctrl+=) and **Zoom out** (Ctrl+-).

**Tools**: **Pause outputs** (Ctrl+Shift+P), **Reload sources** (F5), **Collect OCR training data** (on or off) and **OCR Training Data Setup** (see [OCR Training Data](data_annotation.md)).

On macOS, **About** is in the **ScoreSight** application menu (next to the Apple menu) instead of the **File** menu.
