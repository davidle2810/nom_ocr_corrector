import json
import os
import pandas as pd
import core.tools
from unidecode import unidecode
from dotenv import load_dotenv
load_dotenv('.env')

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
