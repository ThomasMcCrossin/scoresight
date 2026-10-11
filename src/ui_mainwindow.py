# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *  # type: ignore
from PySide6.QtGui import *  # type: ignore
from PySide6.QtWidgets import *  # type: ignore

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1180, 700)
        self.actionNewField = QAction(MainWindow)
        self.actionNewField.setObjectName(u"actionNewField")
#if QT_CONFIG(shortcut)
        self.actionNewField.setShortcut(u"Ctrl+N")
#endif // QT_CONFIG(shortcut)
        self.actionPlaceOnPicture = QAction(MainWindow)
        self.actionPlaceOnPicture.setObjectName(u"actionPlaceOnPicture")
        self.actionRemoveFromPicture = QAction(MainWindow)
        self.actionRemoveFromPicture.setObjectName(u"actionRemoveFromPicture")
        self.actionRenameField = QAction(MainWindow)
        self.actionRenameField.setObjectName(u"actionRenameField")
#if QT_CONFIG(shortcut)
        self.actionRenameField.setShortcut(u"F2")
#endif // QT_CONFIG(shortcut)
        self.actionDeleteField = QAction(MainWindow)
        self.actionDeleteField.setObjectName(u"actionDeleteField")
#if QT_CONFIG(shortcut)
        self.actionDeleteField.setShortcut(u"Del")
#endif // QT_CONFIG(shortcut)
        self.actionResetFieldSettings = QAction(MainWindow)
        self.actionResetFieldSettings.setObjectName(u"actionResetFieldSettings")
        self.actionCopyValue = QAction(MainWindow)
        self.actionCopyValue.setObjectName(u"actionCopyValue")
#if QT_CONFIG(shortcut)
        self.actionCopyValue.setShortcut(u"Ctrl+C")
#endif // QT_CONFIG(shortcut)
        self.actionZoomToBox = QAction(MainWindow)
        self.actionZoomToBox.setObjectName(u"actionZoomToBox")
        self.actionCheckForUpdates = QAction(MainWindow)
        self.actionCheckForUpdates.setObjectName(u"actionCheckForUpdates")
        self.actionCheckForUpdates.setMenuRole(QAction.NoRole)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionAbout.setMenuRole(QAction.AboutRole)
        self.actionViewLog = QAction(MainWindow)
        self.actionViewLog.setObjectName(u"actionViewLog")
        self.actionViewLog.setMenuRole(QAction.NoRole)
        self.actionImportConfiguration = QAction(MainWindow)
        self.actionImportConfiguration.setObjectName(u"actionImportConfiguration")
        self.actionImportConfiguration.setMenuRole(QAction.NoRole)
        self.actionExportConfiguration = QAction(MainWindow)
        self.actionExportConfiguration.setObjectName(u"actionExportConfiguration")
        self.actionExportConfiguration.setMenuRole(QAction.NoRole)
        self.actionOpenConfigurationFolder = QAction(MainWindow)
        self.actionOpenConfigurationFolder.setObjectName(u"actionOpenConfigurationFolder")
        self.actionOpenConfigurationFolder.setMenuRole(QAction.NoRole)
        self.actionOCRTrainingDataSetup = QAction(MainWindow)
        self.actionOCRTrainingDataSetup.setObjectName(u"actionOCRTrainingDataSetup")
        self.actionOCRTrainingDataSetup.setMenuRole(QAction.NoRole)
        self.actionPauseOutputs = QAction(MainWindow)
        self.actionPauseOutputs.setObjectName(u"actionPauseOutputs")
#if QT_CONFIG(shortcut)
        self.actionPauseOutputs.setShortcut(u"Ctrl+Shift+P")
#endif // QT_CONFIG(shortcut)
        self.actionBinaryView = QAction(MainWindow)
        self.actionBinaryView.setObjectName(u"actionBinaryView")
#if QT_CONFIG(shortcut)
        self.actionBinaryView.setShortcut(u"Ctrl+B")
#endif // QT_CONFIG(shortcut)
        self.actionFitPicture = QAction(MainWindow)
        self.actionFitPicture.setObjectName(u"actionFitPicture")
#if QT_CONFIG(shortcut)
        self.actionFitPicture.setShortcut(u"Ctrl+0")
#endif // QT_CONFIG(shortcut)
        self.actionReloadSources = QAction(MainWindow)
        self.actionReloadSources.setObjectName(u"actionReloadSources")
#if QT_CONFIG(shortcut)
        self.actionReloadSources.setShortcut(u"F5")
