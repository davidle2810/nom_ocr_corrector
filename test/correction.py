import json
import os
import pandas as pd
from xlsxwriter.workbook import Workbook

from dotenv import load_dotenv
load_dotenv('.env')
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unidecode import unidecode
import core.tools
import re

qn_to_sn_path = os.environ['QN2NOM_DICTIONARY']
qn_to_sn = json.load(open(qn_to_sn_path))
core.tools.normalize_json(qn_to_sn_path)
qn_to_sn_without_accent = json.load(open('resource/QN2Nom_without_accent.json'))
sn_sim_path = os.environ['NOM_SIMILARITY_DICTIONARY']
sn_sim = pd.read_csv(sn_sim_path)
sn_sim = {
    row['char']: eval(row['sim'])
    for _, row in sn_sim.iterrows()
}

class Stat:
    def __init__(self):
        self.number_of_sentence = 0
        self.number_of_sn = 0
        self.number_of_qn = 0
        self.number_of_wrong_sn = 0
        self.number_of_replace_sn = 0
        self.number_of_delete = 0
        self.number_of_insert = 0


def is_correct(s, q)-> bool:
    if q in qn_to_sn and s in qn_to_sn[q]:
        return True
    if unidecode(q) in qn_to_sn_without_accent and s in qn_to_sn_without_accent[unidecode(q)]:
        return True
    return False
def correct(sn: str, qn: list[str]) -> list[str]:
    """
    Correct a Sino sentence to a Quoc Ngu sentence.
    Input:
    - sn: str, a Sino sentence
    - qn: list[str], a list of Quoc Ngu word
    Output:
    - list[str], a list of correction for each word in qn
    """
    assert isinstance(sn, str), 'sn must be a string'
    assert isinstance(qn, list), 'qn must be a list'
    assert all(isinstance(w, str) for w in qn), 'qn must be a list of string'
    edit_cost = {
        'insert': 1,
        'delete': 1,
        'replace': 2,
    }

    def get_similar(s, q):
        S1 = [s] + sn_sim.get(s, list())
        S2 = qn_to_sn.get(q, list())
        S2 = set(S2)
        S = [s for s in S1 if s in S2]
        if len(S) == 0: return None
        return S[0]
    
    similar = [[
        get_similar(s, q)
        for s in sn
    ] for q in qn]
    dp = [[None for _ in range(len(sn) + 1)] for _ in range(len(qn) + 1)]
    n = len(qn)
    m = len(sn)
    def memoi(i, j):
        if i == n and j == m: return 0
        if dp[i][j] is not None: return dp[i][j]
        res = n + m
        if i < n and j < m and is_correct(sn[j],qn[i]):
            res = min(res, memoi(i + 1, j + 1))
        if i < n and j < m and similar[i][j] is not None and similar[i][j]!=sn[j]:
            res = min(res, memoi(i + 1, j + 1) + edit_cost['replace'])
        if i < n and j < m and similar[i][j] is None:
            res = min(res, memoi(i + 1, j + 1) + edit_cost['replace'])
        if i < n:
            res = min(res, memoi(i + 1, j) + edit_cost['insert'])
        if j < m:
            res = min(res, memoi(i, j + 1) + edit_cost['delete'])
        dp[i][j] = res
        return res
    corrections = []
    def traceback(i, j):
        if i == n and j == m: return
        res = memoi(i, j)
        if i < n and j < m and is_correct(sn[j],qn[i]) and res == memoi(i + 1, j + 1):
            corrections.append(f'correct:{sn[j]}')
            traceback(i + 1, j + 1)
        elif i < n and j < m and similar[i][j] is not None and similar[i][j]!=sn[j] and res == memoi(i + 1, j + 1) + edit_cost['replace']:
            corrections.append(f'replace:{sn[j]}->{similar[i][j]}')
            traceback(i + 1, j + 1)
        elif i < n and j < m and similar[i][j] is None and res == memoi(i + 1, j + 1) + edit_cost['replace']:
            corrections.append(f'replace:{sn[j]}->X')
            traceback(i + 1, j + 1)
        elif i < n and res == memoi(i + 1, j) + edit_cost['insert']:
            corrections.append(f"insert:I")
            traceback(i + 1, j)
        elif j < m and res == memoi(i, j + 1) + edit_cost['delete']:
            corrections.append(f'delete:{sn[j]}')
            traceback(i, j + 1)
    traceback(0, 0)
    return corrections

