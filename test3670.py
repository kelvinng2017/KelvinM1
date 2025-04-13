import re
from global_variables import M1_global_variables

original_string = "HelloWorld_LP2"


result_string = re.sub(M1_global_variables.re_pattern_of_LP, '', original_string)

print(result_string)



pattern = re.compile(M1_global_variables.re_pattern_of_eq_3910)


strings = ["EQ_3910_P01_LP1", "EQ_3910_P02_LP1"]


for s in strings:
    match = pattern.match(s)
    if match:
        
        print(match.groups())
    else:
        print("nn")

equipmentID="EQ_3670_P01"

if equipmentID in ["EQ_3670_P01"]:
    print("jaja")
