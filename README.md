# Geant4 Detector Simulation Pipeline

This repository contains a Geant4-based detector simulation project with a Python pipeline for generating macros, running simulations, validating ROOT outputs, analyzing deposited-energy spectra, and producing reference tables and plots.

The project is designed for scintillation detector studies involving solid cylindrical, hollow cylindrical, and soccerball / 4π detector geometries.

---

## Repository Contents

```text
.
├── CMakeLists.txt
├── README.md
├── configs/
├── include/
├── src/
├── scripts/
│   └── geant4_pipeline.py
├── macros/
│   ├── examples/
│   │   ├── vrml_solid.mac
│   │   ├── vrml_hollow.mac
│   │   └── vrml_soccerball.mac
│   └── generated/
│       ├── solid_cs137_10k.mac
│       ├── hollow_cs137_10k.mac
│       └── soccerball_cs137_10k.mac
└── results/
    ├── root/
    ├── logs/
    ├── spectra/
    ├── tables/
    └── vrml/
```

---

## Main Features

- Geant4 detector simulation using C++
- Python-controlled simulation pipeline
- Automatic macro generation
- Simulation execution from Python
- ROOT output checking
- Analysis of deposited energy in the detector crystal
- Total non-zero count extraction
- Peak count extraction around selected energies
- Spectrum plotting
- CSV and Excel table generation
- VRML geometry export for visual inspection

---

## Supported Detector Geometries

The project currently supports:

```text
solid       solid cylindrical detector
hollow      hollow cylindrical detector
soccerball  4π soccerball-style modular detector geometry
```

### Solid Cylinder

The solid detector uses commands such as:

```text
/det/geometry solid
/det/material NaI
/det/radius 24.900 mm
/det/halfZ 24.900 mm
/det/alThickness 0.400 mm
```

### Hollow Cylinder

The hollow detector uses commands such as:

```text
/det/geometry hollow
/det/material NaI
/det/innerRadius 45.720 mm
/det/thickness 50.800 mm
/det/halfZ 76.200 mm
/det/alThickness 0.400 mm
```

### Soccerball / 4π Geometry

The soccerball geometry uses:

```text
/det/geometry soccerball
/det/material BGO
```

For holder/plastic placement, the example macros use:

```text
/geom/usePlastic true
/geom/plasticZ 0.000 mm
/src/usePlastic true
/src/depth 1.000 mm
```

---

## Reference Simulations Included

This repository includes three small reference simulations, each with `10000` events:

```text
solid_cs137_10k
hollow_cs137_10k
soccerball_cs137_10k
```

These are generated and run using the Python pipeline.

The generated macros are stored in:

```text
macros/generated/
```

The ROOT outputs are stored in:

```text
results/root/
```

The analyzed tables are stored in:

```text
results/tables/
```

The spectra are stored in:

```text
results/spectra/
```

The run logs are stored in:

```text
results/logs/
```

The VRML geometry files are stored in:

```text
results/vrml/
```

---

## Reference Output Files

### Generated Macros

```text
macros/generated/solid_cs137_10k.mac
macros/generated/hollow_cs137_10k.mac
macros/generated/soccerball_cs137_10k.mac
```

### ROOT Files

```text
results/root/solid_cs137_10k.root
results/root/hollow_cs137_10k.root
results/root/soccerball_cs137_10k.root
```

### Spectra

```text
results/spectra/solid_cs137_10k.png
results/spectra/hollow_cs137_10k.png
results/spectra/soccerball_cs137_10k.png
```

### Tables

```text
results/tables/reference_summary_long.csv
results/tables/reference_summary_wide.csv
results/tables/reference_summary.xlsx
```

### VRML Geometry Files

```text
results/vrml/solid_geometry.wrl
results/vrml/hollow_geometry.wrl
results/vrml/soccerball_geometry.wrl
```

---

## Requirements

### System Requirements

- Geant4
- CMake
- C++17 compatible compiler
- ROOT-compatible Python environment for analysis

