#alert config


# 过滤器设置
filiter_dbpath = 'database/filiter_db.db'
zhfiliter = False
dictfiliter = True
afterfiliter = True

# 后处理设置
transfordict_path = 'transfor_dict'

location_structure = 'transfor_dict/location.json'
replace_dict = 'search_dict.txt'
inner_db = 'database/inner_correct.db'
outer_db = 'database/outer_correct.db'
afterProcess = True

#形似字判断
need_xingsifiliter=True
char_meta_fname = 'transfor_dict/char_meta.txt'
threshold_shape = 0.5
#音似字判断
need_yinsifilter=True
distance=5#编辑距离小于5认为音似
#繁体字判断
fantidict_path="transfor_dict/Chinese_dict.txt"
fantifiliter = True