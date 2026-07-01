#!/usr/bin/env python3
"""
Unified Geant4-Python detector simulation pipeline.

Campaigns:
    reference
        Existing three 1M Cs-137 reference cases.

    cascade
        Soccerball NaI + 2 mm Al chamber campaign for Nb-94, Co-60,
        Sc-46, and Na-24. For each source, this generates three mono
        gamma runs (E1, E2, Esum) plus one radioactive-decay ion run.

Default output behavior:
    If --output-dir is not given, the pipeline uses the existing public
    layout:
        macros/generated/
        results/root/
        results/tables/
        results/spectra/
        results/logs/

Private/local output behavior:
    If --output-dir is given, all generated outputs are redirected there:
        <output-dir>/macros/
        <output-dir>/root/
        <output-dir>/tables/
        <output-dir>/spectra/
        <output-dir>/logs/

Examples:
    python3 scripts/geant4_pipeline.py --campaign reference --all

    python3 scripts/geant4_pipeline.py \
        --campaign cascade \
        --output-dir private_runs/cascade_soccer_nai_chamber \
        --events 1000000 \
        --all
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
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

# These are configured by configure_output_paths().
MACRO_DIR = PROJECT_ROOT / "macros" / "generated"
RESULTS_DIR = PROJECT_ROOT / "results"
ROOT_DIR = RESULTS_DIR / "root"
TABLE_DIR = RESULTS_DIR / "tables"
SPECTRA_DIR = RESULTS_DIR / "spectra"
LOG_DIR = RESULTS_DIR / "logs"


def configure_output_paths(output_dir: str | None) -> None:
    """Configure output directories.

    If output_dir is None, keep the original public repo layout.
    If output_dir is provided, write everything inside that directory.
    """
    global MACRO_DIR, RESULTS_DIR, ROOT_DIR, TABLE_DIR, SPECTRA_DIR, LOG_DIR

    if output_dir is None:
        MACRO_DIR = PROJECT_ROOT / "macros" / "generated"
        RESULTS_DIR = PROJECT_ROOT / "results"
        ROOT_DIR = RESULTS_DIR / "root"
        TABLE_DIR = RESULTS_DIR / "tables"
        SPECTRA_DIR = RESULTS_DIR / "spectra"
        LOG_DIR = RESULTS_DIR / "logs"
    else:
        base = Path(output_dir)
        if not base.is_absolute():
            base = PROJECT_ROOT / base

        RESULTS_DIR = base
        MACRO_DIR = RESULTS_DIR / "macros"
        ROOT_DIR = RESULTS_DIR / "root"
        TABLE_DIR = RESULTS_DIR / "tables"
        SPECTRA_DIR = RESULTS_DIR / "spectra"
        LOG_DIR = RESULTS_DIR / "logs"


def ensure_directories() -> None:
    for directory in [MACRO_DIR, ROOT_DIR, TABLE_DIR, SPECTRA_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


# ============================================================
# Case definition
# ============================================================

@dataclass
class SimulationCase:
    name: str
    campaign: str
    geometry: str
    material: str
    events: int
    source_name: str
    source_mode: str  # "mono" or "decay"
    expected_peaks_keV: list[float]

    # Mono source
    source_energy_keV: float | None = None

    # Ion source for radioactive decay: /gps/ion Z A Q E
    ion_z: int | None = None
    ion_a: int | None = None
    ion_q: int = 0
    ion_excitation_keV: float = 0.0

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
    use_soccer_chamber: bool = False
    soccer_chamber_outer_radius_mm: float = 70.0
    soccer_chamber_halfz_mm: float = 68.5
    soccer_chamber_thickness_mm: float = 2.0


# ============================================================
# Campaign definitions
# ============================================================

def reference_cases(events: int | None = None) -> list[SimulationCase]:
    n = 1_000_000 if events is None else events
    return [
        SimulationCase(
            name="solid_cs137_1M" if events is None else f"solid_cs137_{n}",
            campaign="reference",
            geometry="solid",
            material="NaI",
            events=n,
            source_name="Cs137",
            source_mode="mono",
            source_energy_keV=662.0,
            expected_peaks_keV=[662.0],
            radius_mm=24.9,
            halfz_mm=24.9,
            al_thickness_mm=0.4,
            source_z_mm=-28.3,
        ),
        SimulationCase(
            name="hollow_cs137_1M" if events is None else f"hollow_cs137_{n}",
            campaign="reference",
            geometry="hollow",
            material="NaI",
            events=n,
            source_name="Cs137",
            source_mode="mono",
            source_energy_keV=662.0,
            expected_peaks_keV=[662.0],
            inner_radius_mm=45.72,
            thickness_mm=50.8,
            halfz_mm=76.2,
            al_thickness_mm=0.4,
            source_z_mm=0.0,
        ),
        SimulationCase(
            name="soccerball_cs137_1M" if events is None else f"soccerball_cs137_{n}",
            campaign="reference",
            geometry="soccerball",
            material="BGO",
            events=n,
            source_name="Cs137",
            source_mode="mono",
            source_energy_keV=662.0,
            expected_peaks_keV=[662.0],
            al_thickness_mm=0.4,
            source_z_mm=0.0,
            use_plastic=False,
            plastic_z_mm=0.0,
            source_depth_mm=1.0,
        ),
    ]


def energy_tag(energy_keV: float) -> str:
    if abs(energy_keV - round(energy_keV)) < 1e-9:
        return f"{int(round(energy_keV))}keV"
    return f"{energy_keV:.1f}keV".replace(".", "p")


def cascade_cases(events: int) -> list[SimulationCase]:
    # Energies requested by user. Each source has mono E1, mono E2,
    # mono Esum, plus one radioactive-decay run.
    sources = [
        {
            "key": "nb94",
            "name": "Nb94",
            "ion_z": 41,
            "ion_a": 94,
            "energies": [703.0, 871.1, 1573.0],
        },
        {
            "key": "co60",
            "name": "Co60",
            "ion_z": 27,
            "ion_a": 60,
            "energies": [1173.0, 1332.0, 2505.0],
        },
        {
            "key": "sc46",
            "name": "Sc46",
            "ion_z": 21,
            "ion_a": 46,
            "energies": [889.0, 1120.0, 2009.0],
        },
        {
            "key": "na24",
            "name": "Na24",
            "ion_z": 11,
            "ion_a": 24,
            "energies": [1368.0, 2754.0, 4122.0],
        },
    ]

    cases: list[SimulationCase] = []

    for src in sources:
        for energy in src["energies"]:
            cases.append(
                SimulationCase(
                    name=f"soccerball_nai_chamber2mm_{src['key']}_mono_{energy_tag(energy)}",
                    campaign="cascade",
                    geometry="soccerball",
                    material="NaI",
                    events=events,
                    source_name=src["name"],
                    source_mode="mono",
                    source_energy_keV=energy,
                    expected_peaks_keV=[energy],
                    source_z_mm=0.0,
                    use_plastic=False,
                    plastic_z_mm=0.0,
                    source_depth_mm=1.0,
                    use_soccer_chamber=True,
                    soccer_chamber_outer_radius_mm=70.0,
                    soccer_chamber_halfz_mm=68.5,
                    soccer_chamber_thickness_mm=2.0,
                )
            )

        cases.append(
            SimulationCase(
                name=f"soccerball_nai_chamber2mm_{src['key']}_decay",
                campaign="cascade",
                geometry="soccerball",
                material="NaI",
                events=events,
                source_name=src["name"],
                source_mode="decay",
                expected_peaks_keV=list(src["energies"]),
                ion_z=int(src["ion_z"]),
                ion_a=int(src["ion_a"]),
                ion_q=0,
                ion_excitation_keV=0.0,
                source_z_mm=0.0,
                use_plastic=False,
                plastic_z_mm=0.0,
                source_depth_mm=1.0,
                use_soccer_chamber=True,
                soccer_chamber_outer_radius_mm=70.0,
                soccer_chamber_halfz_mm=68.5,
                soccer_chamber_thickness_mm=2.0,
            )
        )

    return cases


def get_cases(campaign: str, events: int | None) -> list[SimulationCase]:
    if campaign == "reference":
        return reference_cases(events=events)
    if campaign == "cascade":
        return cascade_cases(events=1_000_000 if events is None else events)
    raise ValueError(f"Unsupported campaign: {campaign}")


# ============================================================
# Utility functions
# ============================================================

def format_mm(value: float) -> str:
    return f"{value:.3f} mm"


def macro_path_for(case: SimulationCase) -> Path:
    return MACRO_DIR / f"{case.name}.mac"


def root_path_for(case: SimulationCase) -> Path:
    return ROOT_DIR / f"{case.name}.root"


def log_path_for(case: SimulationCase) -> Path:
    return LOG_DIR / f"{case.name}.log"


def spectrum_path_for(case: SimulationCase) -> Path:
    return SPECTRA_DIR / f"{case.name}.png"


# ============================================================
# Macro generation
# ============================================================

def source_macro_lines(case: SimulationCase) -> str:
    if case.source_mode == "mono":
        if case.source_energy_keV is None:
            raise ValueError(f"Mono case {case.name} requires source_energy_keV.")
        return f"""/gps/particle gamma
