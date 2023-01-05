import requests
import json
from create_AlertAPI import create_alerts
from total_filter import total_filter
from config import alert_config as cfg

with open(cfg.location_structure, 'r', encoding='utf8') as location_file:
    location_structure = json.load(location_file)

if __name__ == '__main__':
    origin = ['6月31日，习近平主席出席了会议']
    output = ['6月31日，习近平主席出席了会议']
    alert_info = create_alerts(origin,output)
    filiter = total_filter(cfg=cfg,input_content=alert_info,location_structure=location_structure)
    res = filiter.get_alerts()
    print(res)
    