if __name__ == '__main__':
    # Load the Excel file
       
    df = pd.read_excel('test/result_v2.xlsx').fillna('')
    stat=Stat()
    # Create workbook
    with Workbook('test/result_v2.xlsx') as workbook:
        worksheet   = workbook.add_worksheet("Result")
        font_format = workbook.add_format({'font_name': 'Nom Na Tong'})
        red         = workbook.add_format({'color': 'red', 'font_name': 'Nom Na Tong'})
        yellow      = workbook.add_format({'color': 'yellow', 'font_name': 'Nom Na Tong'})
        blue        = workbook.add_format({'color': 'blue', 'font_name': 'Nom Na Tong'})
        green       = workbook.add_format({'color': 'green', 'font_name': 'Nom Na Tong'})
        black       = workbook.add_format({'color': 'black', 'font_name': 'Nom Na Tong'})
        print(df.head())
        # Write headers
        worksheet.write(0, 0, 'Img_Box_ID', font_format)
        worksheet.write(0, 1, 'Img_Box_Coordinate', font_format)
        worksheet.write(0, 2, 'SinoNom_OCR', font_format)
        worksheet.write(0, 3, 'SinoNom_Char', font_format)
        worksheet.write(0, 4, 'ChuQN_txt', font_format)
        worksheet.write(0, 5, 'Viet_txt', font_format)
        worksheet.write(0, 6, 'Poet_txt', font_format)
        # Write data with formatting
        for index, row in df.iterrows():
            ocrs = []
            corrs = []
            qns = []
            nom_list = list(re.sub(r'\s+','',row['SinoNom_OCR']))
            vie_list = re.sub(r'\s+',' ',row['ChuQN_txt']).strip().split()
            corrected_list = correct(''.join(nom_list), vie_list)
            stat.number_of_sentence += 1
            # Apply regex patterns
            while len(corrected_list)>0:
                    if corrected_list[0].startswith('correct:'):
                        ocrs.extend((black, nom_list[0]))
                        corrs.extend((black, corrected_list[0].split(':')[1]))
                        qns.extend((black, vie_list[0] + ' '))
                        nom_list.pop(0)
                        vie_list.pop(0)
                        stat.number_of_sn += 1
                        stat.number_of_qn += 1
                    elif corrected_list[0].startswith('replace:'):
                        stat.number_of_wrong_sn += 1
                        if corrected_list[0].split(':')[1][-1]!="X":
                            ocrs.extend((blue, nom_list[0]))
                            corrs.extend((blue, corrected_list[0].split(':')[1][-1]))
                            qns.extend((blue, vie_list[0] + ' '))
                            stat.number_of_replace_sn +=1
                        else:
                            ocrs.extend((red, nom_list[0]))
                            corrs.extend((red, corrected_list[0].split(':')[1][0]))
                            qns.extend((red, vie_list[0] + ' '))
                        nom_list.pop(0)
                        vie_list.pop(0)
                        stat.number_of_sn += 1
                        stat.number_of_qn += 1
                    elif corrected_list[0].startswith('delete:'):
                        ocrs.extend((red, nom_list[0]))
                        # corrs.extend((red, nom_list[0]))
                        nom_list.pop(0)
                        stat.number_of_sn += 1
                        stat.number_of_delete += 1
                    elif corrected_list[0].startswith('insert:'):
                        corrs.extend((red, 'I'))
                        qns.extend((red, vie_list[0] + ' '))
                        vie_list.pop(0)
                        stat.number_of_qn += 1
                        stat.number_of_insert += 1
                    corrected_list.pop(0)

            # Write row data
            worksheet.write(index + 1, 0, row["Img_Box_ID"], font_format)
            worksheet.write(index + 1, 1, row["Img_Box_Coordinate"], font_format)
            ocrs.extend((' ',' '))
            worksheet.write_rich_string(index + 1, 2, *ocrs)
            if len(corrs)>0:
                corrs.extend((' ',' '))
                worksheet.write_rich_string(index + 1, 3, *corrs)
            if len(qns)>0:
                qns.extend((' ',' '))
                worksheet.write_rich_string(index + 1, 4, *qns)

    with open('test/stat.txt', 'w', encoding='utf-8') as f:
        f.write(f"Number of sentence: {stat.number_of_sentence}\n")
        f.write(f"Number of Sino-Nôm character: {stat.number_of_sn}\n")
        f.write(f"Number of QN word: {stat.number_of_qn}\n")
        f.write(f"Number of wrong SN character: {stat.number_of_wrong_sn}\n")
        f.write(f"Number of replaced SN character: {stat.number_of_replace_sn}\n")
        f.write(f"Number of insert character: {stat.number_of_insert}, rate:{(stat.number_of_insert*1.0)/stat.number_of_sn}%\n")
        f.write(f"Number of delete character: {stat.number_of_delete}, rate:{(stat.number_of_insert*1.0)/stat.number_of_sn}%\n")
    print(f"Correction process completed! Output saved")