import json
import os
from constants import MAPS_DIR
folder_names = [
            entry for entry in os.listdir(MAPS_DIR)
            if os.path.isdir(os.path.join(MAPS_DIR, entry))
        ]
for map_name in folder_names:
    map_folder = os.path.join(MAPS_DIR, map_name)
    objects_file = os.path.join(map_folder, f"objs_{map_name}.json")
    print(map_name)
    with open(objects_file, 'r') as f:
        objects_data = json.load(f)
    for obj_name, obj_data in objects_data.items():
        if "x" in obj_data and "y" in obj_data:
            objects_data[obj_name]["position"] = (obj_data["x"], obj_data["y"])
            objects_data[obj_name].pop("x")
            objects_data[obj_name].pop("y")
    with open(objects_file, "w") as f:
        json.dump(objects_data, f, indent=2)
    