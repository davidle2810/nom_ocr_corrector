from flask import Flask, request, send_file, make_response
from flask_cors import CORS
import core.align
import core.crop_images
import core.convert_to_paddle as cvt
import os
import pandas as pd
import shutil
app = Flask(__name__)
CORS(app)

# Define the upload folder and allowed file types
UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'pdf'}  # Add more types as needed

from dotenv import load_dotenv
load_dotenv('.env')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file(file_name):
    if os.path.exists(os.environ['OUTPUT_FOLDER']):
        shutil.rmtree(os.environ['OUTPUT_FOLDER'])
    os.makedirs(os.environ['OUTPUT_FOLDER'])
    os.makedirs(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'))
    os.makedirs(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label','crop_img'))
    output_file_path = core.align.align_bboxes(file_name)
    df = pd.read_excel(output_file_path)[['image_name','id', 'bbox', 'correction']]
    image_names = cvt.convert_data_to_Labeltxt(df,os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'))
    cvt.convert_data_to_fileStatetxt(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'),image_names)
    core.crop_images.crop_image(output_file_path)
    shutil.make_archive(os.path.splitext(os.path.basename(file_name))[0], 'zip', os.environ['OUTPUT_FOLDER'])
    shutil.rmtree(os.environ['OUTPUT_FOLDER'])

# API to upload a file and process it
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return  make_response("No file part", 400)
    file = request.files['file']
    
    if file.filename == '':
        return  make_response("No selected file", 400)
    # Ensure the upload folder exists
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER)
    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        process_file(filename)
        # Process the file
        processed_filename = 'output.zip'

        # Return the processed file as a response with proper headers
        return send_file(
            processed_filename,
            as_attachment=True,
            download_name=os.path.basename(processed_filename),  # Just the file name, not the full path
            )
    return  make_response("Invalid file type", 400)

if __name__ == '__main__':
    app.run(debug=False)

