import json
with open(r'utils/city.md', 'r',encoding='utf-8') as f:
    content = f.read()
    for i in json.loads(content):
        if i['areaid'] == 101010100:
            print(i['countyname'])