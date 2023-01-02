import re

class check_location():
    def __init__(self,location_structure,data,alerts):
        self.data=data
        self.alerts=alerts
        self.location_structure=location_structure

    def post_enable_location(self):
        """
            根据原文查找202错误：对行政区划的层级进行判断处理，
            分析主要的问题是：检测出模型未检出的202错误，并提示。
            :param model_json:
            :return:
            """
        p = re.compile(r"[\u4e00-\u9fa5]{1,4}[省市县区]")
        p0 = re.compile(r"[\u4e00-\u9fa5]+省((?!市).)*区")
        location_hashmap = self.create_gov_level_hash()
        for item, sentence_error in zip(self.data,self.alerts):
            sentence=item['origin']
            errorList = re.findall(p, sentence)
            errorList = self.delete_conjunctions(errorList)
            errorList = [self.clean_location_name(name, location_hashmap) for name in errorList]
            for text in errorList:
                if 'error' in text:
                    # text = text[5:]
                    # if not is_same_location_error_exist(text, sentence_error):
                    #     start = sentence.find(text)
                    #     item = createAdvise(text, start, '', '地址错误')
                    #     sentence_error.append(item)
                    continue
                if re.match(p0, text):
                    if self.is_process_needed(text):
                        if not is_same_location_error_exist(text, self.sentence_error):
                            start = sentence.find(text)
                            ##这里没太看懂？？
                            item = self.createAlert(text, start, revise=self.location_structure,message='行政区划错误',fix_advise=True)
                            sentence_error.append(item)
                    else:
                        if not is_same_location_error_exist(text, sentence_error):
                            start = sentence.find(text)
                            item = self.createAlert(text, start, revise='', message='地址错误',fix_advise=False)
                            sentence_error.append(item)

                if re.match(r"([\u4e00-\u9fa5]+省)?[\u4e00-\u9fa5]+市([\u4e00-\u9fa5]+[区县])?", text):
                    exist_wrong, revise = self.wrong_gov_level(text, location_hashmap)
                    if exist_wrong:
                        if not self.is_same_location_error_exist(text, sentence_error):
                            start = sentence.find(text)
                            item = self.createAlert(text, start, revise, message='归属地错误',fix_advise=False)
                            sentence_error.append(item)

        # return model_json

    def delete_conjunctions(self,errorlist):
        res = []
        for error in errorlist:
            if self.exist_conjunctions(error):
                temp = re.split('和|及|与|兼|跟|在|或', error)
                for m in temp:
                    res.append(m)
            else:
                res.append(error)
        return res

    def exist_conjunctions(self,text):
        words = ['和', '及', '与', '兼', '跟', '在', '或']
        citys = ['呼和浩特市', '和县', '和区', '和田']
        for word in words:
            if word in text:
                for c in citys:
                    if c in text:
                        return False
                return True
        return False

    def clean_location_name(self,text, hashmap):
        p = re.compile(r"(?<=[省市县区])")
        place = re.split(p, text)
        place.pop()
        if '城区' in place:
            place.remove('城区')
        lenth = len(place)
        res = ''
        for i in range(lenth):
            newp = self.catch_location_name(place[i], hashmap)
            if newp == 'error':
                return 'error' + text
            else:
                res += newp
        return res

    # def createAdvise(self,text, start, revise, message):
    #     res = {
    #         'advancedTip': True,
    #         'message': message,
    #         'alertType': 4,
    #         'end': start + len(text) - 1,
    #         'errorType': 202,
    #         'replaceText': revise,
    #         'sourceText': text,
    #         'start': start
    #     }
    #     return res

    def catch_location_name(self,text, location_hashmap):
        '''
        因为切词的不严谨会导致多切一些内容，所以需要修正一下行政名
        :param text:
        :param location_hashmap:
        :return: 正确的行政名
        '''
        if text[-1] == '省':
            if text in location_hashmap['p2c']:
                return text
            else:
                for province_name in location_hashmap['p2c'].keys():
                    if province_name in text:
                        text = province_name
                        return text
                return 'error'
        elif text[-1] == '市':
            if text in location_hashmap['c2co']:
                return text
            else:
                for city_name in location_hashmap['c2co'].keys():
                    if city_name in text:
                        text = city_name
                        return text
                return 'error'
        elif text[-1] == '区':
            if text in location_hashmap['co2c']:
                return text
            else:
                for name in location_hashmap['co2c'].keys():
                    if name in text:
                        text = name
                        return text
                return 'error'
        elif text[-1] == '县':
            if text in location_hashmap['co2c']:
                return text
            else:
                for name in location_hashmap['co2c'].keys():
                    if name in text:
                        text = name
                        return text
                return 'error'
        else:
            return 'error'

    def wrong_gov_level(self,text, location_hashmap):
        '''
        返回是否出现归属地错误，且返回修改内容
        :param text:
        :param location_hashmap:
        :return: bool，text
        '''
        p = re.compile(r"(?<=[省市区县])")
        place = re.split(p, text)
        place.pop()
        lenth = len(place)
        for i in range(lenth):
            newp = self.catch_location_name(place[i], location_hashmap)
            if newp == 'error':
                return False, ''
            else:
                place[i] = newp
        if lenth == 2:
            if place[0][-1] == '省':
                if place[1] in location_hashmap['p2c'][place[0]]:
                    return False, ''
                else:
                    if place[1] not in location_hashmap['c2p'] and place[1] in location_hashmap['c2co']:
                        return True, place[1]
                    else:
                        maybep = location_hashmap['c2p'][place[1]][0]
                        return True, maybep + place[1]
            elif place[0][-1] == '市':
                if place[1] in location_hashmap['c2co'][place[0]]:
                    return False, ''
                else:
                    maybec = location_hashmap['co2c'][place[1]][0]
                    return True, maybec + place[1]
            else:
                return False, ''

        elif lenth == 3:
            if place[0] in location_hashmap['p2c']:
                if place[1] in location_hashmap['p2c'][place[0]]:
                    if place[2] in location_hashmap['c2co'][place[1]]:
                        return False, ''
                    else:
                        if place[2] in location_hashmap['co2c']:
                            maybe_city = location_hashmap['co2c'][place[2]]
                            for mc in maybe_city:
                                if mc in location_hashmap['p2c'][place[0]]:
                                    return True, place[0] + mc + place[2]
                        else:
                            return True, place[0] + place[1]
                else:
                    if place[2] in location_hashmap['co2c']:
                        maybe_city = location_hashmap['co2c'][place[2]]
                        for mc in maybe_city:
                            if mc not in location_hashmap['c2p'] and mc in location_hashmap['c2co']:
                                return True, mc + place[2]
                            elif mc in location_hashmap['p2c'][place[0]]:
                                return True, place[0] + mc + place[2]

                        cy = maybe_city[0]
                        pv = location_hashmap['c2p'][cy][0]
                        return True, pv + cy + place[2]
                    else:
                        return False, ''
            else:
                return False, ''
        else:
            return False, ''

    def create_gov_level_hash(self):
        '''
        创建hash表，p2c对应省到市,c2p对应市到省,c2co对应市到区，co2c对应区到市
        :param location_structure:
        :return: hashmap{'p2c','c2p','c2co','co2c'}
        '''
        province_city = {}
        city_province = {}
        city_county = {}
        county_city = {}
        for province in self.location_structure:
            for city in province['city']:
                if city['name'] != '市辖区' and city['name'] != '县':
                    for county in city['county']:

                        if city['name'] not in city_county:
                            city_county[city['name']] = [county]
                        else:
                            city_county[city['name']].append(county)

                        if county not in county_city:
                            county_city[county] = [city['name']]
                        else:
                            county_city[county].append(city['name'])
                else:
                    for county in city['county']:
                        if province["province"] not in city_county:
                            city_county[province["province"]] = [county]
                        else:
                            city_county[province["province"]].append(county)

                        if county not in county_city:
                            county_city[county] = [province["province"]]
                        else:
                            county_city[county].append(province["province"])

                if city['name'] != '市辖区' and city['name'] != '县':
                    if province["province"] not in province_city:
                        province_city[province["province"]] = [city['name']]
                    else:
                        province_city[province["province"]].append(city['name'])

                    if city['name'] not in city_province:
                        city_province[city['name']] = [province["province"]]
                    else:
                        city_province[city['name']].append(province["province"])
        res = {
            'p2c': province_city,
            'c2p': city_province,
            'c2co': city_county,
            'co2c': county_city
        }
        return res

    def is_process_needed(self,text):  # 新增
        p = re.compile(r"(?<=[省区])")
        place = re.split(p, text)  # 将词条切分为：XX省，XX市，XX县
        place.pop()
        for province in self.location_structure:
            if province['province'] == place[0]:
                for city in province['city']:
                    if place[1] in city["county"]:
                        return True
                return False

    def is_same_location_error_exist(text, sentence_error):
        res = False
        for item in sentence_error:
            if text in item['sourceText']:
                return True
        return res

    def createAlert(self,text, start,message,revise,fix_advise=False):
        res = {
            'advancedTip': True,
            'message':message,
            'alertType': 4,
            'end': start + len(text) - 1,
            'errorType': 202,
            'error_type':'4-2',
            'replaceText': self.revise_202(text) if fix_advise is True else revise,
            'sourceText': text,
            'start': start
        }
        return res

    def revise_202(self,text):  # 针对XX省XX区的错误

        p = re.compile(r"(?<=[省市县区镇村])")
        place = re.split(p, text)  # 将词条切分为：XX省，XX市，XX县
        place.pop()
        for province in self.location_structure:
            if province['province'] == place[0]:
                for city in province['city']:
                    if place[1] in city["county"]:
                        return place[0] + city['name'] + place[1]
        return text

    def post_disable_local(self):
        """
        针对C1错误：对行政区划的层级进行判断处理，
        分析主要的问题是：模型中会将县级市和县两个行政等级补全，这个功能不需要。
        解决方法：使用逻辑判断是否需要删除
        :param model_json:
        :return:
        """

        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if alert_error['errorType'] == 202:
                    sentence_errors.remove(alert_error)
        # return model_json

    def correct_location_error(self):
        """
                针对中国石油云南分公司的错误，
                解决方法：source是 XX+某省，replace是 某省的，比如 大美山东 -> 山东省， 去掉错误
                :param model_json:
                :return:
                """
        pr = re.compile(r'[\u4e00-\u9fa5]{1,4}省$')
        p = re.compile(r'省')
        for sentence_errors in self.alerts:
            for alert_error in list(sentence_errors):
                if re.match(pr, alert_error['replaceText']) and \
                        self.is_province_location(alert_error['replaceText']):
                    province = re.split(p, alert_error['replaceText'])[0]
                    ps = re.compile(r'[\u4e00-\u9fa5]+' + province + r'$')
                    if re.match(ps, alert_error['sourceText']):
                        sentence_errors.remove(alert_error)
        # return model_json

    def is_province_location(self,text):
        for province in self.location_structure:
            if province['province'] == text:
                return True
        return False

    def location_detected(self):
        for alerts,item in zip(self.alerts,self.data):
            pass

    def switch(self):
        self.post_disable_local()
        self.correct_location_error()
        self.post_enable_location()

    def get_alerts(self):
        self.switch()
        return self.alerts


