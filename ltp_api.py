from ltp import LTP
from loguru import logger
import time
import math
from flask import Flask,request

logger.add("log/ltp_log.log")
app = Flask(__name__)

# ltp = LTP("LTP/base1")
ltp = LTP("LTP/legacy")

@app.route('/cws',methods=['POST'])
def ltp_cut():
    data = request.json.get('texts')
    start = time.time()
    listMaxNum = 100
    batch_num = math.ceil(len(data)/listMaxNum)
    
    if len(data) > listMaxNum:
        result = []
        i = 0
        while i < batch_num:
            if (i+1)*listMaxNum >= len(data):
                temp = data[i*listMaxNum:]
            else:
                temp = data[i*listMaxNum:(i+1)*listMaxNum]
            i += 1
            s = ltp.pipeline(temp,tasks=['cws'])
            result.extend(s.cws)
    else:
        result = ltp.pipeline(data,tasks=['cws'])
        result = result.cws

    spendtime = round(time.time()-start,3)
    l = len(data)
    logger.info(f'sentence_num:{l},batch_num:{batch_num},spendtime:{spendtime}')
    item = {
        'result':result
    }
    return item

@app.route('/pos',methods=['POST'])
def ltp_pos():
    data = request.json.get('texts')
    start = time.time()
    listMaxNum = 100
    batch_num = math.ceil(len(data)/listMaxNum)
    
    if len(data) > listMaxNum:
        result = []
        i = 0
        while i < batch_num:
            if (i+1)*listMaxNum >= len(data):
                temp = data[i*listMaxNum:]
            else:
                temp = data[i*listMaxNum:(i+1)*listMaxNum]
            i += 1
            s = ltp.pipeline(temp,tasks=['cws','pos'])
            for c,p in zip(s.cws,s.pos):
                result.append([c,p])
    else:
        s = ltp.pipeline(data,tasks=['cws','pos'])
        result = [s.cws,s.pos]
            
    spendtime = round(time.time()-start,3)
    l = len(data)
    logger.info(f'sentence_num:{l},batch_num:{batch_num},spendtime:{spendtime}')
    item = {
        'result':result
    }
    return item

if __name__=="__main__":
    app.run(host='127.0.0.1', port=6666)

