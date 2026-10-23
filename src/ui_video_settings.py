# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'video_settings.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *  # type: ignore
from PySide6.QtGui import *  # type: ignore
from PySide6.QtWidgets import *  # type: ignore

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(400, 259)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widget = QWidget(Dialog)
        self.widget.setObjectName(u"widget")
        self.formLayout = QFormLayout(self.widget)
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label)

        self.comboBox_fourcc = QComboBox(self.widget)
        self.comboBox_fourcc.addItem("")
        self.comboBox_fourcc.setObjectName(u"comboBox_fourcc")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.comboBox_fourcc)

        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.spinBox_fps = QSpinBox(self.widget)
        self.spinBox_fps.setObjectName(u"spinBox_fps")
        self.spinBox_fps.setMinimum(1)
        self.spinBox_fps.setMaximum(60)
        self.spinBox_fps.setValue(30)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.spinBox_fps)

        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.comboBox_resolution = QComboBox(self.widget)
        self.comboBox_resolution.addItem("")
        self.comboBox_resolution.addItem(u"320x240")
        self.comboBox_resolution.addItem(u"640x480")
        self.comboBox_resolution.addItem(u"800x600")
        self.comboBox_resolution.addItem(u"1280x720")
        self.comboBox_resolution.addItem(u"1280x960")
        self.comboBox_resolution.addItem(u"1600x900")
        self.comboBox_resolution.addItem(u"1920x1080")
        self.comboBox_resolution.addItem(u"3840x2160")
        self.comboBox_resolution.addItem(u"2560x1440")
        self.comboBox_resolution.addItem(u"2048x1080")
        self.comboBox_resolution.addItem(u"4096x2160")
        self.comboBox_resolution.setObjectName(u"comboBox_resolution")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.comboBox_resolution)

        self.plainTextEdit_videoProps = QPlainTextEdit(self.widget)
        self.plainTextEdit_videoProps.setObjectName(u"plainTextEdit_videoProps")

        self.formLayout.setWidget(5, QFormLayout.ItemRole.FieldRole, self.plainTextEdit_videoProps)

        self.groupBox_pictureLevels = QGroupBox(self.widget)
        self.groupBox_pictureLevels.setObjectName(u"groupBox_pictureLevels")
        self.formLayout_pictureLevels = QFormLayout(self.groupBox_pictureLevels)
        self.formLayout_pictureLevels.setObjectName(u"formLayout_pictureLevels")
        self.checkBox_pictureLevels = QCheckBox(self.groupBox_pictureLevels)
        self.checkBox_pictureLevels.setObjectName(u"checkBox_pictureLevels")

        self.formLayout_pictureLevels.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.checkBox_pictureLevels)

        self.label_blackPoint = QLabel(self.groupBox_pictureLevels)
        self.label_blackPoint.setObjectName(u"label_blackPoint")

        self.formLayout_pictureLevels.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_blackPoint)

        self.spinBox_blackPoint = QSpinBox(self.groupBox_pictureLevels)
        self.spinBox_blackPoint.setObjectName(u"spinBox_blackPoint")
        self.spinBox_blackPoint.setMaximum(254)

        self.formLayout_pictureLevels.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spinBox_blackPoint)

        self.label_whitePoint = QLabel(self.groupBox_pictureLevels)
        self.label_whitePoint.setObjectName(u"label_whitePoint")

        self.formLayout_pictureLevels.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_whitePoint)

        self.spinBox_whitePoint = QSpinBox(self.groupBox_pictureLevels)
        self.spinBox_whitePoint.setObjectName(u"spinBox_whitePoint")
        self.spinBox_whitePoint.setMinimum(1)
        self.spinBox_whitePoint.setMaximum(255)
        self.spinBox_whitePoint.setValue(255)

        self.formLayout_pictureLevels.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spinBox_whitePoint)

        self.label_gamma = QLabel(self.groupBox_pictureLevels)
        self.label_gamma.setObjectName(u"label_gamma")

        self.formLayout_pictureLevels.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_gamma)

        self.doubleSpinBox_gamma = QDoubleSpinBox(self.groupBox_pictureLevels)
        self.doubleSpinBox_gamma.setObjectName(u"doubleSpinBox_gamma")
        self.doubleSpinBox_gamma.setDecimals(2)
        self.doubleSpinBox_gamma.setMinimum(0.100000000000000)
        self.doubleSpinBox_gamma.setMaximum(10.000000000000000)
        self.doubleSpinBox_gamma.setSingleStep(0.100000000000000)
        self.doubleSpinBox_gamma.setValue(1.000000000000000)

        self.formLayout_pictureLevels.setWidget(3, QFormLayout.ItemRole.FieldRole, self.doubleSpinBox_gamma)


        self.formLayout.setWidget(6, QFormLayout.ItemRole.SpanningRole, self.groupBox_pictureLevels)

        self.label_4 = QLabel(self.widget)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.comboBox_captureBackend = QComboBox(self.widget)
        self.comboBox_captureBackend.addItem("")
        self.comboBox_captureBackend.setObjectName(u"comboBox_captureBackend")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox_captureBackend)


        self.gridLayout.addWidget(self.widget, 1, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 1)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Video Format", None))
        self.comboBox_fourcc.setItemText(0, QCoreApplication.translate("Dialog", u"Default", None))

        self.label_2.setText(QCoreApplication.translate("Dialog", u"FPS", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"Resolution", None))
        self.comboBox_resolution.setItemText(0, QCoreApplication.translate("Dialog", u"Default", None))

        self.groupBox_pictureLevels.setTitle(QCoreApplication.translate("Dialog", u"Picture levels", None))
#if QT_CONFIG(tooltip)
        self.groupBox_pictureLevels.setToolTip(QCoreApplication.translate("Dialog", u"Cut what a dim LED or LCD display shows for the segments that are off (ghosting), and stretch the lit segments back to full white. Applies to the whole picture: the preview, Binary View and the OCR.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.checkBox_pictureLevels.setToolTip(QCoreApplication.translate("Dialog", u"Apply a black point, a white point and a gamma to every frame. Off by default.", None))
#endif // QT_CONFIG(tooltip)
        self.checkBox_pictureLevels.setText(QCoreApplication.translate("Dialog", u"Apply black point and white point", None))
        self.label_blackPoint.setText(QCoreApplication.translate("Dialog", u"Black point", None))
#if QT_CONFIG(tooltip)
        self.spinBox_blackPoint.setToolTip(QCoreApplication.translate("Dialog", u"Every gray level up to this one becomes black. Raise it past the level the display shows for segments that are off (the ghosting), and below the lit segments.", None))
#endif // QT_CONFIG(tooltip)
        self.label_whitePoint.setText(QCoreApplication.translate("Dialog", u"White point", None))
#if QT_CONFIG(tooltip)
        self.spinBox_whitePoint.setToolTip(QCoreApplication.translate("Dialog", u"Every gray level from this one up becomes white. Keep it at or below the brightest lit segments.", None))
#endif // QT_CONFIG(tooltip)
        self.label_gamma.setText(QCoreApplication.translate("Dialog", u"Gamma", None))
#if QT_CONFIG(tooltip)
        self.doubleSpinBox_gamma.setToolTip(QCoreApplication.translate("Dialog", u"Brightens (above 1) or darkens (below 1) the midtones after the levels. 1.00 leaves them as they are.", None))
#endif // QT_CONFIG(tooltip)
        self.label_4.setText(QCoreApplication.translate("Dialog", u"Capture Backend", None))
        self.comboBox_captureBackend.setItemText(0, QCoreApplication.translate("Dialog", u"Default / Any", None))

    # retranslateUi

