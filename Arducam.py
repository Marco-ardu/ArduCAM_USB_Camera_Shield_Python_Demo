import threading
from loguru import logger
import ArducamSDK
from DetectThread import DetectThread, I2CDeviceDetector, USBDeviceDetector
from utils import *


setPath()


class ArducamCamera(object):
    def __init__(self, config_file):
        self.isOpened = False
        self.running_ = False
        self.capture_thread_ = None
        self.config_file = config_file
        self.callback = None
        self.signal_ = threading.Condition()
    
        self.deviceDetector = USBDeviceDetector()
        self.deviceDetector.registerCallback(self.initDevice)

        self.i2cDeviceDetector = I2CDeviceDetector()
        self.i2cDeviceDetector.registerCallback(self.initSensor)

        self.detectThread = DetectThread()
        self.detectThread.daemon = True
        self.detectThread.start()
        self.detectThread.registerDetector(self.deviceDetector)
        self.detectThread.registerDetector(self.i2cDeviceDetector)
        pass

    @logger.catch
    def openCamera(self, index=0):
        self.isOpened, self.handle, self.cameraCfg, self.color_mode = camera_initFromFile(
            self.config_file, index)

        return self.isOpened

    @logger.catch
    def registerCallback(self, callback):
        self.callback = callback

    @logger.catch
    def initDevice(self, flag, index=0):
        if flag:
            while True:
                self.isOpened, self.handle, self.cameraCfg, self.readConfig, self.I2cAddr, self.color_mode = camera_initCPLD(
                    self.config_file, index)
                if self.isOpened:
                    break
                time.sleep(1)

            self.start()

            if self.callback:
                self.callback(self.isOpened)

            self.i2cDeviceDetector.setCamera(self)
        else:
            self.handle = None
            self.running_ = False
            self.i2cDeviceDetector.setCamera(None)
            if self.capture_thread_:
                self.capture_thread_.join()
                self.capture_thread_ = None

    @logger.catch
    def initSensor(self, flag):
        if flag:
            camera_initSensor(self.handle, self.readConfig, self.cameraCfg['usbType'], self.I2cAddr)

    @logger.catch
    def start(self):
        if not self.isOpened:
            raise RuntimeError("The camera has not been opened.")

        self.running_ = True
        ArducamSDK.Py_ArduCam_setMode(self.handle, ArducamSDK.CONTINUOUS_MODE)

        self.capture_thread_ = threading.Thread(target=self.capture_thread)
        self.capture_thread_.daemon = True
        self.capture_thread_.start()

    @logger.catch(reraise=True)
    def read(self, timeout=1500):
        if not self.running_:
            raise Exception("The camera is not running.")

        if ArducamSDK.Py_ArduCam_availableImage(self.handle) <= 0:
            with self.signal_:
                self.signal_.wait(timeout/1000.0)

        if ArducamSDK.Py_ArduCam_availableImage(self.handle) <= 0:
            return (False, None, None)

        ret, data, cfg = ArducamSDK.Py_ArduCam_readImage(self.handle)
        ArducamSDK.Py_ArduCam_del(self.handle)
        size = cfg['u32Size']
        if ret != 0 or size == 0:
            return (False, data, cfg)
    
        return (True, data, cfg)

    @logger.catch
    def stop(self):
        if not self.running_:
            raise RuntimeError("The camera is not running.")

        self.running_ = False
        self.capture_thread_.join()

    @logger.catch
    def closeCamera(self):
        if not self.isOpened:
            raise RuntimeError("The camera has not been opened.")

        if (self.running_):
            self.stop()
        self.isOpened = False
        ArducamSDK.Py_ArduCam_close(self.handle)
        self.handle = None

    @logger.catch
    def capture_thread(self):
        ret = ArducamSDK.Py_ArduCam_beginCaptureImage(self.handle)

        if ret != 0:
            self.running_ = False
            raise RuntimeError("Error beginning capture, Error : {}".format(GetErrorString(ret)))

        logger.info("Capture began, Error : {}".format(GetErrorString(ret)))
        while self.running_:
            ret = ArducamSDK.Py_ArduCam_captureImage(self.handle)
            if ret > 255:
                
                if ret == ArducamSDK.USB_CAMERA_USB_TASK_ERROR:
                    with self.signal_:
                        self.signal_.notify()
                    break
                elif ret == ArducamSDK.USB_CAMERA_USB_TIMEOUT_ERROR:
                    continue
                logger.info("Error capture image, Error : {}".format(GetErrorString(ret)))
            elif ret > 0:
                with self.signal_:
                    self.signal_.notify()
            
        self.running_ = False
        ArducamSDK.Py_ArduCam_endCaptureImage(self.handle)

    @logger.catch
    def setCtrl(self, func_name, val):
        return ArducamSDK.Py_ArduCam_setCtrl(self.handle, func_name, val)

    @logger.catch
    def dumpDeviceInfo(self):
        USB_CPLD_I2C_ADDRESS=0x46
        cpld_info={}
        ret, version = ArducamSDK.Py_ArduCam_readReg_8_8(
            self.handle, USB_CPLD_I2C_ADDRESS, 0x00)
        ret, year = ArducamSDK.Py_ArduCam_readReg_8_8(
            self.handle, USB_CPLD_I2C_ADDRESS, 0x05)
        ret, mouth = ArducamSDK.Py_ArduCam_readReg_8_8(
            self.handle, USB_CPLD_I2C_ADDRESS, 0x06)
        ret, day = ArducamSDK.Py_ArduCam_readReg_8_8(
            self.handle, USB_CPLD_I2C_ADDRESS, 0x07)

        cpld_info["version"] = "v{}.{}".format(version>>4, version & 0x0F)
        cpld_info["year"] = year
        cpld_info["mouth"] = mouth
        cpld_info["day"] = day

        logger.info(cpld_info)

        ret, data = ArducamSDK.Py_ArduCam_getboardConfig(
            self.handle, 0x80, 0x00, 0x00, 2
        )

        usb_info={}
        usb_info["fw_version"] = "v{}.{}".format((data[0] & 0xFF), (data[1] & 0xFF))
        usb_info["interface"] = 2 if self.cameraCfg["usbType"] == 4 else 3
        usb_info["device"] = 3 if self.cameraCfg["usbType"] == 3 or self.cameraCfg["usbType"] == 4 else 2

        logger.info(usb_info)

    @logger.catch
    def getCamInformation(self):
        self.version = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 00)[1]
        self.year = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 5)[1]
        self.mouth = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 6)[1]
        self.day = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 7)[1]
        cpldVersion = "V{:d}.{:d}\t20{:0>2d}/{:0>2d}/{:0>2d}".format(self.version >> 4, self.version & 0x0F, self.year,
                                                                     self.mouth, self.day)
        return cpldVersion

    @logger.catch
    def getMipiDataInfo(self):
        mipiData = {"mipiDataID": "",
                    "mipiDataRow": "",
                    "mipiDataCol": "",
                    "mipiDataClk": "",
                    "mipiWordCount": "",
                    "mFramerateValue": ""}
        self.getCamInformation()
        cpld_version = self.version & 0xF0
        date = (self.year * 1000 + self.mouth * 100 + self.day)
        if cpld_version not in [0x20, 0x30]:
            return None
        if cpld_version == 0x20 and date < (19 * 1000 + 7 * 100 + 8):
            return None
        elif cpld_version == 0x30 and date < (19 * 1000 + 3 * 100 + 22):
            return None

        mipiDataID = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x1E)[1]
        mipiData["mipiDataID"] = hex(mipiDataID)

        rowMSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x21)[1]
        rowLSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x22)[1]
        mipiDataRow = ((rowMSB & 0xFF) << 8) | (rowLSB & 0xFF)
        mipiData["mipiDataRow"] = str(mipiDataRow)

        colMSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x1F)[1]
        colLSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x20)[1]
        mipiDataCol = ((colMSB & 0xFF) << 8) | (colLSB & 0xFF)
        mipiData["mipiDataCol"] = str(mipiDataCol)

        # after 2020/06/22
        if cpld_version == 0x20 and date < (20 * 1000 + 6 * 100 + 22):
            return mipiData
        elif cpld_version == 0x30 and date < (20 * 1000 + 6 * 100 + 22):
            return mipiData

        mipiDataClk = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x27)[1]
        mipiData["mipiDataClk"] = str(mipiDataClk)

        if (cpld_version == 0x30 and date >= (21 * 1000 + 3 * 100 + 1)) or (
                cpld_version == 0x20 and date >= (21 * 1000 + 9 * 100 + 6)):
            wordCountMSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x25)[1]
            wordCountLSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x26)[1]
            mipiWordCount = ((wordCountMSB & 0xFF) << 8) | (wordCountLSB & 0xFF)
            mipiData["mipiWordCount"] = str(mipiWordCount)

        if date >= (21 * 1000 + 6 * 100 + 22):
            fpsMSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x2A)[1]
            fpsLSB = ArducamSDK.Py_ArduCam_readReg_8_8(self.handle, 0x46, 0x2B)[1]
            fps = (fpsMSB << 8 | fpsLSB) / 4.0
            fpsResult = "{:.1f}".format(fps)
            mipiData["mFramerateValue"] = fpsResult
        return mipiData