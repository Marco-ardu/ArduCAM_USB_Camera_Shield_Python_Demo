import numpy as np
import cv2
import yaml

ARUCO_DICT = cv2.aruco.Dictionary_get( cv2.aruco.DICT_4X4_1000 )
# BOARD = cv2.aruco.CharucoBoard_create(19, 13, 50/1000, 39/1000, ARUCO_DICT)
BOARD = cv2.aruco.CharucoBoard_create(33, 23, 50/1000, 39/1000, ARUCO_DICT)
ARUCO_PARAMS = cv2.aruco.DetectorParameters_create()
ARUCO_PARAMS.minMarkerDistanceRate = 0.01

# set some example thresholds for FAIL/PASS criteria
with open('setting.yaml', 'r') as stream:
    settingconfig = yaml.load(stream, Loader=yaml.FullLoader)
threshold_mean = settingconfig["threshold_mean"]
threshold_min = settingconfig["threshold_min"]

def save_yml_image_number(image_number):
    with open('setting.yaml', 'r') as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    with open('setting.yaml', 'w') as stream:
        config['save_image_number'] = image_number
        config = yaml.dump(config)
        stream.write(config)

def save_yml_threshold(threshold_mean, threshold_min):
    with open('setting.yaml', 'r') as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    with open('setting.yaml', 'w') as stream:
        config['threshold_mean'] = threshold_mean
        config['threshold_min'] = threshold_min
        config = yaml.dump(config)
        stream.write(config)

def detect_charuco_board(image: np.array):
    markers, marker_ids, rejectedImgPoints = cv2.aruco.detectMarkers(image, ARUCO_DICT, parameters=ARUCO_PARAMS)  # First, detect markers
    marker_corners, marker_ids, refusd, recoverd = cv2.aruco.refineDetectedMarkers(image, BOARD, markers, marker_ids, rejectedCorners=rejectedImgPoints)

    # If found, add object points, image points (after refining them)
    if len(marker_corners)>0:
        num_corners, corners, ids = cv2.aruco.interpolateCornersCharuco(marker_corners,marker_ids,image, BOARD, minMarkers = 1)
        return num_corners, corners, ids, marker_corners, marker_ids
    else:
        return 0, np.array([]), np.array([]), np.array([]), np.array([])    

def analyze_sharpness_fft(img, corners, roi_size):
    sharpness_scores = []

    h, w = img.shape
    for corner in corners:
        x, y = corner[0].astype(int)
        # Define the ROI around the corner
        if x < roi_size:
            x = roi_size
        if x >= w - roi_size:
            x = w - roi_size-1
        if y < roi_size:
            y = roi_size
        if y >= h - roi_size:
            y = h - roi_size-1
        roi = img[y - roi_size:y + roi_size, x - roi_size:x + roi_size]
        fft = np.fft.fft2(roi)
        size = 2
        fft[0:size, 0:size] = 0
        recon = np.fft.ifft2(fft)
        magnitude = 20 * np.log(np.abs(recon))
        sharpness = np.mean(magnitude/255)
        sharpness_scores.append(sharpness)

    return sharpness_scores


def upadte_threshold_mean(value=0.001):
    global threshold_mean
    threshold_mean += value
    save_yml_threshold(threshold_mean, threshold_min)

def upadte_threshold_min(value=0.001):
    global threshold_min
    threshold_min += value
    save_yml_threshold(threshold_mean, threshold_min)

best_sharpness = 0.0

def test(img, gray):
    global best_sharpness
    w, h = gray.shape
    corners = detect_charuco_board(gray)
    # print(corners)
    if corners[0] > 0:
        max_sharpness_value = 0.35
        min_sharpness_value = 0.3
        sharpness_scores = analyze_sharpness_fft(gray, corners[1], 5)

        idx = 0
        for corner in corners[1]:
            corner = corner[0]
            score = np.clip(sharpness_scores[idx],min_sharpness_value,max_sharpness_value)
            score = (score-min_sharpness_value)/(max_sharpness_value - min_sharpness_value)
            color = (0,int(score*255),int((1-score)*255))
            img = cv2.circle(img, (int(corner[0]),int(corner[1])), 3, color, 5)
            idx+=1
        mean_sharpness = np.mean(sharpness_scores)
        min_sharpness = np.quantile(sharpness_scores,0.05)
        cv2.putText(img, f'Threshold Mean(-/= key): {threshold_mean:0.3f}', (10,120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(img, f'Threshold Min(o/p key): {threshold_min:0.3f}', (10,150),  cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

        cv2.putText(img, f'Mean sharpness: {mean_sharpness:0.3f}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(img, f'Min sharpness: {min_sharpness:0.3f}', (10,60),  cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        if mean_sharpness > best_sharpness:
            best_sharpness = mean_sharpness
        if np.abs(mean_sharpness - best_sharpness)/best_sharpness < 0.005:
            cv2.putText(img, f'Best: {min_sharpness:0.3f}', (10,90),  cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        
        if mean_sharpness > threshold_mean and min_sharpness > threshold_min:
            cv2.putText(img, f'PASSED: {min_sharpness:0.3f}', (int(w/2),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        else:
            cv2.putText(img, f'FAILED: {min_sharpness:0.3f}', (int(w/2),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        
        return mean_sharpness, min_sharpness, best_sharpness
    
    return -1, -1, -1
        # cv2.imshow('Image', img)
        # display = cv2.resize(img, None, fx=0.5, fy=0.5)
        # cv2.imshow("Image", display)
    
        # key = cv2.waitKey(1)
        # if key == ord('q'):
        #     return False
        
        # return True