import re
import subprocess
import sys
from time import sleep
import threading
from utils import DetectI2c
import abc


def getSystem():
    return sys.platform


class WinUSBDevice:
    def __init__(self) -> None:
        pass

    def get_usb_device_id(self):
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:")
        for usb in wmi.InstancesOf("Win32_USBHub"):
            if usb.DeviceID == r"USB\VID_04B4&PID_03F2\6&37588625&0&1":
                return True
        return False


class LinuxUSBDevice:
    def __init__(self) -> None:
        self.device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$",
                                    re.I)

    def get_usb_device_id(self):
        df = subprocess.check_output("lsusb")
        for i in df.split(b'\n'):
            if i:
                info = self.device_re.match(i)
                if info:
                    dinfo = info.groupdict()
                    return dinfo["id"] in [b'04b4:03f1', b'04B4:03F1']


DetectDeviceMap = {
    "": LinuxUSBDevice,
    "win32": WinUSBDevice
}


class AbstractDetector(abc.ABC):
    @abc.abstractmethod
    def __init__(self):
        self.callback = None

    @abc.abstractmethod
    def run(self):
        pass

    def registerCallback(self, callback):
        self.callback = callback


class USBDeviceDetector(AbstractDetector):
    def __init__(self) -> None:
        super().__init__()
        self.__system = getSystem()
        self.detectDevice = DetectDeviceMap[self.__system]()
        self.is_detected = False

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

    def run(self):
        if self.camera is None:
            return

        tmp = DetectI2c(self.camera)
        if tmp and self.callback is not None and not self.detected:
            self.detected = True
            self.callback(self.detected)
        elif not tmp and self.detected and self.callback is not None:
            self.detected = False
            self.callback(self.detected)

    def setCamera(self, camera):
        self.camera = camera


class DetectThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__()
        self.__running = False
        self.detectors = []

    def registerDetector(self, detector):
        self.detectors.append(detector)

    def removeDetector(self, detector):
        self.detectors.remove(detector)

    def run(self):
        self.__running = True

        while self.__running:
            for detector in self.detectors:
                detector.run()
            sleep(0.5)

    def stop(self):
        self.__running = False

    def __del__(self):
        print("DetectThread Has been destroyed")

# class DetectThread(threading.Thread):
#     def __init__(self) -> None:
#         super().__init__()
#         self.is_detected = False
#         self.__running = False
#         self.__system = getSystem()
#         self.detectDevice = DetectDeviceMap[self.__system]()
#         self.callbackCPLD = None
#         self.callbackCamera = None
#         self.camera = None

#     def registerCPLDCallback(self, callback_func):
#         self.callbackCPLD = callback_func

#     def registerCameraCallback(self, callback_func):
#         self.callbackCamera = callback_func

#     def run(self):
#         self.__running = True

#         while self.__running:
#             if self.detectDevice.get_usb_device_id():
#                 if self.is_detected is False and self.callbackCPLD is not None:
#                     self.camera = self.callbackCPLD(True)
#                     self.callbackCamera(True)
#                 self.is_detected = True
#             else:
#                 if self.is_detected and self.callbackCPLD is not None:
#                     self.camera = self.callbackCPLD(False)
#                 self.is_detected = False

#             if DetectI2c(self.camera) and self.callbackCamera is not None:
#                 self.callbackCamera(True)
#             elif self.callbackCamera is not None:
#                 self.callbackCamera(False)
#             sleep(0.5)

#     def stop(self):
#         self.__running = False

#     def __del__(self):
#         print("DetectThread Has been destroyed")
