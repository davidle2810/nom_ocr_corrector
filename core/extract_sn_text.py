import core.sort_boxes
import http.client
import mimetypes
from codecs import encode
import ssl
import math
import cv2
import numpy as np
from deskew import determine_skew
import json
import os
from PIL import Image
from dotenv import load_dotenv

load_dotenv('.env')
context = ssl._create_unverified_context()
conn = http.client.HTTPSConnection(os.environ['SN_DOMAIN'], context=context)
def upload_image_api(image_path):
    dataList = []
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=image_file; filename={0}'.format('image.png')))

    fileType = mimetypes.guess_type('image_path')[0] or 'application/octet-stream'
    dataList.append(encode('Content-Type: {}'.format(fileType)))
    dataList.append(encode(''))
    with open(image_path, 'rb') as f:
        dataList.append(f.read())
    dataList.append(encode('--'+boundary+'--'))
    dataList.append(encode(''))
    body = b'\r\n'.join(dataList)
    payload = body
    headers = {
    'Content-type': 'multipart/form-data; boundary={}'.format(boundary) 
    }
    conn.request("POST", "/api/web/clc-sinonom/image-upload", payload, headers)
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    if data['is_success']:
        file_name = data['data']['file_name']
    else:
        print("error uploading image:", data['message'])
    return file_name

def ocr_image_api(image_path_server):
    payload = f"""{{"ocr_id": 1, "file_name": "{image_path_server}"}}"""
    headers = {'Content-Type': 'application/json'}
    conn.request("POST", "/api/web/clc-sinonom/image-ocr", payload, headers)
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    if data['is_success']:
        ocr = data['data']['result_bbox']
    else:
        return None
    result = list()
    for i in ocr:
        result.append({'position':i[0],'text': i[1][0]})
    return result

def sn_transliteration_api(text: str) -> str:
    payload = json.dumps({"text": text})  # Using json.dumps to create valid JSON string
    headers = {
        'Content-Type': 'application/json'
    }
    # Convert payload to UTF-8 bytes before sending
    conn.request("POST", "/api/web/clc-sinonom/sinonom-transliteration", payload.encode('utf-8'), headers)
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    if data['is_success']:
        result_text = data['data']['result_text_transcription']
    return result_text

def remove_small_dots(image, max_area=5):
    contours, _ = cv2.findContours(255 - image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) < max_area:
            cv2.drawContours(image, [c], -1, 255, -1)
    return image

def rotate(image, angle, background):
    old_width, old_height = image.shape[:2]
    angle_radian = math.radians(angle)
    width = abs(np.sin(angle_radian) * old_height) + abs(np.cos(angle_radian) * old_width)
    height = abs(np.sin(angle_radian) * old_width) + abs(np.cos(angle_radian) * old_height)

    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    rot_mat[1, 2] += (width - old_width) / 2
    rot_mat[0, 2] += (height - old_height) / 2
    return cv2.warpAffine(image, rot_mat, (int(round(height)), int(round(width))), borderValue=background)

def deskew(image):
    angle = determine_skew(image)
    rotated = rotate(image, angle, (0, 0, 0))
    return rotated

def resize_image(image_path, max_size=1200):
    with Image.open(image_path) as img:
        width, height = img.size
        total_size = width + height

        if total_size > max_size:
            scale_factor = max_size / total_size
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            img.save(image_path)


def sn_image_cleaning(image_path, kernel_size=50, offset=True, offsetMeasure=10):
    # Load the image
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    deskewed = deskew(gray)
    blurred = cv2.medianBlur(deskewed, 5)
    _, binary = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    expanded = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    # Connected Components with Area and Size Filtering
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(expanded, connectivity=8)

    # Define thresholds
    min_area = 10          # Keep very small components
    min_width = 1
    min_height = 1

    # Initialize clean mask
    filtered = np.zeros(binary.shape, dtype=np.uint8)

    # Loop through components (excluding background)
    for label in range(1, num_labels):
        x, y, w, h, area = stats[label]
        
        if area >= min_area and w >= min_width and h >= min_height:
            filtered[labels == label] = 255
    # Find contours in the binary mask
    enhanced = cv2.detailEnhance(cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR), sigma_s=50, sigma_r=0.2)
    contours, _ = cv2.findContours(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return    
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    if offset:
        x -= offsetMeasure
        y -= offsetMeasure
        w += 2 * offsetMeasure
        h += 2 * offsetMeasure
    x = max(x, 0)
    y = max(y, 0)
    w = min(w, image.shape[1] - x)
    h = min(h, image.shape[0] - y)
    cropped_image = image[y:y + h, x:x + w]
    cv2.imwrite(image_path, cropped_image)
    resize_image(image_path)

def extract_pages(image_path: str) -> list:
    """
    Extracts the NS text from each page of the provided file.
    :param file_name: The path to the NS file.
    :return: A list of dictionaries, where each dictionary represents a page in the file and contains:
        - 'page_number': An integer representing the page index (starting from 0).
        - 'content': A list of dictionaries, each representing a line of text on the page. Each line dictionary contains:
            - 'bbox': A list of four tuples representing the coordinates of the bounding box for the text, in the form [[x0, y0], [x1, y1], [x2, y2], [x3, y3]].
            - 'content': The text content within the bounding box.
            - 'transliteration': The transliterated version of the text content.
    """
    sn_image_cleaning(image_path)
    main_image = Image.open(image_path)  # replace with your image path
    # Get width and height
    main_image_width, main_image_height = main_image.size
    # Calculate area
    main_image_area = float(main_image_width * main_image_height)
    page_content = list()
    try:
        text_lines = ocr_image_api(upload_image_api(image_path))
        transliterate_text = sn_transliteration_api('\n'.join([text_line['text'] for text_line in text_lines]))
    except:
        text_lines = ocr_image_api(upload_image_api(image_path))
        transliterate_text = sn_transliteration_api('\n'.join([text_line['text'] for text_line in text_lines]))           
    for line_id, text_line in enumerate(text_lines):
        bbox = core.sort_boxes.normalize_bbox(text_line['position'])
        if (core.sort_boxes.quadrilateral_area(bbox)/main_image_area) > 0.005:
            page_content.append({'bbox': bbox, 'content': text_line['text'], 'transliteration': transliterate_text[line_id]})
    return core.sort_boxes.sort(page_content)
