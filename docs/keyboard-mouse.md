---
title: Keyboard & Mouse
parent: Reference
nav_order: 3
description: "All mouse and keyboard controls in ScoreSight's viewer, field list, panes and Training Dojo."
---

# Keyboard & Mouse

## Viewer

| Action | Control |
|---|---|
| Zoom in / out | **Ctrl + mouse wheel** (**⌘ Cmd + mouse wheel** on macOS), 0.33x to 3x |
| Fit picture to window | **1:1** button, or **Ctrl+0** |
| Scroll | Mouse wheel; scroll bars when zoomed in |
| Pan | Hold the **middle mouse button** and drag |
| Select a box | **Left-click** the box |
| Move a box | **Left-drag** the box |
| Resize a box | **Left-drag** an edge or a corner handle of the selected box |
| Deselect | **Left-click** empty space, or press **Esc** |
| Set 4-corner points | With **4-corner Correction** active, **left-click** four corners |
| Add a per-character sub-box | With **Per-character sub-boxes** on (in the Box tab's **Image cleanup**), click the green **+** in the box (experimental) |

Box positions and sizes are saved automatically.

## Field list

| Action | Control |
|---|---|
| Select a field (and its box) | Click its name or its value |
| The selected field's actions | **Right-click** it: Place on picture or Remove from picture, Rename..., Delete field..., Reset settings to defaults, Copy value, Zoom to box |
| Rename a custom field | Double-click its name, or **F2** |
| Add a custom field | **+** at the top of the list, or **Ctrl+N** |
| Delete the selected custom field | **Delete field** under the list, or **Del** (**Backspace** on a Mac; asks first) |
| Copy the selected field's value | **Ctrl+C** |
| Put the selected field on the picture | **Place on picture** under the list (in ScoreSight 0.1.x: **Add to Scene**) |
| Take the selected field off the picture | **Remove from picture** under the list (in 0.1.x: **Remove Selected**) |
| Deselect | **Esc** |

**F2**, **Del** and **Ctrl+C** work while the field list has the focus (click a field first).

## Panes

| Action | Control |
|---|---|
| Make the field list, the picture or the inspector wider | Drag the dividers between them |
| Hide or show the field list or the inspector | Double-click the divider next to it, or drag it to the window's edge |

ScoreSight remembers the widths and which panes are hidden. A click on an output in the status bar shows the inspector's **Outputs** tab, also when the inspector was hidden.

## Main window shortcuts

On macOS, use **⌘ Cmd** wherever this table says **Ctrl**. The tooltips of the buttons show their shortcut.

| Key | Action |
|---|---|
| **Ctrl + Shift + P** | Pause outputs / Resume outputs |
| **Ctrl + B** | Binary View on or off (once a source is open) |
| **Ctrl + 0** | Fit the picture to the window (the **1:1** button) |
| **F5** | Reload the sources (cameras and NDI) |
| **Ctrl + N** | New custom field |
| **Esc** | Deselect the box |

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

On Windows and Linux, the **File** menu is at the top of the main window. On macOS it is in the system menu bar. It includes:

- **Check for Updates** (asks GitHub for the latest release and always shows the result), **About**
- **View Current Log**
- **Import Configuration**, **Export Configuration**, **Open Configuration Folder**
- **OCR Training Data Setup**
- **Language**: each language is listed in its own language: English (US), Français, Español, Deutsch, Italiano, 日本語, 한국어, Nederlands, Polski, Português (Brasil), Português (Portugal), Русский and 简体中文. The current one is ticked, and the choice is remembered
- **Appearance**: System, Light or Dark colour scheme. The choice is remembered

On macOS, **About** is in the **ScoreSight** application menu (next to the Apple menu) instead of the **File** menu.
