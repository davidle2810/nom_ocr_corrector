import os
import re
import base64
import shutil
import openai
import pdfplumber
import sinonom_pdf_helper as sn

from dotenv import load_dotenv
load_dotenv('.env')

api_key = os.environ['OPENAI_API_KEY']
client = openai.OpenAI(api_key=api_key)
syllable_file_path = os.environ['SYLLABLE']
with open(syllable_file_path, encoding='utf-16') as f:
    morpho_syllable = f.read().splitlines() 

def convert_to_bw(image, threshold=128): 
    # Apply thresholding to create a binary (black and white) image
    return image.convert('L').point(lambda p: p > threshold and 255)

def pdf_to_images(pdf_path, output_folder="output_images"):
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)  # Delete the folder and its contents
    os.makedirs(output_folder)
    image_paths = []
    page_number = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            image = convert_to_bw(page.to_image(resolution=300).original)  # Convert to image with 300 DPI for better OCR accuracy
            width, height = image.size
            if (width/height) > 0.9:
                left_half = image.crop((0, 0, width // 2, height))
                right_half = image.crop((width // 2, 0, width, height))
                # Save both halves
                left_half.save(os.path.join(output_folder, f"page_{page_number}.png"), format="PNG")
                right_half.save(os.path.join(output_folder, f"page_{page_number+1}.png"), format="PNG")
                image_paths.append(os.path.join(output_folder, f"page_{page_number}.png"))
                image_paths.append(os.path.join(output_folder, f"page_{page_number+1}.png"))
                page_number = page_number+2
            else:
                image.save(os.path.join(output_folder, f"page_{page_number}.png"), format="PNG")
                image_paths.append(os.path.join(output_folder, f"page_{page_number}.png"))
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
def splitting(text_list):
   
    result = []
    if len(text_list)==0:
        return ['#']
    for i in range(1,len(text_list)+1):
        if len(set([''.join(text_list[:i])]).intersection(set(morpho_syllable)))>0 and len(text_list[:i])!=1:
            result.append([''.join(text_list[:i]),splitting(text_list[i:])])            
    return result


# Recursive splitting function
def connect(text, structure):
    results = []
    
    # Helper function to traverse the structure
    def traverse(node, remaining_text, current_split):
        if not remaining_text:
            # If there's no text left and '#' is a valid terminal, add the result
            if "#" in node:
                results.append(" ".join(current_split))
            return
        
        # Iterate over each child node
        for syllable, children in node:
            # Check if the current text starts with this syllable
            if remaining_text.startswith(syllable):
                # Recursively process the remaining text
                traverse(children, remaining_text[len(syllable):], current_split + [syllable])
        
        # If no valid path matches, stop the traversal
        if "#" in node:
            results.append(" ".join(current_split))
    
    # Start traversal
    traverse(structure, text, [])
    return min(results, key=len) if results else None

def clean_text(text):
    """ 
    Removing non-latin chars
    But keeping numbers and punctuations as default
    """
    text = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9\s\n]+', ' ', text)
     # Replace multiple consecutive spaces with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    def replace_number(match):
        num = int(match.group(0))  # Get the number from the match
        return number_to_text(num)  # Convert number to Vietnamese words
    
    # Replace all numbers in the text with their Vietnamese words
    text = re.sub(r'\d+', replace_number, text.lower())
    new_line = ''
    for word in text.split():
        if (word in morpho_syllable) or (word.isdigit()) or len(word)==1:
            new_line += word + ' '
        else:
            candidate = connect(word,splitting(list(word)))
            if candidate:
                new_line+= candidate + ' '
            else:
                new_line += word + ' '
    return new_line

# Function to call GPT-4o API with the base64 image and a question
def extract_page_content(image_path):
    prompt = "Read the input image, if the content is Vietnamese, return ONLY the content in the image, else return 'ns_image'"
    img_type = 'image/png'
    #client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{img_type};base64,{encode_image_to_base64(image_path)}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content.lower()

def get_content_from_bitext(file_path):
    image_paths = pdf_to_images(pdf_path=file_path)
    sn_page_number = 0
    vn_page_number = 0
    sn_content = list()
    vn_content = list()
    for page_number in range(len(image_paths)):
        page_content = extract_page_content(os.path.join('output_images', f"page_{page_number}.png"))
        if 'ns_image' in page_content.lower():
            sn_content.append({'page_number': sn_page_number, 'content': sn.extract_pages(os.path.join('output_images', f"page_{page_number}.png"))})
            sn_page_number = sn_page_number + 1
        else:
            vn_content.append({'page_number': vn_page_number, 'content': clean_text(page_content)})
            vn_page_number = vn_page_number + 1
    return sn_content, vn_content