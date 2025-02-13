import bitext_helper as bitext
import corrector_updating as crt
import argparse
import shutil
import os
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
                'source_page_number': source_page['page_number'],
                'source_text': source_page['content'],
                'target_page_number': target_page['page_number'],
                'target_text': target_page['content'],
                'similarity_score': float(best_score)
            })
    return alignment_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser('Multimodal Alignment',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input', type=str, required=True,
                        help='path_to_bitext_document')

    args = parser.parse_args()
    # read the content of 2 pdf files: nom and viet
    input_file = args.input
    sn_content, vn_content = bitext.get_content_from_bitext(input_file)
    # get the transliteration of sino-nom content
    sn2vn_content = list()
    for page in sn_content:
        sn2vn_content.append({'page_number': page['page_number'], 'content': '\n'.join([line['transliteration'] for line in page['content']])})
    # align paragraphs
    paragraph_alignments = align_paragraphs(sn2vn_content,vn_content)
    shutil.rmtree('output_images')
    # align sentences
    output_file = os.path.splitext(input_file)[0] + '.xlsx'
    with Workbook(output_file) as workbook:
        worksheet   = workbook.add_worksheet(f"Result")
        font_format = workbook.add_format({'font_name': 'Nom Na Tong'})
        red         = workbook.add_format({'color': 'red', 'font_name': 'Nom Na Tong'})
        yellow      = workbook.add_format({'color': 'yellow', 'font_name': 'Nom Na Tong'})
        blue        = workbook.add_format({'color': 'blue', 'font_name': 'Nom Na Tong'})
        green       = workbook.add_format({'color': 'green', 'font_name': 'Nom Na Tong'})
        black       = workbook.add_format({'color': 'black', 'font_name': 'Nom Na Tong'})
        worksheet.write(0, 0, 'page_id', font_format)
        worksheet.write(0, 1, 'bbox', font_format)
        worksheet.write(0, 2, 'ocr', font_format)
        worksheet.write(0, 3, 'correction', font_format)
        worksheet.write(0, 4, 'nom', font_format)
        row_id = 1
        for idx, alignment in enumerate(paragraph_alignments):
            src_id = alignment['source_page_number']
            tgt_id = alignment['target_page_number']
            src_lines = [(line['bbox'],line['content']) for line in sn_content[src_id]['content']]
            tgt_lines = ' '.join(vn_content[tgt_id]['content'].split('\n')).split(' ')
            nom_lines = ''.join([line[1] for line in src_lines])
            corrected_list=crt.correct(nom_lines,tgt_lines)
            vie_list = tgt_lines.copy()
            for chunk in src_lines:
                page_id = src_id
                bbox = chunk[0]
                nom = ''
                corrected_nom = ''
                vie = '' 
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
                        # corrs.extend((red, corrected_list[0].split(':')[1]))
                        qns.extend((red, vie_list[0] + ' '))
                        vie_list.pop(0)
                    corrected_list.pop(0)
                worksheet.write(row_id, 0, page_id, font_format)
                worksheet.write(row_id, 1, str(bbox), font_format)
                ocrs.extend((' ',' '))
                worksheet.write_rich_string(row_id, 2, *ocrs)
                if len(corrs)>0:
                    corrs.extend((' ',' '))
                    worksheet.write_rich_string(row_id, 3, *corrs)
                if len(qns)>0:
                    qns.extend((' ',' '))
                    worksheet.write_rich_string(row_id, 4, *qns)
                row_id =  row_id + 1
    print('Output file is save to ', output_file)     