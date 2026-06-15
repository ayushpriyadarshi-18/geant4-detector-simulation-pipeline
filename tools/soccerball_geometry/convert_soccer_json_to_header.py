#!/usr/bin/env python3

import json
from pathlib import Path

JSON_FILE = Path("soccer_detector_faces.json")
HEADER_FILE = Path("SoccerBallGeometryData.hh")

CM_TO_MM = 10.0

with open(JSON_FILE, "r") as f:
    data = json.load(f)

faces = data["faces"]


def write_vertices(out, vertices_cm):
    out.write("        {\n")
    for v in vertices_cm:
        x, y, z = [coord * CM_TO_MM for coord in v]
        out.write(f"            {{{x:.10f}, {y:.10f}, {z:.10f}}},\n")
    out.write("        }")


with open(HEADER_FILE, "w") as out:
    out.write("#ifndef SOCCER_BALL_GEOMETRY_DATA_HH\n")
    out.write("#define SOCCER_BALL_GEOMETRY_DATA_HH\n\n")

    out.write("#include <vector>\n\n")

    out.write("struct SoccerVertex {\n")
    out.write("    double x_mm;\n")
    out.write("    double y_mm;\n")
    out.write("    double z_mm;\n")
    out.write("};\n\n")

    out.write("struct SoccerModuleData {\n")
    out.write("    const char* id;\n")
    out.write("    const char* type;\n")
    out.write("    int n_sides;\n\n")

    out.write("    // Full unshrunk soccer-ball cell boundary, used for Al envelope\n")
    out.write("    std::vector<SoccerVertex> cell_inner_vertices_mm;\n")
    out.write("    std::vector<SoccerVertex> cell_outer_vertices_mm;\n\n")

    out.write("    // Shrunk active crystal boundary\n")
    out.write("    std::vector<SoccerVertex> inner_vertices_mm;\n")
    out.write("    std::vector<SoccerVertex> outer_vertices_mm;\n")
    out.write("};\n\n")

    out.write("static const std::vector<SoccerModuleData> soccerModules = {\n")

    for face in faces:
        out.write("    {\n")
        out.write(f"        \"{face['id']}\",\n")
        out.write(f"        \"{face['type']}\",\n")
        out.write(f"        {face['n_sides']},\n")

        # Full unshrunk cell vertices
        write_vertices(out, face["cell_inner_vertices_cm"])
        out.write(",\n")

        write_vertices(out, face["cell_outer_vertices_cm"])
        out.write(",\n")

        # Shrunk crystal vertices
        write_vertices(out, face["inner_vertices_cm"])
        out.write(",\n")

        write_vertices(out, face["outer_vertices_cm"])
        out.write("\n")

        out.write("    },\n")

    out.write("};\n\n")

    out.write(f"static const int soccerNumberOfModules = {len(faces)};\n")
    out.write(f"static const double soccerInnerRadius_mm = {data['inner_radius_cm'] * CM_TO_MM:.10f};\n")
    out.write(f"static const double soccerOuterRadius_mm = {data['outer_radius_cm'] * CM_TO_MM:.10f};\n")
    out.write(f"static const double soccerCrystalSideShrink_mm = {data['crystal_side_shrink_cm'] * CM_TO_MM:.10f};\n")
    out.write(f"static const double soccerExpectedCrystalGap_mm = {data['expected_crystal_to_crystal_gap_mm']:.10f};\n\n")

    out.write("#endif\n")

print(f"Saved {HEADER_FILE}")
print(f"Number of modules: {len(faces)}")
print(f"Pentagons: {sum(1 for f in faces if f['type'] == 'pentagon')}")
print(f"Hexagons : {sum(1 for f in faces if f['type'] == 'hexagon')}")
print(f"Inner radius: {data['inner_radius_cm'] * CM_TO_MM:.2f} mm")
print(f"Outer radius: {data['outer_radius_cm'] * CM_TO_MM:.2f} mm")
print(f"Crystal side shrink: {data['crystal_side_shrink_cm'] * CM_TO_MM:.3f} mm")
print(f"Expected crystal gap: {data['expected_crystal_to_crystal_gap_mm']:.3f} mm")
print("Exported: full cell vertices + shrunk crystal vertices")