import core.sort_boxes
import base64
import requests
import json
import os

TOKEN = "677596f6-bc67-472b-a46d-c5bc6d49012d"
EMAIL = "ngthach3110@gmail.com"

from dotenv import load_dotenv
load_dotenv('.env')

def encode_image_to_base64(image_path):
    """
    Converts an image file to a base64-encoded string.
    :param image_path: Path to the image file
    :return: Base64-encoded string
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string

def kandian_ocr_api(
    token,
    email,
    image_base64,
    det_mode="auto",
    char_ocr=False,
    image_size=0,
    return_position=False,
    return_choices=False
):
    """
    Calls the Kandian Ancient Books OCR API with the specified parameters.
    :param token: API token
    :param email: Registered email
    :param image_base64: Base64-encoded image string
    :param det_mode: Text content layout style ('auto', 'sp', 'hp')
    :param char_ocr: Detect and recognize single characters only (Boolean)
    :param image_size: Image size adjustment before recognition (Integer)
    :param return_position: Return text line and character coordinate info (Boolean)
    :param return_choices: Return alternative candidate words for each character (Boolean)
    :return: Response from the API
    """
    url = "https://ocr.kandianguji.com/ocr_api"

    payload = {
        "token": token,
        "email": email,
        "image": image_base64,
        "det_mode": det_mode,
        "char_ocr": char_ocr,
        "image_size": image_size,
        "return_position": return_position,
        "return_choices": return_choices,
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"HTTP {response.status_code}: {response.text}"}

def upload_image_api(image_path):
    headers = {"User-Agent": "upload_image"}
    url_upload = os.environ['SN_IMAGE_UPLOAD']
    files = {'image_file': open(image_path, 'rb')}
    response = requests.post(url_upload, files=files)
    data = json.loads(response.text)
    if data['is_success']:
        file_name = data['data']['file_name']
    else:
        print("error uploading image:", data['message'])
    return file_name

def ocr_image_api(image_path_server):
    headers = {"User-Agent": "ocr"}
    url_ocr = os.environ['SN_OCR']
    data = {
        "ocr_id": 1,
        "file_name": image_path_server
    }
 
    ocr_response = requests.post(url_ocr, json=data)  
    data = json.loads(ocr_response.text)
    if data['is_success']:
        ocr = data['data']['result_bbox']
    else:
        return None
    result = list()
    for i in ocr:
        result.append({'position':i[0],'text': i[1][0]})
    return result

def sn_transliteration_api(text: str) -> str:
    """
    Calls the transliteration API to convert the input text.
    
    :param text: The text to be transliterated.
    :return: The transliterated text if successful, else an empty string.
    """
    headers = {"User-Agent": "transliteration"}
    url_transliteration = os.environ['SN_TRANSLITERATE']
    data = {"text":text}
    response = requests.post(url_transliteration, headers=headers, json=data)  
    data = json.loads(response.text)
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
    # text_lines = kandian_ocr_api(
    #             token=TOKEN,
    #             email=EMAIL,
    #             image_base64=encode_image_to_base64(image_path),
    #             det_mode="auto",
    #             char_ocr=False,
    #             image_size=0,
    #             return_position=True,
    #             return_choices=False,
    #         )['data']['text_lines']
    transliterate_text = sn_transliteration_api('\n'.join([text_line['text'] for text_line in text_lines]))        
    for line_id, text_line in enumerate(text_lines):
        page_content.append({'bbox': text_line['position'], 'content': text_line['text'], 'transliteration': transliterate_text[line_id]})
    return core.sort_boxes.sort(page_content)
    