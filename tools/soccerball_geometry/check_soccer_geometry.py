#!/usr/bin/env python3

import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

JSON_FILE = "soccer_detector_faces.json"

with open(JSON_FILE, "r") as f:
    data = json.load(f)

fig = plt.figure(figsize=(9, 9))
ax = fig.add_subplot(111, projection="3d")

all_pts = []

for face in data["faces"]:
    verts = np.array(face["inner_vertices_cm"])
    all_pts.extend(verts)

    if face["type"] == "pentagon":
        alpha = 0.55
    else:
        alpha = 0.25

    poly = Poly3DCollection(
        [verts],
        alpha=alpha,
        edgecolor="black",
        linewidth=0.8
    )
    ax.add_collection3d(poly)

    center = verts.mean(axis=0)
    ax.text(
        center[0],
        center[1],
        center[2],
        face["id"],
        fontsize=5,
        ha="center"
    )

all_pts = np.array(all_pts)

max_range = np.max(np.abs(all_pts)) * 1.05

ax.set_xlim(-max_range, max_range)
ax.set_ylim(-max_range, max_range)
ax.set_zlim(-max_range, max_range)

# Very important: force equal 3D aspect ratio
ax.set_box_aspect([1, 1, 1])

ax.set_xlabel("X cm")
ax.set_ylabel("Y cm")
ax.set_zlabel("Z cm")

ax.set_title("Inner surface: soccer-ball detector faces")

# Set a cleaner viewing angle
ax.view_init(elev=20, azim=35)

plt.tight_layout()
plt.savefig("soccer_inner_faces_check_equal_aspect.png", dpi=300)
plt.show()

print("Saved soccer_inner_faces_check_equal_aspect.png")