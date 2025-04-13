if global_variables.RackNaming == 42:
    EventInterval=30
elif global_variables.RackNaming == 36:
    if target == "E0167920":
        EventInterval=60
    else:
        EventInterval=10
else:
    EventInterval=10