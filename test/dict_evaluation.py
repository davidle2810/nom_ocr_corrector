import json
import os
import pandas as pd
from xlsxwriter.workbook import Workbook

from dotenv import load_dotenv
load_dotenv('.env')

import os
import json
import pandas as pd


class SinoCorrector:
    def __init__(self, sn_sim_path):
        """
        Initializes the SinoCorrector with dictionaries for corrections.

        :param qn_to_sn_path: Path to the QN to Sino dictionary (JSON)
        :param sn_sim_path: Path to the Sino similarity dictionary (CSV)
        """
        self.qn_to_sn_path = os.environ['QN2NOM_DICTIONARY']
        self.sn_sim_path = sn_sim_path

        # Load QN to Sino dictionary
        self.qn_to_sn = json.load(open(self.qn_to_sn_path))

        # Load Sino similarity dictionary
        self.sn_sim = pd.read_csv(sn_sim_path)
        self.sn_sim = {
            row['char']: eval(row['sim'])
            for _, row in self.sn_sim.iterrows()
        }

    def is_correct(self, s, q) -> bool:
        """Checks if a character pair (s, q) is a correct mapping."""
        if q in self.qn_to_sn and s in self.qn_to_sn[q]:
            return True
        return False

    def get_similar(self, s, q):
            """Finds similar characters using the similarity dictionary."""
            S1 = [s] + self.sn_sim.get(s, list())
            S2 = self.qn_to_sn.get(q, list())
            S2 = set(S2)
            S = [s for s in S1 if s in S2]
            return S[0] if S else None
    
    def correct(self, sn: str, qn: list[str]) -> list[str]:
        """
        Correct a Sino sentence to a Quoc Ngu sentence.

        :param sn: str, a Sino sentence
        :param qn: list[str], a list of Quoc Ngu words
        :return: list[str], a list of corrections for each word in qn
        """
        assert isinstance(sn, str), 'sn must be a string'
        assert isinstance(qn, list), 'qn must be a list'
        assert all(isinstance(w, str) for w in qn), 'qn must be a list of strings'

        edit_cost = {'insert': 1, 'delete': 1, 'replace': 2}

        similar = [[self.get_similar(s, q) for s in sn] for q in qn]
        dp = [[None for _ in range(len(sn) + 1)] for _ in range(len(qn) + 1)]
        n, m = len(qn), len(sn)

        def memoi(i, j):
            if i == n and j == m:
                return 0
            if dp[i][j] is not None:
                return dp[i][j]

            res = n + m  # Large initial value
            if i < n and j < m and self.is_correct(sn[j], qn[i]):
                res = min(res, memoi(i + 1, j + 1))
            if i < n and j < m and similar[i][j] is not None and similar[i][j] != sn[j]:
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
            if i == n and j == m:
                return
            res = memoi(i, j)
            if i < n and j < m and self.is_correct(sn[j], qn[i]) and res == memoi(i + 1, j + 1):
                corrections.append(f'correct:{sn[j]}')
                traceback(i + 1, j + 1)
            elif i < n and j < m and similar[i][j] is not None and similar[i][j] != sn[j] and res == memoi(i + 1, j + 1) + edit_cost['replace']:
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

def count_false_replace(file_path):
    df = pd.read_excel(file_path)

    # Initialize false_replace counter
    false_replace_count_1 = 0
    false_replace_count_2 = 0

    # Iterate through each row
    for id, row in df.iterrows():
        correction_1 = str(row["correction_1"])  # Convert to string to avoid NaN issues
        correction_2 = str(row["correction_2"])  # Convert to string to avoid NaN issues
        nom = str(row["nom"])  # Convert to string

        # Ensure both strings have the same length before comparison
        min_length = min(len(correction_1), len(correction_2), len(nom))

        for i in range(min_length):
            if correction_1[i] != nom[i] and correction_1[i] not in ['X', 'I']:
                false_replace_count_1 += 1
                print(id+2,correction_1[i])
            if correction_2[i] != nom[i] and correction_2[i] not in ['X', 'I']:
                false_replace_count_2 += 1
                #print(id+2,correction_2[i])
    return false_replace_count_1, false_replace_count_2

