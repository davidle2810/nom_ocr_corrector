from flask import Flask, request, send_file, make_response
from flask_cors import CORS
import core.align
import core.crop_images
import core.convert_to_paddle as cvt
import os
import pandas as pd
import shutil
import argparse

from dotenv import load_dotenv
load_dotenv('.env')


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

if __name__ == '__main__':
    parser = argparse.ArgumentParser('Sentence alignment using sentence embeddings',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input', type=str, required=True,
                        help='path_to_input_document')
    args = parser.parse_args()
    # read the content of 2 pdf files: nom and viet
    input_file = args.input
    process_file(input_file)
    print('Results are saved to ',os.path.splitext(os.path.basename(input_file))[0]+'.zip')


