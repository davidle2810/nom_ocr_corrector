import core.extract_bitext as bitext
import core.corrector as crt
import shutil
import os
import pandas as pd
import numpy as np
from laserembeddings import Laser
from sklearn.metrics.pairwise import cosine_similarity
from xlsxwriter.workbook import Workbook
laser = Laser()

from dotenv import load_dotenv
load_dotenv('.env')

def align_paragraphs(sn2vn_content,vn_content):
    source_embeddings = laser.embed_sentences([page['content'] for page in sn2vn_content], lang='vi')  # or "en" if your source is in English, etc.
    target_embeddings = laser.embed_sentences([page['content'] for page in vn_content], lang='vi')  # adapt the language code as needed
    source_embeddings = np.array(source_embeddings)
    target_embeddings = np.array(target_embeddings)
    alignment_results = list()
    similarities = cosine_similarity(source_embeddings, target_embeddings)
    best_i = np.argmax(similarities, axis=1)
    best_j = np.argmax(similarities, axis=0)
    for i, source_page in enumerate(sn2vn_content):
        if best_j[best_i[i]]==i:
            best_score = similarities[i][best_i[i]]
            target_page = vn_content[best_i[i]]
            
            alignment_results.append({
                'file_page_number': source_page['file_page_number'],
                'source_page_number': source_page['page_number'],
                'source_text': source_page['content'],
                'target_page_number': target_page['page_number'],
                'target_text': target_page['content'],
                'similarity_score': float(best_score)
            })
    alignment_results.sort(key=lambda x: x['target_page_number'], reverse = False)
    return alignment_results

def align_bboxes(input_file):
    sn_content, vn_content = bitext.get_content_from_bitext(input_file)
    # get the transliteration of sino-nom content
    sn2vn_content = list()
    for page in sn_content:
        sn2vn_content.append({'page_number': page['page_number'], 'file_page_number': page['file_page_number'],'content': '\n'.join([line['transliteration'] for line in page['content']])})
    # align paragraphs
    paragraph_alignments = align_paragraphs(sn2vn_content,vn_content)
    shutil.rmtree('images')
    # align sentences
    output_file = os.path.splitext(os.path.basename(input_file))[0]  + '.xlsx'
    with Workbook(os.path.join(os.environ['OUTPUT_FOLDER'],output_file)) as workbook:
        worksheet   = workbook.add_worksheet(f"Result")
        font_format = workbook.add_format({'font_name': 'Nom Na Tong'})
        red         = workbook.add_format({'color': 'red', 'font_name': 'Nom Na Tong'})
        blue        = workbook.add_format({'color': 'blue', 'font_name': 'Nom Na Tong'})
        black       = workbook.add_format({'color': 'black', 'font_name': 'Nom Na Tong'})
        worksheet.write(0, 0, 'image_name', font_format)
        worksheet.write(0, 1, 'id', font_format)
        worksheet.write(0, 2, 'bbox', font_format)
        worksheet.write(0, 3, 'ocr', font_format)
        worksheet.write(0, 4, 'correction', font_format)
        worksheet.write(0, 5, 'nom', font_format)
        row_id = 1
        for alignment in paragraph_alignments:
            file_page_number = alignment['file_page_number']
            src_id = alignment['source_page_number']
            tgt_id = alignment['target_page_number']
            bbox_id = 1
            src_lines = [(line['bbox'],line['content']) for line in sn_content[src_id]['content']]
            tgt_lines = ' '.join(vn_content[tgt_id]['content'].split('\n')).split(' ')
            nom_lines = ''.join([line[1] for line in src_lines])
            corrected_list=crt.correct(nom_lines,tgt_lines)
            vie_list = tgt_lines.copy()
            for chunk in src_lines:
                bbox = chunk[0]
                nom_list = list(chunk[1])
                ocrs = []
                corrs = []
                qns = []
                while len(nom_list)>0:
                    if corrected_list[0].startswith('correct:'):
                        ocrs.extend((black, nom_list[0]))
                        corrs.extend((black, corrected_list[0].split(':')[1]))
                        qns.extend((black, vie_list[0] + ' '))
                        nom_list.pop(0)
                        vie_list.pop(0)
                    elif corrected_list[0].startswith('replace:'):
                        if corrected_list[0].split(':')[1][-1]!="X":
                            ocrs.extend((blue, nom_list[0]))
                            corrs.extend((blue, corrected_list[0].split(':')[1][-1]))
                            qns.extend((blue, vie_list[0] + ' '))
                        else:
                            ocrs.extend((red, nom_list[0]))
                            corrs.extend((red, corrected_list[0].split(':')[1][-1]))
                            qns.extend((red, vie_list[0] + ' '))
                        nom_list.pop(0)
                        vie_list.pop(0)
                    elif corrected_list[0].startswith('delete:'):
                        ocrs.extend((red, nom_list[0]))
                        nom_list.pop(0)
                    elif corrected_list[0].startswith('insert:'):
                        # corrs.extend((red, 'X'))
                        # qns.extend((red, vie_list[0] + ' '))
                        vie_list.pop(0)
                    corrected_list.pop(0)
                worksheet.write(row_id, 0, f'{os.path.splitext(os.path.basename(input_file))[0] }_page{file_page_number:03}.png', font_format)
                worksheet.write(row_id, 1, f'{os.path.splitext(os.path.basename(input_file))[0] }.{file_page_number:03}.{bbox_id:03}', font_format)
                worksheet.write(row_id, 2, str(bbox), font_format)
                ocrs.extend((' ',' '))
                worksheet.write_rich_string(row_id, 3, *ocrs)
                if len(corrs)>0:
                    corrs.extend((' ',' '))
                    worksheet.write_rich_string(row_id, 4, *corrs)
                if len(qns)>0:
                    qns.extend((' ',' '))
                    worksheet.write_rich_string(row_id, 5, *qns)
                bbox_id = bbox_id + 1
                row_id =  row_id + 1 
    return os.path.join(os.environ['OUTPUT_FOLDER'],output_file) 
    