if __name__ == '__main__':
    # Load the Excel file
    os.chdir('/mnt/d/nom_ocr_corrector')
    
    file_path = 'data/evaluation_data.xlsx'  # Change to your actual file path
    sim_path_1 = 'resource/SN_similarities.csv'
    sim_path_2 = 'resource/SinoNom_Similar_Phúc.csv'
    number_of_changes_1 = 0
    number_of_changes_2 = 0
    false_rep_1 = 0
    false_rep_2 = 0
    df = pd.read_excel(file_path)
    # Create workbook
    with Workbook('data/output.xlsx') as workbook:
        worksheet   = workbook.add_worksheet("Result")
        font_format = workbook.add_format({'font_name': 'Nom Na Tong'})
        red         = workbook.add_format({'color': 'red', 'font_name': 'Nom Na Tong'})
        yellow      = workbook.add_format({'color': 'yellow', 'font_name': 'Nom Na Tong'})
        blue        = workbook.add_format({'color': 'blue', 'font_name': 'Nom Na Tong'})
        green       = workbook.add_format({'color': 'green', 'font_name': 'Nom Na Tong'})
        black       = workbook.add_format({'color': 'black', 'font_name': 'Nom Na Tong'})

        # Write headers
        headers = ["page_id", "row_number", "bbox", "ocr", 
            os.path.splitext(os.path.basename(sim_path_1))[0], os.path.splitext(os.path.basename(sim_path_2))[0], "nom", "qn"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, font_format)
        corrector_1 = SinoCorrector(sim_path_1)
        corrector_2 = SinoCorrector(sim_path_2)
        total_chars_1 = 0
        total_chars_2 = 0
        # Write data with formatting
        for index, row in df.iterrows():
            corrs1 = []
            corrected_list_1 = corrector_1.correct(row['ocr'], row['qn'].split())
            corrs2 = []
            corrected_list_2 = corrector_2.correct(row['ocr'], row['qn'].split())
            corrected_string = ''
            # Apply regex patterns
            for i in range(len(corrected_list_1)):
                if corrected_list_1[i].startswith('correct:'):
                    corrs1.extend((black, corrected_list_1[i].split(':')[1]))
                    corrected_string += corrected_list_1[i].split(':')[1]
                elif corrected_list_1[i].startswith('replace:'):
                    total_chars_1+=1
                    if corrected_list_1[i].split(':')[1][-1]!="X":
                        corrected_string += corrected_list_1[i].split(':')[1][-1]
                        number_of_changes_1 += 1
                        if corrected_string[-1]!=row['nom'][len(corrected_string)-1]:
                            false_rep_1 += 1
                            corrs1.extend((blue, corrected_list_1[i].split(':')[1][-1]))
                        else:
                            corrs1.extend((green, corrected_list_1[i].split(':')[1][-1]))
                                
                    else:
                        corrs1.extend((red, corrected_list_1[i].split(':')[1][-1]))
                        corrected_string += corrected_list_1[i].split(':')[1][-1]
                elif corrected_list_1[i].startswith('delete:'):
                    continue
                elif corrected_list_1[i].startswith('insert:'):
                    corrs1.extend((red, 'I'))
                    corrected_string += 'I'
            corrected_string = ''
            for i in range(len(corrected_list_2)):
                if corrected_list_2[i].startswith('correct:'):
                    corrs2.extend((black, corrected_list_2[i].split(':')[1]))
                    corrected_string += corrected_list_2[i].split(':')[1]
                elif corrected_list_2[i].startswith('replace:'):
                    total_chars_2 += 1
                    if corrected_list_2[i].split(':')[1][-1]!="X":
                        corrected_string += corrected_list_2[i].split(':')[1][-1]
                        number_of_changes_2 += 1
                        if corrected_string[-1]!=row['nom'][len(corrected_string)-1]:
                            false_rep_2 += 1
                            corrs2.extend((blue, corrected_list_2[i].split(':')[1][-1]))
                        else:
                            corrs2.extend((green, corrected_list_2[i].split(':')[1][-1]))
                    else:
                        corrs2.extend((red, corrected_list_2[i].split(':')[1][-1]))
                        corrected_string += corrected_list_2[i].split(':')[1][-1]
                elif corrected_list_2[i].startswith('delete:'):
                    continue
                elif corrected_list_2[i].startswith('insert:'):
                    corrs2.extend((red, 'I'))
                    corrected_string += 'I'

            # Write row data
            worksheet.write(index + 1, 0, row["page_id"], font_format)
            worksheet.write(index + 1, 1, row["row_number"], font_format)
            worksheet.write(index + 1, 2, row["bbox"], font_format)
            worksheet.write(index + 1, 3, row["ocr"], font_format)
            worksheet.write_rich_string(index + 1, 4, *corrs1, font_format)
            worksheet.write_rich_string(index + 1, 5, *corrs2, font_format)
            worksheet.write(index + 1, 6,  row["nom"], font_format)
            worksheet.write(index + 1, 7,  row["qn"], font_format)

    print(f"Correction process completed! Output saved as {file_path}")
    print(f"1st dictionary: {number_of_changes_1}/{total_chars_1} chars, false replaced {false_rep_1}")
    print(f"2nd dictionary: {number_of_changes_2}/{total_chars_2} chars, false replaced {false_rep_2}")