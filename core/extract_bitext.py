import os
import re
import base64
import shutil
from google.cloud import vision
import io
import ast
import pdfplumber
import langdetect
import core.extract_sn_text as sn
import core.extract_vn_text as vn
from dotenv import load_dotenv
load_dotenv('.env')
api_key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]


def convert_to_bw(image, threshold=128): 
    # Apply thresholding to create a binary (black and white) image
    return image.convert('L').point(lambda p: p > threshold and 255)

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
                    sn.sn_image_cleaning(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                    shutil.copy(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"), os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', f"{base_file_name}_{page_number+1:03}.png"))
                    sn_content.append({'page_number': sn_page_number, 'file_page_number': page_number+1, 'content': sn_page_content})
                    sn_page_number = sn_page_number + 1
                else:
                    vn_content.append({'page_number': vn_page_number, 'content': vn.clean_text(page_content)})
                    vn_page_number = vn_page_number + 1
            except (SyntaxError, ValueError):
                vn_content.append({'page_number': vn_page_number, 'content': vn.clean_text(page_content)})
                vn_page_number = vn_page_number + 1
        else:
            page_content = extract_page_content(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
            if page_content:
                try:
                    if langdetect.detect(page_content)=='vi':
                        vn_page_content = vn.clean_text(page_content)
                        vn_content.append({'page_number': vn_page_number, 'content': vn_page_content})
                        vn_page_number = vn_page_number + 1
                        with open(txt_file, 'w', encoding='utf-8') as file:
                            file.write(vn_page_content)
                    else:
                        sn.sn_image_cleaning(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                        shutil.copy(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"), os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', f"{base_file_name}_{page_number+1:03}.png"))
                        sn_page_content = sn.extract_pages(os.path.join('images', f"{base_file_name}_{page_number+1:03}.png"))
                        sn_content.append({'page_number': sn_page_number, 'file_page_number': page_number+1, 'content': sn_page_content})
                        sn_page_number = sn_page_number + 1
                        with open(txt_file, 'w', encoding='utf-8') as file:
                            file.write(str(sn_page_content)) 
                except:
                    with open(txt_file, 'w', encoding='utf-8') as file:
                        file.write('') 
            else:
                with open(txt_file, 'w', encoding='utf-8') as file:
                    file.write('') 
    return sn_content, vn_content