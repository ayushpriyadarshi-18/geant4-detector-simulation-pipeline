#!/usr/bin/env python3
"""
Unified Geant4-Python detector simulation pipeline.

This first release version supports a tested reference workflow:

    python scripts/geant4_pipeline.py --reference --generate
    python scripts/geant4_pipeline.py --reference --run
    python scripts/geant4_pipeline.py --reference --analyze
    python scripts/geant4_pipeline.py --reference --all
    python scripts/geant4_pipeline.py --reference --dry-run

Reference cases:
    1. solid_cs137_1M
    2. hollow_cs137_1M
    3. soccerball_cs137_1M

Each case runs 1,000,000 events using a Cs-137-like 662 keV monoenergetic gamma source.

Outputs:
    macros/reference/*.mac
    results/root/*.root
    results/tables/reference_summary_long.csv
    results/tables/reference_summary_wide.csv
    results/tables/reference_summary.xlsx
    results/spectra/*.png
    results/logs/*.log
"""

from __future__ import annotations

import argparse
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / "build"
EXECUTABLE = BUILD_DIR / "hollowdetectorsim"

MACRO_REFERENCE_DIR = PROJECT_ROOT / "macros" / "generated"
MACRO_GENERATED_DIR = PROJECT_ROOT / "macros" / "generated"

RESULTS_DIR = PROJECT_ROOT / "results"
ROOT_DIR = RESULTS_DIR / "root"
TABLE_DIR = RESULTS_DIR / "tables"
SPECTRA_DIR = RESULTS_DIR / "spectra"
LOG_DIR = RESULTS_DIR / "logs"


# ============================================================
# Reference case definition
# ============================================================

@dataclass
class ReferenceCase:
    name: str
    geometry: str
    material: str
    events: int
    source_name: str
    source_energy_keV: float
    expected_peaks_keV: list[float]

    # Solid geometry
    radius_mm: float | None = None
    halfz_mm: float | None = None

    # Hollow geometry
    inner_radius_mm: float | None = None
    thickness_mm: float | None = None

    # Common detector/source
    al_thickness_mm: float = 0.4
    source_z_mm: float = 0.0

    # Soccerball options
    use_plastic: bool = False
    plastic_z_mm: float = 0.0
    source_depth_mm: float = 1.0


REFERENCE_CASES = [
    ReferenceCase(
        name="solid_cs137_1M",
        geometry="solid",
        material="NaI",
        events=1_000_000,
        source_name="Cs137",
        source_energy_keV=662.0,
        expected_peaks_keV=[662.0],
        radius_mm=24.9,
        halfz_mm=24.9,
        al_thickness_mm=0.4,
        source_z_mm=-28.3,
    ),
    ReferenceCase(
        name="hollow_cs137_1M",
        geometry="hollow",
        material="NaI",
        events=1_000_000,
        source_name="Cs137",
        source_energy_keV=662.0,
        expected_peaks_keV=[662.0],
        inner_radius_mm=45.72,
        thickness_mm=50.8,
        halfz_mm=76.2,
        al_thickness_mm=0.4,
        source_z_mm=0.0,
    ),
    ReferenceCase(
        name="soccerball_cs137_1M",
        geometry="soccerball",
        material="BGO",
        events=1_000_000,
        source_name="Cs137",
        source_energy_keV=662.0,
        expected_peaks_keV=[662.0],
        al_thickness_mm=0.4,
        source_z_mm=0.0,
        use_plastic=False,
        plastic_z_mm=0.0,
        source_depth_mm=1.0,
    ),
]


# ============================================================
# Utility functions
# ============================================================

def ensure_directories() -> None:
    MACRO_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    MACRO_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    SPECTRA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def format_mm(value: float) -> str:
    return f"{value:.3f} mm"


def macro_path_for(case: ReferenceCase) -> Path:
    return MACRO_REFERENCE_DIR / f"{case.name}.mac"


def root_path_for(case: ReferenceCase) -> Path:
    return ROOT_DIR / f"{case.name}.root"


def log_path_for(case: ReferenceCase) -> Path:
    return LOG_DIR / f"{case.name}.log"


def spectrum_path_for(case: ReferenceCase) -> Path:
    return SPECTRA_DIR / f"{case.name}.png"


# ============================================================
# Macro generation
# ============================================================

