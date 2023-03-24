import cv2


from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter



class WebcamCameraOut(DetectorManager):
    """ DetectorManager that deals with Webcam cameras and the
    parameters for frame extraction from them.

    Manager properties:


    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        #host = detectorInfo.managerProperties['cameraHost']
        #port = detectorInfo.managerProperties['cameraPort']
        self._camera = cv2.VideoCapture(0)

        #model = self._camera.model
        self._running = False
        #self._adjustingParameters = False

        #for propertyName, propertyValue in detectorInfo.managerProperties['esp32cam'].items():
        #    self._camera.setPropertyValue(propertyName, propertyValue)

        #fullShape = (self._camera.getPropertyValue('image_width'),
        #             self._camera.getPropertyValue('image_height'))

        #self.crop(hpos=0, vpos=0, hsize=fullShape[0], vsize=fullShape[1])

        # Prepare parameters
        #parameters = {
            
        #    'exposure': DetectorNumberParameter(group='Misc', value=100, valueUnits='ms',
        #                                        editable=True),
        #    'gain': DetectorNumberParameter(group='Misc', value=1, valueUnits='arb.u.',
        #                                    editable=True),
        #    'blacklevel': DetectorNumberParameter(group='Misc', value=100, valueUnits='arb.u.',
        #                                    editable=True),
        #    'image_width': DetectorNumberParameter(group='Misc', value=fullShape[0], valueUnits='arb.u.',
        #                editable=False),
        #    'image_height': DetectorNumberParameter(group='Misc', value=fullShape[1], valueUnits='arb.u.',
        #                editable=False),
            
        #    }            

        # Prepare actions
        #actions = {
        #    'More properties': DetectorAction(group='Misc',
        #                                      func=self._camera.openPropertiesGUI)
        #}

        super().__init__(detectorInfo)#, fullShape=fullShape, supportedBinnings=[1],
        #                 model=model, parameters=parameters, actions=actions, croppable=True)

    def getLatestFrame(self, is_save=False):
        if True:
            ret, frame = self._camera.read()
            return frame





    def startAcquisition(self):
        if not self._running:
            while True:
                self.getLatestFrame()
            #self._camera.start_live()
            self._running = True
            self.__logger.debug('startlive')

    def stopAcquisition(self):
        if self._running:
            self._running = False
            self._camera.release() 
            #self._camera.suspend_live()
            self.__logger.debug('suspendlive')




    def closeEvent(self):
        self._camera.release()