/gps/pos/type Point
/gps/pos/centre 0 0 {format_mm(case.source_z_mm)}
/gps/ang/type iso
/gps/ene/type Mono
/gps/ene/mono {case.source_energy_keV:.6f} keV"""

    if case.source_mode == "decay":
        if case.ion_z is None or case.ion_a is None:
            raise ValueError(f"Decay case {case.name} requires ion_z and ion_a.")
        return f"""/gps/particle ion
/gps/ion {case.ion_z} {case.ion_a} {case.ion_q} {case.ion_excitation_keV:.6f}
/gps/pos/type Point
/gps/pos/centre 0 0 {format_mm(case.source_z_mm)}
/gps/ang/type iso
/gps/ene/type Mono
/gps/ene/mono 0.000000 keV"""

    raise ValueError(f"Unsupported source_mode: {case.source_mode}")


def generate_solid_macro(case: SimulationCase) -> str:
    if case.radius_mm is None or case.halfz_mm is None:
        raise ValueError(f"Solid case {case.name} requires radius_mm and halfz_mm.")

    return f"""# ============================================================
# Macro: {case.name}
# Campaign: {case.campaign}
# Geometry: solid cylinder
# Material: {case.material}
# Source: {case.source_name} {case.source_mode}
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
{source_macro_lines(case)}

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_hollow_macro(case: SimulationCase) -> str:
    if case.inner_radius_mm is None or case.thickness_mm is None or case.halfz_mm is None:
        raise ValueError(
            f"Hollow case {case.name} requires inner_radius_mm, thickness_mm, and halfz_mm."
        )

    return f"""# ============================================================
# Macro: {case.name}
# Campaign: {case.campaign}
# Geometry: hollow cylinder
# Material: {case.material}
# Source: {case.source_name} {case.source_mode}
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
/det/alThickness {format_mm(case.al_thickness_mm)}

# Source position
/src/manualZ {format_mm(case.source_z_mm)}

# Initialize
/run/initialize

# Source setup
{source_macro_lines(case)}

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_soccerball_macro(case: SimulationCase) -> str:
    use_plastic_text = "true" if case.use_plastic else "false"
    use_chamber_text = "true" if case.use_soccer_chamber else "false"

    chamber_lines = ""
    if case.use_soccer_chamber:
        chamber_lines = f"""
