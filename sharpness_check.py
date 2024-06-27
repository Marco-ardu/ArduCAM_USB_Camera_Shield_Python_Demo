import numpy as np
import cv2
import yaml


# set some example thresholds for FAIL/PASS criteria
with open('setting.yaml', 'r') as stream:
    settingconfig = yaml.load(stream, Loader=yaml.FullLoader)
threshold_mean = settingconfig["threshold_mean"]
threshold_min = settingconfig["threshold_min"]

ARUCO_DICT = cv2.aruco.Dictionary_get( cv2.aruco.DICT_4X4_1000 )
BOARD = cv2.aruco.CharucoBoard_create(settingconfig["CharucoBoardWidth"], settingconfig["CharucoBoardHeight"], settingconfig["squareLength"]/1000, settingconfig["markerLength"]/1000, ARUCO_DICT)
# BOARD = cv2.aruco.CharucoBoard_create(33, 23, 50/1000, 39/1000, ARUCO_DICT)
ARUCO_PARAMS = cv2.aruco.DetectorParameters_create()
ARUCO_PARAMS.minMarkerDistanceRate = 0.01

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

def analyze_sharpness_fft(img, corners, roi_size, fft_cutoff):
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
        roi = img[y - roi_size:y + roi_size, x - roi_size:x + roi_size].copy()
        cv2.normalize(roi, roi, 0, 255, cv2.NORM_MINMAX)
        fft = np.fft.fft2(roi)
        fft[0:fft_cutoff, 0:fft_cutoff] = 0
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

def get_sharpness_image(corners, sharpness_scores, res, nbins):
    sharpness_sector_scores = [[[] for j in range(nbins[1])] for i in range(nbins[0])]       
    for j, loc in enumerate(corners):
        binx = np.clip(int(loc[0][0]/res[0]*nbins[0]), 0, nbins[0]-1)
        biny = np.clip(int(loc[0][1]/res[1]*nbins[1]), 0, nbins[1]-1)
        sharpness_sector_scores[binx][biny].append(sharpness_scores[j])                           
    sharpness_sector_scores = [[np.median(cell) if len(cell) > 0 else 0 for cell in row] for row in sharpness_sector_scores]
    sharpness_sector_scores = np.array(sharpness_sector_scores)
    # print(sharpness_sector_scores.T)
    return sharpness_sector_scores.T

def test(img, gray):
    global best_sharpness
    h, w = gray.shape
    corners = detect_charuco_board(gray)
    if corners[0] > 0:
        max_sharpness_value = 0.35
        min_sharpness_value = 0.3
        sharpness_scores = analyze_sharpness_fft(gray, corners[1], settingconfig['roi_size'], settingconfig['fft_cutoff'])
        idx = 0
        for corner in corners[1]:
            corner = corner[0]
            score = np.clip(sharpness_scores[idx],min_sharpness_value,max_sharpness_value)
            score = (score-min_sharpness_value)/(max_sharpness_value - min_sharpness_value)
            color = (0,int(score*255),int((1-score)*255))
            img = cv2.circle(img, (int(corner[0]),int(corner[1])), 3, color, 5)
            idx+=1
        sharpness_scores_sectors = get_sharpness_image(corners[1], sharpness_scores, (w,h), (settingconfig['binx'], settingconfig['biny']))
        if settingconfig['mean_sectors']:
            if settingconfig['mean_zeros']:
                mean_sharpness = np.mean(sharpness_scores_sectors)
            else:
                mean_sharpness = np.mean(sharpness_scores_sectors[sharpness_scores_sectors>0])
        else:
            mean_sharpness = np.mean(sharpness_scores)
        if settingconfig['min_sectors']:
            if settingconfig['min_zeros']:
                min_sharpness = np.quantile(sharpness_scores_sectors, settingconfig['min_sharpness_quantile'])
            else:
                min_sharpness = np.quantile(sharpness_scores_sectors[sharpness_scores_sectors>0], settingconfig['min_sharpness_quantile'])
        else:
            min_sharpness = np.quantile(sharpness_scores, settingconfig['min_sharpness_quantile'])
        coverage = ((settingconfig['binx']*settingconfig['biny'])-np.sum(sharpness_scores_sectors==0))/(settingconfig['binx']*settingconfig['biny'])
        cv2.putText(img, f'Mean sharpness: {mean_sharpness:0.3f}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(img, f'Min sharpness: {min_sharpness:0.3f}', (10,60),  cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        if mean_sharpness > best_sharpness:
            best_sharpness = mean_sharpness
        cv2.putText(img, f'Coverage: {coverage:0.3f}', (10,90),  cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        
        if mean_sharpness < settingconfig['threshold_mean']:
            cv2.putText(img, f'FAILED: mean sharpness {mean_sharpness:0.3f} < {settingconfig["threshold_mean"]:0.3f}', (int(w/4),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        elif min_sharpness < settingconfig['threshold_min']:
            cv2.putText(img, f'FAILED: min sharpness {min_sharpness:0.3f} < {settingconfig["threshold_min"]:0.3f}', (int(w/4),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        elif coverage < settingconfig['coverage_threshold']:
            cv2.putText(img, f'FAILED: coverage {coverage:0.2f} < {settingconfig["coverage_threshold"]:0.2f}', (int(w/4),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        else:
            cv2.putText(img, f'PASSED', (int(w/2),int(h/2)),  cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    
        return mean_sharpness, min_sharpness, best_sharpness, sharpness_scores_sectors, coverage
    
    return -1, -1, -1, -1, -1
        # cv2.imshow('Image', img)
        # display = cv2.resize(img, None, fx=0.5, fy=0.5)
        # cv2.imshow("Image", display)
    
        # key = cv2.waitKey(1)
        # if key == ord('q'):
        #     return False
        
        # return True