def generate_solid_macro(case: ReferenceCase) -> str:
    if case.radius_mm is None or case.halfz_mm is None:
        raise ValueError(f"Solid case {case.name} requires radius_mm and halfz_mm.")

    return f"""# ============================================================
# Reference macro: {case.name}
# Geometry: solid cylinder
# Material: {case.material}
# Source: Cs-137-like {case.source_energy_keV:.1f} keV mono gamma
# Events: {case.events}
# ============================================================

/control/verbose 1
/run/verbose 1
/event/verbose 0
/tracking/verbose 0

# Detector setup
/det/material {case.material}
/det/geometry solid
/det/radius {format_mm(case.radius_mm)}
/det/halfZ {format_mm(case.halfz_mm)}
/det/alThickness {format_mm(case.al_thickness_mm)}

# Source position
/src/manualZ {format_mm(case.source_z_mm)}

# Initialize
/run/initialize

# Source setup
/gps/particle gamma
/gps/pos/type Point
/gps/pos/centre 0 0 {format_mm(case.source_z_mm)}
/gps/ang/type iso
/gps/ene/type Mono
/gps/ene/mono {case.source_energy_keV:.1f} keV

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_hollow_macro(case: ReferenceCase) -> str:
    if case.inner_radius_mm is None or case.thickness_mm is None or case.halfz_mm is None:
        raise ValueError(
            f"Hollow case {case.name} requires inner_radius_mm, thickness_mm, and halfz_mm."
        )

    return f"""# ============================================================
# Reference macro: {case.name}
# Geometry: hollow cylinder
# Material: {case.material}
# Source: Cs-137-like {case.source_energy_keV:.1f} keV mono gamma
# Events: {case.events}
# ============================================================

/control/verbose 1
/run/verbose 1
/event/verbose 0
/tracking/verbose 0

# Detector setup
/det/material {case.material}
/det/geometry hollow
/det/innerRadius {format_mm(case.inner_radius_mm)}
/det/thickness {format_mm(case.thickness_mm)}
/det/halfZ {format_mm(case.halfz_mm)}

# Hollow-cylinder Al lining thickness
# This does not control soccerball Al geometry.
/det/alThickness {format_mm(case.al_thickness_mm)}

# Source at centre of hollow cavity
/src/manualZ {format_mm(case.source_z_mm)}

# Initialize
/run/initialize

