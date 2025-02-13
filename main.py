from flask import Flask, request, send_file
import core.alignment
import os

app = Flask(__name__)

# Define the upload folder and allowed file types
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}  # Add more types as needed

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API to upload a file and process it
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file", 400
    
    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        core.alignment.processing(filename)
        # Process the file
        processed_filename = os.path.splitext(filename)[0] + '.xlsx'        
        # Return the processed file as a response
        return send_file(processed_filename, as_attachment=True, download_name=f"{processed_filename}")

    return "Invalid file type", 400

if __name__ == '__main__':
    app.run(debug=True)
