import argparse
import signal

import numpy as np
from loguru import logger
from Arducam import *
from ImageConvert import *

exit_ = False

setPath()


@logger.catch
def sigint_handler(signum, frame):
    global exit_
    exit_ = True


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


@logger.catch
def display_fps(index):
    display_fps.frame_count += 1

    current = time.time()
    if current - display_fps.start >= 1:
        logger.info("fps: {}".format(display_fps.frame_count))
        display_fps.frame_count = 0
        display_fps.start = current


display_fps.start = time.time()
display_fps.frame_count = 0


class HotPlugCamera:
    def __init__(self, args):
        self.camera = None
        self.signal_ = threading.Condition()

        self.config_file = args.config_file
        self.verbose = args.verbose
        self.preview_width = args.preview_width
        self.no_preview = args.nopreview
        self.fullscreen = args.fullscreen
        self.scale_width = self.preview_width
        self.scale_height = args.preview_height

    @logger.catch
    def start(self):
        self.displayThread = threading.Thread(target=self.runCamera)
        self.displayThread.daemon = True
        self.displayThread.start()

    @logger.catch
    def join(self):
        self.displayThread.join()

    @logger.catch
    def stop(self):
        if self.displayThread:
            self.displayThread.stop()

    @logger.catch
    def notify(self, flag):
        if flag:
            with self.signal_:
                self.signal_.notify()

    @logger.catch
    def runCamera(self):
        global exit_
        self.camera = ArducamCamera(self.config_file)
        self.camera.registerCallback(self.notify)
        if self.fullscreen:
            cv2.namedWindow("Arducam", cv2.WINDOW_KEEPRATIO)
            cv2.setWindowProperty("Arducam", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        while not exit_:

            with self.signal_:
                if self.signal_.wait(1) is False:
                    mind = cv2AddChineseText(
                                            np.full(fill_value=255, shape=(1080, 1920, 3), dtype=np.uint8),
                                            "请重新连接USB接口",
                                            (450, 70),
                                            (0, 0, 255),
                                            50)
                    cv2.imshow("Arducam", mind)
                    cv2.waitKey(1)
                    logger.info("wait")
                    continue

            while not exit_:
                if not self.camera.isOpened:
                    break

                try:
                    ret, data, cfg = self.camera.read()
                except Exception:
                    break

                display_fps(0)

                if self.no_preview:
                    continue

                if ret:
                    if data is None:
                        logger.info("data is None")
                        continue

                    image = convert_image(data, cfg, self.camera.color_mode)

                    if image is None:
                        logger.info("image is None")
                        continue

                    if self.fullscreen:
                        x, y, w, h = cv2.getWindowImageRect('Arducam')
                        scale = h / image.shape[0]
                        image = cv2.resize(image, None, fx=scale, fy=scale)
                        bordersize = (w - image.shape[1]) // 2
                        image = cv2.copyMakeBorder(
                            image,
                            top=0,
                            bottom=0,
                            left=bordersize,
                            right=bordersize,
                            borderType=cv2.BORDER_CONSTANT,
                        )

                    elif self.scale_width != -1:
                        scale = self.scale_width / image.shape[1]
                        image = cv2.resize(image, None, fx=scale, fy=scale)

                    cv2.imshow("Arducam", image)
                else:
                    mind = cv2AddChineseText(
                                            np.full(fill_value=255, shape=(1080, 1920, 3), dtype=np.uint8),
                                            "请连接Sensor模组",
                                            (450, 70),
                                            (0, 0, 255),
                                            50)
                    cv2.imshow("Arducam", mind)
                    logger.info("timeout")

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
                        default="10.JPEG_capture_2592x1944.cfg")
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Output device information.')
    parser.add_argument('--preview-width', type=int, required=False, default=1080, help='Set the display width')
    parser.add_argument('--preview-height', type=int, required=False, default=200, help='Set the display width')
    parser.add_argument('-a', '--fullscreen', action='store_true', required=False, help='Set the display full')
    parser.add_argument('-n', '--nopreview', action='store_true', required=False, help='Disable preview windows.')

    args = parser.parse_args()

    hotPlugCamera = HotPlugCamera(args)
    hotPlugCamera.start()
    hotPlugCamera.join()
