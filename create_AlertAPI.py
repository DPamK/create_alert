from loguru import logger
import difflib
import time
from flask import Flask,request
from alert_format import creat_alert_item
from transfer import deal_with_alert
from total_filter import total_filter
from config import alert_config as cfg
from word_cut import lac_cwspos,ltp_cwspos

logger.add("log/alert_log.log")
app = Flask(__name__)


def participle(sources,predicts):
    alltexts = sources+predicts
    lsource = len(sources)
    try:
        allparts_cws,allparts_pos = ltp_cwspos(alltexts)
        source_cws = allparts_cws[:lsource]
        source_pos = allparts_pos[:lsource]
        predict_cws = allparts_cws[lsource:]
        predict_pos = allparts_pos[lsource:]    
        return source_cws,predict_cws,0,'',source_pos
    except:
        logger.warning('LTP can not run.')
           
        return [],[],2,'LTP can not process input_sentence',[]

def list2str(strlist):
    res = ''.join(strlist)
    return res

def error_info_json(errorindex):
    if errorindex == 2:
        res = {
            'error': 'error input',
            'info': 'Please check the input, which should not contain special characters that are not text, such as \\u3000 \\xa0'
            }
    else:
        res = {
            'error': 'error undefine',
            'info': 'Please connect ours'
            }
    return res

def create_alerts(sources,predicts):
    alerts = []
    datas = []
    error_type = ""
    inputs,outputs,errCode,errMsg,source_poss = participle(sources,predicts)
    if errCode == 0:
        for source,output,predict,source_pos in zip(inputs,outputs,predicts,source_poss):
            alert = []
            textlenth = [len(text) for text in source]
            s = difflib.SequenceMatcher(None,source,output)
            for (type, ori_pos_begin, ori_pos_end, out_pos_begin, out_pos_end) in s.get_opcodes():
                if type == 'equal':
                    continue
                else:            
                    sourcelist = source[ori_pos_begin: ori_pos_end]
                    sourceText = list2str(sourcelist)
                    replacelist = output[out_pos_begin: out_pos_end]
                    replaceText = list2str(replacelist)
                    alertMessage = ""
                    alertType,errorType = -1,-1
                    start = sum(textlenth[:ori_pos_begin])
                    
                    if type == 'replace':
                        alertMessage = f"建议用“{replaceText}”替换“{sourceText}”"
                        alertType = 4
                        errorType = 1
                    elif type == 'delete':
                        alertMessage = f"建议删除“{sourceText}”"
                        alertType = 3
                        errorType = 5
                        error_type = "1-4"
                    elif type == 'insert':
                        alertMessage = f"建议添加“{replaceText}”"
                        #判断添加位置，抽取添加字符的位置，和原文进行比较
                        if ori_pos_begin == 0:
                            sourceText = source[0]
                            replacelist += sourceText
                            start = 0
                            alertType = 1
                        elif ori_pos_end == len(textlenth):
                            sourceText = source[-1]
                            start = sum(textlenth[:-1])
                            alertType = 2
                        else:
                            sourceText = source[ori_pos_begin-1]
                            start = sum(textlenth[:ori_pos_begin-1])
                            alertType = 2
                        errorType = 5
                        error_type = "1-5"
                    alert_item = creat_alert_item(alertMessage, alertType, errorType, replaceText, sourceText, start, start+len(sourceText)-1,error_type)
                    alert.append(alert_item)  
            oritextltp = "".join(source)
            alerts.append(alert)
            logger.info(f'origin:{oritextltp}')
            logger.info(f'output:{predict}')
            data = {
                'origin':oritextltp,
                'origin_cws':source,
                'origin_pos':source_pos,
                'output':predict,
                'output_cws':output
            }
            datas.append(data)
    # 创建返回的样式
    result = {
        'alerts':alerts,
        'data':datas,
        'errCode':errCode,
        'errMsg':errMsg
    }
    return result
# import pdb;pdb.set_trace()
@app.route('/alert',methods=['POST'])
def catch_alert():
    # 设定请求需求
    request_info = request.json.get('way')
    result_style = request_info['style']
    if 'fliter' in request_info:
        fliter_request = request_info['fliter']
        if fliter_request == "Normal":
            fliter_cfg = cfg
        elif fliter_request == "OnePart":
            fliter_cfg = cfg
            fliter_cfg.afterProcess = False
        elif fliter_request == "":
            fliter_cfg = None
    else:
        fliter_cfg = None
    # 数据收集
    datalist = request.json.get('data')
    sources = []
    fixeds = []
    for item in datalist:
        sources.append(item['originText'])
        fixeds.append(item['correctText'])
    # pipeline
    alert_info = create_alerts(sources=sources,predicts=fixeds)
    if alert_info['errCode'] == 0:
        if fliter_cfg != None:
            filiter = total_filter(cfg=fliter_cfg,input_content=alert_info)
            alert_info = filiter.get_alerts()

        if result_style == 'correct':
            
            return alert_info
        elif result_style == 'transfer':
            result = deal_with_alert(alert_info['alerts'])
            return result
        else:
            return {'error':f'request_info:{result_style} not exist'}
    else:
        result = error_info_json(alert_info['errCode'])
        return result



if __name__=="__main__":
    app.run(host='0.0.0.0', port=18080)