### Python Requirements

Install the Python packages using:

```bash
pip install numpy pandas matplotlib uproot openpyxl
```

---

## Building the Geant4 Project

From the repository root:

```bash
mkdir -p build
cd build
cmake ..
make -j4
```

The executable should be created as:

```text
build/hollowdetectorsim
```

---

## Running the Python Pipeline

Return to the repository root:

```bash
cd ..
```

### Generate Reference Macros Only

```bash
python scripts/geant4_pipeline.py --reference --generate
```

This creates:

```text
macros/generated/solid_cs137_10k.mac
macros/generated/hollow_cs137_10k.mac
macros/generated/soccerball_cs137_10k.mac
```

### Dry Run

```bash
python scripts/geant4_pipeline.py --reference --dry-run
```

This prints the commands that would be executed without running Geant4.

### Run Reference Simulations

```bash
python scripts/geant4_pipeline.py --reference --run
```

This runs the three reference simulations and saves ROOT files and logs.

### Analyze Existing ROOT Files

```bash
python scripts/geant4_pipeline.py --reference --analyze
```

This creates spectra and summary tables.

### Full Workflow

```bash
python scripts/geant4_pipeline.py --reference --all
```

This performs:

```text
macro generation
simulation execution
ROOT output checking
spectrum generation
peak-count extraction
table generation
```

---

## Analysis Details

The analysis script reads the ROOT file using `uproot`.

It expects:

```text
TTree name: events
Branch name: EdepCrystal_keV
```

For each case, it calculates:

```text
total_nonzero_counts
peak_counts
```

For the included Cs-137 reference cases, the expected peak is:

```text
662 keV
```

The default peak-counting window is:

```text
±20 keV
```

This can be changed using:

```bash
python scripts/geant4_pipeline.py --reference --analyze --peak-window-kev 10
```

The default spectrum bin width is:

```text
2 keV
```

This can be changed using:

```bash
python scripts/geant4_pipeline.py --reference --analyze --bin-width-kev 1
```

---

## VRML Geometry Visualization

Example VRML macros are provided in:

```text
macros/examples/
```

Available examples:

```text
vrml_solid.mac
vrml_hollow.mac
vrml_soccerball.mac
```

These macros produce `.wrl` files that can be opened in a VRML viewer.

The included reference VRML outputs are:

```text
results/vrml/solid_geometry.wrl
results/vrml/hollow_geometry.wrl
results/vrml/soccerball_geometry.wrl
```

The hollow and soccerball VRML examples include the plastic holder.

---

## Source Library Planned for Future Versions

The current committed pipeline demonstrates the workflow using Cs-137-like 662 keV monoenergetic gamma rays.

Future versions are planned to support a larger source library, including:

```text
Cs137
Co60
Sc46
Nb94
Na24
Na22
O14
Y88
Cl38
Artificial6000
Artificial8000
custom mono energies
```

Example peak definitions planned for analysis:

```text
Cs137: 662 keV

Co60:
  1173 keV
  1332 keV
  2505 keV sum peak

Sc46:
  889 keV
  1120 keV
  2009 keV sum peak

Nb94:
  703 keV
  870 keV
  1573 keV sum peak

Na24:
  1368 keV
  2754 keV
  4122 keV sum peak

Na22:
  511 keV
  1022 keV
  1275 keV
  1786 keV
  2297 keV

O14:
  511 keV
  1022 keV
  2313 keV
  2824 keV
  3335 keV

Y88:
  898 keV
  1836 keV
  2734 keV sum peak

Cl38:
  1642 keV
  2167 keV
  3809 keV sum peak
```

---

## Notes

On some systems, Geant4 may produce a segmentation fault during shutdown after a successful run. In this project, the Python runner checks whether the ROOT file was produced successfully and treats the run as valid if the expected ROOT output exists.

This behavior was observed during testing and does not necessarily indicate failure of the simulation output.

---

## Author

Ayush Priyadarshi  
Department of Physics  
IIT Roorkee
