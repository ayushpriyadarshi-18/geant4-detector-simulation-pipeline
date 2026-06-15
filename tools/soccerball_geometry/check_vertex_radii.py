#!/usr/bin/env python3

import json
import math
import numpy as np

JSON_FILE = "soccer_detector_faces.json"

with open(JSON_FILE, "r") as f:
    data = json.load(f)

def radius(v):
    x, y, z = v
    return math.sqrt(x*x + y*y + z*z)

print("\n=== Vertex radius check ===")
print(f"Expected inner face center radius: {data['inner_radius_cm']} cm")
print(f"Expected outer face center radius: {data['outer_radius_cm']} cm\n")

for face_type in ["pentagon", "hexagon"]:
    inner_radii = []
    outer_radii = []

    for face in data["faces"]:
        if face["type"] != face_type:
            continue

        inner_radii.extend(radius(v) for v in face["inner_vertices_cm"])
        outer_radii.extend(radius(v) for v in face["outer_vertices_cm"])

    print(f"{face_type.upper()}:")
    print(f"  inner vertex radius min = {min(inner_radii):.4f} cm")
    print(f"  inner vertex radius max = {max(inner_radii):.4f} cm")
    print(f"  inner vertex radius avg = {np.mean(inner_radii):.4f} cm")

    print(f"  outer vertex radius min = {min(outer_radii):.4f} cm")
    print(f"  outer vertex radius max = {max(outer_radii):.4f} cm")
    print(f"  outer vertex radius avg = {np.mean(outer_radii):.4f} cm")
    print()

print("=== Per-face inner radius range ===")

for face in data["faces"]:
    radii = [radius(v) for v in face["inner_vertices_cm"]]
    print(
        f"{face['id']:8s} {face['type']:8s} "
        f"min={min(radii):.4f} cm  "
        f"max={max(radii):.4f} cm  "
        f"spread={(max(radii)-min(radii)):.4f} cm"
    )
