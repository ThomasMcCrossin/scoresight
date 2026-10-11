"""Help > Keyboard shortcuts: a dialog that lists the main window's keys.

The keys of the menus and of the field list come from their actions (so the
list is always the one the window uses, written as the platform writes keys:
⌘ on macOS); the viewer's mouse and keys, which have no action, are added by
name.
"""

from collections.abc import Iterable

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

NATIVE = QKeySequence.SequenceFormat.NativeText


def action_name(action: QAction) -> str:
    """An action's text without its "&" mnemonic and trailing dots."""
    text = action.text().replace("&&", "\0").replace("&", "").replace("\0", "&")
    return text.rstrip(".…").strip()


def key_text(sequence: QKeySequence | str) -> str:
    """A key as the platform writes it (Ctrl+B, ⌘B on macOS)."""
    return QKeySequence(sequence).toString(NATIVE)


def action_rows(actions: Iterable[QAction]) -> list[tuple[str, str]]:
    """(name, keys) of the actions that have a shortcut, in their order; an
    action with several shortcuts lists them all."""
    rows = []
    for action in actions:
        keys = [key_text(shortcut) for shortcut in action.shortcuts()]
        keys = [key for key in keys if key]
        if keys:
            rows.append((action_name(action), ", ".join(keys)))
    return rows


def viewer_rows() -> list[tuple[str, str]]:
    """The viewer's keys and mouse controls, which no action has."""
    tr = QCoreApplication.translate
    ctrl = key_text("Ctrl+B").replace("B", "").rstrip("+") or "Ctrl"
    return [
        (
            tr("KeyboardShortcuts", "Zoom in or out"),
            tr("KeyboardShortcuts", "{ctrl} + mouse wheel").format(ctrl=ctrl),
        ),
        (
            tr("KeyboardShortcuts", "Move the picture"),
            tr("KeyboardShortcuts", "Drag with the middle mouse button"),
        ),
        (
            tr("KeyboardShortcuts", "Move the selected box by 1 pixel"),
            tr("KeyboardShortcuts", "Arrow keys"),
        ),
        (
            tr("KeyboardShortcuts", "Move the selected box by 10 pixels"),
            tr("KeyboardShortcuts", "Shift + arrow keys"),
        ),
        (
            tr("KeyboardShortcuts", "Deselect, or stop picking the 4 corners"),
            key_text("Esc"),
        ),
    ]


class KeyboardShortcutsDialog(QDialog):
    """The shortcuts in groups: (group title, [(name, keys), ...])."""

    def __init__(self, groups: list[tuple[str, list[tuple[str, str]]]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            QCoreApplication.translate("KeyboardShortcuts", "Keyboard shortcuts")
        )
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(
            [
                QCoreApplication.translate("KeyboardShortcuts", "Action"),
                QCoreApplication.translate("KeyboardShortcuts", "Keys"),
            ]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for title, rows in groups:
            if not rows:
                continue
            group = QTreeWidgetItem(self.tree, [title])
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            group.setFirstColumnSpanned(True)
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for name, keys in rows:
                item = QTreeWidgetItem(group, [name, keys])
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.tree.expandAll()
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        layout.addWidget(self.tree)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(520, 560)

    def rows(self) -> list[tuple[str, str, str]]:
        """(group, name, keys) of every row shown."""
        rows = []
        for index in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(index)
            for child in range(group.childCount()):
                item = group.child(child)
                rows.append((group.text(0), item.text(0), item.text(1)))
        return rows
