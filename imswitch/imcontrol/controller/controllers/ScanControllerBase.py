import traceback
import configparser

import numpy as np
import serial, time

from ast import literal_eval

from ..basecontrollers import SuperScanController
from imswitch.imcommon.view.guitools import colorutils
from imswitch.imcommon.model import APIExport


class ScanControllerBase(SuperScanController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._widget.initControls(
            self.positioners.keys(),
            self.TTLDevices.keys(),
            self._master.scanManager.TTLTimeUnits
        )

        self.updatePixels()
        self.updateParameters()
        self.updateScanTime()
        self.updateScanStageAttrs()
        self.updateScanTTLAttrs()

        # Connect ScanWidget signals
        self._widget.sigContLaserPulsesToggled.connect(self.setContLaserPulses)
        self.ard = serial.Serial("COM12", 9600, write_timeout=0.05)

    def setParameters(self):
        self.settingParameters = True
        try:
            for i in range(len(self._analogParameterDict['target_device'])):
                positionerName = self._analogParameterDict['target_device'][i]
                self._widget.setScanDim(i, positionerName)
                self._widget.setScanSize(positionerName,
                                         self._analogParameterDict['axis_length'][i])
                self._widget.setScanStepSize(positionerName,
                                             self._analogParameterDict['axis_step_size'][i])
                self._widget.setScanStartPos(positionerName,
                                              self._analogParameterDict['axis_startpos'][i])
                self._widget.setScanStartPos(positionerName,
                                              self._analogParameterDict['axis_start_time'][i])

            setTTLDevices = []
            for i in range(len(self._digitalParameterDict['target_device'])):
                deviceName = self._digitalParameterDict['target_device'][i]
                self._widget.setTTLStarts(deviceName, self._digitalParameterDict['TTL_start'][i])
                self._widget.setTTLEnds(deviceName, self._digitalParameterDict['TTL_end'][i])
                setTTLDevices.append(deviceName)

            for deviceName in self.TTLDevices:
                if deviceName not in setTTLDevices:
                    self._widget.unsetTTL(deviceName)

            self._widget.setSeqTimePar(self._digitalParameterDict['sequence_time'])
        finally:
            self.settingParameters = False
            self.plotSignalGraph()

    def runTakeImage(self) -> None:
        print("taking Image!")
        self.ard.write((str(self._widget.nImages.text()) + '\n').encode())


    @APIExport(runOnUIThread=True)
    def runTakeImageAPI(self, n_images : float) -> None:
        self.ard.write((str(n_images) + '\n').encode())


    @APIExport(runOnUIThread=True)
    def runScanInit(self, *, recalculateSignals=True) -> None:
        try:
            self._widget.scanButton.setStyleSheet("background-color: green")
            if recalculateSignals or self.signalDict is None or self.scanInfoDict is None:
                self.getParameters()
                try:
                    self.signalDict, self.scanInfoDict = self._master.scanManager.makeFullScan(
                        self._analogParameterDict, self._digitalParameterDict,
                        staticPositioner=self._widget.isContLaserMode()
                    )
                except TypeError:
                    self._logger.error(traceback.format_exc())
            #self._widget.setScanInitButtonChecked(True)
            self._master.nidaqManager.runScanInitialization(self.signalDict, self.scanInfoDict)
        except Exception:
            self._logger.error(traceback.format_exc())


    def runScanAdvanced(self, *, recalculateSignals=True, isNonFinalPartOfSequence=False,
                        sigScanStartingEmitted):
        """ Runs a scan with the set scanning parameters. """
        try:
            self._widget.setScanButtonChecked(True)
            self.isRunning = True

            if recalculateSignals or self.signalDict is None or self.scanInfoDict is None:
                self.getParameters()
                try:
                    self.signalDict, self.scanInfoDict = self._master.scanManager.makeFullScan(
                        self._analogParameterDict, self._digitalParameterDict,
                        staticPositioner=self._widget.isContLaserMode()
                    )
                except TypeError:
                    self._logger.error(traceback.format_exc())
                    self.isRunning = False
                    return

            self.doingNonFinalPartOfSequence = isNonFinalPartOfSequence

            if not sigScanStartingEmitted:
                self.emitScanSignal(self._commChannel.sigScanStarting)
            # set positions of scanners not in scan from centerpos
            for index, positionerName in enumerate(self._analogParameterDict['target_device']):
                if positionerName not in self._positionersScan:
                    position = self._analogParameterDict['axis_centerpos'][index]
                    self._master.positionersManager[positionerName].setPosition(position, 0)
                    self._logger.debug(f'set {positionerName} center to {position} before scan')
            # run scan
            self._master.nidaqManager.runScan(self.signalDict, self.scanInfoDict)
        except Exception:
            self._logger.error(traceback.format_exc())
            self.isRunning = False

    def scanDone(self):
        self.isRunning = False

        if not self._widget.isContLaserMode() and not self._widget.repeatEnabled():
            self.emitScanSignal(self._commChannel.sigScanDone)
            if not self.doingNonFinalPartOfSequence:
                self._widget.setScanButtonChecked(False)
                self.emitScanSignal(self._commChannel.sigScanEnded)
        else:
            self.runScanAdvanced(sigScanStartingEmitted=True)



    def getParameters(self):
        if self.settingParameters:
            return
        self._analogParameterDict['target_device'] = []
        self._analogParameterDict['axis_length'] = []
        self._analogParameterDict['axis_step_size'] = []
        self._analogParameterDict['axis_centerpos'] = []
        self._analogParameterDict['axis_startpos'] = []
        self._analogParameterDict['axis_start_time'] = []
        self._analogParameterDict['scan_time_edit'] = []
        self._positionersScan = []
        for i in range(len(self.positioners)):
            self._positionersScan.append(self._widget.getScanDim(i))
        for positionerName in self._positionersScan:
            if positionerName != 'None':
                size = self._widget.getScanSize(positionerName)
                stepSize = self._widget.getScanStepSize(positionerName)
                start = self._widget.getScanStartPos(positionerName)
                start_time = self._widget.getScanStartTime(positionerName) 
                scan_time_edit = self._widget.getScanTimeEdit(positionerName)

                #start = list(self._master.positionersManager[positionerName].position.values())
                self._analogParameterDict['target_device'].append(positionerName)
                self._analogParameterDict['axis_length'].append(size)
                self._analogParameterDict['axis_step_size'].append(stepSize)
                self._analogParameterDict['axis_centerpos'].append([0])
                self._analogParameterDict['axis_startpos'].append([start])
                self._analogParameterDict['axis_start_time'].append([start_time])
                self._analogParameterDict['scan_time_edit'].append([scan_time_edit])
        for positionerName in self.positioners:
            if positionerName not in self._positionersScan:
                size = 1.0
                stepSize = 1.0
                center = self._widget.getScanStartPos(positionerName)
                start = [0]
                self._analogParameterDict['target_device'].append(positionerName)
                self._analogParameterDict['axis_length'].append(size)
                self._analogParameterDict['axis_step_size'].append(stepSize)
                self._analogParameterDict['axis_centerpos'].append(center)
                self._analogParameterDict['axis_startpos'].append(start)
                self._analogParameterDict['axis_start_time'].append(start_time)
                self._analogParameterDict['scan_time_edit'].append([scan_time_edit])

        self._digitalParameterDict['target_device'] = []
        self._digitalParameterDict['TTL_start'] = []
        self._digitalParameterDict['TTL_end'] = []
        for deviceName, _ in self.TTLDevices.items():
            if not self._widget.getTTLIncluded(deviceName):
                continue

            self._digitalParameterDict['target_device'].append(deviceName)
            self._digitalParameterDict['TTL_start'].append(self._widget.getTTLStarts(deviceName))
            self._digitalParameterDict['TTL_end'].append(self._widget.getTTLEnds(deviceName))

        self._digitalParameterDict['sequence_time'] = self._widget.getSeqTimePar()
        self._analogParameterDict['sequence_time'] = self._widget.getSeqTimePar()

    def setContLaserPulses(self, isContLaserPulses):
        for i in range(len(self.positioners)):
            positionerName = self._widget.scanPar['scanDim' + str(i)].currentText()
            self._widget.setScanDimEnabled(i, not isContLaserPulses)
            self._widget.setScanSizeEnabled(positionerName, not isContLaserPulses)
            self._widget.setScanStepSizeEnabled(positionerName, not isContLaserPulses)
            #self._widget.setScanStartPosEnabled(positionerName, not isContLaserPulses)

    def updatePixels(self):
        self.getParameters()
        for index, positionerName in enumerate(self.positioners):
            if float(self._analogParameterDict['axis_step_size'][index]) != 0:
                pixels = round((float(self._analogParameterDict['axis_length'][index])- float(self._analogParameterDict['axis_startpos'][index][0])) /
                               float(self._analogParameterDict['axis_step_size'][index]))
                self._widget.setScanPixels(positionerName, pixels)
                self._widget.setAllSliders( 
                                           float(self._widget.scanPar['size' + positionerName].text()), 
                                           float(self._widget.scanPar['start' + positionerName].text()),
                                           float(self._widget.scanPar['start_time' + positionerName].text()),
                                           float(self._widget.scanPar['scan_time_edit' + positionerName].text())
                                           )

    def updateParameters(self):
        # for updating the parameters from the sliders changing
        for index, positionerName in enumerate(self.positioners):
            if positionerName=='OptotuneLens':
                self._widget.setAllParams(positionerName, self._widget.scanSizeSlider.value()/20, 
                                          self._widget.scanStartVoltageSlider.value()/20, 
                                          self._widget.scanStartTimeSlider.value()/2, 
                                          self._widget.scanTimeSlider.value()/2)





    def updateScanTime(self):
        self.getParameters()
        #print("The sequence time is: inside the ScanControllerBase.py")
        #print(self._analogParameterDict['sequence_time'])
        for index, positionerName in enumerate(self.positioners):
            if float(self._analogParameterDict['axis_step_size'][index]) != 0:
                scantimes = round((float(self._analogParameterDict['axis_length'][index]) - float(self._analogParameterDict['axis_startpos'][index][0])) * float(self._analogParameterDict['sequence_time']) *1000.0 /
                               float(self._analogParameterDict['axis_step_size'][index]), 3)
                self._widget.setScanTime(positionerName, scantimes)

    def emitScanSignal(self, signal, *args):
        if not self._widget.isContLaserMode():  # Cont. laser pulses mode is not a real scan
            signal.emit(*args)

    def saveScanParamsToFile(self, filePath: str) -> None:
        """ Saves the set scanning parameters to the specified file. """
        self.getParameters()
        config = configparser.ConfigParser()
        config.optionxform = str

        config['analogParameterDict'] = self._analogParameterDict
        config['digitalParameterDict'] = self._digitalParameterDict
        config['Modes'] = {'scan_or_not': self._widget.isScanMode()}

        with open(filePath, 'w') as configfile:
            config.write(configfile)

    def loadScanParamsFromFile(self, filePath: str) -> None:
        """ Loads scanning parameters from the specified file. """
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(filePath)

        for key in self._analogParameterDict:
            self._analogParameterDict[key] = literal_eval(
                config._sections['analogParameterDict'][key]
            )

        for key in self._digitalParameterDict:
            self._digitalParameterDict[key] = literal_eval(
                config._sections['digitalParameterDict'][key]
            )

        scanOrNot = (config._sections['Modes']['scan_or_not'] == 'True')
        if scanOrNot:
            self._widget.setScanMode()
        else:
            self._widget.setContLaserMode()

        self.setParameters()

# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
