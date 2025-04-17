# import re
# from global_variables import M1_global_variables

# original_string = "HelloWorld_LP2"


# result_string = re.sub(M1_global_variables.re_pattern_of_LP, '', original_string)

# print(result_string)



# pattern = re.compile(M1_global_variables.re_pattern_of_eq_3910)


# strings = ["EQ_3910_P01_LP1", "EQ_3910_P02_LP1"]

port_type="E016"

if "_I" in port_type or "_O" in port_type:
    print("haha")
# for s in strings:
#     match = pattern.match(s)
#     if match:
        
#         print(match.groups())
#     else:
#         print("nn")

# equipmentID="EQ_3670_P01"

# if equipmentID in ["EQ_3670_P01"]:
#     print("jaja")
def add_to_list_dict(d, key, value):
    if key not in d:
        d[key] = []
    d[key].append(value)

test1 = {}
add_to_list_dict(test1, "EQ12", "DO D")
# add_to_list_dict(test1, "EQ12", "DO O")
print(test1)

actions_in_order=[]
actions=[]
actions_in_order.extend(test1["EQ12"])

actions.extend(actions_in_order)

print(actions)
print(actions_in_order)