# Central aluminum chamber
/det/useSoccerChamber {use_chamber_text}
/det/soccerChamberOuterRadius {format_mm(case.soccer_chamber_outer_radius_mm)}
/det/soccerChamberHalfZ {format_mm(case.soccer_chamber_halfz_mm)}
/det/soccerChamberThickness {format_mm(case.soccer_chamber_thickness_mm)}
""".strip()
    else:
        chamber_lines = f"/det/useSoccerChamber {use_chamber_text}"

    return f"""# ============================================================
# Macro: {case.name}
# Campaign: {case.campaign}
# Geometry: soccerball / near-4pi modular detector
# Material: {case.material}
# Source: {case.source_name} {case.source_mode}
# Events: {case.events}
# ============================================================

/control/verbose 1
/run/verbose 1
/event/verbose 0
/tracking/verbose 0

# Detector setup
/det/material {case.material}
/det/geometry soccerball

{chamber_lines}

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
{source_macro_lines(case)}

# Output
/analysis/setFileName events

# Run
/run/beamOn {case.events}
"""


def generate_macro(case: SimulationCase) -> Path:
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


def generate_cases(cases: list[SimulationCase]) -> list[Path]:
    return [generate_macro(case) for case in cases]


# ============================================================
# Simulation running
# ============================================================

def run_case(case: SimulationCase, dry_run: bool = False) -> None:
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
    print(f"CAMPAIGN: {case.campaign}")
    print(f"GEOMETRY: {case.geometry}")
    print(f"MATERIAL: {case.material}")
    print(f"SOURCE: {case.source_name} {case.source_mode}")
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

    produced_root_candidates = [
        BUILD_DIR / "events.root",
        PROJECT_ROOT / "events.root",
    ]

    for produced_root in produced_root_candidates:
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

    produced_root = next((p for p in produced_root_candidates if p.exists()), None)

    if produced_root is None:
        expected = " or ".join(str(p) for p in produced_root_candidates)
        raise FileNotFoundError(
            f"ROOT file was not produced for case {case.name}.\n"
            f"Expected: {expected}\n"
            f"Check log: {final_log_path}\n"
            f"Exit code: {completed.returncode}"
        )

    if final_root_path.exists():
        final_root_path.unlink()

    shutil.move(str(produced_root), str(final_root_path))

    print(f"Saved ROOT: {final_root_path}")
    print(f"Saved log : {final_log_path}")
    print(f"Exit code : {completed.returncode}")


def run_cases(cases: list[SimulationCase], dry_run: bool = False) -> None:
    for case in cases:
        run_case(case, dry_run=dry_run)


# ============================================================
# Analysis
# ============================================================

def analyze_root_file(
    case: SimulationCase,
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
                "campaign": case.campaign,
                "geometry": case.geometry,
                "material": case.material,
                "source": case.source_name,
                "source_mode": case.source_mode,
                "events": case.events,
                "expected_peak_keV": peak,
                "peak_window_keV": peak_window_keV,
                "peak_counts": peak_counts,
                "peak_efficiency": peak_counts / case.events,
                "peak_efficiency_percent": 100.0 * peak_counts / case.events,
                "total_nonzero_counts": total_nonzero,
                "total_detection_efficiency": total_nonzero / case.events,
                "total_detection_efficiency_percent": 100.0 * total_nonzero / case.events,
                "root_file": safe_rel(root_path),
                "spectrum_file": safe_rel(spectrum_path_for(case)),
            }
        )

    # Make spectrum
    if len(nonzero) > 0:
        xmax = max(float(np.max(nonzero)), max(case.expected_peaks_keV) + 200.0)
    else:
        xmax = max(case.expected_peaks_keV) + 200.0

    bins = np.arange(0.0, xmax + bin_width_keV, bin_width_keV)

    plt.figure(figsize=(6.8, 5.0))

    counts, edges = np.histogram(nonzero, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    ax = plt.gca()
    ax.plot(centers, counts, linewidth=0.9)

    ax.set_yscale("log")
    ax.set_xlabel("Energy deposited in crystal (keV)", fontsize=12)
    ax.set_ylabel("Counts", fontsize=12)

    geometry_label = {
        "solid": "Solid detector",
        "hollow": "Hollow detector",
        "soccerball": "Near-4π detector",
    }.get(case.geometry, case.geometry)

    ax.set_title(
        f"{case.material} {geometry_label}, {case.source_name} {case.source_mode}, {case.events:,} events",
        fontsize=12,
        pad=12,
    )

    xmax_plot = max(case.expected_peaks_keV) + 200.0
    ax.set_xlim(0, xmax_plot)

    positive_counts = counts[counts > 0]
    if len(positive_counts) > 0:
        ymin = max(1, positive_counts.min() * 0.7)
        ymax = positive_counts.max() * 3.0
        ax.set_ylim(ymin, ymax)

    ymin, ymax = ax.get_ylim()
    label_y = ymax / 1.7

    for peak in case.expected_peaks_keV:
        ax.axvline(
            peak,
            color="black",
            linewidth=0.9,
            linestyle=":",
            zorder=1,
        )

        ax.text(
            peak + 12,
            label_y,
            f"{peak:.0f}",
            ha="left",
            va="bottom",
            fontsize=10,
        )

    ax.tick_params(axis="both", which="both", direction="in")
    ax.tick_params(axis="both", which="major", labelsize=11, length=5)
    ax.tick_params(axis="both", which="minor", length=3)

    for spine in ax.spines.values():
        spine.set_linewidth(1.0)

    plt.tight_layout()

    spec_path = spectrum_path_for(case)
    plt.savefig(spec_path, dpi=300)
    plt.close()

    wide_row = {
        "case_name": case.name,
        "campaign": case.campaign,
        "geometry": case.geometry,
        "material": case.material,
        "source": case.source_name,
        "source_mode": case.source_mode,
        "events": case.events,
        "total_nonzero_counts": total_nonzero,
        "total_detection_efficiency": total_nonzero / case.events,
        "total_detection_efficiency_percent": 100.0 * total_nonzero / case.events,
        "root_file": safe_rel(root_path),
        "spectrum_file": safe_rel(spec_path),
    }

    for row in long_rows:
        peak_label = f"peak_{str(row['expected_peak_keV']).replace('.', 'p')}_counts"
        wide_row[peak_label] = row["peak_counts"]
        wide_row[peak_label.replace("_counts", "_efficiency_percent")] = row[
            "peak_efficiency_percent"
        ]

    return long_rows, wide_row


def analyze_cases(
    cases: list[SimulationCase],
    campaign: str,
    peak_window_keV: float = 20.0,
    bin_width_keV: float = 2.0,
) -> None:
    ensure_directories()

    all_long_rows = []
    all_wide_rows = []

    for case in cases:
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

    long_csv = TABLE_DIR / f"{campaign}_summary_long.csv"
    wide_csv = TABLE_DIR / f"{campaign}_summary_wide.csv"
    xlsx = TABLE_DIR / f"{campaign}_summary.xlsx"

    long_df.to_csv(long_csv, index=False)
    wide_df.to_csv(wide_csv, index=False)

    try:
        with pd.ExcelWriter(xlsx) as writer:
            long_df.to_excel(writer, sheet_name="long", index=False)
            wide_df.to_excel(writer, sheet_name="wide", index=False)
        wrote_xlsx = True
    except Exception as exc:
        print(f"Warning: could not write XLSX: {exc}")
        wrote_xlsx = False

    print(f"Saved: {long_csv}")
    print(f"Saved: {wide_csv}")
    if wrote_xlsx:
        print(f"Saved: {xlsx}")


# ============================================================
# Dry-run preview
# ============================================================

def dry_run_cases(cases: list[SimulationCase]) -> None:
    """Print what would happen without creating, modifying, or deleting files."""
    for case in cases:
        macro_path = macro_path_for(case)
        final_root_path = root_path_for(case)
        final_log_path = log_path_for(case)
        command = [str(EXECUTABLE), str(macro_path)]

        print()
        print("=" * 70)
        print(f"CASE: {case.name}")
        print(f"CAMPAIGN: {case.campaign}")
        print(f"GEOMETRY: {case.geometry}")
        print(f"MATERIAL: {case.material}")
        print(f"SOURCE: {case.source_name} {case.source_mode}")
        print(f"EVENTS: {case.events}")
        print(f"WOULD WRITE MACRO: {macro_path}")
        print(f"WOULD RUN COMMAND: {' '.join(command)}")
        print(f"WOULD SAVE ROOT: {final_root_path}")
        print(f"WOULD SAVE LOG : {final_log_path}")
        print("DRY RUN: no files were written and Geant4 was not executed.")


# ============================================================
# CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified Geant4-Python detector simulation pipeline"
    )

    parser.add_argument(
        "--campaign",
        choices=["reference", "cascade"],
        default=None,
        help="Campaign to run. Use 'reference' for Cs-137 cases or 'cascade' for Nb-94/Co-60/Sc-46/Na-24.",
    )

    parser.add_argument(
        "--reference",
        action="store_true",
        help="Backward-compatible shortcut for --campaign reference.",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output base directory. If omitted, uses macros/generated and results/.",
    )

    parser.add_argument(
        "--events",
        type=int,
        default=None,
        help="Number of events per case. Defaults: reference=1,000,000; cascade=1,000,000.",
    )

    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate macros for the selected campaign.",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Run simulations for the selected campaign.",
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze ROOT files and create spectra/tables for the selected campaign.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate macros, run simulations, and analyze outputs.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview campaign actions without writing files or executing simulations.",
    )

    parser.add_argument(
        "--peak-window-kev",
        type=float,
        default=20.0,
        help="Half-width of peak counting window in keV.",
    )

    parser.add_argument(
        "--bin-width-kev",
        type=float,
        default=2.0,
        help="Spectrum bin width in keV.",
    )

    args = parser.parse_args()

    campaign = args.campaign
    if args.reference:
        campaign = "reference"

    if campaign is None:
        print("Select a campaign with --campaign reference, --campaign cascade, or --reference.")
        parser.print_help()
        return

    configure_output_paths(args.output_dir)
    cases = get_cases(campaign, events=args.events)

    if args.all:
        args.generate = True
        args.run = True
        args.analyze = True

    print(f"Campaign   : {campaign}")
    print(f"Cases      : {len(cases)}")
    print(f"Output base: {RESULTS_DIR}")
    print(f"Macro dir  : {MACRO_DIR}")
    print(f"Root dir   : {ROOT_DIR}")
    print(f"Log dir    : {LOG_DIR}")
    print(f"Table dir  : {TABLE_DIR}")
    print(f"Spectra dir: {SPECTRA_DIR}")

    if args.dry_run:
        dry_run_cases(cases)
        return

    if args.generate:
        generate_cases(cases)

    if args.run:
        run_cases(cases, dry_run=False)

    if args.analyze:
        analyze_cases(
            cases,
            campaign=campaign,
            peak_window_keV=args.peak_window_kev,
            bin_width_keV=args.bin_width_kev,
        )

    if not any([args.generate, args.run, args.analyze, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
