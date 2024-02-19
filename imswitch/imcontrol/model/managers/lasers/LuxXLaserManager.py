from lantz import Q_

from imswitch.imcommon.model import initLogger
from .LantzLaserManager import LantzLaserManager
import sys

sys.path.append("C:\\Users\\admin\\Desktop\\drivers_lightsheet\\OmicronPython")
from luxx_communication import Laser




class LuxXLaserManager(LantzLaserManager):
    """ LaserManager for Cobolt 06-01 lasers. Uses digital modulation mode when
    scanning. Does currently not support DPL type lasers.

    Manager properties:

    - ``digitalPorts`` -- a string array containing the COM ports to connect
      to, e.g. ``["COM4"]``
    """

    def __init__(self, laserInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)


        self.laserX = Laser(port="COM5")
        self.laserX.set_mode("CW-ACC")
        self.laserX.set_autostart(False)

        super().__init__(laserInfo, name, isBinary=False, valueUnits='mW', valueDecimals=0,
                         **_lowLevelManagers)

        self._digitalMod = False

        self._laser.digital_mod = False
        self._laser.enabled = False
        self._laser.autostart = False

    def setEnabled(self, enabled):
        if enabled:
            self.laserX.stop()
            self._laser.enabled = False
        else:
            self.laserX.start()
            self._laser.enabled = True

    def setValue(self, power):
        power = int(power)

        self._setBasicPower(power * Q_(1, 'mW'))



    def _setBasicPower(self, power):
        self.laserX.set_power(power)
        self._laser.power_sp = power / self._numLasers

    def finalize(self):
        self.laserX.stop()
        del self.laserX




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
