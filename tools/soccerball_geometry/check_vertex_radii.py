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

def unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)

def face_plane_distance(vertices):
    pts = [np.array(v, dtype=float) for v in vertices]
    normal = unit(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
    center = np.mean(pts, axis=0)

    if np.dot(normal, center) < 0:
        normal = -normal

    return float(np.dot(normal, pts[0]))

def print_plane_summary(label, key, expected=None):
    distances = [face_plane_distance(face[key]) for face in data["faces"]]

    print(f"{label}:")
    print(f"  min = {min(distances):.6f} cm")
    print(f"  max = {max(distances):.6f} cm")
    print(f"  avg = {np.mean(distances):.6f} cm")

    if expected is not None:
        print(f"  expected min = {expected:.6f} cm")

    print()

print("\n=== Vertex radius check ===")
print(f"Expected inner face-plane distance: {data['inner_radius_cm']} cm")
print(f"Expected outer face-plane distance: {data['outer_radius_cm']} cm\n")

for face_type in ["pentagon", "hexagon"]:
    cell_inner_radii = []
    cell_outer_radii = []
    crystal_inner_radii = []
    crystal_outer_radii = []

    for face in data["faces"]:
        if face["type"] != face_type:
            continue

        cell_inner_radii.extend(radius(v) for v in face["cell_inner_vertices_cm"])
        cell_outer_radii.extend(radius(v) for v in face["cell_outer_vertices_cm"])
        crystal_inner_radii.extend(radius(v) for v in face["inner_vertices_cm"])
        crystal_outer_radii.extend(radius(v) for v in face["outer_vertices_cm"])

    print(f"{face_type.upper()}:")
    print(f"  cell inner vertex radius min = {min(cell_inner_radii):.4f} cm")
    print(f"  cell inner vertex radius max = {max(cell_inner_radii):.4f} cm")
    print(f"  cell inner vertex radius avg = {np.mean(cell_inner_radii):.4f} cm")

    print(f"  cell outer vertex radius min = {min(cell_outer_radii):.4f} cm")
    print(f"  cell outer vertex radius max = {max(cell_outer_radii):.4f} cm")
    print(f"  cell outer vertex radius avg = {np.mean(cell_outer_radii):.4f} cm")

    print(f"  crystal inner vertex radius min = {min(crystal_inner_radii):.4f} cm")
    print(f"  crystal inner vertex radius max = {max(crystal_inner_radii):.4f} cm")
    print(f"  crystal inner vertex radius avg = {np.mean(crystal_inner_radii):.4f} cm")

    print(f"  crystal outer vertex radius min = {min(crystal_outer_radii):.4f} cm")
    print(f"  crystal outer vertex radius max = {max(crystal_outer_radii):.4f} cm")
    print(f"  crystal outer vertex radius avg = {np.mean(crystal_outer_radii):.4f} cm")
    print()

print("=== Face-plane distance check ===")

inner_expected = data["inner_face_plane_distance_cm"]
outer_expected = data["outer_face_plane_distance_cm"]
crystal_inner_expected = inner_expected + data["inner_al_thickness_cm"]
crystal_outer_expected = outer_expected

print_plane_summary("Cell inner face-plane distance", "cell_inner_vertices_cm", inner_expected)
print_plane_summary("Cell outer face-plane distance", "cell_outer_vertices_cm", outer_expected)
print_plane_summary("Crystal inner face-plane distance", "inner_vertices_cm", crystal_inner_expected)
print_plane_summary("Crystal outer face-plane distance", "outer_vertices_cm", crystal_outer_expected)

crystal_inner_distances = [face_plane_distance(face["inner_vertices_cm"]) for face in data["faces"]]
crystal_outer_distances = [face_plane_distance(face["outer_vertices_cm"]) for face in data["faces"]]
crystal_thicknesses = [
    outer - inner
    for inner, outer in zip(crystal_inner_distances, crystal_outer_distances)
]

print("Crystal/scintillator face-plane thickness:")
print(f"  min = {min(crystal_thicknesses):.6f} cm")
print(f"  max = {max(crystal_thicknesses):.6f} cm")
print(f"  avg = {np.mean(crystal_thicknesses):.6f} cm")
print(f"  expected min = {data['scintillator_thickness_cm']:.6f} cm")
print()

print("=== Per-face cell inner face-plane distance ===")

for face in data["faces"]:
    distance = face_plane_distance(face["cell_inner_vertices_cm"])
    print(
        f"{face['id']:8s} {face['type']:8s} "
        f"plane_distance={distance:.6f} cm"
    )
