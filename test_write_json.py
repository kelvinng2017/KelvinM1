import json

data = {
    "name": "Alice",
    "age": 30,
    "city": "Taipei"
}
write_path="./host_tr_cmd/data.json"

with open(write_path, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)