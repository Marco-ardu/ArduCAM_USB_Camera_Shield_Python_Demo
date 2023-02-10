import argparse
import time
import signal
import cv2

from Arducam import *
from ImageConvert import *
from DetectThread import DetectThread, I2CDeviceDetector, USBDeviceDetector

exit_ = False


def sigint_handler(signum, frame):
    global exit_
    exit_ = True


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


def display_fps(index):
    display_fps.frame_count += 1

    current = time.time()
    if current - display_fps.start >= 1:
        print("fps: {}".format(display_fps.frame_count))
        display_fps.frame_count = 0
        display_fps.start = current


display_fps.start = time.time()
display_fps.frame_count = 0


class HotPlugCamera():
    def __init__(self, args):
        self.camera = None
        self.signal_ = threading.Condition()

        self.config_file = args.config_file
        self.verbose = args.verbose
        self.preview_width = args.preview_width
        self.no_preview = args.nopreview
        self.scale_width = self.preview_width

    def start(self):
        self.deviceDetector = USBDeviceDetector()
        self.deviceDetector.registerCallback(self.initDevice)

        self.i2cDeviceDetector = I2CDeviceDetector()
        self.i2cDeviceDetector.registerCallback(self.initSensor)

        self.detectThread = DetectThread()
        self.detectThread.daemon = True
        self.detectThread.start()
        self.detectThread.registerDetector(self.deviceDetector)
        self.detectThread.registerDetector(self.i2cDeviceDetector)

        self.displayThread = threading.Thread(target=self.runCamera)
        self.displayThread.daemon = True
        self.displayThread.start()

    def join(self):
        self.displayThread.join()

    def stop(self):
        if self.displayThread:
            self.displayThread.stop()

    def initDevice(self, flag):
        if flag:
            self.camera = ArducamCamera()

            count = 0

            while not self.camera.initDevice(self.config_file) and count < 3:
                count += 1
                time.sleep(1)

            if count == 3:
                raise RuntimeError("initialize CPLD Failed, try 3 times.")

            self.camera.start()

            with self.signal_:
                self.signal_.notify()
        else:
            self.camera = None

        self.i2cDeviceDetector.setCamera(self.camera)

    def initSensor(self, flag):
        if flag and self.camera is not None:
            self.camera.initSensor()

    def runCamera(self):
        global exit_
        while not exit_:
            with self.signal_:
                if self.signal_.wait(1) is False:
                    continue

            while not exit_:
                if self.camera is None:
                    break

                try:
                    ret, data, cfg = self.camera.read()
                except:
                    break

                display_fps(0)

                if self.no_preview:
                    continue

                if ret:
                    image = convert_image(data, cfg, self.camera.color_mode)

                    if self.scale_width != -1:
                        scale = self.scale_width / image.shape[1]
                        image = cv2.resize(image, None, fx=scale, fy=scale)

                    cv2.imshow("Arducam", image)
                else:
                    print("timeout")

                key = cv2.waitKey(1)
                if key == ord('q'):
                    exit_ = True
                    break
                elif key == ord('s'):
                    np.array(data, dtype=np.uint8).tofile("image.raw")

        if self.camera is not None:
            self.camera.stop()
            self.camera.closeCamera()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config-file', type=str, required=False, help='Specifies the configuration file.',
                        default="C:\code\ArduCAM_USB_Camera_Shield_Python_Demo\IMX219_MIPI_2Lane_RAW10_8b_1920x1080.cfg")
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Output device information.')
    parser.add_argument('--preview-width', type=int, required=False, default=-1, help='Set the display width')
    parser.add_argument('-n', '--nopreview', action='store_true', required=False, help='Disable preview windows.')

    args = parser.parse_args()

    hotPlugCamera = HotPlugCamera(args)
    hotPlugCamera.start()
    hotPlugCamera.join()
    # time.sleep(50)
