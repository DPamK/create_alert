import json
import re
from loguru import logger
import cn2an
from dictfiliter import dictfiliter,post_with_databese
from check_location import check_location

class total_filter():
    '''
    后处理函数
    '''
    def __init__(self, cfg,input_content) -> None:
        #初始化数据
        self.alerts=input_content['alerts']#[[{}]]
        self.data=input_content['data']#[{origin，origin_cws[],output,output_cws[]}]

        #初始化配置文件
        self.need_zhfiliter = cfg.zhfiliter
        self.need_dictfiliter = cfg.dictfiliter
        self.need_afterfiliter = cfg.afterfiliter
        self.need_afterProcess = cfg.afterProcess
        

        #初始化数据库
        self.filiter_dbpath=cfg.filiter_dbpath
        self.inner_db=cfg.inner_db
        self.outer_db=cfg.outer_db

        with open(cfg.location_structure, 'r', encoding='utf8') as location_file:
            location_structure = json.load(location_file)
        self.location_structure=location_structure

        if self.need_dictfiliter:
            self.dfiliter = dictfiliter(cfg.filiter_dbpath)


    def filiter_alerts(self):
        total_alert=[]
        alerts=self.alerts
        sentences=self.data
        for sentence,item in zip(sentences,alerts):
            res = []  # [{}],返回形式可能需要修改
            oritext=sentence['origin']
            for alert in item:
                if not self.filiter(alert,oritext):
                    res.append(alert)
                else:
                    alertmessage = alert['alertMessage']
                    logger.warning(f'delete alert {alertmessage}')
            total_alert.append(res)
        
        self.alerts = total_alert

        return True

    def filiter(self,alert,oritext):
        # import pdb;pdb.set_trace()
        if self.need_zhfiliter and self.zh_filiter(alert):
            return True
        if self.need_afterfiliter and self.after_filiter(alert,oritext):
            return True
        if self.need_dictfiliter and self.dfiliter.filter(alert):
            return True
        return False

    # 过滤非中文的修改
    def zh_filiter(self,alert):
        def allChar_zh(strs):
            for _char in strs:
                if not '\u4e00' <= _char <= '\u9fa5':
                    return False
            return True
        type = alert['alertType']
        sourceText = alert['sourceText']
        replaceText = alert['replaceText']
        if type == 4:
            if allChar_zh(sourceText) and allChar_zh(replaceText):
                return False
            else:
                return True
        elif type == 1 or type == 2:
            if allChar_zh(replaceText):
                return False
            else:
                return True
        elif type == 3:
            if allChar_zh(replaceText):
                return False
            else:
                return True
        else:
            True

    #后处理控制开关
    def after_filiter(self,alert,oritext):
        if self.exist_change_zhnum(alert,oritext=oritext):
            return True
        if self.content_in_marks(alert,oritext=oritext):
            return True
        if self.fixedlack(alert):
            return True
        return False

    #过滤中文改成数字
    def exist_change_zhnum(self,alert,oritext):
        start=alert["start"]
        end=alert["end"]
        content = oritext[start:end]
        ptnNumberCN = re.compile('([Ｏ零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟]+)([年月日桶元圆角分])')
        if ptnNumberCN.search(content):#不处理
            return True
        return False

    #过滤成对的标点符号
    def content_in_marks(self,alert,oritext):
        '''
        成对的标点符号
        '''
        ori_content = oritext
        start=alert["start"]
        content_befor = ori_content[:start]
        mark_dict={
            "“":"”",
            "《":"》",
            "（":"）",
            "【":"】"
        }
        left,right=0,0
        for key,value in zip(mark_dict.keys(),mark_dict.values()):
            left=content_befor.count(key)
            right=content_befor.count(value)
            if left>right:#不处理
                return True
                # item.remove(alert)
        return False

    # 过滤fixed与source相差巨大
    def fixedlack(self,alert):
        type = alert['alertType']
        sourceText = alert['sourceText']
        replaceText = alert['replaceText']
        if type == 4:
            if abs(len(sourceText)-len(replaceText)) < max(3,int(len(sourceText)*0.3)):
                return False
            else:
                return True
        else:
            return False

    '''
    下面的返回值目前是model_json
    '''
    #过滤重复的alert
    def post_disable_repeat(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['alertType'] != 16:
                    new_alert_error = dict(alert_error)
                    new_alert_error["alertType"] = 16

                    for alert_error_2 in sentence_errors:
                        if alert_error_2['start'] == new_alert_error['start'] \
                                and alert_error_2['end'] == new_alert_error['end'] \
                                and alert_error_2['alertType'] == new_alert_error['alertType']:
                            sentence_errors.remove(alert_error_2)
                            break

        # return model_json

    #针对行政区划的过滤
    def post_disable_location(self):
        model_json=check_location(self.location_structure,self.data,self.alerts)
        self.alerts=model_json.get_alerts()

    #对于需要从数据库中过滤
    def post_disable_from_database(self):
        model_json=post_with_databese(self.data,self.alerts,self.inner_db,self.outer_db)
        self.alerts=model_json.get_alerts()

    #无意义修改词,这个或许可以加入字典
    def post_disable_context(self):
        '''
        C6 无意义修改词，未按语境理解词义
        “审计”->"升级，省级..."
        '''

        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                error_word = alert_error['replaceText']
                if alert_error['sourceText'][:2] == "审计" and error_word[:2] == "审计":
                    print(alert_error['sourceText'][:2])
                    continue
                elif error_word[:2] == "审计":
                    continue
                elif alert_error['sourceText'][:2] == "审计" and error_word[:2] != "审计":
                    sentence_errors.remove(alert_error)
        # return model_json

    #过滤公文规范
    def post_disable_gongwenguifan(self):
        '''
        可能是词库硬匹配造成的
        提供专有名称给算法（目前不多）
        中国特色社会主义审计制度、中国特色社会主义审计事业、中国特色社会主义审计道路、合同法、合同工、
        贯彻落实党中央各项决策部署、贯彻落实审计署决策部署
        '''
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                error_word = alert_error['replaceText']
                error_type = alert_error['alertMessage']
                if error_type[0:8] == '建议使用公文规范':
                    sentence_errors.remove(alert_error)
        # return model_json

    #修改前后标点相同
    def post_disable_space_after_puncs(self):
        '''
        "中文逗号（冒号、引号）,
        建议修改成中文逗号（冒号、引号）,
        建议修改和原始标点符号是相同的
        '''
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['errorType'] == 2 and alert_error['alertMessage'] == '中文符号后不空格':
                    sentence_errors.remove(alert_error)
        # return model_json

    #中间有空格
    def post_disable_space(self):
        '''
        中间有空格的会识别出错误
        '''
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                error_cla = alert_error['sourceText']
                if len(error_cla) == 3:
                    if error_cla[1] == ' ' or error_cla[1] == ' ':
                        sentence_errors.remove(alert_error)
        # return model_json

    #阿拉伯数字转化为汉字
    def post_disable_number(self):
        """
        针对C12错误：阿拉伯数组转换为汉语
        :param model_json:
        :return:
        """
        p = re.compile(r"[0-9]+[多几]+")  # 存储对应的正则表达式
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if re.match(p, alert_error['sourceText']):
                    sentence_errors.remove(alert_error)
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                source_text = alert_error['sourceText']
                replace_text = alert_error['replaceText']
                if source_text[0] == '第' and source_text[-1] == '届' and replace_text[0] == '第' and replace_text[
                    -1] == '届':
                    source_number = int(source_text[1:-1])
                    replace_number = cn2an.cn2an(replace_text[1:-1], "normal")
                    if source_number == replace_number:
                        sentence_errors.remove(alert_error)
        # return model_json

    #书名号
    def post_disable_bookname(self):
        """
        把书名号错误，取消处理
        :param model_json:
        :return:
        """
        len_book = 50
        for item, sentence_errors in zip(self.data,self.alerts):
            sentence=item['origin']
            for alert_error in list(sentence_errors):
                start = alert_error['start']
                end = alert_error['end']
                sentence_range = sentence[max(0, start - len_book):min(len(sentence), end + len_book + 1)]
                res = re.finditer('《(.*?)》', sentence_range)
                for bookidx in res:
                    start_idx, end_idx = bookidx.span()
                    if max(0, start - len_book) + start_idx <= start and max(0, start - len_book) + end_idx > end:
                        sentence_errors.remove(alert_error)
                        break
        # return model_json

    #日期错误
    def post_disable_date(self):
        """
        把日期错误，取消处理
        :param model_json:
        :return:
        """
        res = []
        for item, sentence_errors in zip(self.data,self.alerts):
            input_sentence = item['origin']
            date_regular = r"[0-9]*[0-9]+[月][0-9]*[0-9]+[日]*"
            date_search = re.search(date_regular,input_sentence)
            start_end = date_search.span()
            start = start_end[0]
            end = start_end[1]
            date_search = date_search.group(0)
            #print(start_end)
            alert = {}
            month_dict = {1:31,2:29,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
            month = int(re.match(r"[0-9]*[0-9]+[月]",date_search).group(0).strip('月'))
            if month>12:
                alert["advancedTip"] = "True"
                alert["alertMessage"] = "日期存在问题"
                alert["alertType"] = 16
                alert["end"] = end
                alert["errorType"] = 101
                alert["error_type"] = "3-3"
                alert["replaceText"] = ""
                alert["sourceText"] = date_search
                alert["start"] = start
            day = int(re.search("[0-9]*[0-9]+日+",date_search).group(0).strip('日'))
            if len(alert)==0 and month in month_dict.keys() and day>month_dict[month]:
                alert["advancedTip"] = "True"
                alert["alertMessage"] = "日期存在问题"
                alert["alertType"] = 16
                alert["end"] = end
                alert["errorType"] = 101
                alert["error_type"] = "3-3"
                alert["replaceText"] = ""
                alert["sourceText"] = date_search
                alert["start"] = start
            if len(alert)>0:
                sentence_errors.append(alert)
            res.append(sentence_errors)
        self.alerts = res
            

    #字词错误
    def post_disable_rongyu(self):
        """
        字词错误，c13.1 和 c7类型都能处理
        取消修改
        :param model_json:
        :return:
        """
        target_string = ['冗余', '罐']  # 冗余是指alertMessage的语义冗余提示， 罐 是针对客户提出的一个特定用例
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if 'replaceText' in alert_error.keys():
                    for string in target_string:
                        if string in alert_error['alertMessage'] or string == alert_error['sourceText']:
                            sentence_errors.remove(alert_error)
                            break
                else:
                    sentence_errors.remove(alert_error)
        # return model_json

    #法律名称不能带有书名号
    def post_disable_low(self):
        """
           删掉 法律名称简写不能使用书名号C12.4
           :param model_json:
           :return:
           """
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                message = alert_error['alertMessage']
                for j in range(0, len(message)):
                    if message[j:] == "法律法规简称一般推荐不带书名号。":
                        sentence_errors.remove(alert_error)
        # return model_json

    #词序颠倒
    def post_disable_reverse_words(self):
        """
        删掉  词序颠倒C6.6
        :param
        :return:
        """
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                replaceText = list(alert_error['replaceText'])
                sourceText = list(alert_error['sourceText'])
                replaceText.sort()
                sourceText.sort()
                if sourceText == replaceText:
                    sentence_errors.remove(alert_error)
        # return model_json

    #单双引号
    # def post_disable_error_quotation(input_sentence, model_json):
    #     """
    #       单双引号
    #       :param model_json:input:字典
    #       :return:
    #       """
    #
    #     def check_quotation(sentence, start_idx):
    #         return len(re.findall("“", sentence[0: start_idx])) % 2 == 0
    #
    #     # 遍历每个sentence 的报错列表
    #     for sentence, sentence_errors in zip(input_sentence["sentences"], model_json['alerts']):
    #         # 获取当前数据源句子
    #         # 遍历当前sentence的 error
    #         for alert_error in list(sentence_errors):
    #             if alert_error['alertMessage'] == "建议使用双引号" and not check_quotation(sentence,
    #                                                                                        alert_error["start"]):
    #                 sentence_errors.remove(alert_error)
    #
    #     return model_json

    #过滤没有replaceText的alert
    def post_disable_empty_replace_text(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if 'replaceText' not in alert_error.keys():
                    sentence_errors.remove(alert_error)
        # return model_json

    #过滤错误的quotes
    def post_disable_remove_error_quotes(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['sourceText'] == '“' + alert_error['replaceText'] + '”':
                    sentence_errors.remove(alert_error)
        # return model_json

    #成对的标点符号
    def post_enable_mix_pair_symbol_detection(self):
        mix_pairs = {'（': ')', '(': '）', '［': ']', '[': '］', '｛': '}', '{': '｝', '《': '>', '<': '》'}
        english_to_chinese_pair = {"(": "（", ")": "）", "[": "［", "]": "］", "{": "｛", "}": "｝", "<": "《", ">": "》"}
        mix_pairs_inverse = {v: k for k, v in mix_pairs.items()}
        quotes_list = ['"', "'", '“', '”', '‘', '’']

        for item, sentence_errors in zip(self.data,self.alerts):
            sentence=item['origin']
            for alert_error in list(sentence_errors):
                if '成对' in alert_error['alertMessage']:
                    if alert_error['sourceText'] in mix_pairs_inverse.keys():
                        start = alert_error['start']
                        anchor_symbol = mix_pairs_inverse[alert_error['sourceText']]
                        mix_pair_flag = False
                        for i in range(0, start):
                            current_index = start - i
                            if sentence[current_index] == anchor_symbol:
                                alert_error['start'] = current_index
                                alert_error['end'] = current_index
                                alert_error['sourceText'] = anchor_symbol
                                alert_error['replaceText'] = english_to_chinese_pair[anchor_symbol]
                                alert_error['alertType'] = 4
                                mix_pair_flag = True
                                break
                        if not mix_pair_flag:
                            alert_error['message'] = '缺乏成对的标点符号'
                            alert_error['alertType'] = 10
                    elif alert_error['sourceText'] in quotes_list:
                        alert_error['message'] = '缺乏成对的标点符号'
                        alert_error['alertType'] = 10
                    else:
                        sentence_errors.remove(alert_error)

    def de_question(self,alert):
        if alert['sourceText'] in ['的','地','得'] and alert['replaceText'] in ['的','地','得']:
            return True
        else:
            return False
    
    def fix_deQuestion(self):
        def fix_deProcess(alert,cws,pos):
            start = alert['start']
            index = -1
            num = 0
            for i in range(len(cws)):
                if num == start:
                    index = i
                    break
                else:
                    num += len(cws[i])
            if index <= 0:
                return None
            elif index +1 >= len(cws):
                alert['replaceText'] = '的'
                return alert
            else:
                if pos[index-1] in ['a','b','d','n','nd','nh','ni','nl','ns','nt','nz'] and pos[index+1] in ['n','nd','nh','ni','nl','ns','nt','nz']:
                    replace = '的'
                elif pos[index-1] == 'v' and pos[index+1] in ['a','b','d']:
                    replace = '得'
                elif pos[index+1] == 'v' :
                    replace = '地'
                else:
                    replace = ''
                if replace == '':
                    return None
                elif replace == alert['sourceText']:
                    return None
                else:
                    alert['replaceText'] = replace
                    return alert
        total_alert=[]
        for sentence_errors,item in zip(self.alerts,self.data):
            res = []
            for alert_error in sentence_errors:
                if self.de_question(alert=alert_error):
                    cws = item['origin_cws']
                    pos = item['origin_pos']
                    temp = fix_deProcess(alert_error,cws,pos)
                    if temp != None:
                        temp['error_type'] = "1-12"
                        res.append(temp)
                else:
                    res.append(alert_error)
            total_alert.append(res)
        self.alerts = total_alert

    def clean_data(self):
        datas = self.data
        res = []
        for item in datas:
            temp = {
                "originText":item['origin'],
                "output":item['output']
            }
            res.append(temp)
        self.data = res
        return True

    def get_alerts(self):

        self.switch()
        self.clean_data()
        model_json={}
        model_json['alerts']=self.alerts
        model_json['data'] = self.data
        model_json['errCode']=0
        model_json['errMsg']=''
        return model_json

    def switch(self):
        self.filiter_alerts()
        self.fix_deQuestion()
        if self.need_afterProcess:
            self.post_disable_repeat()              #处理重复alert
            self.post_disable_location()            #针对行政区划的过滤
            self.post_disable_from_database()       #对于需要从数据库中过滤
            self.post_disable_context()             #无意义修改词
            self.post_disable_gongwenguifan()       #过滤公文规范
            self.post_disable_space_after_puncs()   #修改前后标点相同
            self.post_disable_space()               #中间有空格
            self.post_disable_number()              #阿拉伯数字转化为汉字
            self.post_disable_bookname()            #把书名号错误，取消处理
            # self.post_disable_date()                #把日期错误，取消处理
            self.post_disable_rongyu()              #冗余字词错误
            self.post_disable_low()                 #法律名称不能带有书名号
            self.post_disable_reverse_words()       #词序颠倒
            self.post_disable_empty_replace_text()  #过滤没有replaceText的alert
            self.post_disable_remove_error_quotes() #过滤错误的quotes
            self.post_enable_mix_pair_symbol_detection()#成对的标点符号


if __name__ == '__main__':
    inputCont={
    "alerts": [
        [
            {
                "advancedTip": "True",
                "alertMessage": "建议用“审计组已”替换“审计组己”",
                "alertType": 4,
                "end": 5,
                "errorType": 1,
                "replaceText": "审计组已",
                "sourceText": "审计组己",
                "start": 2
            }
        ]
    ],
    "data": [
        {
            "origin": "相关审计组己开展了对州财政局、州地税局、国库、州民政局、州农委等九个部门预算执行情况进行审计和审计调查。",
            "origin_cws": [
                "相关",
                "审计",
                "组己",
                "开展",
                "了",
                "对州",
                "财政局",
                "、",
                "州",
                "地税局",
                "、",
                "国库",
                "、",
                "州",
                "民政局",
                "、",
                "州",
                "农委",
                "等",
                "九",
                "个",
                "部门",
                "预算",
                "执行",
                "情况",
                "进行",
                "审计",
                "和",
                "审计",
                "调查",
                "。"
            ],
            "origin_pos": [
                "v",
                "v",
                "v",
                "v",
                "u",
                "ns",
                "n",
                "wp",
                "n",
                "j",
                "wp",
                "n",
                "wp",
                "n",
                "n",
                "wp",
                "n",
                "j",
                "u",
                "m",
                "q",
                "n",
                "n",
                "v",
                "n",
                "v",
                "v",
                "c",
                "v",
                "v",
                "wp"
            ]
        }
    ],
    "errCode": 0,
    "errMsg": ""
}
    # filiter=total_filter(input_content=inputCont,cfg=cfg)
    # print(filiter.get_alerts())




