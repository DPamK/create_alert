from config import alert_config as cfg
import json
class loadFiles():
    def __init__(self,cfg):
        self.fantidict_path=cfg.fantidict_path#繁体字
        self.char_meta_fname=cfg.char_meta_fname#形似字
        self.location_structure=cfg.location_structure#地址
    def set_location_structure(self):
        with open(cfg.location_structure, 'r', encoding='utf8') as location_file:
            location_structure = json.load(location_file)
            self.location_structure= location_structure
            # print(self.location_structure)

    def set_fantidict(self):
        with open(self.fantidict_path, 'r', encoding='utf8') as fanti_file:
            fanti_dict= json.load(fanti_file)
            # print(type(fanti_dict))
            self.fanti_dict=fanti_dict

    def set_char_meta_fname(self):
        data = {}
        f = open(self.char_meta_fname, 'r', encoding='utf-8')
        for line in f:
            items = line.strip().split('\t')
            code_point = items[0]
            char = items[1]
            pronunciation = items[2]
            decompositions = items[3:]
            assert char not in data
            data[char] = {"code_point": code_point, "pronunciation": pronunciation, "decompositions": decompositions}
            self.xingsi_dict= data

    def set_All(self):
        self.set_location_structure()
        self.set_fantidict()
        self.set_char_meta_fname()

if __name__ == '__main__':
    fileContent=loadFiles(cfg)
    fileContent.set_All()
