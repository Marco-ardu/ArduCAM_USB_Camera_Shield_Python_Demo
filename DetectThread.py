import re
import subprocess
import sys
from time import sleep
import threading
from utils import DetectI2c, setPath
import abc
from loguru import logger


@logger.catch
def getSystem():
    return sys.platform


setPath()

class WinUSBDevice:
    def __init__(self) -> None:
        pass

    @logger.catch
    def get_usb_device_id(self):
        device_id = None
        import pythoncom
        pythoncom.CoInitialize()
        import wmi
        c = wmi.WMI()
        wql = "Select DeviceID From Win32_PnPEntity WHERE DeviceID LIKE 'USB\\VID_04B4&PID_03F2%' OR  DeviceID LIKE 'USB\\VID_52CB&PID_52CB%'"
        for item in c.query(wql):
            device_id = item
        if device_id:
            return True
        return False


class LinuxUSBDevice:
    def __init__(self) -> None:
        self.device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$",
                                    re.I)

    @logger.catch
    def get_usb_device_id(self):
        df = subprocess.check_output("lsusb")
        for i in df.split(b'\n'):
            if i:
                info = self.device_re.match(i)
                if info:
                    dinfo = info.groupdict()
                    return dinfo["id"] in [b'04b4:03f1', b'04B4:03F1']


DetectDeviceMap = {
    "Linux": LinuxUSBDevice,
    "win32": WinUSBDevice
}


class AbstractDetector(abc.ABC):
    @abc.abstractmethod
    def __init__(self):
        self.callback = None

    @abc.abstractmethod
    def run(self):
        pass

    @logger.catch
    def registerCallback(self, callback):
        self.callback = callback


class USBDeviceDetector(AbstractDetector):
    def __init__(self) -> None:
        super().__init__()
        self.__system = getSystem()
        self.detectDevice = DetectDeviceMap[self.__system]()
        self.is_detected = False

    @logger.catch
    def run(self):
        if self.detectDevice.get_usb_device_id():
            if self.is_detected is False and self.callback is not None:
                self.callback(True)
            self.is_detected = True
        else:
            if self.is_detected and self.callback is not None:
                self.callback(False)
            self.is_detected = False


class I2CDeviceDetector(AbstractDetector):
    def __init__(self) -> None:
        super().__init__()
        self.detected = False
        self.camera = None

    @logger.catch
    def run(self):
        if self.camera is None:
            return

        tmp = DetectI2c(self.camera)
        # print("tmp", tmp)
        if tmp and self.callback is not None and not self.detected:
            self.detected = True
            self.callback(self.detected)
        elif not tmp and self.detected and self.callback is not None:
            self.detected = False
            self.callback(self.detected)

    @logger.catch
    def setCamera(self, camera):
        self.camera = camera
        if camera is None:
            self.detected = False


class DetectThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__()
        self.__running = False
        self.detectors = []

    @logger.catch
    def registerDetector(self, detector):
        self.detectors.append(detector)

    @logger.catch
    def removeDetector(self, detector):
        self.detectors.remove(detector)

    @logger.catch
    def run(self):
        self.__running = True

        while self.__running:
            for detector in self.detectors:
                detector.run()
            sleep(0.5)

    @logger.catch
    def stop(self):
        self.__running = False
