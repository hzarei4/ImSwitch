import numpy as np
import matplotlib.pyplot as plt

from .basesignaldesigners import ScanDesigner
from imswitch.imcommon.model import initLogger

class BetaScanDesigner(ScanDesigner):
    """ Scan designer for X/Y/Z stages that move a sample.
    Designer params:
    - ``return_time`` -- time to wait between lines for the stage to return to
      the first position of the next line, in seconds.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._expectedParameters = ['target_device',
                                    'axis_length',
                                    'axis_step_size',
                                    'axis_startpos',
                                    'axis_start_time',
                                    'scan_time_edit',
                                    'return_time']

    def checkSignalComp(self, scanParameters, setupInfo, scanInfo):
        """ Check analog scanning signals so that they are inside the range of
        the acceptable scanner voltages."""
        return True  # TODO

    def make_signal(self, parameterDict, setupInfo):

        if not self.parameterCompatibility(parameterDict):
            self._logger.error([*parameterDict])
            self._logger.error(self._expectedParameters)
            self._logger.error('Stage scan parameters seem incompatible, this error should not be'
                               ' since this should be checked at program start-up')
            return None

        if len(parameterDict['target_device']) != 1:
            raise ValueError(f'{self.__class__.__name__} requires 1 target devices/axes')

        for i in range(1):
            if len(parameterDict['axis_startpos'][i]) > 1:
                raise ValueError(f'{self.__class__.__name__} does not support multi-axis'
                                 f' positioners')

        convFactors = [positioner.managerProperties['conversionFactor']
                       for positioner in setupInfo.positioners.values() if positioner.forScanning]

        # Retrieve sizes
        [fast_axis_size] = \
            [(parameterDict['axis_length'][i] / convFactors[i]) for i in range(1)]

        # Retrieve step sizes
        [fast_axis_step_size] = \
            [(parameterDict['axis_step_size'][i] / convFactors[i]) for i in range(1)]

        # Retrive starting position
        [fast_axis_start] = \
            [(parameterDict['axis_startpos'][i][0] / convFactors[i]) for i in range(1)]

        # Retrive starting position
        [fast_axis_start_time] = \
            [(parameterDict['axis_start_time'][i][0] / convFactors[i]) for i in range(1)]
        
        # Retrive scan time edit
        [fast_axis_scan_time_edit] = \
            [(parameterDict['scan_time_edit'][i][0]) for i in range(1)]

        #fast_axis_positions = 1 if fast_axis_size == 0 or fast_axis_step_size == 0 else \
        #    1 + int(np.ceil(fast_axis_size / fast_axis_step_size))



        sampleRate = setupInfo.scan.sampleRate
        sequenceSamples =  float(fast_axis_scan_time_edit)/1000.0  * sampleRate


        returnSamples = parameterDict['return_time'] * sampleRate
        if not sequenceSamples.is_integer():
            self._logger.warning('Non-integer number of sequence samples, rounding up')
        sequenceSamples = int(np.ceil(sequenceSamples))
        if not returnSamples.is_integer():
            self._logger.warning('Non-integer number of return samples, rounding up')
        returnSamples = int(np.ceil(returnSamples))

        # Make fast axis signal
        #rampSamples = fast_axis_positions * sequenceSamples
        #lineSamples = rampSamples + returnSamples
        #rampSignal = np.zeros(rampSamples)
        #self._logger.debug(fast_axis_positions)
        
        """
        for s in range(fast_axis_positions):
            start = s * sequenceSamples
            end = s * sequenceSamples + sequenceSamples
            smooth = int(np.ceil(0.001 * sampleRate))
            settling = int(np.ceil(0.001 * sampleRate))
            rampSignal[start: end] = rampValues[s]
            if s is not fast_axis_positions - 1:
                if (end - smooth - settling) > 0:
                    rampSignal[end - smooth - settling: end - settling] = self.__smoothRamp(rampValues[s], rampValues[s + 1], smooth)
                    rampSignal[end - settling:end] = rampValues[s + 1]
        """
        #returnRamp = self.__smoothRamp(fast_axis_size, fast_axis_start, returnSamples)
        """
        t1 = 0
        for t in range(len(rampValues)):
    
            rampExactValues = np.linspace(fast_axis_start, fast_axis_size, num=fast_axis_positions)
            try:
                if rampValues[t] >= rampExactValues[t1] and rampValues[t] < rampExactValues[t1+1]:
                    rampValues[t] = rampExactValues[t1]
                else:
                    t1+=1
                    rampValues[t] = rampExactValues[t1]
            except:
                pass
        """
        #rampValues = self.__makeRamp(fast_axis_start, fast_axis_size, sequenceSamples)
        #rampValues = self.__smoothRamp(fast_axis_start, fast_axis_size, 0.6, sequenceSamples)  # exponential
        #rampValues = self.__quadraticSig(fast_axis_start, fast_axis_size, 1.0, sequenceSamples)
        rampValues = self.__mixedSig(fast_axis_start, fast_axis_size, sequenceSamples)
        tempp = np.concatenate((fast_axis_start *np.ones(int(sampleRate*fast_axis_start_time/1000.0)), rampValues))
        
        # return ramp as a flipped triangular
        #fullLineSignal = np.concatenate((tempp, np.flip(rampValues)))

        # return ramp as a sharp edge
        fullLineSignal_1 = np.concatenate((tempp, fast_axis_size *np.ones(int(sampleRate*5.0/1000.0))))

        fastAxisSignal = np.concatenate((fullLineSignal_1, fast_axis_start *np.ones(1))) # fullLineSignal

        
        sig_dict = {parameterDict['target_device'][0]: fastAxisSignal,
                    }

        # scanInfoDict, for parameters that are important to relay to TTLCycleDesigner and/or image
        # acquisition managers
        scanInfoDict = {
            'positions': [1], #[fast_axis_positions],
            'return_time': parameterDict['return_time']
        }
        return sig_dict, scanInfoDict['positions'], scanInfoDict

    def __makeRamp(self, start, end, samples):
        return np.linspace(float(start), float(end), num=samples-1)

    def __smoothRamp(self, start, end, curve_half, samples):
        start = float(start)
        end = float(end)
        curve_half = float(curve_half)
        n = int(np.floor(curve_half * samples))
        x = np.linspace(0, np.pi / 2, num=n, endpoint=True)
        signal = start + (end - start) * np.sin(x)
        signal = np.append(signal, end * np.ones(int(np.ceil((1 - curve_half) * samples))))
        return signal
    
    def __quadraticSig(self, start, end, coeff, samples):
        return (-1.0 * coeff *( np.linspace(float(-1), float(0), num=samples-1))**2 + 1.0) * (end -start) +start

    def __mixedSig(self, start, end, samples):
        n1 = np.linspace(float(0.0), float(0.5), num=int((samples-1)/2.0))
        n2 = 4*np.linspace(float(0.5), float(1), num=int((samples-1)/2.0)) -2.0 + 0.5
        #(1.0 * coeff *( np.linspace(float(0.5), float(1), num=int((samples-1)/2.0)))**4 + 0.0) - (0.5)**4 +0.5
    
        return (np.concatenate((n1, n2)) / max(n2)) * (end -start) +start


# Copyright (C) 2020, 2021 TestaLab
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
