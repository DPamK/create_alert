import requests
import json

def ltp_pos(texts):
    url = "http://127.0.0.1:6666/pos"
    temp = {
        "texts": texts
    }
    payload = json.dumps(temp)
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response = json.loads(response.text)
    result = response['result']
    return result

def ltp_cwspos(texts):
    result = ltp_pos(texts=texts)
    cws,pos = result
    return cws,pos


def lac2ltp(nerlist):
    translist = {
        'n':'n',
        'f':'nd',
        's':'ns',
        'nw':'nz',
        'nz':'nz',
        'v':'v',
        'vd':'d',
        'vn':'n',
        'a':'a',
        'ad':'d',
        'an':'n',
        'd':'d',
        'm':'m',
        'q':'q',
        'r':'r',
        'p':'p',
        'c':'c',
        'u':'u',
        'xc':'',
        'w':'wp',
        'PER':'nh',
        'LOC':'nl',
        'ORG':'ni',
        'TIME':'nt'
    }
    res = [translist[ner] for ner in nerlist]
    return res

def lac_cwspos(laclist):
    cws = []
    pos = []
    for c,p in laclist:
        cws.append(c)
        pos.append(lac2ltp(p))
    return cws,pos