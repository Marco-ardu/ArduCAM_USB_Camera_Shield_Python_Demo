import argparse
import time
import signal
import cv2

from Arducam import *
from ImageConvert import *
from DetectThread import DetectThread

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

camera = None
signal_ = threading.Condition()

def runCPLD(flag):
    global camera
    if flag: 
        camera = ArducamCamera()

        cpldCount = 0
        
        while not camera.initCPLD(config_file) and cpldCount < 3:
            cpldCount += 1
            time.sleep(1)

        if cpldCount == 3:
            raise RuntimeError("initialize CPLD Failed, try 3 times.")
        return camera
    else:
        camera = None
    return None
    
def runCamera(flag):
    global camera
    if flag and camera is not None:
        openCount = 0
        while not camera.openCamera() and openCount < 3:
            # openCount += 1
            time.sleep(1)

        if openCount == 3:
            raise RuntimeError("open Camera Failed, try 3 times.")

        if verbose:
            camera.dumpDeviceInfo()

        camera.start()

        with signal_:
            signal_.notify()
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config-file', type=str, required=False, help='Specifies the configuration file.', default="C:\code\ArduCAM_USB_Camera_Shield_Python_Demo\IMX219_MIPI_2Lane_RAW10_8b_1920x1080.cfg")
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Output device information.')
    parser.add_argument('--preview-width', type=int, required=False, default=-1, help='Set the display width')
    parser.add_argument('-n', '--nopreview', action='store_true', required=False, help='Disable preview windows.')
    

    args = parser.parse_args()
    config_file = args.config_file
    verbose = args.verbose
    preview_width = args.preview_width
    no_preview = args.nopreview

    scale_width = preview_width
    

    

    autoDetect3_0 = DetectThread()
    autoDetect3_0.daemon = True
    autoDetect3_0.start()
    autoDetect3_0.registerCPLDCallback(runCPLD)
    autoDetect3_0.registerCameraCallback(runCamera)

    while not exit_:
        with signal_:
            if signal_.wait(1) is False:
                continue

        while True:
            if camera is None:
                break
            
            try:
                ret, data, cfg = camera.read()
            except:
                break

            display_fps(0)

            if no_preview:
                continue

            if ret:
                image = convert_image(data, cfg, camera.color_mode)

                if scale_width != -1:
                    scale = scale_width / image.shape[1]
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

    if camera is not None:
        camera.stop()
        camera.closeCamera()
