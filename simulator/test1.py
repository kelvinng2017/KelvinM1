import re
import json
text1 = '<0><0><0><3><carrier_3800><2><BUFFER><11><{"pick":"1"}>0047'

# 修改正則表達式以允許空的 JSON 和多餘內容
pattern = r"<(\d+)><(\d+)><(\d+)><(\d+)><([^<>]+)><(\d+)><([^<>]+)><(\d+)><({.*})>.*"

# 匹配
r = re.match(pattern, text1)
if r:
    print("匹配成功！提取內容如下：")
    e84, cs, cont, carriertype, from_port, fromportnum, to_port, toportnum, addition=r.groups()
    addition=json.loads(addition)
    print(e84, cs, cont, carriertype, from_port, fromportnum, to_port, toportnum, addition)
else:
    print("匹配失敗")
