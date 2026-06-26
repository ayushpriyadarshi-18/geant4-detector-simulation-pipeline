#!/usr/bin/env python3

import json
import math
import numpy as np
from itertools import combinations

INNER_RADIUS_CM = 10.00
INNER_AL_THICKNESS_CM = 0.05
# Controls the outward scintillator thickness of the soccerball modules.
SCINTILLATOR_THICKNESS_INCH = 2.0
SCINTILLATOR_THICKNESS_CM = SCINTILLATOR_THICKNESS_INCH * 2.54
OUTER_RADIUS_CM = INNER_RADIUS_CM + INNER_AL_THICKNESS_CM + SCINTILLATOR_THICKNESS_CM

# 0.5 mm inward shrink from each polygon edge.
# This creates approximately 1.0 mm crystal-to-crystal gap
# between neighbouring crystal modules.
CRYSTAL_SIDE_SHRINK_CM = 0.05

OUTPUT_FILE = "soccer_detector_faces.json"


def unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)


def face_plane_distance(points):
    points = [np.array(p, dtype=float) for p in points]
    normal = unit(np.cross(points[1] - points[0], points[2] - points[0]))
    center = np.mean(points, axis=0)

    if np.dot(normal, center) < 0:
        normal = -normal

    return np.dot(normal, points[0])


def cross2d(a, b):
    """
    2D cross product scalar.
    Avoids NumPy 2.0 warning for np.cross on 2D vectors.
    """
    return a[0] * b[1] - a[1] * b[0]


def shrink_polygon_about_center(points, shrink_cm):
    """
    Shrink a flat polygon inward by approximately shrink_cm from each edge.

    The full cell polygon is kept separately for Al.
    The shrunk polygon is used for the active crystal.
    """
    points = [np.array(p, dtype=float) for p in points]
    center = np.mean(points, axis=0)

    normal = unit(center)

    ref = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(ref, normal)) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])

    u = ref - normal * np.dot(ref, normal)
    u = unit(u)
    v = np.cross(normal, u)

    pts2d = []
    for p in points:
        r = p - center
        pts2d.append(np.array([np.dot(r, u), np.dot(r, v)]))

    apothem = 1e99
    n = len(pts2d)

    for i in range(n):
        p1 = pts2d[i]
        p2 = pts2d[(i + 1) % n]
        edge = p2 - p1

        # Distance from polygon center/origin to edge line
        dist = abs(cross2d(edge, -p1)) / np.linalg.norm(edge)
        apothem = min(apothem, dist)

    scale = (apothem - shrink_cm) / apothem

    if scale <= 0:
        raise ValueError("Shrink is too large for polygon.")

    shrunk_points = [center + scale * (p - center) for p in points]
    return shrunk_points


def sort_points_around_face(points, normal):
    normal = unit(normal)
    center = np.mean(points, axis=0)

    ref = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(ref, normal)) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])

    u = ref - normal * np.dot(ref, normal)
    u = unit(u)
    v = np.cross(normal, u)

    angles = []
    for p in points:
        rel = p - center
        angle = math.atan2(np.dot(rel, v), np.dot(rel, u))
        angles.append(angle)

    sorted_points = [p for _, p in sorted(zip(angles, points))]

    # Make sure ordering is outward-facing
    n_test = np.cross(
        sorted_points[1] - sorted_points[0],
        sorted_points[2] - sorted_points[0]
    )

    if np.dot(n_test, center) < 0:
        sorted_points = sorted_points[::-1]

    return sorted_points


# -------------------------------
# 1. Build icosahedron vertices
# -------------------------------

phi = (1.0 + math.sqrt(5.0)) / 2.0

vertices = []

for y in [-1, 1]:
    for z in [-phi, phi]:
        vertices.append([0, y, z])

for x in [-1, 1]:
    for y in [-phi, phi]:
        vertices.append([x, y, 0])

for x in [-phi, phi]:
    for z in [-1, 1]:
        vertices.append([x, 0, z])

vertices = np.array(vertices, dtype=float)


# -------------------------------
# 2. Find triangular faces
# -------------------------------

dist = np.linalg.norm(vertices[:, None, :] - vertices[None, :, :], axis=-1)
edge_length = np.min(dist[dist > 1e-9])

ico_faces = []

for tri in combinations(range(len(vertices)), 3):
    d01 = dist[tri[0], tri[1]]
    d12 = dist[tri[1], tri[2]]
    d20 = dist[tri[2], tri[0]]

    if (
        abs(d01 - edge_length) < 1e-6 and
        abs(d12 - edge_length) < 1e-6 and
        abs(d20 - edge_length) < 1e-6
    ):
        pts = vertices[list(tri)]
        normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        center = np.mean(pts, axis=0)

        if np.dot(normal, center) < 0:
            tri = (tri[0], tri[2], tri[1])

        ico_faces.append(tri)


# -------------------------------
# 3. Truncate icosahedron
# -------------------------------

def point_near_vertex(i, j):
    """
    Point on edge i-j closer to vertex i.
    Truncation point at 1/3 of the edge from i to j.
    """
    return (2.0 * vertices[i] + vertices[j]) / 3.0


