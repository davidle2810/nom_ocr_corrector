import core.sort_boxes
import http.client
import mimetypes
from codecs import encode
import ssl
import certifi
import json
import os

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
    page_content = list()
    text_lines = ocr_image_api(upload_image_api(image_path))
    transliterate_text = sn_transliteration_api('\n'.join([text_line['text'] for text_line in text_lines]))        
    for line_id, text_line in enumerate(text_lines):
        page_content.append({'bbox': text_line['position'], 'content': text_line['text'], 'transliteration': transliterate_text[line_id]})
    return core.sort_boxes.sort(page_content)
    