#endif // QT_CONFIG(shortcut)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_31 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_31.setObjectName(u"horizontalLayout_31")
        self.horizontalLayout_31.setContentsMargins(6, 0, 6, 0)
        self.splitter_main = QSplitter(self.centralwidget)
        self.splitter_main.setObjectName(u"splitter_main")
        self.splitter_main.setOrientation(Qt.Horizontal)
        self.splitter_main.setChildrenCollapsible(False)
        self.splitter_main.setHandleWidth(6)
        self.widget_leftPane = QWidget(self.splitter_main)
        self.widget_leftPane.setObjectName(u"widget_leftPane")
        self.verticalLayout_leftPane = QVBoxLayout(self.widget_leftPane)
        self.verticalLayout_leftPane.setSpacing(4)
        self.verticalLayout_leftPane.setObjectName(u"verticalLayout_leftPane")
        self.verticalLayout_leftPane.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_fieldsHeader = QHBoxLayout()
        self.horizontalLayout_fieldsHeader.setSpacing(4)
        self.horizontalLayout_fieldsHeader.setObjectName(u"horizontalLayout_fieldsHeader")
        self.label_fields = QLabel(self.widget_leftPane)
        self.label_fields.setObjectName(u"label_fields")
        font = QFont()
        font.setBold(True)
        self.label_fields.setFont(font)

        self.horizontalLayout_fieldsHeader.addWidget(self.label_fields)

        self.horizontalSpacer_fieldsHeader = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_fieldsHeader.addItem(self.horizontalSpacer_fieldsHeader)

        self.pushButton_stopUpdates = QPushButton(self.widget_leftPane)
        self.pushButton_stopUpdates.setObjectName(u"pushButton_stopUpdates")
        self.pushButton_stopUpdates.setCheckable(True)

        self.horizontalLayout_fieldsHeader.addWidget(self.pushButton_stopUpdates)

        self.toolButton_addBox = QToolButton(self.widget_leftPane)
        self.toolButton_addBox.setObjectName(u"toolButton_addBox")
        self.toolButton_addBox.setMinimumSize(QSize(27, 0))
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self.toolButton_addBox.setFont(font1)
        self.toolButton_addBox.setText(u"+")

        self.horizontalLayout_fieldsHeader.addWidget(self.toolButton_addBox)


        self.verticalLayout_leftPane.addLayout(self.horizontalLayout_fieldsHeader)

        self.label_fieldsHint = QLabel(self.widget_leftPane)
        self.label_fieldsHint.setObjectName(u"label_fieldsHint")
        self.label_fieldsHint.setWordWrap(True)
        self.label_fieldsHint.setProperty(u"hint", True)

        self.verticalLayout_leftPane.addWidget(self.label_fieldsHint)

        self.groupBox_sb_info = QWidget(self.widget_leftPane)
        self.groupBox_sb_info.setObjectName(u"groupBox_sb_info")
        self.groupBox_sb_info.setEnabled(False)
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_sb_info)
        self.verticalLayout_3.setSpacing(4)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tableWidget_boxes = QTableWidget(self.groupBox_sb_info)
        if (self.tableWidget_boxes.columnCount() < 2):
            self.tableWidget_boxes.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.tableWidget_boxes.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tableWidget_boxes.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.tableWidget_boxes.setObjectName(u"tableWidget_boxes")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.tableWidget_boxes.sizePolicy().hasHeightForWidth())
        self.tableWidget_boxes.setSizePolicy(sizePolicy)
        self.tableWidget_boxes.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_boxes.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_boxes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget_boxes.setTabKeyNavigation(False)
        self.tableWidget_boxes.setDragDropOverwriteMode(False)
        self.tableWidget_boxes.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget_boxes.setShowGrid(False)
        self.tableWidget_boxes.horizontalHeader().setMinimumSectionSize(100)
        self.tableWidget_boxes.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_boxes.verticalHeader().setVisible(False)

        self.verticalLayout_3.addWidget(self.tableWidget_boxes)

        self.horizontalLayout_fieldsFooter = QHBoxLayout()
        self.horizontalLayout_fieldsFooter.setSpacing(4)
        self.horizontalLayout_fieldsFooter.setObjectName(u"horizontalLayout_fieldsFooter")
        self.pushButton_makeBox = QPushButton(self.groupBox_sb_info)
        self.pushButton_makeBox.setObjectName(u"pushButton_makeBox")
        self.pushButton_makeBox.setEnabled(False)

        self.horizontalLayout_fieldsFooter.addWidget(self.pushButton_makeBox)

        self.pushButton_removeBox = QPushButton(self.groupBox_sb_info)
        self.pushButton_removeBox.setObjectName(u"pushButton_removeBox")
        self.pushButton_removeBox.setEnabled(False)

        self.horizontalLayout_fieldsFooter.addWidget(self.pushButton_removeBox)

        self.horizontalSpacer_fieldsFooter = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_fieldsFooter.addItem(self.horizontalSpacer_fieldsFooter)

        self.toolButton_removeBox = QToolButton(self.groupBox_sb_info)
        self.toolButton_removeBox.setObjectName(u"toolButton_removeBox")

        self.horizontalLayout_fieldsFooter.addWidget(self.toolButton_removeBox)


        self.verticalLayout_3.addLayout(self.horizontalLayout_fieldsFooter)


        self.verticalLayout_leftPane.addWidget(self.groupBox_sb_info)

        self.horizontalSpacer_fieldsWidth = QSpacerItem(220, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.verticalLayout_leftPane.addItem(self.horizontalSpacer_fieldsWidth)

        self.splitter_main.addWidget(self.widget_leftPane)
        self.frame_source_view = QFrame(self.splitter_main)
        self.frame_source_view.setObjectName(u"frame_source_view")
        self.frame_source_view.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_source_view.sizePolicy().hasHeightForWidth())
        self.frame_source_view.setSizePolicy(sizePolicy1)
        self.frame_source_view.setFrameShape(QFrame.StyledPanel)
        self.frame_source_view.setFrameShadow(QFrame.Raised)
        self._3 = QVBoxLayout(self.frame_source_view)
        self._3.setSpacing(0)
        self._3.setObjectName(u"_3")
        self._3.setContentsMargins(4, 4, 4, 4)
        self.widget_4 = QWidget(self.frame_source_view)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_4.setSpacing(6)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.widget_3 = QWidget(self.widget_4)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_3 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.widget_3)
        self.label.setObjectName(u"label")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy2)

        self.horizontalLayout_3.addWidget(self.label)

        self.comboBox_camera_source = QComboBox(self.widget_3)
        self.comboBox_camera_source.addItem("")
        self.comboBox_camera_source.addItem("")
        self.comboBox_camera_source.addItem("")
        self.comboBox_camera_source.addItem("")
        self.comboBox_camera_source.setObjectName(u"comboBox_camera_source")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.comboBox_camera_source.sizePolicy().hasHeightForWidth())
        self.comboBox_camera_source.setSizePolicy(sizePolicy3)
        self.comboBox_camera_source.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.comboBox_camera_source.setMinimumContentsLength(16)

        self.horizontalLayout_3.addWidget(self.comboBox_camera_source)

        self.toolButton_videoSettings = QToolButton(self.widget_3)
        self.toolButton_videoSettings.setObjectName(u"toolButton_videoSettings")
        self.toolButton_videoSettings.setEnabled(False)

        self.horizontalLayout_3.addWidget(self.toolButton_videoSettings)

        self.pushButton_refresh_sources = QToolButton(self.widget_3)
        self.pushButton_refresh_sources.setObjectName(u"pushButton_refresh_sources")

        self.horizontalLayout_3.addWidget(self.pushButton_refresh_sources)


        self.horizontalLayout_4.addWidget(self.widget_3)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.pushButton_saveOCRTrainingData = QPushButton(self.widget_4)
        self.pushButton_saveOCRTrainingData.setObjectName(u"pushButton_saveOCRTrainingData")
        self.pushButton_saveOCRTrainingData.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.pushButton_saveOCRTrainingData)


        self._3.addWidget(self.widget_4)

        self.widget_viewTools = QWidget(self.frame_source_view)
        self.widget_viewTools.setObjectName(u"widget_viewTools")
        self.widget_viewTools.setEnabled(False)
        self.horizontalLayout_10 = QHBoxLayout(self.widget_viewTools)
        self.horizontalLayout_10.setSpacing(3)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 3)
        self.pushButton_binary = QToolButton(self.widget_viewTools)
        self.pushButton_binary.setObjectName(u"pushButton_binary")
        self.pushButton_binary.setCheckable(True)

        self.horizontalLayout_10.addWidget(self.pushButton_binary)

        self.pushButton_fourCorner = QToolButton(self.widget_viewTools)
        self.pushButton_fourCorner.setObjectName(u"pushButton_fourCorner")
        self.pushButton_fourCorner.setCheckable(True)

        self.horizontalLayout_10.addWidget(self.pushButton_fourCorner)

        self.toolButton_topCrop = QToolButton(self.widget_viewTools)
        self.toolButton_topCrop.setObjectName(u"toolButton_topCrop")
        self.toolButton_topCrop.setCheckable(True)

        self.horizontalLayout_10.addWidget(self.toolButton_topCrop)

        self.toolButton_rotate = QToolButton(self.widget_viewTools)
        self.toolButton_rotate.setObjectName(u"toolButton_rotate")

        self.horizontalLayout_10.addWidget(self.toolButton_rotate)

        self.pushButton_stabilize = QToolButton(self.widget_viewTools)
        self.pushButton_stabilize.setObjectName(u"pushButton_stabilize")
        self.pushButton_stabilize.setCheckable(True)

        self.horizontalLayout_10.addWidget(self.pushButton_stabilize)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_2)

        self.comboBox_boxDisplayStyle = QComboBox(self.widget_viewTools)
        self.comboBox_boxDisplayStyle.addItem("")
        self.comboBox_boxDisplayStyle.addItem("")
        self.comboBox_boxDisplayStyle.addItem("")
        self.comboBox_boxDisplayStyle.addItem("")
        self.comboBox_boxDisplayStyle.setObjectName(u"comboBox_boxDisplayStyle")

        self.horizontalLayout_10.addWidget(self.comboBox_boxDisplayStyle)

        self.toolButton_osd = QToolButton(self.widget_viewTools)
        self.toolButton_osd.setObjectName(u"toolButton_osd")
        self.toolButton_osd.setCheckable(True)
        self.toolButton_osd.setChecked(True)

        self.horizontalLayout_10.addWidget(self.toolButton_osd)

        self.toolButton_zoomReset = QToolButton(self.widget_viewTools)
        self.toolButton_zoomReset.setObjectName(u"toolButton_zoomReset")

        self.horizontalLayout_10.addWidget(self.toolButton_zoomReset)

        self.label_11 = QLabel(self.widget_viewTools)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setEnabled(False)
        self.label_11.setMinimumSize(QSize(1, 0))

        self.horizontalLayout_10.addWidget(self.label_11)


        self._3.addWidget(self.widget_viewTools)

        self.widget_cropPanel = QWidget(self.frame_source_view)
        self.widget_cropPanel.setObjectName(u"widget_cropPanel")
        self.widget_cropPanel.setEnabled(False)
        self.widget_cropPanel.setMaximumSize(QSize(16777215, 18))
        font2 = QFont()
        font2.setPointSize(8)
        self.widget_cropPanel.setFont(font2)
        self.horizontalLayout_26 = QHBoxLayout(self.widget_cropPanel)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_26.setContentsMargins(0, 0, 0, 0)
        self.label_16 = QLabel(self.widget_cropPanel)
        self.label_16.setObjectName(u"label_16")

        self.horizontalLayout_26.addWidget(self.label_16)

        self.spinBox_leftCrop = QSpinBox(self.widget_cropPanel)
        self.spinBox_leftCrop.setObjectName(u"spinBox_leftCrop")
        self.spinBox_leftCrop.setMinimumSize(QSize(70, 0))
        self.spinBox_leftCrop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spinBox_leftCrop.setMaximum(999)

        self.horizontalLayout_26.addWidget(self.spinBox_leftCrop)

        self.label_17 = QLabel(self.widget_cropPanel)
        self.label_17.setObjectName(u"label_17")

        self.horizontalLayout_26.addWidget(self.label_17)

        self.spinBox_topCrop = QSpinBox(self.widget_cropPanel)
        self.spinBox_topCrop.setObjectName(u"spinBox_topCrop")
        self.spinBox_topCrop.setMinimumSize(QSize(70, 0))
        self.spinBox_topCrop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spinBox_topCrop.setMaximum(999)

        self.horizontalLayout_26.addWidget(self.spinBox_topCrop)

        self.label_18 = QLabel(self.widget_cropPanel)
        self.label_18.setObjectName(u"label_18")

        self.horizontalLayout_26.addWidget(self.label_18)

        self.spinBox_rightCrop = QSpinBox(self.widget_cropPanel)
        self.spinBox_rightCrop.setObjectName(u"spinBox_rightCrop")
        self.spinBox_rightCrop.setMinimumSize(QSize(70, 0))
        self.spinBox_rightCrop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spinBox_rightCrop.setMaximum(999)

        self.horizontalLayout_26.addWidget(self.spinBox_rightCrop)

        self.label_19 = QLabel(self.widget_cropPanel)
        self.label_19.setObjectName(u"label_19")

        self.horizontalLayout_26.addWidget(self.label_19)

        self.spinBox_bottomCrop = QSpinBox(self.widget_cropPanel)
        self.spinBox_bottomCrop.setObjectName(u"spinBox_bottomCrop")
        self.spinBox_bottomCrop.setMinimumSize(QSize(70, 0))
        self.spinBox_bottomCrop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spinBox_bottomCrop.setMaximum(999)

        self.horizontalLayout_26.addWidget(self.spinBox_bottomCrop)

        self.label_22 = QLabel(self.widget_cropPanel)
        self.label_22.setObjectName(u"label_22")

        self.horizontalLayout_26.addWidget(self.label_22)

        self.toolButton_speed = QToolButton(self.widget_cropPanel)
        self.toolButton_speed.setObjectName(u"toolButton_speed")

        self.horizontalLayout_26.addWidget(self.toolButton_speed)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_26.addItem(self.horizontalSpacer_4)


        self._3.addWidget(self.widget_cropPanel)

        self.frame_pausedBanner = QFrame(self.frame_source_view)
        self.frame_pausedBanner.setObjectName(u"frame_pausedBanner")
        self.frame_pausedBanner.setFrameShape(QFrame.StyledPanel)
        self.horizontalLayout_pausedBanner = QHBoxLayout(self.frame_pausedBanner)
        self.horizontalLayout_pausedBanner.setSpacing(8)
        self.horizontalLayout_pausedBanner.setObjectName(u"horizontalLayout_pausedBanner")
        self.horizontalLayout_pausedBanner.setContentsMargins(8, 4, 4, 4)
        self.label_pausedBanner = QLabel(self.frame_pausedBanner)
        self.label_pausedBanner.setObjectName(u"label_pausedBanner")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.label_pausedBanner.sizePolicy().hasHeightForWidth())
        self.label_pausedBanner.setSizePolicy(sizePolicy4)
        self.label_pausedBanner.setTextFormat(Qt.RichText)
        self.label_pausedBanner.setWordWrap(True)

        self.horizontalLayout_pausedBanner.addWidget(self.label_pausedBanner)

        self.pushButton_resumeOutputs = QPushButton(self.frame_pausedBanner)
        self.pushButton_resumeOutputs.setObjectName(u"pushButton_resumeOutputs")

        self.horizontalLayout_pausedBanner.addWidget(self.pushButton_resumeOutputs)


        self._3.addWidget(self.frame_pausedBanner)

        self.frame_for_source_view_label = QFrame(self.frame_source_view)
        self.frame_for_source_view_label.setObjectName(u"frame_for_source_view_label")
        self.frame_for_source_view_label.setEnabled(True)
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.frame_for_source_view_label.sizePolicy().hasHeightForWidth())
        self.frame_for_source_view_label.setSizePolicy(sizePolicy5)
        self.gridLayout = QGridLayout(self.frame_for_source_view_label)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SetMaximumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label_12 = QLabel(self.frame_for_source_view_label)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setEnabled(False)
        self.label_12.setTextFormat(Qt.MarkdownText)
        self.label_12.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.label_12, 0, 0, 1, 1)


        self._3.addWidget(self.frame_for_source_view_label)

        self.splitter_main.addWidget(self.frame_source_view)
        self.tabWidget_inspector = QTabWidget(self.splitter_main)
        self.tabWidget_inspector.setObjectName(u"tabWidget_inspector")
        self.tab_box = QWidget()
        self.tab_box.setObjectName(u"tab_box")
        self.verticalLayout_boxTab = QVBoxLayout(self.tab_box)
        self.verticalLayout_boxTab.setSpacing(6)
        self.verticalLayout_boxTab.setObjectName(u"verticalLayout_boxTab")
        self.verticalLayout_boxTab.setContentsMargins(4, 4, 4, 4)
        self.stackedWidget_boxSettings = QStackedWidget(self.tab_box)
        self.stackedWidget_boxSettings.setObjectName(u"stackedWidget_boxSettings")
        self.page_boxEmpty = QWidget()
        self.page_boxEmpty.setObjectName(u"page_boxEmpty")
        self.verticalLayout_boxEmpty = QVBoxLayout(self.page_boxEmpty)
        self.verticalLayout_boxEmpty.setSpacing(6)
        self.verticalLayout_boxEmpty.setObjectName(u"verticalLayout_boxEmpty")
        self.verticalLayout_boxEmpty.setContentsMargins(12, 24, 12, 12)
        self.label_boxEmptyTitle = QLabel(self.page_boxEmpty)
        self.label_boxEmptyTitle.setObjectName(u"label_boxEmptyTitle")
        self.label_boxEmptyTitle.setFont(font)
        self.label_boxEmptyTitle.setAlignment(Qt.AlignCenter)

        self.verticalLayout_boxEmpty.addWidget(self.label_boxEmptyTitle)

        self.label_boxEmpty = QLabel(self.page_boxEmpty)
        self.label_boxEmpty.setObjectName(u"label_boxEmpty")
        self.label_boxEmpty.setWordWrap(True)
        self.label_boxEmpty.setAlignment(Qt.AlignCenter)
        self.label_boxEmpty.setProperty(u"hint", True)

        self.verticalLayout_boxEmpty.addWidget(self.label_boxEmpty)

        self.verticalSpacer_boxEmpty = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_boxEmpty.addItem(self.verticalSpacer_boxEmpty)

        self.stackedWidget_boxSettings.addWidget(self.page_boxEmpty)
        self.page_boxSettings = QWidget()
        self.page_boxSettings.setObjectName(u"page_boxSettings")
        self.verticalLayout_boxSettingsPage = QVBoxLayout(self.page_boxSettings)
        self.verticalLayout_boxSettingsPage.setSpacing(2)
        self.verticalLayout_boxSettingsPage.setObjectName(u"verticalLayout_boxSettingsPage")
        self.verticalLayout_boxSettingsPage.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_boxHeader = QHBoxLayout()
        self.horizontalLayout_boxHeader.setSpacing(6)
        self.horizontalLayout_boxHeader.setObjectName(u"horizontalLayout_boxHeader")
        self.horizontalLayout_boxHeader.setContentsMargins(4, 6, 4, 2)
        self.verticalLayout_boxTitle = QVBoxLayout()
        self.verticalLayout_boxTitle.setSpacing(0)
        self.verticalLayout_boxTitle.setObjectName(u"verticalLayout_boxTitle")
        self.label_selectedInfo = QLabel(self.page_boxSettings)
        self.label_selectedInfo.setObjectName(u"label_selectedInfo")
        self.label_selectedInfo.setFont(font)
        self.label_selectedInfo.setText(u"")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.label_selectedInfo.sizePolicy().hasHeightForWidth())
        self.label_selectedInfo.setSizePolicy(sizePolicy6)
        self.label_selectedInfo.setTextInteractionFlags(Qt.NoTextInteraction)

        self.verticalLayout_boxTitle.addWidget(self.label_selectedInfo)

        self.label_6 = QLabel(self.page_boxSettings)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setProperty(u"hint", True)

        self.verticalLayout_boxTitle.addWidget(self.label_6)


        self.horizontalLayout_boxHeader.addLayout(self.verticalLayout_boxTitle)

        self.pushButton_restoreDefaults = QPushButton(self.page_boxSettings)
        self.pushButton_restoreDefaults.setObjectName(u"pushButton_restoreDefaults")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.pushButton_restoreDefaults.sizePolicy().hasHeightForWidth())
        self.pushButton_restoreDefaults.setSizePolicy(sizePolicy7)

        self.horizontalLayout_boxHeader.addWidget(self.pushButton_restoreDefaults, 0, Qt.AlignTop)


        self.verticalLayout_boxSettingsPage.addLayout(self.horizontalLayout_boxHeader)

        self.scrollArea_boxSettings = QScrollArea(self.page_boxSettings)
        self.scrollArea_boxSettings.setObjectName(u"scrollArea_boxSettings")
        self.scrollArea_boxSettings.setFrameShape(QFrame.NoFrame)
        self.scrollArea_boxSettings.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_boxSettings.setWidgetResizable(True)
        self.scrollAreaWidgetContents_boxSettings = QWidget()
        self.scrollAreaWidgetContents_boxSettings.setObjectName(u"scrollAreaWidgetContents_boxSettings")
        self.verticalLayout_boxSettings = QVBoxLayout(self.scrollAreaWidgetContents_boxSettings)
        self.verticalLayout_boxSettings.setSpacing(10)
        self.verticalLayout_boxSettings.setObjectName(u"verticalLayout_boxSettings")
        self.verticalLayout_boxSettings.setContentsMargins(4, 4, 4, 8)
        self.label_boxNote = QLabel(self.scrollAreaWidgetContents_boxSettings)
        self.label_boxNote.setObjectName(u"label_boxNote")
        self.label_boxNote.setText(u"")
        self.label_boxNote.setWordWrap(True)

        self.verticalLayout_boxSettings.addWidget(self.label_boxNote)

        self.groupBox_target_settings = QWidget(self.scrollAreaWidgetContents_boxSettings)
        self.groupBox_target_settings.setObjectName(u"groupBox_target_settings")
        self.verticalLayout_targetSettings = QVBoxLayout(self.groupBox_target_settings)
        self.verticalLayout_targetSettings.setSpacing(4)
        self.verticalLayout_targetSettings.setObjectName(u"verticalLayout_targetSettings")
        self.verticalLayout_targetSettings.setContentsMargins(0, 0, 0, 0)
        self.formLayout_reading = QFormLayout()
        self.formLayout_reading.setObjectName(u"formLayout_reading")
        self.formLayout_reading.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formLayout_reading.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_reading.setHorizontalSpacing(8)
        self.formLayout_reading.setVerticalSpacing(4)
        self.formLayout_reading.setContentsMargins(0, 0, 0, 0)
        self.label_sectionReading = QLabel(self.groupBox_target_settings)
        self.label_sectionReading.setObjectName(u"label_sectionReading")
        self.label_sectionReading.setFont(font)

        self.formLayout_reading.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_sectionReading)

        self.label_13 = QLabel(self.groupBox_target_settings)
        self.label_13.setObjectName(u"label_13")

        self.formLayout_reading.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_13)

        self.comboBox_fieldType = QComboBox(self.groupBox_target_settings)
        self.comboBox_fieldType.addItem("")
        self.comboBox_fieldType.addItem("")
        self.comboBox_fieldType.addItem("")
        self.comboBox_fieldType.setObjectName(u"comboBox_fieldType")

        self.formLayout_reading.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox_fieldType)

        self.label_2 = QLabel(self.groupBox_target_settings)
        self.label_2.setObjectName(u"label_2")

        self.formLayout_reading.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.comboBox_formatPrefix = QComboBox(self.groupBox_target_settings)
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.addItem("")
        self.comboBox_formatPrefix.setObjectName(u"comboBox_formatPrefix")

        self.formLayout_reading.setWidget(2, QFormLayout.ItemRole.FieldRole, self.comboBox_formatPrefix)

        self.lineEdit_format = QLineEdit(self.groupBox_target_settings)
        self.lineEdit_format.setObjectName(u"lineEdit_format")

        self.formLayout_reading.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.lineEdit_format)

        self.label_formatStatus = QLabel(self.groupBox_target_settings)
        self.label_formatStatus.setObjectName(u"label_formatStatus")
        self.label_formatStatus.setText(u"")
        self.label_formatStatus.setWordWrap(True)

        self.formLayout_reading.setWidget(4, QFormLayout.ItemRole.SpanningRole, self.label_formatStatus)

        self.horizontalLayout_removeLeadingZeros = QHBoxLayout()
        self.horizontalLayout_removeLeadingZeros.setSpacing(6)
        self.horizontalLayout_removeLeadingZeros.setObjectName(u"horizontalLayout_removeLeadingZeros")
        self.checkBox_removeLeadingZeros = QCheckBox(self.groupBox_target_settings)
        self.checkBox_removeLeadingZeros.setObjectName(u"checkBox_removeLeadingZeros")

        self.horizontalLayout_removeLeadingZeros.addWidget(self.checkBox_removeLeadingZeros)

        self.label_removeLeadingZerosHint = QLabel(self.groupBox_target_settings)
        self.label_removeLeadingZerosHint.setObjectName(u"label_removeLeadingZerosHint")
        self.label_removeLeadingZerosHint.setWordWrap(True)
        sizePolicy4.setHeightForWidth(self.label_removeLeadingZerosHint.sizePolicy().hasHeightForWidth())
        self.label_removeLeadingZerosHint.setSizePolicy(sizePolicy4)
        self.label_removeLeadingZerosHint.setProperty(u"hint", True)

        self.horizontalLayout_removeLeadingZeros.addWidget(self.label_removeLeadingZerosHint)


        self.formLayout_reading.setLayout(5, QFormLayout.ItemRole.SpanningRole, self.horizontalLayout_removeLeadingZeros)

        self.horizontalLayout_ordinalIndicator = QHBoxLayout()
        self.horizontalLayout_ordinalIndicator.setSpacing(6)
        self.horizontalLayout_ordinalIndicator.setObjectName(u"horizontalLayout_ordinalIndicator")
        self.checkBox_ordinalIndicator = QCheckBox(self.groupBox_target_settings)
        self.checkBox_ordinalIndicator.setObjectName(u"checkBox_ordinalIndicator")

        self.horizontalLayout_ordinalIndicator.addWidget(self.checkBox_ordinalIndicator)

        self.label_ordinalIndicatorHint = QLabel(self.groupBox_target_settings)
        self.label_ordinalIndicatorHint.setObjectName(u"label_ordinalIndicatorHint")
        self.label_ordinalIndicatorHint.setWordWrap(True)
        sizePolicy4.setHeightForWidth(self.label_ordinalIndicatorHint.sizePolicy().hasHeightForWidth())
        self.label_ordinalIndicatorHint.setSizePolicy(sizePolicy4)
        self.label_ordinalIndicatorHint.setProperty(u"hint", True)

        self.horizontalLayout_ordinalIndicator.addWidget(self.label_ordinalIndicatorHint)


        self.formLayout_reading.setLayout(6, QFormLayout.ItemRole.SpanningRole, self.horizontalLayout_ordinalIndicator)

        self.checkBox_dotDetector = QCheckBox(self.groupBox_target_settings)
        self.checkBox_dotDetector.setObjectName(u"checkBox_dotDetector")

        self.formLayout_reading.setWidget(7, QFormLayout.ItemRole.SpanningRole, self.checkBox_dotDetector)


        self.verticalLayout_targetSettings.addLayout(self.formLayout_reading)

        self.verticalSpacer_reading = QSpacerItem(20, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_targetSettings.addItem(self.verticalSpacer_reading)

        self.formLayout_filtering = QFormLayout()
        self.formLayout_filtering.setObjectName(u"formLayout_filtering")
        self.formLayout_filtering.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formLayout_filtering.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_filtering.setHorizontalSpacing(8)
        self.formLayout_filtering.setVerticalSpacing(4)
        self.formLayout_filtering.setContentsMargins(0, 0, 0, 0)
        self.label_sectionFiltering = QLabel(self.groupBox_target_settings)
        self.label_sectionFiltering.setObjectName(u"label_sectionFiltering")
        self.label_sectionFiltering.setFont(font)

        self.formLayout_filtering.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_sectionFiltering)

        self.label_3 = QLabel(self.groupBox_target_settings)
        self.label_3.setObjectName(u"label_3")

        self.formLayout_filtering.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.horizontalLayout_confThresh = QHBoxLayout()
        self.horizontalLayout_confThresh.setSpacing(6)
        self.horizontalLayout_confThresh.setObjectName(u"horizontalLayout_confThresh")
        self.horizontalSlider_conf_thresh = QSlider(self.groupBox_target_settings)
        self.horizontalSlider_conf_thresh.setObjectName(u"horizontalSlider_conf_thresh")
        self.horizontalSlider_conf_thresh.setMaximum(99)
        self.horizontalSlider_conf_thresh.setValue(0)
        self.horizontalSlider_conf_thresh.setOrientation(Qt.Horizontal)

        self.horizontalLayout_confThresh.addWidget(self.horizontalSlider_conf_thresh)

        self.label_confThreshValue = QLabel(self.groupBox_target_settings)
        self.label_confThreshValue.setObjectName(u"label_confThreshValue")
        self.label_confThreshValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_confThresh.addWidget(self.label_confThreshValue)


        self.formLayout_filtering.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_confThresh)

        self.checkBox_smoothing = QCheckBox(self.groupBox_target_settings)
        self.checkBox_smoothing.setObjectName(u"checkBox_smoothing")

        self.formLayout_filtering.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.checkBox_smoothing)

        self.horizontalLayout_skipSimilarImage = QHBoxLayout()
        self.horizontalLayout_skipSimilarImage.setSpacing(6)
        self.horizontalLayout_skipSimilarImage.setObjectName(u"horizontalLayout_skipSimilarImage")
        self.checkBox_skip_similar_image = QCheckBox(self.groupBox_target_settings)
        self.checkBox_skip_similar_image.setObjectName(u"checkBox_skip_similar_image")

        self.horizontalLayout_skipSimilarImage.addWidget(self.checkBox_skip_similar_image)

        self.label_skipSimilarImageHint = QLabel(self.groupBox_target_settings)
        self.label_skipSimilarImageHint.setObjectName(u"label_skipSimilarImageHint")
        self.label_skipSimilarImageHint.setWordWrap(True)
        sizePolicy4.setHeightForWidth(self.label_skipSimilarImageHint.sizePolicy().hasHeightForWidth())
        self.label_skipSimilarImageHint.setSizePolicy(sizePolicy4)
        self.label_skipSimilarImageHint.setProperty(u"hint", True)

        self.horizontalLayout_skipSimilarImage.addWidget(self.label_skipSimilarImageHint)


        self.formLayout_filtering.setLayout(3, QFormLayout.ItemRole.SpanningRole, self.horizontalLayout_skipSimilarImage)


        self.verticalLayout_targetSettings.addLayout(self.formLayout_filtering)

        self.verticalSpacer_filtering = QSpacerItem(20, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_targetSettings.addItem(self.verticalSpacer_filtering)

        self.horizontalLayout_imageCleanup = QHBoxLayout()
        self.horizontalLayout_imageCleanup.setSpacing(6)
        self.horizontalLayout_imageCleanup.setObjectName(u"horizontalLayout_imageCleanup")
        self.toolButton_imageCleanup = QToolButton(self.groupBox_target_settings)
        self.toolButton_imageCleanup.setObjectName(u"toolButton_imageCleanup")
        self.toolButton_imageCleanup.setFont(font)
        self.toolButton_imageCleanup.setCheckable(True)
        self.toolButton_imageCleanup.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolButton_imageCleanup.setAutoRaise(True)
        self.toolButton_imageCleanup.setArrowType(Qt.RightArrow)

        self.horizontalLayout_imageCleanup.addWidget(self.toolButton_imageCleanup)

        self.label_imageCleanupBadge = QLabel(self.groupBox_target_settings)
        self.label_imageCleanupBadge.setObjectName(u"label_imageCleanupBadge")
        self.label_imageCleanupBadge.setText(u"")
        self.label_imageCleanupBadge.setProperty(u"hint", True)

        self.horizontalLayout_imageCleanup.addWidget(self.label_imageCleanupBadge)

        self.horizontalSpacer_imageCleanup = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_imageCleanup.addItem(self.horizontalSpacer_imageCleanup)

        self.toolButton_cleanupBinary = QToolButton(self.groupBox_target_settings)
        self.toolButton_cleanupBinary.setObjectName(u"toolButton_cleanupBinary")
        self.toolButton_cleanupBinary.setCheckable(True)

        self.horizontalLayout_imageCleanup.addWidget(self.toolButton_cleanupBinary)


        self.verticalLayout_targetSettings.addLayout(self.horizontalLayout_imageCleanup)

        self.frame_imageCleanup = QFrame(self.groupBox_target_settings)
        self.frame_imageCleanup.setObjectName(u"frame_imageCleanup")
        self.frame_imageCleanup.setFrameShape(QFrame.NoFrame)
        self.formLayout_imageCleanup = QFormLayout(self.frame_imageCleanup)
        self.formLayout_imageCleanup.setObjectName(u"formLayout_imageCleanup")
        self.formLayout_imageCleanup.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formLayout_imageCleanup.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_imageCleanup.setHorizontalSpacing(8)
        self.formLayout_imageCleanup.setVerticalSpacing(4)
        self.formLayout_imageCleanup.setContentsMargins(0, 0, 0, 0)
        self.label_binarizationMethod = QLabel(self.frame_imageCleanup)
        self.label_binarizationMethod.setObjectName(u"label_binarizationMethod")

        self.formLayout_imageCleanup.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_binarizationMethod)

        self.comboBox_binarizationMethod = QComboBox(self.frame_imageCleanup)
        self.comboBox_binarizationMethod.addItem("")
        self.comboBox_binarizationMethod.addItem("")
        self.comboBox_binarizationMethod.addItem("")
        self.comboBox_binarizationMethod.addItem("")
        self.comboBox_binarizationMethod.setObjectName(u"comboBox_binarizationMethod")

        self.formLayout_imageCleanup.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboBox_binarizationMethod)

        self.label_4 = QLabel(self.frame_imageCleanup)
        self.label_4.setObjectName(u"label_4")

        self.formLayout_imageCleanup.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.horizontalLayout_cleanup = QHBoxLayout()
        self.horizontalLayout_cleanup.setSpacing(6)
        self.horizontalLayout_cleanup.setObjectName(u"horizontalLayout_cleanup")
        self.horizontalSlider_cleanup = QSlider(self.frame_imageCleanup)
        self.horizontalSlider_cleanup.setObjectName(u"horizontalSlider_cleanup")
        self.horizontalSlider_cleanup.setOrientation(Qt.Horizontal)

        self.horizontalLayout_cleanup.addWidget(self.horizontalSlider_cleanup)

        self.label_cleanupValue = QLabel(self.frame_imageCleanup)
        self.label_cleanupValue.setObjectName(u"label_cleanupValue")
        self.label_cleanupValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_cleanup.addWidget(self.label_cleanupValue)


        self.formLayout_imageCleanup.setLayout(1, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_cleanup)

        self.label_15 = QLabel(self.frame_imageCleanup)
        self.label_15.setObjectName(u"label_15")

        self.formLayout_imageCleanup.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_15)

        self.horizontalLayout_vscale = QHBoxLayout()
        self.horizontalLayout_vscale.setSpacing(6)
        self.horizontalLayout_vscale.setObjectName(u"horizontalLayout_vscale")
        self.horizontalSlider_vscale = QSlider(self.frame_imageCleanup)
        self.horizontalSlider_vscale.setObjectName(u"horizontalSlider_vscale")
        self.horizontalSlider_vscale.setMinimum(1)
        self.horizontalSlider_vscale.setMaximum(10)
        self.horizontalSlider_vscale.setPageStep(5)
        self.horizontalSlider_vscale.setValue(10)
        self.horizontalSlider_vscale.setOrientation(Qt.Horizontal)

        self.horizontalLayout_vscale.addWidget(self.horizontalSlider_vscale)

        self.label_vscaleValue = QLabel(self.frame_imageCleanup)
        self.label_vscaleValue.setObjectName(u"label_vscaleValue")
        self.label_vscaleValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_vscale.addWidget(self.label_vscaleValue)


        self.formLayout_imageCleanup.setLayout(2, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_vscale)

        self.label_14 = QLabel(self.frame_imageCleanup)
        self.label_14.setObjectName(u"label_14")

        self.formLayout_imageCleanup.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_14)

        self.horizontalLayout_skew = QHBoxLayout()
        self.horizontalLayout_skew.setSpacing(6)
        self.horizontalLayout_skew.setObjectName(u"horizontalLayout_skew")
        self.horizontalSlider_skew = QSlider(self.frame_imageCleanup)
        self.horizontalSlider_skew.setObjectName(u"horizontalSlider_skew")
        self.horizontalSlider_skew.setMinimum(-10)
        self.horizontalSlider_skew.setMaximum(10)
        self.horizontalSlider_skew.setOrientation(Qt.Horizontal)

        self.horizontalLayout_skew.addWidget(self.horizontalSlider_skew)

        self.label_skewValue = QLabel(self.frame_imageCleanup)
        self.label_skewValue.setObjectName(u"label_skewValue")
        self.label_skewValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_skew.addWidget(self.label_skewValue)


        self.formLayout_imageCleanup.setLayout(3, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_skew)

        self.label_9 = QLabel(self.frame_imageCleanup)
        self.label_9.setObjectName(u"label_9")

        self.formLayout_imageCleanup.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_9)

        self.horizontalLayout_dilate = QHBoxLayout()
        self.horizontalLayout_dilate.setSpacing(6)
        self.horizontalLayout_dilate.setObjectName(u"horizontalLayout_dilate")
        self.horizontalSlider_dilate = QSlider(self.frame_imageCleanup)
        self.horizontalSlider_dilate.setObjectName(u"horizontalSlider_dilate")
        self.horizontalSlider_dilate.setMaximum(5)
        self.horizontalSlider_dilate.setPageStep(1)
        self.horizontalSlider_dilate.setOrientation(Qt.Horizontal)

        self.horizontalLayout_dilate.addWidget(self.horizontalSlider_dilate)

        self.label_dilateValue = QLabel(self.frame_imageCleanup)
        self.label_dilateValue.setObjectName(u"label_dilateValue")
        self.label_dilateValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_dilate.addWidget(self.label_dilateValue)


        self.formLayout_imageCleanup.setLayout(4, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_dilate)

        self.checkBox_invertPatch = QCheckBox(self.frame_imageCleanup)
        self.checkBox_invertPatch.setObjectName(u"checkBox_invertPatch")

        self.formLayout_imageCleanup.setWidget(5, QFormLayout.ItemRole.SpanningRole, self.checkBox_invertPatch)

        self.checkBox_autocrop = QCheckBox(self.frame_imageCleanup)
        self.checkBox_autocrop.setObjectName(u"checkBox_autocrop")

        self.formLayout_imageCleanup.setWidget(6, QFormLayout.ItemRole.SpanningRole, self.checkBox_autocrop)

        self.checkBox_rescalePatch = QCheckBox(self.frame_imageCleanup)
        self.checkBox_rescalePatch.setObjectName(u"checkBox_rescalePatch")

        self.formLayout_imageCleanup.setWidget(7, QFormLayout.ItemRole.SpanningRole, self.checkBox_rescalePatch)

        self.checkBox_normWHRatio = QCheckBox(self.frame_imageCleanup)
        self.checkBox_normWHRatio.setObjectName(u"checkBox_normWHRatio")

        self.formLayout_imageCleanup.setWidget(8, QFormLayout.ItemRole.SpanningRole, self.checkBox_normWHRatio)

        self.label_legacy = QLabel(self.frame_imageCleanup)
        self.label_legacy.setObjectName(u"label_legacy")
        self.label_legacy.setProperty(u"hint", True)

        self.formLayout_imageCleanup.setWidget(9, QFormLayout.ItemRole.SpanningRole, self.label_legacy)

        self.horizontalLayout_compositeBox = QHBoxLayout()
        self.horizontalLayout_compositeBox.setSpacing(6)
        self.horizontalLayout_compositeBox.setObjectName(u"horizontalLayout_compositeBox")
        self.checkBox_compositeBox = QCheckBox(self.frame_imageCleanup)
        self.checkBox_compositeBox.setObjectName(u"checkBox_compositeBox")

        self.horizontalLayout_compositeBox.addWidget(self.checkBox_compositeBox)

        self.label_compositeBoxHint = QLabel(self.frame_imageCleanup)
        self.label_compositeBoxHint.setObjectName(u"label_compositeBoxHint")
        self.label_compositeBoxHint.setWordWrap(True)
        sizePolicy4.setHeightForWidth(self.label_compositeBoxHint.sizePolicy().hasHeightForWidth())
        self.label_compositeBoxHint.setSizePolicy(sizePolicy4)
        self.label_compositeBoxHint.setProperty(u"hint", True)

        self.horizontalLayout_compositeBox.addWidget(self.label_compositeBoxHint)


        self.formLayout_imageCleanup.setLayout(10, QFormLayout.ItemRole.SpanningRole, self.horizontalLayout_compositeBox)

        self.horizontalLayout_skipEmpty = QHBoxLayout()
        self.horizontalLayout_skipEmpty.setSpacing(6)
        self.horizontalLayout_skipEmpty.setObjectName(u"horizontalLayout_skipEmpty")
        self.checkBox_skip_empty = QCheckBox(self.frame_imageCleanup)
        self.checkBox_skip_empty.setObjectName(u"checkBox_skip_empty")

        self.horizontalLayout_skipEmpty.addWidget(self.checkBox_skip_empty)

        self.label_skipEmptyHint = QLabel(self.frame_imageCleanup)
        self.label_skipEmptyHint.setObjectName(u"label_skipEmptyHint")
        self.label_skipEmptyHint.setWordWrap(True)
        sizePolicy4.setHeightForWidth(self.label_skipEmptyHint.sizePolicy().hasHeightForWidth())
        self.label_skipEmptyHint.setSizePolicy(sizePolicy4)
        self.label_skipEmptyHint.setProperty(u"hint", True)

        self.horizontalLayout_skipEmpty.addWidget(self.label_skipEmptyHint)


        self.formLayout_imageCleanup.setLayout(11, QFormLayout.ItemRole.SpanningRole, self.horizontalLayout_skipEmpty)


        self.verticalLayout_targetSettings.addWidget(self.frame_imageCleanup)


        self.verticalLayout_boxSettings.addWidget(self.groupBox_target_settings)

        self.widget_templateField = QWidget(self.scrollAreaWidgetContents_boxSettings)
        self.widget_templateField.setObjectName(u"widget_templateField")
        self.verticalLayout_templateField = QVBoxLayout(self.widget_templateField)
        self.verticalLayout_templateField.setSpacing(4)
        self.verticalLayout_templateField.setObjectName(u"verticalLayout_templateField")
        self.verticalLayout_templateField.setContentsMargins(0, 0, 0, 0)
        self.label_sectionTemplate = QLabel(self.widget_templateField)
        self.label_sectionTemplate.setObjectName(u"label_sectionTemplate")
        self.label_sectionTemplate.setFont(font)

        self.verticalLayout_templateField.addWidget(self.label_sectionTemplate)

        self.checkBox_templatefield = QCheckBox(self.widget_templateField)
        self.checkBox_templatefield.setObjectName(u"checkBox_templatefield")

        self.verticalLayout_templateField.addWidget(self.checkBox_templatefield)

        self.horizontalLayout_templateText = QHBoxLayout()
        self.horizontalLayout_templateText.setSpacing(4)
        self.horizontalLayout_templateText.setObjectName(u"horizontalLayout_templateText")
        self.lineEdit_templatefield = QLineEdit(self.widget_templateField)
        self.lineEdit_templatefield.setObjectName(u"lineEdit_templatefield")
        self.lineEdit_templatefield.setText(u"")

        self.horizontalLayout_templateText.addWidget(self.lineEdit_templatefield)

        self.toolButton_insertField = QToolButton(self.widget_templateField)
        self.toolButton_insertField.setObjectName(u"toolButton_insertField")
        self.toolButton_insertField.setPopupMode(QToolButton.InstantPopup)
        self.toolButton_insertField.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self.horizontalLayout_templateText.addWidget(self.toolButton_insertField)


        self.verticalLayout_templateField.addLayout(self.horizontalLayout_templateText)

        self.label_templateHint = QLabel(self.widget_templateField)
        self.label_templateHint.setObjectName(u"label_templateHint")
        self.label_templateHint.setText(u"")
        self.label_templateHint.setWordWrap(True)
        self.label_templateHint.setProperty(u"hint", True)

        self.verticalLayout_templateField.addWidget(self.label_templateHint)


        self.verticalLayout_boxSettings.addWidget(self.widget_templateField)

        self.verticalSpacer_boxSettings = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_boxSettings.addItem(self.verticalSpacer_boxSettings)

        self.scrollArea_boxSettings.setWidget(self.scrollAreaWidgetContents_boxSettings)

        self.verticalLayout_boxSettingsPage.addWidget(self.scrollArea_boxSettings)

        self.stackedWidget_boxSettings.addWidget(self.page_boxSettings)

        self.verticalLayout_boxTab.addWidget(self.stackedWidget_boxSettings)

        self.groupBox_allBoxes = QGroupBox(self.tab_box)
        self.groupBox_allBoxes.setObjectName(u"groupBox_allBoxes")
        self.formLayout_allBoxes = QFormLayout(self.groupBox_allBoxes)
        self.formLayout_allBoxes.setObjectName(u"formLayout_allBoxes")
        self.formLayout_allBoxes.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formLayout_allBoxes.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_allBoxes.setHorizontalSpacing(8)
        self.formLayout_allBoxes.setVerticalSpacing(4)
        self.formLayout_allBoxes.setContentsMargins(0, 0, 0, 0)
        self.label_allBoxesScope = QLabel(self.groupBox_allBoxes)
        self.label_allBoxesScope.setObjectName(u"label_allBoxesScope")
        self.label_allBoxesScope.setWordWrap(True)
        self.label_allBoxesScope.setProperty(u"hint", True)

        self.formLayout_allBoxes.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_allBoxesScope)

        self.label_10 = QLabel(self.groupBox_allBoxes)
        self.label_10.setObjectName(u"label_10")

        self.formLayout_allBoxes.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_10)

        self.comboBox_ocrModel = QComboBox(self.groupBox_allBoxes)
        self.comboBox_ocrModel.setObjectName(u"comboBox_ocrModel")

        self.formLayout_allBoxes.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox_ocrModel)

        self.label_detectionCadence = QLabel(self.groupBox_allBoxes)
        self.label_detectionCadence.setObjectName(u"label_detectionCadence")

        self.formLayout_allBoxes.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_detectionCadence)

        self.horizontalLayout_detectionCadence = QHBoxLayout()
        self.horizontalLayout_detectionCadence.setSpacing(6)
        self.horizontalLayout_detectionCadence.setObjectName(u"horizontalLayout_detectionCadence")
        self.horizontalSlider_detectionCadence = QSlider(self.groupBox_allBoxes)
        self.horizontalSlider_detectionCadence.setObjectName(u"horizontalSlider_detectionCadence")
        self.horizontalSlider_detectionCadence.setMinimum(1)
        self.horizontalSlider_detectionCadence.setMaximum(15)
        self.horizontalSlider_detectionCadence.setPageStep(5)
        self.horizontalSlider_detectionCadence.setValue(5)
        self.horizontalSlider_detectionCadence.setOrientation(Qt.Horizontal)
        self.horizontalSlider_detectionCadence.setTickPosition(QSlider.TicksBelow)
        self.horizontalSlider_detectionCadence.setTickInterval(5)

        self.horizontalLayout_detectionCadence.addWidget(self.horizontalSlider_detectionCadence)

        self.label_detectionCadenceValue = QLabel(self.groupBox_allBoxes)
        self.label_detectionCadenceValue.setObjectName(u"label_detectionCadenceValue")
        self.label_detectionCadenceValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_detectionCadence.addWidget(self.label_detectionCadenceValue)


        self.formLayout_allBoxes.setLayout(2, QFormLayout.ItemRole.FieldRole, self.horizontalLayout_detectionCadence)

        self.checkBox_updateOnchange = QCheckBox(self.groupBox_allBoxes)
        self.checkBox_updateOnchange.setObjectName(u"checkBox_updateOnchange")
        self.checkBox_updateOnchange.setChecked(True)

        self.formLayout_allBoxes.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.checkBox_updateOnchange)


        self.verticalLayout_boxTab.addWidget(self.groupBox_allBoxes)

        self.horizontalSpacer_inspectorWidth = QSpacerItem(290, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.verticalLayout_boxTab.addItem(self.horizontalSpacer_inspectorWidth)

        self.tabWidget_inspector.addTab(self.tab_box, "")
        self.widget_outputs = QWidget()
        self.widget_outputs.setObjectName(u"widget_outputs")
        self.verticalLayout_outputs = QVBoxLayout(self.widget_outputs)
        self.verticalLayout_outputs.setSpacing(3)
        self.verticalLayout_outputs.setObjectName(u"verticalLayout_outputs")
        self.verticalLayout_outputs.setContentsMargins(4, 4, 4, 4)
        self.splitter_outputs = QSplitter(self.widget_outputs)
        self.splitter_outputs.setObjectName(u"splitter_outputs")
        self.splitter_outputs.setOrientation(Qt.Vertical)
        self.splitter_outputs.setChildrenCollapsible(False)
        self.listView_destinations = QListView(self.splitter_outputs)
        self.listView_destinations.setObjectName(u"listView_destinations")
        sizePolicy4.setHeightForWidth(self.listView_destinations.sizePolicy().hasHeightForWidth())
        self.listView_destinations.setSizePolicy(sizePolicy4)
        self.listView_destinations.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listView_destinations.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView_destinations.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listView_destinations.setUniformItemSizes(True)
        self.splitter_outputs.addWidget(self.listView_destinations)
        self.widget_outputDetails = QWidget(self.splitter_outputs)
        self.widget_outputDetails.setObjectName(u"widget_outputDetails")
        self.verticalLayout_outputDetails = QVBoxLayout(self.widget_outputDetails)
        self.verticalLayout_outputDetails.setSpacing(3)
        self.verticalLayout_outputDetails.setObjectName(u"verticalLayout_outputDetails")
        self.verticalLayout_outputDetails.setContentsMargins(0, 0, 0, 0)
        self.frame_destinationStatus = QFrame(self.widget_outputDetails)
        self.frame_destinationStatus.setObjectName(u"frame_destinationStatus")
        self.frame_destinationStatus.setFrameShape(QFrame.NoFrame)
        self.horizontalLayout_destinationStatus = QHBoxLayout(self.frame_destinationStatus)
        self.horizontalLayout_destinationStatus.setObjectName(u"horizontalLayout_destinationStatus")
        self.horizontalLayout_destinationStatus.setContentsMargins(8, 5, 8, 5)
        self.label_destinationStatus = QLabel(self.frame_destinationStatus)
        self.label_destinationStatus.setObjectName(u"label_destinationStatus")
        self.label_destinationStatus.setTextFormat(Qt.RichText)
        self.label_destinationStatus.setWordWrap(True)
        self.label_destinationStatus.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.horizontalLayout_destinationStatus.addWidget(self.label_destinationStatus)


        self.verticalLayout_outputDetails.addWidget(self.frame_destinationStatus)

        self.stackedWidget_outputs = QStackedWidget(self.widget_outputDetails)
        self.stackedWidget_outputs.setObjectName(u"stackedWidget_outputs")
        self.stackedWidget_outputs.setFrameShape(QFrame.StyledPanel)
        self.tab_textFiles = QWidget()
        self.tab_textFiles.setObjectName(u"tab_textFiles")
        sizePolicy8 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(0)
        sizePolicy8.setHeightForWidth(self.tab_textFiles.sizePolicy().hasHeightForWidth())
        self.tab_textFiles.setSizePolicy(sizePolicy8)
        self.formLayout_2 = QFormLayout(self.tab_textFiles)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.formLayout_2.setVerticalSpacing(3)
        self.formLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.label_7 = QLabel(self.tab_textFiles)
        self.label_7.setObjectName(u"label_7")

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_7)

        self.widget_5 = QWidget(self.tab_textFiles)
        self.widget_5.setObjectName(u"widget_5")
        sizePolicy9 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy9.setHorizontalStretch(0)
        sizePolicy9.setVerticalStretch(0)
        sizePolicy9.setHeightForWidth(self.widget_5.sizePolicy().hasHeightForWidth())
        self.widget_5.setSizePolicy(sizePolicy9)
        self.horizontalLayout_6 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.lineEdit_folder = QLineEdit(self.widget_5)
        self.lineEdit_folder.setObjectName(u"lineEdit_folder")
        self.lineEdit_folder.setReadOnly(True)

        self.horizontalLayout_6.addWidget(self.lineEdit_folder)

        self.pushButton_selectFolder = QToolButton(self.widget_5)
        self.pushButton_selectFolder.setObjectName(u"pushButton_selectFolder")

        self.horizontalLayout_6.addWidget(self.pushButton_selectFolder)

        self.toolButton_trashFolder = QToolButton(self.widget_5)
        self.toolButton_trashFolder.setObjectName(u"toolButton_trashFolder")

        self.horizontalLayout_6.addWidget(self.toolButton_trashFolder)


        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.widget_5)

        self.widget_12 = QWidget(self.tab_textFiles)
        self.widget_12.setObjectName(u"widget_12")
        sizePolicy9.setHeightForWidth(self.widget_12.sizePolicy().hasHeightForWidth())
        self.widget_12.setSizePolicy(sizePolicy9)
        self.horizontalLayout_14 = QVBoxLayout(self.widget_12)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.checkBox_saveCsv = QCheckBox(self.widget_12)
        self.checkBox_saveCsv.setObjectName(u"checkBox_saveCsv")

        self.horizontalLayout_14.addWidget(self.checkBox_saveCsv)

        self.checkBox_saveXML = QCheckBox(self.widget_12)
        self.checkBox_saveXML.setObjectName(u"checkBox_saveXML")

        self.horizontalLayout_14.addWidget(self.checkBox_saveXML)


        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.FieldRole, self.widget_12)

        self.label_append = QLabel(self.tab_textFiles)
        self.label_append.setObjectName(u"label_append")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_append)

        self.comboBox_appendMethod = QComboBox(self.tab_textFiles)
        self.comboBox_appendMethod.addItem("")
        self.comboBox_appendMethod.addItem("")
        self.comboBox_appendMethod.addItem("")
        self.comboBox_appendMethod.addItem("")
        self.comboBox_appendMethod.setObjectName(u"comboBox_appendMethod")
        sizePolicy9.setHeightForWidth(self.comboBox_appendMethod.sizePolicy().hasHeightForWidth())
        self.comboBox_appendMethod.setSizePolicy(sizePolicy9)

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.comboBox_appendMethod)

        self.label_savePerSec = QLabel(self.tab_textFiles)
        self.label_savePerSec.setObjectName(u"label_savePerSec")

        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_savePerSec)

        self.widget_aggsPerSecond = QWidget(self.tab_textFiles)
        self.widget_aggsPerSecond.setObjectName(u"widget_aggsPerSecond")
        self.horizontalLayout_aggsPerSecond = QHBoxLayout(self.widget_aggsPerSecond)
        self.horizontalLayout_aggsPerSecond.setObjectName(u"horizontalLayout_aggsPerSecond")
        self.horizontalLayout_aggsPerSecond.setContentsMargins(0, 0, 0, 0)
        self.horizontalSlider_aggsPerSecond = QSlider(self.widget_aggsPerSecond)
        self.horizontalSlider_aggsPerSecond.setObjectName(u"horizontalSlider_aggsPerSecond")
        self.horizontalSlider_aggsPerSecond.setMinimum(1)
        self.horizontalSlider_aggsPerSecond.setMaximum(10)
        self.horizontalSlider_aggsPerSecond.setPageStep(1)
        self.horizontalSlider_aggsPerSecond.setValue(5)
        self.horizontalSlider_aggsPerSecond.setOrientation(Qt.Horizontal)
        self.horizontalSlider_aggsPerSecond.setTickPosition(QSlider.TicksBelow)

        self.horizontalLayout_aggsPerSecond.addWidget(self.horizontalSlider_aggsPerSecond)

        self.label_aggsPerSecondValue = QLabel(self.widget_aggsPerSecond)
        self.label_aggsPerSecondValue.setObjectName(u"label_aggsPerSecondValue")
        self.label_aggsPerSecondValue.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_aggsPerSecond.addWidget(self.label_aggsPerSecondValue)


        self.formLayout_2.setWidget(3, QFormLayout.ItemRole.FieldRole, self.widget_aggsPerSecond)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.formLayout_2.setItem(4, QFormLayout.ItemRole.FieldRole, self.verticalSpacer_2)

        self.stackedWidget_outputs.addWidget(self.tab_textFiles)
        self.tab_browser = QWidget()
        self.tab_browser.setObjectName(u"tab_browser")
        self.verticalLayout_4 = QVBoxLayout(self.tab_browser)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_8 = QLabel(self.tab_browser)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setTextFormat(Qt.RichText)
        self.label_8.setWordWrap(True)
        self.label_8.setOpenExternalLinks(True)
        self.label_8.setTextInteractionFlags(Qt.LinksAccessibleByMouse|Qt.TextSelectableByMouse)

        self.verticalLayout_4.addWidget(self.label_8, 0, Qt.AlignTop)

        self.stackedWidget_outputs.addWidget(self.tab_browser)
        self.tab_obs = QWidget()
        self.tab_obs.setObjectName(u"tab_obs")
        self.gridLayout_2 = QGridLayout(self.tab_obs)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setVerticalSpacing(2)
        self.widget_obsConnection = QWidget(self.tab_obs)
        self.widget_obsConnection.setObjectName(u"widget_obsConnection")
        self.horizontalLayout_obsConnection = QHBoxLayout(self.widget_obsConnection)
        self.horizontalLayout_obsConnection.setObjectName(u"horizontalLayout_obsConnection")
        self.horizontalLayout_obsConnection.setContentsMargins(0, 0, 0, 0)
        self.pushButton_connectObs = QPushButton(self.widget_obsConnection)
        self.pushButton_connectObs.setObjectName(u"pushButton_connectObs")
        sizePolicy10 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy10.setHorizontalStretch(0)
        sizePolicy10.setVerticalStretch(0)
        sizePolicy10.setHeightForWidth(self.pushButton_connectObs.sizePolicy().hasHeightForWidth())
        self.pushButton_connectObs.setSizePolicy(sizePolicy10)
        self.pushButton_connectObs.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_obsConnection.addWidget(self.pushButton_connectObs)

        self.pushButton_disconnectObs = QPushButton(self.widget_obsConnection)
        self.pushButton_disconnectObs.setObjectName(u"pushButton_disconnectObs")
        self.pushButton_disconnectObs.setEnabled(False)
        sizePolicy7.setHeightForWidth(self.pushButton_disconnectObs.sizePolicy().hasHeightForWidth())
        self.pushButton_disconnectObs.setSizePolicy(sizePolicy7)

        self.horizontalLayout_obsConnection.addWidget(self.pushButton_disconnectObs)


        self.gridLayout_2.addWidget(self.widget_obsConnection, 0, 0, 1, 1)

        self.widget_18 = QWidget(self.tab_obs)
        self.widget_18.setObjectName(u"widget_18")
        self.horizontalLayout_22 = QHBoxLayout(self.widget_18)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.lineEdit_sceneName = QLineEdit(self.widget_18)
        self.lineEdit_sceneName.setObjectName(u"lineEdit_sceneName")
        self.lineEdit_sceneName.setEnabled(False)

        self.horizontalLayout_22.addWidget(self.lineEdit_sceneName)

        self.pushButton_createOBSScene = QPushButton(self.widget_18)
        self.pushButton_createOBSScene.setObjectName(u"pushButton_createOBSScene")
        self.pushButton_createOBSScene.setEnabled(False)

        self.horizontalLayout_22.addWidget(self.pushButton_createOBSScene)

        self.checkBox_recreate = QCheckBox(self.widget_18)
        self.checkBox_recreate.setObjectName(u"checkBox_recreate")
        self.checkBox_recreate.setEnabled(False)
        self.checkBox_recreate.setChecked(True)

        self.horizontalLayout_22.addWidget(self.checkBox_recreate)


        self.gridLayout_2.addWidget(self.widget_18, 1, 0, 1, 1, Qt.AlignTop)

        self.verticalSpacer_obs = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_obs, 2, 0, 1, 1)

        self.stackedWidget_outputs.addWidget(self.tab_obs)
        self.tab_vmix = QWidget()
        self.tab_vmix.setObjectName(u"tab_vmix")
        self.gridLayout_3 = QGridLayout(self.tab_vmix)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setVerticalSpacing(2)
        self.tableView_vmixMapping = QTableView(self.tab_vmix)
        self.tableView_vmixMapping.setObjectName(u"tableView_vmixMapping")
        self.tableView_vmixMapping.setMinimumSize(QSize(0, 120))
        self.tableView_vmixMapping.horizontalHeader().setVisible(False)
        self.tableView_vmixMapping.horizontalHeader().setStretchLastSection(True)

        self.gridLayout_3.addWidget(self.tableView_vmixMapping, 1, 0, 1, 1)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.connectionWidget = QWidget(self.tab_vmix)
        self.connectionWidget.setObjectName(u"connectionWidget")
        self.horizontalLayout_18 = QHBoxLayout(self.connectionWidget)
        self.horizontalLayout_18.setSpacing(3)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.connectionLabel = QLabel(self.connectionWidget)
        self.connectionLabel.setObjectName(u"connectionLabel")

        self.horizontalLayout_18.addWidget(self.connectionLabel)

        self.lineEdit_vmixHost = QLineEdit(self.connectionWidget)
        self.lineEdit_vmixHost.setObjectName(u"lineEdit_vmixHost")
        self.lineEdit_vmixHost.setText(u"localhost")

        self.horizontalLayout_18.addWidget(self.lineEdit_vmixHost)

        self.label_5 = QLabel(self.connectionWidget)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_18.addWidget(self.label_5)

        self.lineEdit_vmixPort = QLineEdit(self.connectionWidget)
        self.lineEdit_vmixPort.setObjectName(u"lineEdit_vmixPort")
        sizePolicy7.setHeightForWidth(self.lineEdit_vmixPort.sizePolicy().hasHeightForWidth())
        self.lineEdit_vmixPort.setSizePolicy(sizePolicy7)
        self.lineEdit_vmixPort.setMaximumSize(QSize(50, 16777215))
        self.lineEdit_vmixPort.setText(u"8088")

        self.horizontalLayout_18.addWidget(self.lineEdit_vmixPort)

        self.pushButton_startvmix = QPushButton(self.connectionWidget)
        self.pushButton_startvmix.setObjectName(u"pushButton_startvmix")
        sizePolicy7.setHeightForWidth(self.pushButton_startvmix.sizePolicy().hasHeightForWidth())
        self.pushButton_startvmix.setSizePolicy(sizePolicy7)
        self.pushButton_startvmix.setCheckable(True)
        self.pushButton_startvmix.setChecked(False)

        self.horizontalLayout_18.addWidget(self.pushButton_startvmix)


        self.verticalLayout_6.addWidget(self.connectionWidget)

        self.widget_16 = QWidget(self.tab_vmix)
        self.widget_16.setObjectName(u"widget_16")
        self.widget_16.setMinimumSize(QSize(0, 0))
        self.horizontalLayout_19 = QHBoxLayout(self.widget_16)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.horizontalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.vmixinputLabel = QLabel(self.widget_16)
        self.vmixinputLabel.setObjectName(u"vmixinputLabel")

        self.horizontalLayout_19.addWidget(self.vmixinputLabel)

        self.inputLineEdit_vmix = QLineEdit(self.widget_16)
        self.inputLineEdit_vmix.setObjectName(u"inputLineEdit_vmix")
        self.inputLineEdit_vmix.setText(u"1")

        self.horizontalLayout_19.addWidget(self.inputLineEdit_vmix)

        self.checkBox_vmix_send_same = QCheckBox(self.widget_16)
        self.checkBox_vmix_send_same.setObjectName(u"checkBox_vmix_send_same")

        self.horizontalLayout_19.addWidget(self.checkBox_vmix_send_same)


        self.verticalLayout_6.addWidget(self.widget_16)


        self.gridLayout_3.addLayout(self.verticalLayout_6, 0, 0, 1, 1)

        self.stackedWidget_outputs.addWidget(self.tab_vmix)
        self.tab_uno = QWidget()
        self.tab_uno.setObjectName(u"tab_uno")
        self.gridLayout_5 = QGridLayout(self.tab_uno)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.widget_uno_props = QWidget(self.tab_uno)
        self.widget_uno_props.setObjectName(u"widget_uno_props")
        self.verticalLayout_8 = QVBoxLayout(self.widget_uno_props)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.connectionWidget_2 = QWidget(self.widget_uno_props)
        self.connectionWidget_2.setObjectName(u"connectionWidget_2")
        self.horizontalLayout_29 = QHBoxLayout(self.connectionWidget_2)
        self.horizontalLayout_29.setSpacing(3)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(0, 0, 0, 0)
        self.connectionLabel_2 = QLabel(self.connectionWidget_2)
        self.connectionLabel_2.setObjectName(u"connectionLabel_2")

        self.horizontalLayout_29.addWidget(self.connectionLabel_2)

        self.lineEdit_unoUrl = QLineEdit(self.connectionWidget_2)
        self.lineEdit_unoUrl.setObjectName(u"lineEdit_unoUrl")
        self.lineEdit_unoUrl.setText(u"https://app.overlays.uno/apiv2/controlapps/.../api")

        self.horizontalLayout_29.addWidget(self.lineEdit_unoUrl)

        self.toolButton_toggleUno = QToolButton(self.connectionWidget_2)
        self.toolButton_toggleUno.setObjectName(u"toolButton_toggleUno")
        self.toolButton_toggleUno.setCheckable(True)

        self.horizontalLayout_29.addWidget(self.toolButton_toggleUno)


        self.verticalLayout_8.addWidget(self.connectionWidget_2)

        self.widget_26 = QWidget(self.widget_uno_props)
        self.widget_26.setObjectName(u"widget_26")
        self.widget_26.setMinimumSize(QSize(0, 0))
        self.horizontalLayout_30 = QHBoxLayout(self.widget_26)
        self.horizontalLayout_30.setObjectName(u"horizontalLayout_30")
        self.horizontalLayout_30.setContentsMargins(0, 5, 0, 5)
        self.checkBox_uno_send_same = QCheckBox(self.widget_26)
        self.checkBox_uno_send_same.setObjectName(u"checkBox_uno_send_same")
        sizePolicy7.setHeightForWidth(self.checkBox_uno_send_same.sizePolicy().hasHeightForWidth())
        self.checkBox_uno_send_same.setSizePolicy(sizePolicy7)

        self.horizontalLayout_30.addWidget(self.checkBox_uno_send_same)

        self.checkBox_uno_essentials = QCheckBox(self.widget_26)
        self.checkBox_uno_essentials.setObjectName(u"checkBox_uno_essentials")
        sizePolicy7.setHeightForWidth(self.checkBox_uno_essentials.sizePolicy().hasHeightForWidth())
        self.checkBox_uno_essentials.setSizePolicy(sizePolicy7)

        self.horizontalLayout_30.addWidget(self.checkBox_uno_essentials)


        self.verticalLayout_8.addWidget(self.widget_26)

        self.widget_uno_essentials_details = QWidget(self.widget_uno_props)
        self.widget_uno_essentials_details.setObjectName(u"widget_uno_essentials_details")
        self.horizontalLayout_21 = QHBoxLayout(self.widget_uno_essentials_details)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(0, 0, 0, 0)
        self.label_24 = QLabel(self.widget_uno_essentials_details)
        self.label_24.setObjectName(u"label_24")
        sizePolicy2.setHeightForWidth(self.label_24.sizePolicy().hasHeightForWidth())
        self.label_24.setSizePolicy(sizePolicy2)

        self.horizontalLayout_21.addWidget(self.label_24)

        self.lineEdit_uno_essentials_id = QLineEdit(self.widget_uno_essentials_details)
        self.lineEdit_uno_essentials_id.setObjectName(u"lineEdit_uno_essentials_id")
        sizePolicy10.setHeightForWidth(self.lineEdit_uno_essentials_id.sizePolicy().hasHeightForWidth())
        self.lineEdit_uno_essentials_id.setSizePolicy(sizePolicy10)
        self.lineEdit_uno_essentials_id.setText(u"")

        self.horizontalLayout_21.addWidget(self.lineEdit_uno_essentials_id)


        self.verticalLayout_8.addWidget(self.widget_uno_essentials_details)


        self.gridLayout_5.addWidget(self.widget_uno_props, 0, 0, 1, 1)

        self.tableView_unoMapping = QTableView(self.tab_uno)
        self.tableView_unoMapping.setObjectName(u"tableView_unoMapping")
        self.tableView_unoMapping.setMinimumSize(QSize(0, 120))
        self.tableView_unoMapping.horizontalHeader().setVisible(False)
        self.tableView_unoMapping.horizontalHeader().setStretchLastSection(True)

        self.gridLayout_5.addWidget(self.tableView_unoMapping, 2, 0, 1, 1)

        self.stackedWidget_outputs.addWidget(self.tab_uno)
        self.tab_api = QWidget()
        self.tab_api.setObjectName(u"tab_api")
        self.formLayout_3 = QFormLayout(self.tab_api)
        self.formLayout_3.setObjectName(u"formLayout_3")
        self.formLayout_3.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_3.setVerticalSpacing(3)
        self.checkBox_enableOutAPI = QCheckBox(self.tab_api)
        self.checkBox_enableOutAPI.setObjectName(u"checkBox_enableOutAPI")

        self.formLayout_3.setWidget(0, QFormLayout.ItemRole.FieldRole, self.checkBox_enableOutAPI)

        self.label_21 = QLabel(self.tab_api)
        self.label_21.setObjectName(u"label_21")

        self.formLayout_3.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_21)

        self.comboBox_api_encode = QComboBox(self.tab_api)
        self.comboBox_api_encode.addItem("")
        self.comboBox_api_encode.addItem("")
        self.comboBox_api_encode.addItem("")
        self.comboBox_api_encode.addItem("")
        self.comboBox_api_encode.setObjectName(u"comboBox_api_encode")

        self.formLayout_3.setWidget(4, QFormLayout.ItemRole.FieldRole, self.comboBox_api_encode)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.formLayout_3.setItem(5, QFormLayout.ItemRole.FieldRole, self.verticalSpacer)

        self.widget_24 = QWidget(self.tab_api)
        self.widget_24.setObjectName(u"widget_24")
        self.horizontalLayout_27 = QHBoxLayout(self.widget_24)
        self.horizontalLayout_27.setSpacing(2)
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.horizontalLayout_27.setContentsMargins(0, 0, 0, 0)
        self.lineEdit_api_url = QLineEdit(self.widget_24)
        self.lineEdit_api_url.setObjectName(u"lineEdit_api_url")

        self.horizontalLayout_27.addWidget(self.lineEdit_api_url)

        self.comboBox_outApiMethod = QComboBox(self.widget_24)
        self.comboBox_outApiMethod.addItem("")
        self.comboBox_outApiMethod.addItem("")
        self.comboBox_outApiMethod.addItem("")
        self.comboBox_outApiMethod.setObjectName(u"comboBox_outApiMethod")

        self.horizontalLayout_27.addWidget(self.comboBox_outApiMethod)


        self.formLayout_3.setWidget(1, QFormLayout.ItemRole.FieldRole, self.widget_24)

        self.label_20 = QLabel(self.tab_api)
        self.label_20.setObjectName(u"label_20")

        self.formLayout_3.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_20)

        self.stackedWidget_outputs.addWidget(self.tab_api)

        self.verticalLayout_outputDetails.addWidget(self.stackedWidget_outputs)

        self.splitter_outputs.addWidget(self.widget_outputDetails)

        self.verticalLayout_outputs.addWidget(self.splitter_outputs)

        self.tabWidget_inspector.addTab(self.widget_outputs, "")
        self.splitter_main.addWidget(self.tabWidget_inspector)

        self.horizontalLayout_31.addWidget(self.splitter_main)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuLanguage = QMenu(self.menuFile)
        self.menuLanguage.setObjectName(u"menuLanguage")
        self.menuAppearance = QMenu(self.menuFile)
        self.menuAppearance.setObjectName(u"menuAppearance")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menuFile.addAction(self.actionCheckForUpdates)
        self.menuFile.addAction(self.actionAbout)
        self.menuFile.addAction(self.actionViewLog)
        self.menuFile.addAction(self.actionImportConfiguration)
        self.menuFile.addAction(self.actionExportConfiguration)
        self.menuFile.addAction(self.actionOpenConfigurationFolder)
        self.menuFile.addAction(self.actionOCRTrainingDataSetup)
        self.menuFile.addAction(self.menuLanguage.menuAction())
        self.menuFile.addAction(self.menuAppearance.menuAction())

        self.retranslateUi(MainWindow)

        self.tabWidget_inspector.setCurrentIndex(0)
        self.stackedWidget_boxSettings.setCurrentIndex(0)
        self.stackedWidget_outputs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"ScoreSight", None))
        self.actionNewField.setText(QCoreApplication.translate("MainWindow", u"New custom field", None))
        self.actionPlaceOnPicture.setText(QCoreApplication.translate("MainWindow", u"Place on picture", None))
        self.actionRemoveFromPicture.setText(QCoreApplication.translate("MainWindow", u"Remove from picture", None))
        self.actionRenameField.setText(QCoreApplication.translate("MainWindow", u"Rename...", None))
        self.actionDeleteField.setText(QCoreApplication.translate("MainWindow", u"Delete field...", None))
        self.actionResetFieldSettings.setText(QCoreApplication.translate("MainWindow", u"Reset settings to defaults", None))
        self.actionCopyValue.setText(QCoreApplication.translate("MainWindow", u"Copy value", None))
        self.actionZoomToBox.setText(QCoreApplication.translate("MainWindow", u"Zoom to box", None))
        self.actionCheckForUpdates.setText(QCoreApplication.translate("MainWindow", u"Check for Updates", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionViewLog.setText(QCoreApplication.translate("MainWindow", u"View Current Log", None))
        self.actionImportConfiguration.setText(QCoreApplication.translate("MainWindow", u"Import Configuration", None))
        self.actionExportConfiguration.setText(QCoreApplication.translate("MainWindow", u"Export Configuration", None))
        self.actionOpenConfigurationFolder.setText(QCoreApplication.translate("MainWindow", u"Open Configuration Folder", None))
        self.actionOCRTrainingDataSetup.setText(QCoreApplication.translate("MainWindow", u"OCR Training Data Setup", None))
        self.actionPauseOutputs.setText(QCoreApplication.translate("MainWindow", u"Pause outputs", None))
        self.actionBinaryView.setText(QCoreApplication.translate("MainWindow", u"Binary View", None))
        self.actionFitPicture.setText(QCoreApplication.translate("MainWindow", u"Fit picture to window", None))
        self.actionReloadSources.setText(QCoreApplication.translate("MainWindow", u"Reload sources", None))
        self.label_fields.setText(QCoreApplication.translate("MainWindow", u"Fields", None))
#if QT_CONFIG(tooltip)
        self.pushButton_stopUpdates.setToolTip(QCoreApplication.translate("MainWindow", u"Freeze every output (text files, HTTP server, OBS, vMix, UNO, API) at its current values, for example during a timeout or a replay. The readings in this window keep updating.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_stopUpdates.setText(QCoreApplication.translate("MainWindow", u"Pause outputs", None))
#if QT_CONFIG(tooltip)
        self.toolButton_addBox.setToolTip(QCoreApplication.translate("MainWindow", u"New custom field", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.toolButton_addBox.setAccessibleName(QCoreApplication.translate("MainWindow", u"New custom field", None))
#endif // QT_CONFIG(accessibility)
        self.label_fieldsHint.setText(QCoreApplication.translate("MainWindow", u"Open a source to place fields on the picture.", None))
        ___qtablewidgetitem = self.tableWidget_boxes.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"Field", None))
        ___qtablewidgetitem1 = self.tableWidget_boxes.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"Value", None))
#if QT_CONFIG(tooltip)
        self.tableWidget_boxes.setToolTip(QCoreApplication.translate("MainWindow", u"The fields and their latest values. Click a field to select its box; double-click a custom field (or press F2) to rename it; right-click for more.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.tableWidget_boxes.setAccessibleName(QCoreApplication.translate("MainWindow", u"Fields and readings", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.pushButton_makeBox.setToolTip(QCoreApplication.translate("MainWindow", u"Put a box for the selected field on the picture, then drag it over the value. Formerly \u201cAdd to Scene\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_makeBox.setText(QCoreApplication.translate("MainWindow", u"Place on picture", None))
#if QT_CONFIG(tooltip)
        self.pushButton_removeBox.setToolTip(QCoreApplication.translate("MainWindow", u"Take the selected field's box off the picture. Its settings go back to the defaults. Formerly \u201cRemove Selected\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_removeBox.setText(QCoreApplication.translate("MainWindow", u"Remove from picture", None))
#if QT_CONFIG(tooltip)
        self.toolButton_removeBox.setToolTip(QCoreApplication.translate("MainWindow", u"Delete the selected custom field (the standard fields can't be deleted)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.toolButton_removeBox.setAccessibleName(QCoreApplication.translate("MainWindow", u"Delete the selected custom field", None))
#endif // QT_CONFIG(accessibility)
        self.toolButton_removeBox.setText(QCoreApplication.translate("MainWindow", u"Delete field", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Source", None))
        self.comboBox_camera_source.setItemText(0, QCoreApplication.translate("MainWindow", u"Select a source", None))
        self.comboBox_camera_source.setItemText(1, QCoreApplication.translate("MainWindow", u"Open a Video File", None))
        self.comboBox_camera_source.setItemText(2, QCoreApplication.translate("MainWindow", u"URL Source (HTTP, RTSP)", None))
        self.comboBox_camera_source.setItemText(3, QCoreApplication.translate("MainWindow", u"Screen Capture", None))

#if QT_CONFIG(accessibility)
        self.comboBox_camera_source.setAccessibleName(QCoreApplication.translate("MainWindow", u"Source", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_camera_source.setToolTip(QCoreApplication.translate("MainWindow", u"The video source: a camera, capture card or NDI source, a video file, a stream URL or a screen capture", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.toolButton_videoSettings.setToolTip(QCoreApplication.translate("MainWindow", u"The resolution, frame rate and format of a camera or capture card. Only for cameras and capture cards.", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_videoSettings.setText(QCoreApplication.translate("MainWindow", u"Video Settings", None))
#if QT_CONFIG(tooltip)
        self.pushButton_refresh_sources.setToolTip(QCoreApplication.translate("MainWindow", u"Refresh Sources", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_refresh_sources.setText(QCoreApplication.translate("MainWindow", u"Reload", None))
#if QT_CONFIG(tooltip)
        self.pushButton_saveOCRTrainingData.setToolTip(QCoreApplication.translate("MainWindow", u"Save the box images and readings for training an OCR model (see File > OCR Training Data Setup)", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_saveOCRTrainingData.setText(QCoreApplication.translate("MainWindow", u"Save OCR Training Data", None))
#if QT_CONFIG(tooltip)
        self.pushButton_binary.setToolTip(QCoreApplication.translate("MainWindow", u"Show what the OCR reads: the black-and-white image of every box", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_binary.setText(QCoreApplication.translate("MainWindow", u"Binary View", None))
#if QT_CONFIG(tooltip)
        self.pushButton_fourCorner.setToolTip(QCoreApplication.translate("MainWindow", u"Correct the perspective: click the 4 corners of the scoreboard. Clicking it again removes the correction.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_fourCorner.setText(QCoreApplication.translate("MainWindow", u"4-corner Correction", None))
#if QT_CONFIG(tooltip)
        self.toolButton_topCrop.setToolTip(QCoreApplication.translate("MainWindow", u"Apply cropping to the entire image", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_topCrop.setText(QCoreApplication.translate("MainWindow", u"Crop", None))
#if QT_CONFIG(tooltip)
        self.toolButton_rotate.setToolTip(QCoreApplication.translate("MainWindow", u"Rotate the picture by 90 degrees", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_rotate.setText(QCoreApplication.translate("MainWindow", u"Rotate", None))
#if QT_CONFIG(tooltip)
        self.pushButton_stabilize.setToolTip(QCoreApplication.translate("MainWindow", u"Compensate for a shaking camera", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_stabilize.setText(QCoreApplication.translate("MainWindow", u"Stabilize", None))
        self.comboBox_boxDisplayStyle.setItemText(0, QCoreApplication.translate("MainWindow", u"No Box", None))
        self.comboBox_boxDisplayStyle.setItemText(1, QCoreApplication.translate("MainWindow", u"Outline", None))
        self.comboBox_boxDisplayStyle.setItemText(2, QCoreApplication.translate("MainWindow", u"Names", None))
        self.comboBox_boxDisplayStyle.setItemText(3, QCoreApplication.translate("MainWindow", u"All", None))

#if QT_CONFIG(accessibility)
        self.comboBox_boxDisplayStyle.setAccessibleName(QCoreApplication.translate("MainWindow", u"Box display style", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_boxDisplayStyle.setToolTip(QCoreApplication.translate("MainWindow", u"What the viewer draws for each box: nothing, the outline, the outline and the name, or everything", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.toolButton_osd.setToolTip(QCoreApplication.translate("MainWindow", u"Show Statistics", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_osd.setText(QCoreApplication.translate("MainWindow", u"OSD", None))
#if QT_CONFIG(tooltip)
        self.toolButton_zoomReset.setToolTip(QCoreApplication.translate("MainWindow", u"Reset zoom", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_zoomReset.setText(QCoreApplication.translate("MainWindow", u"1:1", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Ctrl-scroll to zoom", None))
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"Left", None))
#if QT_CONFIG(tooltip)
        self.spinBox_leftCrop.setToolTip(QCoreApplication.translate("MainWindow", u"Pixels to cut off the left edge", None))
#endif // QT_CONFIG(tooltip)
        self.spinBox_leftCrop.setSuffix(QCoreApplication.translate("MainWindow", u"px", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"Top", None))
#if QT_CONFIG(tooltip)
        self.spinBox_topCrop.setToolTip(QCoreApplication.translate("MainWindow", u"Pixels to cut off the top edge", None))
#endif // QT_CONFIG(tooltip)
        self.spinBox_topCrop.setSuffix(QCoreApplication.translate("MainWindow", u"px", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Right", None))
#if QT_CONFIG(tooltip)
        self.spinBox_rightCrop.setToolTip(QCoreApplication.translate("MainWindow", u"Pixels to cut off the right edge", None))
#endif // QT_CONFIG(tooltip)
        self.spinBox_rightCrop.setSuffix(QCoreApplication.translate("MainWindow", u"px", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Bottom", None))
#if QT_CONFIG(tooltip)
        self.spinBox_bottomCrop.setToolTip(QCoreApplication.translate("MainWindow", u"Pixels to cut off the bottom edge", None))
#endif // QT_CONFIG(tooltip)
        self.spinBox_bottomCrop.setSuffix(QCoreApplication.translate("MainWindow", u"px", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Speed", None))
#if QT_CONFIG(tooltip)
        self.toolButton_speed.setToolTip(QCoreApplication.translate("MainWindow", u"The playback speed of a video file (skips frames). Doesn't change how often the boxes are read.", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_speed.setText(QCoreApplication.translate("MainWindow", u"x1", None))
#if QT_CONFIG(tooltip)
        self.pushButton_resumeOutputs.setToolTip(QCoreApplication.translate("MainWindow", u"Send the current values to every output again", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_resumeOutputs.setText(QCoreApplication.translate("MainWindow", u"Resume outputs", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"### Open a Camera or Load a File", None))
#if QT_CONFIG(accessibility)
        self.tabWidget_inspector.setAccessibleName(QCoreApplication.translate("MainWindow", u"Inspector", None))
#endif // QT_CONFIG(accessibility)
        self.label_boxEmptyTitle.setText(QCoreApplication.translate("MainWindow", u"No field selected", None))
        self.label_boxEmpty.setText(QCoreApplication.translate("MainWindow", u"Select a field in the list or a box on the picture to tune how it is read. Start with Type and Format.", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Settings for this field only", None))
#if QT_CONFIG(tooltip)
        self.pushButton_restoreDefaults.setToolTip(QCoreApplication.translate("MainWindow", u"Put every setting of this field back to its default. Formerly \u201cDefaults\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_restoreDefaults.setText(QCoreApplication.translate("MainWindow", u"Reset to defaults", None))
        self.label_sectionReading.setText(QCoreApplication.translate("MainWindow", u"Reading", None))
#if QT_CONFIG(tooltip)
        self.label_13.setToolTip(QCoreApplication.translate("MainWindow", u"Which characters the OCR may output", None))
#endif // QT_CONFIG(tooltip)
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Type", None))
        self.comboBox_fieldType.setItemText(0, QCoreApplication.translate("MainWindow", u"Number 0-9", None))
        self.comboBox_fieldType.setItemText(1, QCoreApplication.translate("MainWindow", u"Time 0-9 , . :", None))
        self.comboBox_fieldType.setItemText(2, QCoreApplication.translate("MainWindow", u"Text", None))

#if QT_CONFIG(accessibility)
        self.comboBox_fieldType.setAccessibleName(QCoreApplication.translate("MainWindow", u"Type", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_fieldType.setToolTip(QCoreApplication.translate("MainWindow", u"Which characters the OCR may output. Choose the narrowest: Number for scores, Time for clocks, Text only for words.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_2.setToolTip(QCoreApplication.translate("MainWindow", u"A regular expression the raw reading must match completely", None))
#endif // QT_CONFIG(tooltip)
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Format", None))
        self.comboBox_formatPrefix.setItemText(0, QCoreApplication.translate("MainWindow", u"Time mm:ss.d", None))
        self.comboBox_formatPrefix.setItemText(1, QCoreApplication.translate("MainWindow", u"Time mm:ss", None))
        self.comboBox_formatPrefix.setItemText(2, QCoreApplication.translate("MainWindow", u"Time ss.d", None))
        self.comboBox_formatPrefix.setItemText(3, QCoreApplication.translate("MainWindow", u"Time 0-59", None))
        self.comboBox_formatPrefix.setItemText(4, QCoreApplication.translate("MainWindow", u"Shotclock 0-39", None))
        self.comboBox_formatPrefix.setItemText(5, QCoreApplication.translate("MainWindow", u"Score 1dd", None))
        self.comboBox_formatPrefix.setItemText(6, QCoreApplication.translate("MainWindow", u"Score ddd", None))
        self.comboBox_formatPrefix.setItemText(7, QCoreApplication.translate("MainWindow", u"Period 1-4", None))
        self.comboBox_formatPrefix.setItemText(8, QCoreApplication.translate("MainWindow", u"Period d", None))
        self.comboBox_formatPrefix.setItemText(9, QCoreApplication.translate("MainWindow", u"Alphanumeric", None))
        self.comboBox_formatPrefix.setItemText(10, QCoreApplication.translate("MainWindow", u"Any text", None))
        self.comboBox_formatPrefix.setItemText(11, QCoreApplication.translate("MainWindow", u"Any number", None))
        self.comboBox_formatPrefix.setItemText(12, QCoreApplication.translate("MainWindow", u"Custom", None))

#if QT_CONFIG(accessibility)
        self.comboBox_formatPrefix.setAccessibleName(QCoreApplication.translate("MainWindow", u"Format preset", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_formatPrefix.setToolTip(QCoreApplication.translate("MainWindow", u"The preset whose expression is used, or Custom. Choose a preset to use its expression. Formerly \u201cSelect Preset\u201d.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.lineEdit_format.setAccessibleName(QCoreApplication.translate("MainWindow", u"Format expression", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_format.setToolTip(QCoreApplication.translate("MainWindow", u"A regular expression the raw reading must match completely, or it's rejected. Choose a preset above or type your own. An invalid expression is ignored.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_removeLeadingZeros.setToolTip(QCoreApplication.translate("MainWindow", u"Remove zeros at the start: 07 becomes 7. Formerly \u201cRemove leading 0s\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_removeLeadingZeros.setText(QCoreApplication.translate("MainWindow", u"Remove leading zeros", None))
        self.label_removeLeadingZerosHint.setText(QCoreApplication.translate("MainWindow", u"07 \u2192 7", None))
#if QT_CONFIG(tooltip)
        self.checkBox_ordinalIndicator.setToolTip(QCoreApplication.translate("MainWindow", u"Add an ordinal suffix: 1 becomes 1st, 2 becomes 2nd. Formerly \u201cOrdinal (1st, 2nd, ..)\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_ordinalIndicator.setText(QCoreApplication.translate("MainWindow", u"Add ordinal suffix", None))
        self.label_ordinalIndicatorHint.setText(QCoreApplication.translate("MainWindow", u"2 \u2192 2nd", None))
#if QT_CONFIG(tooltip)
        self.checkBox_dotDetector.setToolTip(QCoreApplication.translate("MainWindow", u"Count the lit dots or lights in the box (for example a period or possession indicator) instead of reading characters. Formerly \u201cDot Counter\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_dotDetector.setText(QCoreApplication.translate("MainWindow", u"Count lights (dot counter)", None))
        self.label_sectionFiltering.setText(QCoreApplication.translate("MainWindow", u"Filtering", None))
#if QT_CONFIG(tooltip)
        self.label_3.setToolTip(QCoreApplication.translate("MainWindow", u"Minimum OCR confidence in % (0-99): Tesseract's confidence in the reading. A reading below it is rejected. 0 turns the check off. Formerly \u201cConf. Th\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Minimum confidence", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_conf_thresh.setAccessibleName(QCoreApplication.translate("MainWindow", u"Minimum confidence", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_conf_thresh.setToolTip(QCoreApplication.translate("MainWindow", u"Minimum OCR confidence in % (0-99): Tesseract's confidence in the reading. A reading below it is rejected (yellow, FailedFilter). 0 turns the check off.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_smoothing.setToolTip(QCoreApplication.translate("MainWindow", u"Show the most common of the box's last 5 accepted readings, to steady a value that flickers. Delays changes by a couple of detection cycles. Formerly \u201cAverage Output\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_smoothing.setText(QCoreApplication.translate("MainWindow", u"Smooth over last 5 readings", None))
#if QT_CONFIG(tooltip)
        self.checkBox_skip_similar_image.setToolTip(QCoreApplication.translate("MainWindow", u"Skip OCR while the box's image hasn't changed since its last accepted reading, and repeat that value. Saves CPU on values that change rarely. Formerly \u201cSkip Similar Image\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_skip_similar_image.setText(QCoreApplication.translate("MainWindow", u"Skip OCR while image is unchanged", None))
        self.label_skipSimilarImageHint.setText(QCoreApplication.translate("MainWindow", u"saves CPU", None))
#if QT_CONFIG(tooltip)
        self.toolButton_imageCleanup.setToolTip(QCoreApplication.translate("MainWindow", u"Show or hide the settings that clean up the box's image before it is read. Binary view shows the result.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.toolButton_imageCleanup.setAccessibleName(QCoreApplication.translate("MainWindow", u"Image cleanup", None))
#endif // QT_CONFIG(accessibility)
        self.toolButton_imageCleanup.setText(QCoreApplication.translate("MainWindow", u"Image cleanup", None))
#if QT_CONFIG(tooltip)
        self.toolButton_cleanupBinary.setToolTip(QCoreApplication.translate("MainWindow", u"Show what the OCR reads: the black-and-white image of every box", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_cleanupBinary.setText(QCoreApplication.translate("MainWindow", u"Binary view", None))
#if QT_CONFIG(tooltip)
        self.label_binarizationMethod.setToolTip(QCoreApplication.translate("MainWindow", u"How the box is turned into black and white before OCR. Formerly \u201cBinarize\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_binarizationMethod.setText(QCoreApplication.translate("MainWindow", u"Black & white", None))
        self.comboBox_binarizationMethod.setItemText(0, QCoreApplication.translate("MainWindow", u"Whole picture", None))
        self.comboBox_binarizationMethod.setItemText(1, QCoreApplication.translate("MainWindow", u"None", None))
        self.comboBox_binarizationMethod.setItemText(2, QCoreApplication.translate("MainWindow", u"This box", None))
        self.comboBox_binarizationMethod.setItemText(3, QCoreApplication.translate("MainWindow", u"Adaptive", None))

#if QT_CONFIG(accessibility)
        self.comboBox_binarizationMethod.setAccessibleName(QCoreApplication.translate("MainWindow", u"Black and white", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_binarizationMethod.setToolTip(QCoreApplication.translate("MainWindow", u"How the box is turned into black and white before OCR. Whole picture: one threshold for the whole picture. None: the grayscale image. This box: a threshold for this box only. Adaptive: a threshold that varies across the box, for uneven lighting.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_4.setToolTip(QCoreApplication.translate("MainWindow", u"Remove specks smaller than a share of the box area (0 = off). Formerly \u201cCleanup\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Remove specks", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_cleanup.setAccessibleName(QCoreApplication.translate("MainWindow", u"Remove specks", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_cleanup.setToolTip(QCoreApplication.translate("MainWindow", u"Remove specks smaller than a share of the box area (0 = off). Too high a value erases thin digits such as 1.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_15.setToolTip(QCoreApplication.translate("MainWindow", u"Squash the box vertically (100 % = unchanged). Formerly \u201cV.Scale\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Squash height", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_vscale.setAccessibleName(QCoreApplication.translate("MainWindow", u"Squash height", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_vscale.setToolTip(QCoreApplication.translate("MainWindow", u"Squash the box vertically (100 % = unchanged), for very tall, narrow fonts", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_14.setToolTip(QCoreApplication.translate("MainWindow", u"Shear the image to straighten slanted digits (0 = off). Formerly \u201cSkew\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Straighten slant", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_skew.setAccessibleName(QCoreApplication.translate("MainWindow", u"Straighten slant", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_skew.setToolTip(QCoreApplication.translate("MainWindow", u"Shear the image horizontally to straighten slanted (italic) digits (0 = off)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_9.setToolTip(QCoreApplication.translate("MainWindow", u"Thicken the bright strokes (0 = off). Formerly \u201cDilate\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Thicken strokes", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_dilate.setAccessibleName(QCoreApplication.translate("MainWindow", u"Thicken strokes", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_dilate.setToolTip(QCoreApplication.translate("MainWindow", u"Thicken the bright strokes by this many passes (0 = off). Raise it when the segments of 7-segment digits don't touch; lower it when digits merge.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_invertPatch.setToolTip(QCoreApplication.translate("MainWindow", u"Swap black and white before OCR, for dark digits on a light background. Formerly \u201cInvert Input\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_invertPatch.setText(QCoreApplication.translate("MainWindow", u"Invert colors", None))
#if QT_CONFIG(tooltip)
        self.checkBox_autocrop.setToolTip(QCoreApplication.translate("MainWindow", u"Crop the box to the area with bright pixels, plus a margin, before OCR. Formerly \u201cAuto Crop\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_autocrop.setText(QCoreApplication.translate("MainWindow", u"Crop to text", None))
#if QT_CONFIG(tooltip)
        self.checkBox_rescalePatch.setToolTip(QCoreApplication.translate("MainWindow", u"Scale the image to 35 pixels high, a favorable size for OCR. Formerly \u201cRescale Input\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_rescalePatch.setText(QCoreApplication.translate("MainWindow", u"Resize to 35 px (recommended)", None))
#if QT_CONFIG(tooltip)
        self.checkBox_normWHRatio.setToolTip(QCoreApplication.translate("MainWindow", u"Scale to a favorable 1:2 width-to-height ratio. Formerly \u201cNormalize W-H Ratio\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_normWHRatio.setText(QCoreApplication.translate("MainWindow", u"Normalize digit width", None))
        self.label_legacy.setText(QCoreApplication.translate("MainWindow", u"Experimental / legacy", None))
#if QT_CONFIG(tooltip)
        self.checkBox_compositeBox.setToolTip(QCoreApplication.translate("MainWindow", u"Experimental: draw one sub-box per character with the green + in the box. Recognition still reads the whole box. Formerly \u201cComposite (Per-Character)\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_compositeBox.setText(QCoreApplication.translate("MainWindow", u"Per-character sub-boxes", None))
        self.label_compositeBoxHint.setText(QCoreApplication.translate("MainWindow", u"not used for reading yet", None))
#if QT_CONFIG(tooltip)
        self.checkBox_skip_empty.setToolTip(QCoreApplication.translate("MainWindow", u"Never write an empty value to the box's text file or OBS text source. Since 0.2.0 they only ever get good readings, so this has no effect. Formerly \u201cSkip Empty Values\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_skip_empty.setText(QCoreApplication.translate("MainWindow", u"Skip empty values", None))
        self.label_skipEmptyHint.setText(QCoreApplication.translate("MainWindow", u"no effect since 0.2.0", None))
        self.label_sectionTemplate.setText(QCoreApplication.translate("MainWindow", u"Template", None))
#if QT_CONFIG(tooltip)
        self.checkBox_templatefield.setToolTip(QCoreApplication.translate("MainWindow", u"Make this custom field a template: its value is built from other fields, for example {{Home Score}} - {{Away Score}}. Formerly \u201cTemplate Field\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_templatefield.setText(QCoreApplication.translate("MainWindow", u"Build from other fields", None))
#if QT_CONFIG(accessibility)
        self.lineEdit_templatefield.setAccessibleName(QCoreApplication.translate("MainWindow", u"Template", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_templatefield.setToolTip(QCoreApplication.translate("MainWindow", u"The template text, with the fields in double braces, for example {{Home Score}} - {{Away Score}}", None))
#endif // QT_CONFIG(tooltip)
        self.lineEdit_templatefield.setPlaceholderText(QCoreApplication.translate("MainWindow", u"{{Home Score}} - {{Away Score}}", None))
#if QT_CONFIG(tooltip)
        self.toolButton_insertField.setToolTip(QCoreApplication.translate("MainWindow", u"Insert a field at the cursor, written exactly as the template needs it", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_insertField.setText(QCoreApplication.translate("MainWindow", u"Insert field", None))
        self.groupBox_allBoxes.setTitle(QCoreApplication.translate("MainWindow", u"All boxes", None))
        self.label_allBoxesScope.setText(QCoreApplication.translate("MainWindow", u"Changes how every field is read", None))
#if QT_CONFIG(tooltip)
        self.label_10.setToolTip(QCoreApplication.translate("MainWindow", u"The OCR model that reads every box", None))
#endif // QT_CONFIG(tooltip)
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"OCR model", None))
#if QT_CONFIG(accessibility)
        self.comboBox_ocrModel.setAccessibleName(QCoreApplication.translate("MainWindow", u"OCR model", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.comboBox_ocrModel.setToolTip(QCoreApplication.translate("MainWindow", u"The OCR model that reads every box, not only the selected one. Load external model... reads a Tesseract .traineddata file.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_detectionCadence.setToolTip(QCoreApplication.translate("MainWindow", u"How many times per second the boxes are read", None))
#endif // QT_CONFIG(tooltip)
        self.label_detectionCadence.setText(QCoreApplication.translate("MainWindow", u"Detections / s", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_detectionCadence.setAccessibleName(QCoreApplication.translate("MainWindow", u"Detections per second", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_detectionCadence.setToolTip(QCoreApplication.translate("MainWindow", u"How many times per second the boxes are read (1-15). Higher values use more CPU; 5 suits most clocks.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_updateOnchange.setToolTip(QCoreApplication.translate("MainWindow", u"Report a reading that equals the field's last good value as unchanged (=, SameNoChange) instead of new (\u2713). vMix and UNO then don't resend unchanged values (unless their Send Same? is on), and the HTTP server and the outbound API mark them as unchanged. OBS and the text files get a value only when it changes either way.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_updateOnchange.setText(QCoreApplication.translate("MainWindow", u"Update on change", None))
        self.tabWidget_inspector.setTabText(self.tabWidget_inspector.indexOf(self.tab_box), QCoreApplication.translate("MainWindow", u"Box", None))
#if QT_CONFIG(accessibility)
        self.listView_destinations.setAccessibleName(QCoreApplication.translate("MainWindow", u"Outputs", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(accessibility)
        self.listView_destinations.setAccessibleDescription(QCoreApplication.translate("MainWindow", u"Select an output to show its settings below. Space turns it on or off.", None))
#endif // QT_CONFIG(accessibility)
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Folder", None))
#if QT_CONFIG(tooltip)
        self.lineEdit_folder.setToolTip(QCoreApplication.translate("MainWindow", u"The folder the text files are written to", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.pushButton_selectFolder.setToolTip(QCoreApplication.translate("MainWindow", u"Choose the output folder", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_selectFolder.setText(QCoreApplication.translate("MainWindow", u"Open", None))
#if QT_CONFIG(tooltip)
        self.toolButton_trashFolder.setToolTip(QCoreApplication.translate("MainWindow", u"Stop writing files (forget the folder)", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_trashFolder.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
#if QT_CONFIG(tooltip)
        self.checkBox_saveCsv.setToolTip(QCoreApplication.translate("MainWindow", u"Also write results.csv: a timestamp and a column per field", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_saveCsv.setText(QCoreApplication.translate("MainWindow", u"Save .csv file", None))
#if QT_CONFIG(tooltip)
        self.checkBox_saveXML.setToolTip(QCoreApplication.translate("MainWindow", u"Also write results.xml: every field with its name, text, state and position", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_saveXML.setText(QCoreApplication.translate("MainWindow", u"Save .xml file", None))
#if QT_CONFIG(tooltip)
        self.label_append.setToolTip(QCoreApplication.translate("MainWindow", u"Add each new value to a log, or keep only the latest values", None))
#endif // QT_CONFIG(tooltip)
        self.label_append.setText(QCoreApplication.translate("MainWindow", u"Append", None))
        self.comboBox_appendMethod.setItemText(0, QCoreApplication.translate("MainWindow", u"Results in .csv file", None))
        self.comboBox_appendMethod.setItemText(1, QCoreApplication.translate("MainWindow", u"Results in .txt files", None))
        self.comboBox_appendMethod.setItemText(2, QCoreApplication.translate("MainWindow", u"Results in both", None))
        self.comboBox_appendMethod.setItemText(3, QCoreApplication.translate("MainWindow", u"Don't append results", None))

#if QT_CONFIG(tooltip)
        self.comboBox_appendMethod.setToolTip(QCoreApplication.translate("MainWindow", u"Add each new value to a log (results.csv, the .txt files or both), or keep only the latest values", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_savePerSec.setToolTip(QCoreApplication.translate("MainWindow", u"How many times per second to save the results to files", None))
#endif // QT_CONFIG(tooltip)
        self.label_savePerSec.setText(QCoreApplication.translate("MainWindow", u"Save / s", None))
#if QT_CONFIG(accessibility)
        self.horizontalSlider_aggsPerSecond.setAccessibleName(QCoreApplication.translate("MainWindow", u"File saves per second", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.horizontalSlider_aggsPerSecond.setToolTip(QCoreApplication.translate("MainWindow", u"How many times per second the files are written (1-10). Affects only the files.", None))
#endif // QT_CONFIG(tooltip)
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Use these endpoints in external software to get live data updates</p><p>HTML Scoreboard: <a href=\"http://localhost:18099/scoresight\">http://localhost:18099/scoresight</a><br/>JSON: <a href=\"http://localhost:18099/json\">http://localhost:18099/json</a> (optional: ?pivot)<br/>XML: <a href=\"http://localhost:18099/xml\">http://localhost:18099/xml</a> (optional: ?pivot)<br/>CSV: <a href=\"http://localhost:18099/csv\">http://localhost:18099/csv</a> (optional: ?pivot)</p></body></html>", None))
#if QT_CONFIG(tooltip)
        self.pushButton_connectObs.setToolTip(QCoreApplication.translate("MainWindow", u"Connect to the WebSocket server of OBS Studio", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_connectObs.setText(QCoreApplication.translate("MainWindow", u"Connect OBS", None))
#if QT_CONFIG(tooltip)
        self.pushButton_disconnectObs.setToolTip(QCoreApplication.translate("MainWindow", u"Close the connection to OBS. ScoreSight connects to OBS again at its next start only after you connect again.", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_disconnectObs.setText(QCoreApplication.translate("MainWindow", u"Disconnect", None))
#if QT_CONFIG(tooltip)
        self.lineEdit_sceneName.setToolTip(QCoreApplication.translate("MainWindow", u"The name of the scene Create OBS Scene makes", None))
#endif // QT_CONFIG(tooltip)
        self.lineEdit_sceneName.setText(QCoreApplication.translate("MainWindow", u"ScoreSight Scene", None))
#if QT_CONFIG(tooltip)
        self.pushButton_createOBSScene.setToolTip(QCoreApplication.translate("MainWindow", u"Create a scene in OBS with a text source for each standard field", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_createOBSScene.setText(QCoreApplication.translate("MainWindow", u"Create OBS Scene", None))
        self.checkBox_recreate.setText(QCoreApplication.translate("MainWindow", u"Recreate", None))
#if QT_CONFIG(tooltip)
        self.tableView_vmixMapping.setToolTip(QCoreApplication.translate("MainWindow", u"Each field and the vMix title field it updates. Edit the right column.", None))
#endif // QT_CONFIG(tooltip)
        self.connectionLabel.setText(QCoreApplication.translate("MainWindow", u"Connection", None))
#if QT_CONFIG(accessibility)
        self.lineEdit_vmixHost.setAccessibleName(QCoreApplication.translate("MainWindow", u"vMix host", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_vmixHost.setToolTip(QCoreApplication.translate("MainWindow", u"The address of the vMix computer (localhost if vMix runs on this computer)", None))
#endif // QT_CONFIG(tooltip)
        self.label_5.setText(QCoreApplication.translate("MainWindow", u":", None))
#if QT_CONFIG(accessibility)
        self.lineEdit_vmixPort.setAccessibleName(QCoreApplication.translate("MainWindow", u"vMix port", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_vmixPort.setToolTip(QCoreApplication.translate("MainWindow", u"The port of the vMix Web API (8088 by default; not 8099)", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.pushButton_startvmix.setAccessibleName(QCoreApplication.translate("MainWindow", u"Start or stop vMix", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.pushButton_startvmix.setToolTip(QCoreApplication.translate("MainWindow", u"Start or stop sending the readings to vMix", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_startvmix.setText(QCoreApplication.translate("MainWindow", u"Start vMix", None))
        self.vmixinputLabel.setText(QCoreApplication.translate("MainWindow", u"Input", None))
#if QT_CONFIG(accessibility)
        self.inputLineEdit_vmix.setAccessibleName(QCoreApplication.translate("MainWindow", u"vMix input", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.inputLineEdit_vmix.setToolTip(QCoreApplication.translate("MainWindow", u"The vMix input (number or name) of the title to update", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_vmix_send_same.setToolTip(QCoreApplication.translate("MainWindow", u"Send only new detections or also existing?", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_vmix_send_same.setText(QCoreApplication.translate("MainWindow", u"Send Same?", None))
        self.connectionLabel_2.setText(QCoreApplication.translate("MainWindow", u"URL", None))
#if QT_CONFIG(accessibility)
        self.lineEdit_unoUrl.setAccessibleName(QCoreApplication.translate("MainWindow", u"UNO URL", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_unoUrl.setToolTip(QCoreApplication.translate("MainWindow", u"The API URL of the overlays.uno control app. Treat it like a password.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.toolButton_toggleUno.setAccessibleName(QCoreApplication.translate("MainWindow", u"Start or stop UNO", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.toolButton_toggleUno.setToolTip(QCoreApplication.translate("MainWindow", u"Start or stop sending the readings to UNO", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_toggleUno.setText(QCoreApplication.translate("MainWindow", u"Start sending", None))
#if QT_CONFIG(tooltip)
        self.checkBox_uno_send_same.setToolTip(QCoreApplication.translate("MainWindow", u"Send only new detections or also existing?", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_uno_send_same.setText(QCoreApplication.translate("MainWindow", u"Send Same?", None))
#if QT_CONFIG(tooltip)
        self.checkBox_uno_essentials.setToolTip(QCoreApplication.translate("MainWindow", u"The overlay uses UNO Essentials content fields", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_uno_essentials.setText(QCoreApplication.translate("MainWindow", u"Essentials", None))
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"Overlay ID", None))
#if QT_CONFIG(tooltip)
        self.lineEdit_uno_essentials_id.setToolTip(QCoreApplication.translate("MainWindow", u"The ID (UUID) of the Essentials overlay", None))
#endif // QT_CONFIG(tooltip)
        self.lineEdit_uno_essentials_id.setPlaceholderText(QCoreApplication.translate("MainWindow", u"aaaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeeee", None))
#if QT_CONFIG(tooltip)
        self.tableView_unoMapping.setToolTip(QCoreApplication.translate("MainWindow", u"Each field and the UNO command (or Essentials field ID) it drives. Edit the right column.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_enableOutAPI.setToolTip(QCoreApplication.translate("MainWindow", u"Send the readings to the URL below on every detection cycle", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_enableOutAPI.setText(QCoreApplication.translate("MainWindow", u"Send out API requests to external services.", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"Encode", None))
        self.comboBox_api_encode.setItemText(0, QCoreApplication.translate("MainWindow", u"JSON (Full)", None))
        self.comboBox_api_encode.setItemText(1, QCoreApplication.translate("MainWindow", u"JSON (Simple key-value)", None))
        self.comboBox_api_encode.setItemText(2, QCoreApplication.translate("MainWindow", u"XML", None))
        self.comboBox_api_encode.setItemText(3, QCoreApplication.translate("MainWindow", u"CSV", None))

#if QT_CONFIG(tooltip)
        self.comboBox_api_encode.setToolTip(QCoreApplication.translate("MainWindow", u"The format of the readings in the requests", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.lineEdit_api_url.setAccessibleName(QCoreApplication.translate("MainWindow", u"API URL", None))
#endif // QT_CONFIG(accessibility)
#if QT_CONFIG(tooltip)
        self.lineEdit_api_url.setToolTip(QCoreApplication.translate("MainWindow", u"The URL the readings are sent to", None))
#endif // QT_CONFIG(tooltip)
        self.lineEdit_api_url.setPlaceholderText(QCoreApplication.translate("MainWindow", u"http://", None))
        self.comboBox_outApiMethod.setItemText(0, QCoreApplication.translate("MainWindow", u"POST", None))
        self.comboBox_outApiMethod.setItemText(1, QCoreApplication.translate("MainWindow", u"PUT", None))
        self.comboBox_outApiMethod.setItemText(2, QCoreApplication.translate("MainWindow", u"GET", None))

#if QT_CONFIG(tooltip)
        self.comboBox_outApiMethod.setToolTip(QCoreApplication.translate("MainWindow", u"The HTTP method of the requests", None))
#endif // QT_CONFIG(tooltip)
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"URL", None))
        self.tabWidget_inspector.setTabText(self.tabWidget_inspector.indexOf(self.widget_outputs), QCoreApplication.translate("MainWindow", u"Outputs", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuLanguage.setTitle(QCoreApplication.translate("MainWindow", u"Language", None))
        self.menuAppearance.setTitle(QCoreApplication.translate("MainWindow", u"Appearance", None))
    # retranslateUi

