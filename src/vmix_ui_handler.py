from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import QCoreApplication, Qt

from text_detection_target import TextDetectionTarget
from ui_mainwindow import Ui_MainWindow
from vmix_output import DEFAULT_VMIX_PORT, VMIX_TCP_API_PORT, VMixAPI
from sc_logging import logger
from storage import fetch_data, store_data

SETTINGS_FILE = "scoresight.json"


def migrate_vmix_port():
    """One-time migration: older versions defaulted the vMix port to 8099, vMix's
    TCP API, which ScoreSight can't talk to (#55). Change a stored 8099 to the
    Web API port 8088 once; a port the user sets later is left alone."""
    if fetch_data(SETTINGS_FILE, "vmix_port_migrated", False):
        return
    if str(fetch_data(SETTINGS_FILE, "vmix_port", "")).strip() == VMIX_TCP_API_PORT:
        store_data(SETTINGS_FILE, "vmix_port", DEFAULT_VMIX_PORT)
        logger.info(
            "vMix port changed from %s (vMix TCP API) to %s (vMix Web API, used "
            "by ScoreSight)",
            VMIX_TCP_API_PORT,
            DEFAULT_VMIX_PORT,
        )
    store_data(SETTINGS_FILE, "vmix_port_migrated", True)


def mapping_from_model(model: QStandardItemModel) -> dict[str, str]:
    """{box name: vMix field name} from the mapping table's model."""
    mapping = {}
    for i in range(model.rowCount()):
        item = model.item(i, 0)
        value = model.item(i, 1)
        if item and value:
            mapping[item.text()] = value.text()
    return mapping


class VMixUIHanlder:
    def __init__(self, ui: Ui_MainWindow):
        self.ui = ui
        self.vmixUpdater = None
        self.vmixUiSetup()

    def globalSettingsChanged(self, settingName, value):
        store_data(SETTINGS_FILE, settingName, value)

    def vmixConnectionChanged(self):
        # Update the existing updater: recreating it lost the field mapping and
        # stopped the output while the button still said "Stop".
        host = self.ui.lineEdit_vmixHost.text().strip()
        port = self.ui.lineEdit_vmixPort.text().strip()
        input_number = self.ui.inputLineEdit_vmix.text().strip()
        self.vmixUpdater.set_connection(host, port, input_number)
        for name, value in (
            ("vmix_host", host),
            ("vmix_port", port),
            ("vmix_input", input_number),
        ):
            if fetch_data(SETTINGS_FILE, name) != value:
                self.globalSettingsChanged(name, value)

    def vmixMappingChanged(self, *_):
        # store entire mapping data in scoresight.json
        model = self.ui.tableView_vmixMapping.model()
        if isinstance(model, QStandardItemModel):
            mapping = mapping_from_model(model)
            self.globalSettingsChanged("vmix_mapping", mapping)
            self.vmixUpdater.set_field_mapping(mapping)
        else:
            logger.error("vmixMappingChanged: model is not a QStandardItemModel")

    def vmixUiSetup(self):
        migrate_vmix_port()
        # populate the vmix connection from storage
        self.ui.lineEdit_vmixHost.setText(
            str(fetch_data(SETTINGS_FILE, "vmix_host", "localhost"))
        )
        self.ui.lineEdit_vmixPort.setText(
            str(fetch_data(SETTINGS_FILE, "vmix_port", DEFAULT_VMIX_PORT))
        )
        self.ui.inputLineEdit_vmix.setText(
            str(fetch_data(SETTINGS_FILE, "vmix_input", "1"))
        )
        # apply a connection change once it's typed (Enter or leaving the
        # field), not on every keystroke
        self.ui.lineEdit_vmixHost.editingFinished.connect(self.vmixConnectionChanged)
        self.ui.lineEdit_vmixPort.editingFinished.connect(self.vmixConnectionChanged)
        self.ui.inputLineEdit_vmix.editingFinished.connect(self.vmixConnectionChanged)

        # create the vmixUpdater
        self.vmixUpdater = VMixAPI(
            self.ui.lineEdit_vmixHost.text().strip(),
            self.ui.lineEdit_vmixPort.text().strip(),
            self.ui.inputLineEdit_vmix.text().strip(),
            {},
        )
        # add standard item model to the tableView_vmixMapping
        self.ui.tableView_vmixMapping.setModel(QStandardItemModel())
        mapping = fetch_data(SETTINGS_FILE, "vmix_mapping", {})
        if mapping:
            self.vmixUpdater.set_field_mapping(mapping)

        self.ui.tableView_vmixMapping.model().dataChanged.connect(
            self.vmixMappingChanged
        )

        self.ui.pushButton_startvmix.toggled.connect(self.togglevMix)

    def restoreUiState(self):
        """Show the current connection and running state again, e.g. after
        retranslateUi() reset the fields and the button to the .ui defaults."""
        self.ui.lineEdit_vmixHost.setText(self.vmixUpdater.host)
        self.ui.lineEdit_vmixPort.setText(self.vmixUpdater.port)
        self.ui.inputLineEdit_vmix.setText(self.vmixUpdater.input_number)
        self.ui.pushButton_startvmix.setChecked(self.vmixUpdater.running)
        self._updateToggleText(self.vmixUpdater.running)

    def _updateToggleText(self, running):
        self.ui.pushButton_startvmix.setText(
            "🛑 " + QCoreApplication.translate("MainWindow", "Stop vMix")
            if running
            else "▶️ " + QCoreApplication.translate("MainWindow", "Start vMix")
        )

    def togglevMix(self, value):
        if not self.vmixUpdater:
            return
        self._updateToggleText(value)
        if value:
            self.vmixUpdater.start()
        else:
            self.vmixUpdater.stop()

    def updatevMixTable(self, detectionTargets: list[TextDetectionTarget]):
        mapping_storage = fetch_data(SETTINGS_FILE, "vmix_mapping")
        # a new model with exactly one row per box, so there are no stale rows
        model = QStandardItemModel()
        model.blockSignals(True)

        for box in detectionTargets:
            # add the detection to the vmix output mapping: tableView_vmixMapping
            # check if the table already has the detectionTarget
            items = model.findItems(box.name, Qt.MatchFlag.MatchExactly)
            if len(items) == 0:
                # add the item to the list
                row = model.rowCount()
                model.insertRow(row)
                model.setItem(row, 0, QStandardItem(box.name))
                # the first item shouldn't be editable
                model.item(row, 0).setFlags(Qt.ItemFlag.NoItemFlags)
            else:
                # update the item in the list
                item = items[0]
                row = item.row()

            # get value from storage or use the box name
            if mapping_storage and box.name in mapping_storage:
                model.setItem(row, 1, QStandardItem(mapping_storage[box.name]))
            else:
                model.setItem(row, 1, QStandardItem(box.name))

        model.blockSignals(False)
        self.ui.tableView_vmixMapping.setModel(model)
        self.ui.tableView_vmixMapping.model().dataChanged.connect(
            self.vmixMappingChanged
        )
        # send with the mapping the table shows (including the defaults for boxes
        # that have no stored mapping yet), without storing it
        self.vmixUpdater.set_field_mapping(mapping_from_model(model))
