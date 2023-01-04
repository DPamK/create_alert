import synonyms
import numpy as np

def SimComputer(src, fixed, t=0.35):
    try:
        vec1 = synonyms.v(src)
        vec2 = synonyms.v(fixed)
        cos_sim = vec1.dot(vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        if cos_sim > t:
            return (True,True)
        else:
            return (True,False)
    except:
        print('不在字典！错误！')
        cos_sim = -1
        return (False,True)

def judgeadvice(sourceText,replaceText):
    frequent, similer = SimComputer(sourceText,replaceText)
    if frequent:
        advancedTip = str(similer)
    else:
        advancedTip = str(similer)
    return advancedTip

def creat_alert_item(alertMessage, alertType, errorType, replaceText, sourceText, ori_pos_begin, ori_pos_end,error_type):
    if alertType == 4:
        advancedTip = judgeadvice(sourceText,replaceText)
    elif alertType == 1:
        advancedTip = judgeadvice(sourceText,replaceText+sourceText)
    elif alertType == 2:
        advancedTip = judgeadvice(sourceText,sourceText+replaceText)
    elif alertType == 3:
        advancedTip = str(True)
    else:
        advancedTip = str(True)
    
    alert_item = item(advancedTip, alertMessage, alertType, errorType, replaceText, sourceText,
                                    ori_pos_begin, ori_pos_end,error_type)
    return  alert_item

def item(advancedTip, alertMessage, alertType, errorType, replaceText, sourceText, ori_pos_begin, ori_pos_end,error_type):
    res = {
        'advancedTip': advancedTip,
        'alertMessage': alertMessage,
        'alertType': alertType,
        'errorType': errorType,
        'replaceText': replaceText,
        'sourceText': sourceText,
        'start': ori_pos_begin,
        'end': ori_pos_end,
        'error_type':error_type
    }
    return res