def make_face_json(face_id, face_type, n_sides, pts):
    center = np.mean(pts, axis=0)
    normal = unit(center)

    # Full unshrunk soccer-ball cell boundary.
    # INNER_RADIUS_CM is the minimum face-plane distance from the origin,
    # not the vertex radius. Uniform scaling keeps neighbouring cells shared.
    cell_inner_pts = [p * (INNER_RADIUS_CM / BASE_MIN_FACE_DISTANCE_CM) for p in pts]
    cell_outer_pts = [p * (OUTER_RADIUS_CM / BASE_MIN_FACE_DISTANCE_CM) for p in pts]

    # Crystal starts behind the inner Al by 0.5 mm.
    crystal_inner_radius_cm = INNER_RADIUS_CM + INNER_AL_THICKNESS_CM
    crystal_outer_radius_cm = OUTER_RADIUS_CM

    crystal_inner_base_pts = [p * (crystal_inner_radius_cm / BASE_MIN_FACE_DISTANCE_CM) for p in pts]
    crystal_outer_base_pts = [p * (crystal_outer_radius_cm / BASE_MIN_FACE_DISTANCE_CM) for p in pts]

    # Shrink crystal laterally to create side-envelope space.
    crystal_inner_pts = shrink_polygon_about_center(
        crystal_inner_base_pts,
        CRYSTAL_SIDE_SHRINK_CM
    )
    crystal_outer_pts = shrink_polygon_about_center(
        crystal_outer_base_pts,
        CRYSTAL_SIDE_SHRINK_CM
    )

    return {
        "id": face_id,
        "type": face_type,
        "n_sides": n_sides,
        "center_direction": normal.tolist(),

        "inner_radius_cm": INNER_RADIUS_CM,
        "outer_radius_cm": OUTER_RADIUS_CM,
        "inner_al_thickness_cm": INNER_AL_THICKNESS_CM,
        "scintillator_thickness_cm": SCINTILLATOR_THICKNESS_CM,
        "crystal_side_shrink_cm": CRYSTAL_SIDE_SHRINK_CM,

        # Full cell vertices for Al envelope
        "cell_inner_vertices_cm": [p.tolist() for p in cell_inner_pts],
        "cell_outer_vertices_cm": [p.tolist() for p in cell_outer_pts],

        # Shrunk crystal vertices
        "inner_vertices_cm": [p.tolist() for p in crystal_inner_pts],
        "outer_vertices_cm": [p.tolist() for p in crystal_outer_pts],
    }


raw_faces = []


# -------------------------------
# 3A. Hexagons from original triangular faces
# -------------------------------

hex_id = 0

for a, b, c in ico_faces:
    pts = [
        point_near_vertex(a, b),
        point_near_vertex(b, a),
        point_near_vertex(b, c),
        point_near_vertex(c, b),
        point_near_vertex(c, a),
        point_near_vertex(a, c),
    ]

    raw_faces.append((f"HEX_{hex_id:02d}", "hexagon", 6, pts))

    hex_id += 1


# -------------------------------
# 3B. Pentagons from original icosahedron vertices
# -------------------------------

neighbours = {i: set() for i in range(len(vertices))}

for a, b, c in ico_faces:
    for i, j in [(a, b), (b, c), (c, a)]:
        neighbours[i].add(j)
        neighbours[j].add(i)

pent_id = 0

for i in range(len(vertices)):
    pts = [point_near_vertex(i, j) for j in neighbours[i]]
    pts = sort_points_around_face(pts, vertices[i])

    raw_faces.append((f"PENT_{pent_id:02d}", "pentagon", 5, pts))

    pent_id += 1


BASE_MIN_FACE_DISTANCE_CM = min(face_plane_distance(face[3]) for face in raw_faces)

faces_json = [
    make_face_json(face_id, face_type, n_sides, pts)
    for face_id, face_type, n_sides, pts in raw_faces
]


# -------------------------------
# 4. Save JSON
# -------------------------------

data = {
    "geometry_name": "soccer_ball_detector",
    "description": (
        "Truncated-icosahedral hollow detector geometry. "
        "Stores full cell vertices for Al envelope and shrunk crystal vertices for active detector modules."
    ),
    "inner_diameter_cm": 20.0,
    "inner_radius_cm": INNER_RADIUS_CM,
    "inner_face_plane_distance_cm": INNER_RADIUS_CM,
    "inner_al_thickness_cm": INNER_AL_THICKNESS_CM,
    "detector_thickness_cm": OUTER_RADIUS_CM - INNER_RADIUS_CM,
    "scintillator_thickness_cm": SCINTILLATOR_THICKNESS_CM,
    "detector_thickness_inch": SCINTILLATOR_THICKNESS_INCH,
    "outer_radius_cm": OUTER_RADIUS_CM,
    "outer_face_plane_distance_cm": OUTER_RADIUS_CM,

    "crystal_side_shrink_cm": CRYSTAL_SIDE_SHRINK_CM,
    "crystal_side_shrink_mm": CRYSTAL_SIDE_SHRINK_CM * 10.0,
    "expected_crystal_to_crystal_gap_mm": 2.0 * CRYSTAL_SIDE_SHRINK_CM * 10.0,

    "number_of_faces": len(faces_json),
    "number_of_pentagons": 12,
    "number_of_hexagons": 20,
    "faces": faces_json,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(data, f, indent=2)

print(f"Saved {OUTPUT_FILE}")
print(f"Total faces      : {len(faces_json)}")
print(f"Pentagons        : {sum(1 for f in faces_json if f['type'] == 'pentagon')}")
print(f"Hexagons         : {sum(1 for f in faces_json if f['type'] == 'hexagon')}")
print(f"Inner face plane cm : {INNER_RADIUS_CM}")
print(f"Outer face plane cm : {OUTER_RADIUS_CM}")
print(f"Crystal inner face plane cm : {INNER_RADIUS_CM + INNER_AL_THICKNESS_CM}")
print(f"Scintillator thickness cm : {SCINTILLATOR_THICKNESS_CM}")
print(f"Crystal shrink   : {CRYSTAL_SIDE_SHRINK_CM * 10.0:.3f} mm per side")
print(f"Expected gap     : {2.0 * CRYSTAL_SIDE_SHRINK_CM * 10.0:.3f} mm between crystals")
print("Stored vertices  : full cell + shrunk crystal")
