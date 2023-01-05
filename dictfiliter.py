import sqlite3
import re
import difflib


def search_type(connect,table,type=None):
    cur = connect.cursor()
    if type==None:
        cur.execute('select * from '+table)
    else:
        cur.execute('SELECT * FROM blank_words WHERE type= ?',(type,))
    res = cur.fetchall()
    return res

def search_sentitiveWord(connect):
    cur = connect.cursor()
    cur.execute('select word from sentitive_words')
    res = cur.fetchall()
    words = []
    for item in res:
        words.append(item[0])
    return words

class dictfiliter():
    def __init__(self,filiter_dbpath) -> None:
        # files = os.listdir(dictpath)
        connect = sqlite3.connect(filiter_dbpath)
        # 对于需要过滤的dict分为四类，其中固定名词1、替换2、插入3、删除4
        self.nameDict = []
        self.replaceDict = {}
        self.insertDict = {}
        self.deleteDict = []
        # 初始化nameDict
        self.table='blank_words'
        examples = search_type(connect,self.table,type='special_n')
        for item in examples:
            self.nameDict.append(item[1])
        # 初始化deleteDict
        examples = search_type(connect,self.table,type='delete')
        for item in examples:
            self.deleteDict.append(item[1])
        # 初始化replaceDict
        examples = search_type(connect,self.table,type='replace')
        for item in examples:
            ori = item[1]
            fix = item[2]
            if ori in self.replaceDict:
                self.replaceDict[ori].append(fix)
            else:
                self.replaceDict[ori] = [fix]
        # 初始化insertDict
        examples = search_type(connect,table=self.table,type='insert')
        for item in examples:
            ori = item[1]
            fix = item[2]
            if ori in self.insertDict:
                self.insertDict[ori].append(fix)
            else:
                self.insertDict[ori] = [fix]
        # 初始化sentitiveWord
        self.sentitiveWord = search_sentitiveWord(connect)
        connect.close()

    def filiter_SentitiveWord(self,alert):
        for senword in self.sentitiveWord:
            if senword in alert['sourceText']:
                if alert['alertType'] >= 3 and senword not in alert['replaceText']:
                    return True
        return False
        

    def filterName(self,alert):
        source = alert['sourceText']
        return source in self.nameDict

    def filterReplace(self,alert):
        source = alert['sourceText']
        fixed = alert['replaceText']
        if source in self.replaceDict:
            return fixed in self.replaceDict[source]
        else:
            return False


    def filiterInsert(self,alert):
        source = alert['sourceText']
        fixed = alert['replaceText']
        if source in self.insertDict:
            return fixed in self.insertDict[source]
        else:
            return False

    def filterDelete(self,alert):
        source = alert['sourceText']
        return source in self.deleteDict

    def filter(self,alert):
        kind = alert['alertType']
        # alert 中 alertType : 4 为替换replace； 3为删除delete； 2为添加insert
        if self.filterName(alert):
            return True
        elif self.filiter_SentitiveWord(alert):
            return True
            
        if kind == 4:
            return self.filterReplace(alert)
        elif kind == 3:
            return self.filterDelete(alert)
        elif kind == 2:
            return self.filiterInsert(alert)
        else:
            return False


