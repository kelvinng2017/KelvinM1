import re

port=""
match = re.match(r'^(\w+?)_(O|I)\d+$', port)
if match:
    base=match.group(1)
    correct_door="DOOR_{}".format(base)
    print(correct_door)

single_cmds_total=0
single_cmd_count=0
merge_max_cmds=8
if (single_cmds_total+single_cmd_count)<=merge_max_cmds:
    print("hah")



my_list = [1, 2, 3, 4, 5, 6, 6, 6, 6, 7]

continue_count = 0

for my_list_index in my_list:
    if my_list_index == 6:
        continue_count += 1
        if continue_count >= 2:
            break
        continue
    else:
        continue_count = 0  
    
    print(my_list_index)

test="cbaamr01BUF02"

if "BUF" in test:
    print("haah")
