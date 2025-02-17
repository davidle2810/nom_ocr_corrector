from flask import Flask, request, send_file, make_response
from flask_cors import CORS
import core.alignment
import os
import shutil
app = Flask(__name__)
CORS(app)

# Define the upload folder and allowed file types
UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'pdf'}  # Add more types as needed



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        core.alignment.process(filename)
        # Process the file
        processed_filename = 'output.zip'
        # headers = {
        #     'Access-Control-Allow-Origin': '*',
        #     'Access-Control-Allow-Credentials': 'true',
        #     'Access-Control-Allow-Methods': '*'
        # }        
        # Return the processed file as a response

        # Return the processed file as a response with proper headers
        return send_file(
            processed_filename,
            as_attachment=True,
            download_name=os.path.basename(processed_filename),  # Just the file name, not the full path
            )
    return  make_response("Invalid file type", 400)

if __name__ == '__main__':
    app.run(debug=False)

