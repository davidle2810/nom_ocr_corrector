
import core.align
import core.crop_images
import core.convert_to_paddle as cvt
import os
import pandas as pd
import shutil
import argparse
from openpyxl import load_workbook
from dotenv import load_dotenv
from xlsxwriter.workbook import Workbook
load_dotenv('.env')


def process_file(file_name):
    if os.path.exists(os.environ['OUTPUT_FOLDER']):
        shutil.rmtree(os.environ['OUTPUT_FOLDER'])
    os.makedirs(os.environ['OUTPUT_FOLDER'])
    os.makedirs(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'))
    os.makedirs(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label','crop_img'))
    output_file_path = core.align.align_bboxes(file_name)
    df = pd.read_excel(output_file_path)[['Img_Box_ID', 'Img_Box_Coordinate', 'SinoNom_Char']]
    image_names = cvt.convert_data_to_Labeltxt(df,os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'))
    cvt.convert_data_to_fileStatetxt(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label'),image_names)
    core.crop_images.crop_image(output_file_path)
    shutil.make_archive(os.path.splitext(os.path.basename(file_name))[0], 'zip', os.environ['OUTPUT_FOLDER'])
    shutil.rmtree(os.environ['OUTPUT_FOLDER'])
    shutil.rmtree('content') 
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser('Sentence alignment using sentence embeddings',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input', type=str, required=True,
                        help='path_to_input_document')
    parser.add_argument('--file_id', type=str, required=False,
                        help='file_id')
    args = parser.parse_args()
    # read the content of 2 pdf files: nom and viet
    input_file = args.input
    file_id = args.file_id if args.file_id else None
    if file_id:
        os.rename(input_file,os.path.join( os.path.dirname(input_file),  file_id+os.path.splitext(input_file)[1]))
        input_file = os.path.join( os.path.dirname(input_file),  file_id+os.path.splitext(input_file)[1])
    process_file(input_file)
    print('Results are saved to ',os.path.splitext(os.path.basename(input_file))[0]+'.zip')


