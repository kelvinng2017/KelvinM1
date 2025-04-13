import re

port=""
match = re.match(r'^(\w+?)_(O|I)\d+$', port)
if match:
    base=match.group(1)
    correct_door="DOOR_{}".format(base)
    print(correct_door)