# Source setup
/gps/particle gamma
/gps/pos/type Point
/gps/pos/centre 0 0 {format_mm(case.source_z_mm)}
/gps/ang/type iso
/gps/ene/type Mono
/gps/ene/mono {case.source_energy_keV:.1f} keV

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_soccerball_macro(case: ReferenceCase) -> str:
    use_plastic_text = "true" if case.use_plastic else "false"

    return f"""# ============================================================
# Reference macro: {case.name}
# Geometry: soccerball / 4pi modular detector
# Material: {case.material}
# Source: Cs-137-like {case.source_energy_keV:.1f} keV mono gamma
# Events: {case.events}
# ============================================================

/control/verbose 1
/run/verbose 1
/event/verbose 0
/tracking/verbose 0

# Detector setup
/det/material {case.material}
/det/geometry soccerball

# Soccerball/plastic options
/geom/usePlastic {use_plastic_text}
/geom/plasticZ {format_mm(case.plastic_z_mm)}
/src/usePlastic {use_plastic_text}
/src/depth {format_mm(case.source_depth_mm)}

# Source at centre
/src/manualZ {format_mm(case.source_z_mm)}

# Initialize
/run/initialize

# Source setup
/gps/particle gamma
/gps/pos/type Point
/gps/pos/centre 0 0 {format_mm(case.source_z_mm)}
/gps/ang/type iso
/gps/ene/type Mono
/gps/ene/mono {case.source_energy_keV:.1f} keV

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_macro(case: ReferenceCase) -> Path:
    ensure_directories()

    if case.geometry == "solid":
        macro_text = generate_solid_macro(case)
    elif case.geometry == "hollow":
        macro_text = generate_hollow_macro(case)
    elif case.geometry == "soccerball":
        macro_text = generate_soccerball_macro(case)
    else:
        raise ValueError(f"Unsupported geometry: {case.geometry}")

    path = macro_path_for(case)
    path.write_text(macro_text)
    print(f"Generated macro: {path}")
    return path


def generate_reference_macros() -> list[Path]:
    return [generate_macro(case) for case in REFERENCE_CASES]


# ============================================================
# Simulation running
# ============================================================

def run_case(case: ReferenceCase, dry_run: bool = False) -> None:
    ensure_directories()

    macro_path = macro_path_for(case)
    final_root_path = root_path_for(case)
    final_log_path = log_path_for(case)

    if not macro_path.exists():
        generate_macro(case)

    command = [str(EXECUTABLE), str(macro_path)]

    print()
    print("=" * 70)
    print(f"CASE: {case.name}")
    print(f"GEOMETRY: {case.geometry}")
    print(f"MATERIAL: {case.material}")
    print(f"EVENTS: {case.events}")
    print(f"MACRO: {macro_path}")
    print(f"COMMAND: {' '.join(command)}")
    print("=" * 70)

    if dry_run:
        print("DRY RUN: not executing Geant4.")
        return

    if not EXECUTABLE.exists():
        raise FileNotFoundError(
            f"Executable not found: {EXECUTABLE}\n\n"
            "Build the project first:\n"
            "  mkdir -p build\n"
            "  cd build\n"
            "  cmake ..\n"
            "  make -j4\n"
        )

    produced_root = BUILD_DIR / "events.root"

    if produced_root.exists():
        produced_root.unlink()

    with final_log_path.open("w") as log_file:
        completed = subprocess.run(
            command,
            cwd=BUILD_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )

    if not produced_root.exists():
        raise FileNotFoundError(
            f"ROOT file was not produced for case {case.name}.\n"
            f"Expected: {produced_root}\n"
            f"Check log: {final_log_path}\n"
            f"Exit code: {completed.returncode}"
        )

    if final_root_path.exists():
        final_root_path.unlink()

    shutil.move(str(produced_root), str(final_root_path))

    print(f"Saved ROOT: {final_root_path}")
    print(f"Saved log : {final_log_path}")
    print(f"Exit code : {completed.returncode}")


def run_reference_cases(dry_run: bool = False) -> None:
    for case in REFERENCE_CASES:
        run_case(case, dry_run=dry_run)


# ============================================================
# Analysis
# ============================================================

def analyze_root_file(
    case: ReferenceCase,
    peak_window_keV: float = 20.0,
    bin_width_keV: float = 2.0,
) -> tuple[list[dict], dict]:
    import uproot
    import matplotlib.pyplot as plt

    root_path = root_path_for(case)
    if not root_path.exists():
        raise FileNotFoundError(f"ROOT file not found: {root_path}")

    with uproot.open(root_path) as root_file:
        if "events" not in root_file:
            raise KeyError(f"TTree 'events' not found in {root_path}")

        tree = root_file["events"]

        if "EdepCrystal_keV" not in tree.keys():
            raise KeyError(
                f"Branch 'EdepCrystal_keV' not found in {root_path}. "
                f"Available branches: {tree.keys()}"
            )

        energy = tree["EdepCrystal_keV"].array(library="np")

    nonzero = energy[energy > 0]
    total_nonzero = int(len(nonzero))

    long_rows = []

    for peak in case.expected_peaks_keV:
        peak_counts = int(
            np.sum(
                (nonzero >= peak - peak_window_keV)
                & (nonzero <= peak + peak_window_keV)
            )
        )

        long_rows.append(
            {
                "case_name": case.name,
                "geometry": case.geometry,
                "material": case.material,
                "source": case.source_name,
                "events": case.events,
                "expected_peak_keV": peak,
                "peak_window_keV": peak_window_keV,
                "peak_counts": peak_counts,
                "total_nonzero_counts": total_nonzero,
                "root_file": str(root_path.relative_to(PROJECT_ROOT)),
                "spectrum_file": str(spectrum_path_for(case).relative_to(PROJECT_ROOT)),
            }
        )

    # Make spectrum
    if len(nonzero) > 0:
        xmax = max(float(np.max(nonzero)), max(case.expected_peaks_keV) + 200.0)
    else:
        xmax = max(case.expected_peaks_keV) + 200.0

    bins = np.arange(0.0, xmax + bin_width_keV, bin_width_keV)

    # Make spectrum
    plt.figure(figsize=(6.2, 5.0))

    counts, edges = np.histogram(nonzero, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    ax = plt.gca()
    ax.plot(centers, counts, linewidth=0.9)

    ax.set_yscale("log")
    ax.set_xlabel("Energy deposited in crystal (keV)", fontsize=12)
    ax.set_ylabel("Counts", fontsize=12)

    # Cleaner thesis-style title
    geometry_label = {
        "solid": "Solid detector",
        "hollow": "Hollow detector",
        "soccerball": "Near-4π detector",
    }.get(case.geometry, case.geometry)

    ax.set_title(
        f"{case.material} {geometry_label}, Cs-137, $10^6$ events",
        fontsize=13,
        pad=12,
    )

    # Limit x-axis to useful Cs-137 range with margin after 662 keV
    xmax_plot = max(case.expected_peaks_keV) + 120.0
    ax.set_xlim(0, xmax_plot)

    # Set y-limit with space for peak labels
    positive_counts = counts[counts > 0]
    if len(positive_counts) > 0:
        ymin = max(1, positive_counts.min() * 0.7)
        ymax = positive_counts.max() * 3.0
        ax.set_ylim(ymin, ymax)

    # Draw peak markers like the hollow-detector matrix plots:
    # vertical line inside plot, label above line
    ymin, ymax = ax.get_ylim()
    label_y = ymax / 1.7

    for peak in case.expected_peaks_keV:
        # Dotted peak marker so the simulated peak remains visible
        ax.axvline(
            peak,
            color="black",
            linewidth=0.9,
            linestyle=":",
            zorder=1,
        )

        # Shift label slightly to the right so it does not sit on the marker line
        ax.text(
            peak + 12,
            label_y,
            f"{peak:.0f}",
            ha="left",
            va="bottom",
            fontsize=11,
        )

    # Clean box-style axes, ticks inside, labels outside
    ax.tick_params(axis="both", which="both", direction="in")
    ax.tick_params(axis="both", which="major", labelsize=11, length=5)
    ax.tick_params(axis="both", which="minor", length=3)

    # Keep full border box visible
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)

    plt.tight_layout()

    spec_path = spectrum_path_for(case)
    plt.savefig(spec_path, dpi=300)
    plt.close()

    wide_row = {
        "case_name": case.name,
        "geometry": case.geometry,
        "material": case.material,
        "source": case.source_name,
        "events": case.events,
        "total_nonzero_counts": total_nonzero,
        "root_file": str(root_path.relative_to(PROJECT_ROOT)),
        "spectrum_file": str(spec_path.relative_to(PROJECT_ROOT)),
    }

    for row in long_rows:
        peak_label = f"peak_{int(row['expected_peak_keV'])}_counts"
        wide_row[peak_label] = row["peak_counts"]

    return long_rows, wide_row


def analyze_reference_cases(
    peak_window_keV: float = 20.0,
    bin_width_keV: float = 2.0,
) -> None:
    ensure_directories()

    all_long_rows = []
    all_wide_rows = []

    for case in REFERENCE_CASES:
        print(f"Analyzing: {case.name}")
        long_rows, wide_row = analyze_root_file(
            case,
            peak_window_keV=peak_window_keV,
            bin_width_keV=bin_width_keV,
        )
        all_long_rows.extend(long_rows)
        all_wide_rows.append(wide_row)

    long_df = pd.DataFrame(all_long_rows)
    wide_df = pd.DataFrame(all_wide_rows)

    long_csv = TABLE_DIR / "reference_summary_long.csv"
    wide_csv = TABLE_DIR / "reference_summary_wide.csv"
    xlsx = TABLE_DIR / "reference_summary.xlsx"

    long_df.to_csv(long_csv, index=False)
    wide_df.to_csv(wide_csv, index=False)

    with pd.ExcelWriter(xlsx) as writer:
        long_df.to_excel(writer, sheet_name="long", index=False)
        wide_df.to_excel(writer, sheet_name="wide", index=False)

    print(f"Saved: {long_csv}")
    print(f"Saved: {wide_csv}")
    print(f"Saved: {xlsx}")


# ============================================================
# CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified Geant4-Python detector simulation pipeline"
    )

    parser.add_argument(
        "--reference",
        action="store_true",
        help="Use the three 1M reference cases: solid, hollow, soccerball",
    )

    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate reference macros",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Run reference simulations",
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze reference ROOT files and create spectra/tables",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate macros, run simulations, and analyze outputs",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing simulations",
    )

    parser.add_argument(
        "--peak-window-kev",
        type=float,
        default=20.0,
        help="Half-width of peak counting window in keV",
    )

    parser.add_argument(
        "--bin-width-kev",
        type=float,
        default=2.0,
        help="Spectrum bin width in keV",
    )

    args = parser.parse_args()

    if not args.reference:
        print("For this release version, use --reference.")
        parser.print_help()
        return

    if args.all:
        args.generate = True
        args.run = True
        args.analyze = True

    if args.dry_run:
        args.generate = True
        args.run = True

    if args.generate:
        generate_reference_macros()

    if args.run:
        run_reference_cases(dry_run=args.dry_run)

    if args.analyze and not args.dry_run:
        analyze_reference_cases(
            peak_window_keV=args.peak_window_kev,
            bin_width_keV=args.bin_width_kev,
        )

    if not any([args.generate, args.run, args.analyze, args.all, args.dry_run]):
        parser.print_help()


if __name__ == "__main__":
    main()
