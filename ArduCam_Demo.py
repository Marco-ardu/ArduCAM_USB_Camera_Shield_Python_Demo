import argparse
import signal

import numpy as np
from loguru import logger
from Arducam import *
from ImageConvert import *
from sharpness_check import *
from matplotlib import pyplot as plt
import matplotlib as mpl
exit_ = False
cmap = mpl.colormaps['Spectral']
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


def save_to_csv(filePath, mean_sharpness, min_sharpness, best_sharpness):
    line = "image_{}, {}, {}, {}\n".format(settingconfig["save_image_number"], mean_sharpness, min_sharpness, best_sharpness)

    with open("{}/record.csv".format(filePath), 'a') as f:
        f.write(line)


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
        self.output_path = "output_images"
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

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

    def show_heatmap(self, sharpness_scores_sectors, mean_sharpness, min_sharpness, coverage):
        fig, ax = plt.subplots()
        plt.imshow(sharpness_scores_sectors, vmin=0.25, vmax=0.4, cmap=cmap, aspect='auto')
        for i in range(sharpness_scores_sectors.shape[0]):
            for j in range(sharpness_scores_sectors.shape[1]):
                text = ax.text(j, i, f"{sharpness_scores_sectors[i, j]:.2f}",
                                ha="center", va="center", color="k")
        plt.axis('off')
        print(f'mean: {mean_sharpness}, min: {min_sharpness}, coverage: {coverage}')
        plt.savefig(f"{self.output_path}/image_{settingconfig['save_image_number']}_sharpness.png", bbox_inches='tight')
        plt.close()
        plt.clf()
        # fig.clf()
        ax.cla()

    @logger.catch
    def runCamera(self):
        global exit_
        self.camera = ArducamCamera(self.config_file)
        self.camera.registerCallback(self.notify)

        cv2.namedWindow("Arducam", cv2.WINDOW_NORMAL)
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
            step = 0.001
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
                    color_frame = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                    mean_sharpness, min_sharpness, best_sharpness, sharpness_scores_sectors, coverage = test(color_frame, image)

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

                    # elif self.scale_width != -1:
                    #     scale = self.scale_width / image.shape[1]
                    #     image = cv2.resize(image, None, fx=scale, fy=scale)

                    cv2.imshow("Arducam", color_frame)
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
                    exit(0)
                elif key == ord('s'):
                    if mean_sharpness != -1:
                        self.show_heatmap(sharpness_scores_sectors, mean_sharpness, min_sharpness, coverage)
                    cv2.imwrite("{}/image_{}.jpg".format(self.output_path, settingconfig["save_image_number"]), image)
                    cv2.imwrite("{}/image_{}_detect.jpg".format(self.output_path, settingconfig["save_image_number"]), color_frame)
                    # cv2.imwrite("{}.png".format(filename), gray)
                    np.frombuffer(data).tofile("{}/image_{}.raw".format(self.output_path, settingconfig["save_image_number"]))
                    # image.data.tofile("{}/image_{}.raw".format(self.output_path, settingconfig["save_image_number"]))
                    save_to_csv(self.output_path, mean_sharpness, min_sharpness, best_sharpness)
                    settingconfig["save_image_number"] += 1
                    save_yml_image_number(settingconfig["save_image_number"])

                elif key == ord('='): # '+' button
                    upadte_threshold_mean(step)
                elif key == ord('-'): # '-' button[]
                    upadte_threshold_mean(-step)
                elif key == ord('p'): # 'p' button
                    upadte_threshold_min(step)
                elif key == ord('o'): # 'o' button
                    upadte_threshold_min(-step)

        if self.camera is not None:
            self.camera.stop()
            self.camera.closeCamera()


if __name__ == "__main__":
    from pathlib import Path
    import os
    # 获取当前用户的主目录路径
    home_dir = Path.home()

    # 创建USBConfig文件夹路径
    usb_config_dir = home_dir / '.USBConfig'

    # 如果USBConfig文件夹不存在，则创建它
    if not usb_config_dir.exists():
        usb_config_dir.mkdir()

    # 创建config.cfg文件路径
    config_file_path = usb_config_dir / 'config.cfg'

    # 写入数据到config.cfg文件
    with config_file_path.open('w') as file:
        file.write(usb_config)

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config-file', type=str, required=False, help='Specifies the configuration file.',
                        default=str(config_file_path))
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Output device information.')
    parser.add_argument('--preview-width', type=int, required=False, default=1080, help='Set the display width')
    parser.add_argument('--preview-height', type=int, required=False, default=200, help='Set the display width')
    parser.add_argument('-a', '--fullscreen', action='store_true', required=False, help='Set the display full')
    parser.add_argument('-n', '--nopreview', action='store_true', required=False, help='Disable preview windows.')

    args = parser.parse_args()

    hotPlugCamera = HotPlugCamera(args)
    hotPlugCamera.start()
    hotPlugCamera.join()

    os.remove(config_file_path)