import os
import re
import base64
import shutil
from google.cloud import vision
import io
import ast
import pdfplumber
from PIL import Image
import langdetect
import core.extract_sn_text as sn
import cv2
import numpy as np
from dotenv import load_dotenv
load_dotenv('.env')
api_key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
syllable_file_path = os.environ['SYLLABLE']
with open(syllable_file_path, encoding='utf-16') as f:
    morpho_syllable = f.read().splitlines() 

def convert_to_bw(image, threshold=128): 
    # Apply thresholding to create a binary (black and white) image
    return image.convert('L').point(lambda p: p > threshold and 255)

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

def resize_images_in_directory(directory_path):
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif')):
            image_path = os.path.join(directory_path, filename)
            resize_image(image_path)


def pdf_to_images(pdf_path, output_folder="images"):
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)  # Delete the folder and its contents
    os.makedirs(output_folder)
    image_paths = []
    page_number = 1
    base_file_name = os.path.splitext(os.path.basename(pdf_path))[0] 
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            image = convert_to_bw(page.to_image(resolution=300).original)  # Convert to image with 300 DPI for better OCR accuracy
            width, height = image.size
            if (width/height) > 0.9:
                left_half = image.crop((0, 0, width // 2, height))
                right_half = image.crop((width // 2, 0, width, height))
                # Save both halves
                left_half.save(os.path.join(output_folder, f"{base_file_name}_{page_number:03}.png"), format="PNG")
                right_half.save(os.path.join(output_folder, f"{base_file_name}_{page_number+1:03}.png"), format="PNG")
                image_paths.append(os.path.join(output_folder, f"{base_file_name}_{page_number:03}.png"))
                image_paths.append(os.path.join(output_folder, f"{base_file_name}_{page_number+1:03}.png"))
                page_number = page_number+2
            else:
                image.save(os.path.join(output_folder, f"{base_file_name}_{page_number:03}.png"), format="PNG")
                image_paths.append(os.path.join(output_folder, f"{base_file_name}_{page_number:03}.png"))
                page_number = page_number + 1
    return image_paths

# Function to encode the image to base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def number_to_text(n: str):
    ones = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    tens = ["lẻ", "mười", "hai mươi", "ba mươi", "bốn mươi", "năm mươi", "sáu mươi", "bảy mươi", "tám mươi", "chín mươi"]
    hundreds = ["", "một trăm", "hai trăm", "ba trăm", "bốn trăm", "năm trăm", "sáu trăm", "bảy trăm", "tám trăm", "chín trăm"]

    
    if n == "0":
        return "không"
    
    result = []

    if n >= 1000000:
        result.append(number_to_text(n//1000000)+' triệu')
        n %= 1000000

    # Process thousands
    if n>=1000:
        result.append(number_to_text(n // 1000)+' nghìn')
        n %= 1000

    # Process hundreds
    if n >= 100:
        result.append(hundreds[n // 100])
        n %= 100

    # Process tens
    if n >= 10:
        result.append(tens[n // 10])
        n %= 10
    else:
        if len(result)>=1:
            result.append('lẻ')

    # Process ones
    if n > 0:
        if n==1:
            if (len(result)>=1) and ('mươi' in result[-1]):
                result.append('mốt')
            else:
                result.append('một')
        elif n==5:
            if (len(result)>=1) and (result[-1]!='lẻ'):
                result.append('lăm')
            else:
                result.append('năm')
        else:
            result.append(ones[n])
    if len(result)>1 and result[-1]=='lẻ':
        return ' '.join(result[:-1]).strip()
    else:
        return ' '.join(result).strip()

# Regex to find numbers in the text
def split_words(word):
    if word == '':
        return ''
    list_chars=list(word)
    words = ''
    for i in range(len(list_chars)):
        if ''.join(list_chars[:i+1]) in morpho_syllable:
            words = ''.join(list_chars[:i+1]) + ' '
            new_list_chars = list_chars[i+1:]
            words += split_words(''.join(new_list_chars))
            if len(word)==len(''.join(words.strip().split())):
                return words
    if len(list_chars)> 0 and ''.join(list_chars) not in morpho_syllable:
        return ''

def clean_text(text):
    """ 
    Removing non-latin chars
    But keeping numbers and punctuations as default
    """
    text = re.sub(r'-\s*\d+\s*-', '', text)  # Remove "- digits -"
    text = re.sub(r'\(\s*\d+\s*\)', '', text)  # Remove "( digits )"
    text = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9\s\n]+', ' ', text)
     # Replace multiple consecutive spaces with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    def replace_number(match):
        num = int(match.group(0))  # Get the number from the match
        return number_to_text(num)  # Convert number to Vietnamese words
    
    # Replace all numbers in the text with their Vietnamese words
    text = re.sub(r'\d+', replace_number, text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    new_line = ''
    for word in text.split():
        if (word in morpho_syllable) or (word.isdigit()) or len(word)==1:
            new_line += word + ' '
        else:
            candidate = split_words(word)
            if candidate:
                new_line+= candidate + ' '
            else:
                new_line += word + ' '
    return re.sub(r'\s+', ' ', new_line).strip()

# Function to call GPT-4o API with the base64 image and a question
def extract_page_content(image_path):
    """Sử dụng Google Cloud Vision để OCR văn bản từ hình ảnh"""
    
    # Khởi tạo Client
    client = vision.ImageAnnotatorClient()

    # Đọc file ảnh
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    # Gửi yêu cầu OCR
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        return texts[0].description
    else:
        return ''

def remove_white_space_area(image_path, kernel_size=50, offset=True, offsetMeasure=10):
    # Load the image
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 5)
    _, binary_mask = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    expanded_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
    # Find contours in the binary mask
    contours, _ = cv2.findContours(expanded_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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

def remove_line(image_path):
    image = cv2.imread(image_path)
    edges = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 50, 200, None, 3)
    # Detect lines using Hough Transform
    lines = cv2.HoughLines(edges, rho=1, theta=np.pi/180, threshold=200)
    # Create a mask for the lines
    mask = np.ones_like(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)) * 255  # White background
    if lines is not None:
        for line in lines:
            rho, theta = line[0]  # Extract rho and theta from HoughLines
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = int(a * rho)
            y0 = int(b * rho)
            x1 = int(x0 + 1000 * (-b))  # Extend the detected line
            y1 = int(y0 + 1000 * (a))
            x2 = int(x0 - 1000 * (-b))
            y2 = int(y0 - 1000 * (a))
            cv2.line(mask, (x1, y1), (x2, y2), 0, thickness=5)  # Draw black lines on the mask
    inpainted = cv2.inpaint(image, (255 - mask), inpaintRadius=1, flags=cv2.INPAINT_TELEA)
    cv2.imwrite(image_path, inpainted)
    

def get_content_from_bitext(file_path):
    image_paths = pdf_to_images(pdf_path=file_path)
    if not os.path.exists('content'):
        os.mkdir('content')
    sn_page_number = 0
    vn_page_number = 0
    sn_content = list()
    vn_content = list()
    base_file_name = os.path.splitext(os.path.basename(file_path))[0] 
    for page_number in range(len(image_paths)):
        print('Extract page', page_number)
        txt_file = os.path.join('content', f"{base_file_name}_{page_number+1:03}.txt")
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as file:
                page_content = file.read()
            try:
                sn_page_content = ast.literal_eval(page_content)
                if isinstance(sn_page_content, list):
                    # remove_line(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    remove_white_space_area(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    resize_image(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    shutil.copy(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"), os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_content.append({'page_number': sn_page_number, 'file_page_number': page_number+1, 'content': sn_page_content})
                    sn_page_number = sn_page_number + 1
                else:
                    vn_content.append({'page_number': vn_page_number, 'content': clean_text(page_content)})
                    vn_page_number = vn_page_number + 1
            except (SyntaxError, ValueError):
                vn_content.append({'page_number': vn_page_number, 'content': clean_text(page_content)})
                vn_page_number = vn_page_number + 1
        else:
            page_content = extract_page_content(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
            try:
                if langdetect.detect(page_content)=='vi':
                    vn_page_content = clean_text(page_content)
                    vn_content.append({'page_number': vn_page_number, 'content': vn_page_content})
                    vn_page_number = vn_page_number + 1
                    with open(txt_file, 'w', encoding='utf-8') as file:
                        file.write(vn_page_content)
                else:
                    # remove_line(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    remove_white_space_area(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    resize_image(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    shutil.copy(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"), os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_page_content = sn.extract_pages(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_content.append({'page_number': sn_page_number, 'file_page_number': page_number+1, 'content': sn_page_content})
                    sn_page_number = sn_page_number + 1
                    with open(txt_file, 'w', encoding='utf-8') as file:
                        file.write(str(sn_page_content)) 
            except:
                try:
                    # remove_line(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    remove_white_space_area(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    resize_image(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    shutil.copy(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"), os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_page_content = sn.extract_pages(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_content.append({'page_number': sn_page_number, 'file_page_number': page_number+1, 'content': sn_page_content})
                    sn_page_number = sn_page_number + 1
                    with open(txt_file, 'w', encoding='utf-8') as file:
                        file.write(str(sn_page_content))
                except:
                    with open(txt_file, 'w', encoding='utf-8') as file:
                            file.write(page_content) 
    return sn_content, vn_content