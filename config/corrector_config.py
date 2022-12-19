#corrector config

# 纠错模型设置
model_dir = '/root/workspace/t5_model/t5_logtrain'
is_small_model = False

# 过滤器设置
filiter_dbpath = 'database/filiter_db.db'
zhfiliter = True    
dictfiliter = True
afterfiliter = True

# 数据库设置
# mongodb
mongohost = 'localhost'
mongoport = 27017
mongodb = 'log_db'
api_collection = 'api_log'
t5_collection =  't5_log'

# 后处理设置
transfordict_path = 'transfor_dict'
location_structure = 'transfor_dict/location.json'
replace_dict = 'search_dict.txt'
inner_db = 'database/inner_correct.db'
outer_db = 'database/outer_correct.db'