class post_with_databese():
    def __init__(self,data,alerts,inner_db,outer_db):
        self.data=data
        self.alerts=alerts
        self.inner_db=inner_db
        self.outer_db=outer_db

    def get_connect(self,dbpath):
        return sqlite3.connect(dbpath)


    def get_db_dict_assets(self,connect):
        black_pairs = search_type(connect, table='black_pairs')  # 匹配两个
        black_pairs = set([pair[1] + ' ' + pair[2] for pair in black_pairs])

        black_words = search_type(connect, table='black_words')  # 匹配source
        black_words = set([word[1] for word in black_words])

        idioms = search_type(connect, table='idioms')
        idioms = set([idiom[1] for idiom in idioms])

        leader_infos = search_type(connect, table='leaders')
        leader_name_set = set([leader[1] for leader in leader_infos])
        leader_position_set = set([leader[2] for leader in leader_infos])

        slogans = search_type(connect, table='slogans')
        slogans = set([slogan[1] for slogan in slogans])

        return black_pairs, black_words, idioms, leader_name_set, leader_position_set, slogans

    def getAllContent(self):
        inner_db_connect =self.get_connect(self.inner_db)
        outer_db_connect = self.get_connect(self.outer_db)

        inner_assets = self.get_db_dict_assets(inner_db_connect)
        outer_assets = self.get_db_dict_assets(outer_db_connect)
        self.leader_position_dict = self.build_leader_info(outer_db_connect)
        inner_db_connect.close()
        outer_db_connect.close()

        self.black_pairs, self.black_words, self.idioms, self.leader_name_set, self.leader_position_set, \
        self.slogans = \
            self.merge_dict_assets(
            inner_assets,
            outer_assets)

    def merge_dict_assets(self,asset_a, asset_b):
        assets = []
        for item_a, item_b in zip(asset_a, asset_b):
            assets.append(set.union(item_a, item_b))
        return tuple(assets)

    def build_leader_info(self,db_connect):
        def leader_dict(leader_infos):
            leader_position_dict = {}
            for leader in leader_infos:
                leader_name = leader[1]
                if leader_name not in leader_position_dict.keys():
                    leader_position_dict[leader_name] = []
                leader_organization = leader[4] if leader[4] is not None else ''
                leader_position_prefix = leader[3] if leader[3] is not None else ''
                leader_position = leader[2]

                leader_position_dict[leader_name].append(leader_organization
                                                         + leader_position_prefix
                                                         + leader_position)
            return leader_position_dict

        leader_infos = search_type(db_connect, 'leaders')
        leader_position_dict = leader_dict(leader_infos)

        return leader_position_dict

    #人名
    def post_disable_nobody(self):
        for item, sentence_errors in zip(self.data, self.alerts):
            sentence = item['origin']
            origin_cws = item['origin_cws']
            origin_pos = item['origin_pos']
            names = self.extract_name(sentence=sentence, origin_cws=origin_cws, origin_pos=origin_pos)
            for name, start, end in names:
                left_border = start - 10 if start - 10 > 0 else 0
                right_border = end + 4
                try:
                    errorType, error_type, message, hit_position, replaceText = self.judge_exit(name, sentence[
                                                                                                      left_border:right_border],
                                                                                                self.leader_name_set,
                                                                                                self.leader_position_set,
                                                                                                self.leader_position_dict)

                    for alert_error in list(sentence_errors):
                        if name in str(alert_error['sourceText']).strip() and alert_error['errorType'] != errorType:
                            sentence_errors.remove(alert_error)
                        if hit_position != '' and hit_position in alert_error['sourceText']:
                            if name in alert_error['sourceText'] and name in alert_error['replaceText']:
                                if alert_error in sentence_errors:
                                    sentence_errors.remove(alert_error)

                    if replaceText != "":  # 领导人名字写错的时候为空
                        new_item = self.creat_name_item(name, start, end, errorType, error_type, message, replaceText)
                        for alert_error in sentence_errors:
                            if name in alert_error['sourceText'] and "，" in alert_error[
                                "sourceText"]:  # sourceText中有人名和逗
                                alert_error["alertMessage"] = alert_error["alertMessage"].replace(
                                    alert_error['sourceText'],
                                    name)
                                alert_error["sourceText"] = name
                            elif name == alert_error['sourceText']:  # sourceText和人名完全相等
                                alert_error = new_item
                        sentence_errors.append(new_item)

                except Exception as ex:
                    print(ex)
        # return model_json

    def extract_name(self, sentence: str, origin_cws, origin_pos):
        namelist = []
        current_pos = 0
        for token, label in zip(origin_cws, origin_pos):
            if label == 'nh':
                if bool(re.search(r'\d', token)):
                    continue
                start = current_pos
                end = start + len(token) - 1
                name_tuple = (token, start, end)
                namelist.append(name_tuple)
            current_pos += len(token)
        return namelist

    def creat_name_item(self, name, start, end, errorType, error_type, message, replaceText):
        res = {
            'advancedTip': True,
            'alertMessage': message,
            'alertType': 10,
            'end': end,
            'errorType': errorType,
            'error_type': error_type,
            'replaceText': replaceText,
            'sourceText': name,
            'start': start
        }
        return res

    def judge_exit(self, name_o, string_before_name, name_set, position_set, leader_position_dict):
        leader_position_list = leader_position_dict[name_o] if name_o in name_set else []
        hit_position = ''
        replaceText = ''
        for position in position_set:
            if position in string_before_name:  # 句子前面有职务
                # print(position)
                hit_position = position
                for leader_position in leader_position_list:
                    if leader_position in string_before_name:  # 句子前面的职务正确
                        errorType = 667
                        error_type = '-'
                        message = "领导职务，请谨慎查验"
                        replaceText = name_o
                        return errorType, error_type, message, hit_position, replaceText
                if len(leader_position_list) > 0:  # 职务不正确：李克强总书记
                    errorType = 201
                    error_type = "2-1"
                    message = "职务可能有误，建议修改为:" + '、'.join(set(leader_position_list))
                    replaceText = name_o
                    return errorType, error_type, message, hit_position, replaceText
                elif len(leader_position_list) == 0:  # 人名不正确：习进平总书记
                    erroType = 201
                    error_type = "2-2"
                    message = "领导人名可能有误"
                    return erroType, error_type, message, hit_position, replaceText
        errorType = 667  # 句子没有职务：张海波
        error_type = "-"
        message = "人名，请谨慎查验"
        replaceText = name_o
        return errorType, error_type, message, hit_position, replaceText


    def post_disable_by_black_words(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['sourceText'] in self.black_words:
                    sentence_errors.remove(alert_error)
        # return model_json

    # 过滤black_pairs
    def post_disable_by_black_pairs(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                pair = str(alert_error['sourceText']).strip() + ' ' + str(alert_error['replaceText'])
                if pair in self.black_pairs:
                    sentence_errors.remove(alert_error)
        # return model_json

    # 口号
    def post_disable_by_sentence_slogan(self):
        for item, sentence_errors in zip(self.data,self.alerts):
            sentence=item['origin']
            slogan_ranges = []
            slogan_existing = False
            for slogan in self.slogans:
                if slogan in sentence:
                    slogan_existing = True
                    slogan_start = sentence.index(slogan)
                    slogan_end = slogan_start + len(slogan) - 1
                    slogan_ranges.append((slogan_start, slogan_end))
            if slogan_existing:
                for alert_error in list(sentence_errors):
                    for slogan_range in slogan_ranges:
                        slogan_start, slogan_end = slogan_range
                        if alert_error['start'] >= slogan_start and alert_error['end'] <= slogan_end:
                            sentence_errors.remove(alert_error)
                            break
        # return model_json

    def post_disable_idioms(self):
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['sourceText'] in self.idioms and alert_error['replaceText'] in self.idioms:
                    sentence_errors.remove(alert_error)
        # return model_json

    def switch(self):
        self.getAllContent()
        self.post_disable_nobody()
        self.post_disable_by_black_words()
        self.post_disable_by_black_pairs()
        self.post_disable_by_sentence_slogan()
        self.post_disable_idioms()

    def get_alerts(self):
        self.switch()
        return self.alerts


if __name__=="__main__":
    connect = sqlite3.connect('database/filiter_db.db')
    res = search_sentitiveWord(connect=connect)
    print(res)



