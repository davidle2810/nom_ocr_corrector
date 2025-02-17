import json
import os
import pandas as pd
from unidecode import unidecode
from dotenv import load_dotenv
load_dotenv('.env')

qn_to_sn_path = 'resource/QN2Nom_cleaned.json'
qn_to_sn = json.load(open(qn_to_sn_path))
sn_sim_path = os.environ['NOM_SIMILARITY']
sn_sim = pd.read_csv(sn_sim_path)
sn_sim = {
    row['char']: eval(row['sim'])
    for _, row in sn_sim.iterrows()
}

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
        if i < n and j < m and similar[i][j] is not None:
            res = min(res, memoi(i + 1, j + 1))
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
        if i < n and j < m and similar[i][j] is not None and res == memoi(i + 1, j + 1):
            corrections.append(f'correct:{similar[i][j]}')
            traceback(i + 1, j + 1)
        elif i < n and j < m and similar[i][j] is None and res == memoi(i + 1, j + 1) + edit_cost['replace']:
            corrections.append(f'replace:{sn[j]}->{qn_to_sn.get(qn[i], ["X"])[0]}')
            traceback(i + 1, j + 1)
        elif i < n and res == memoi(i + 1, j) + edit_cost['insert']:
            corrections.append(f'insert:{qn_to_sn.get(qn[i], ["X"])[0]}')
            traceback(i + 1, j)
        elif j < m and res == memoi(i, j + 1) + edit_cost['delete']:
            corrections.append(f'delete:{sn[j]}')
            traceback(i, j + 1)
    traceback(0, 0)
    return corrections

def normalize_correction(correction: list) -> str:
    """
    Normalize the correction string.
    Input:
    - correction: list, a list of correction
    Output:
    - str, a normalized correction string
    """
    assert isinstance(correction, list), 'correction must be a list'
    def transform(s):
        if s.startswith('correct:'):
            return s.split(':')[1]
        if s.startswith('replace:'):
            return s.split(':')[1][0]
        if s.startswith('insert:'):
            return s.split(':')[1]
        if s.startswith('delete:'):
            return ''
    return ''.join(transform(s) for s in correction)