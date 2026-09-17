# SHM Building Monitoring — Instrumented Building Response

Time-history and ambient-vibration analysis of an instrumented five-story building on the Sharif University campus, combining ETABS design data, OpenSees nonlinear simulation, and accelerometer measurements.

## Overview

The project documents the full SHM pipeline for a real building: geometry from ETABS, conversion to an OpenSees fibre/elastic model, ground-motion scaling per Iranian Standard 2800, nonlinear time-history analysis, and signal processing of ambient tests recorded with ACCULN sensors.

## Research Problem

Predicting and interpreting the dynamic response of an existing building requires reconciling design information, numerical simulation, and measured data. The repository shows how to move from ETABS geometry to a validated OpenSees model and to extract modal and response information from field records.

## Methodology

- **ETABS → OpenSees:** `models/etabs/Civil_SUT_Geometry_Modified.e2k` converted via the geometry and load tables (`models/opensees/Geometry.xlsx`, `Load.xlsx`) into `Civil_SUT.py`. The OpenSees model represents the SUT CE Department building (5 stories).
- **Ground motions:** Scaled PEER records (`data/ground_motions/*_Scaled.txt`) using `src/scale_records/S2800V5.m` per Standard 2800.
- **Nonlinear THA:** `models/opensees/Civil_SUT.py` runs time-history analysis; outputs `THA_Results/*_response.csv` and roof plots.
- **Ambient identification:** ACCULN recordings `data/ambient/East001_5th.npz` (and `SUT-001-* .mat` originals) processed with `src/signal_processing/main.py` (filtering, FFT, modal identification).

## Features

- ETABS geometry translation with story and member definitions
- OpenSeesPy time-history driver with scaled record handling
- ACCULN binary-to-decimal conversion and ambient signal processing
- Representative ground-motion and roof response plots
- Small reproducible sample dataset (two scaled motions, one ambient record)

## Project Structure

```
models/
  etabs/            # Civil_SUT_Geometry_Modified.e2k (sample)
  opensees/         # Civil_SUT.py, Civil_SUT.ipynb, Geometry.xlsx
data/
  ground_motions/   # A-TMZ000_Scaled.txt, A-TMZ270_Scaled.txt (samples)
  ambient/          # East001_5th.npz (sample)
src/
  signal_processing/# main.py, main.ipynb
  scale_records/    # S2800V5.m, Design_Spectrum_Data.txt
results/figures/    # A-TMZ*_roof_*.png, *_response.csv samples
```

## Requirements

- Python 3.10+ with `openseespy`, `numpy`, `pandas`, `matplotlib`, `scipy`
- MATLAB R2020+ (for `S2800V5.m`) or Octave — only needed for spectrum scaling
- ETABS 20+ if regenerating the original `.e2k`

## Installation

```bash
pip install openseespy numpy pandas matplotlib scipy
```

MATLAB toolboxes: none beyond base (signal processing optional for `main.ipynb` FFT).

## Usage

Run the OpenSees model (after placing a scaled record in `data/ground_motions`):

```bash
python models/opensees/Civil_SUT.py
```

Process ambient data:

```bash
python src/signal_processing/main.py
# or
jupyter notebook src/signal_processing/main.ipynb
```

Scale a new record per 2800:

```matlab
% In MATLAB:
S2800V5
```

## Results - Linear

- `results/figures/A-TMZ000_Scaled_roof_acc.png` — roof acceleration for scaled Tabas
- `results/figures/A-TMZ000_Scaled_ground_motion.png` — input motion
- Response CSVs in `results/figures/*.csv` allow direct comparison of simulation vs ambient-identified periods.

## Results - Nonlinear

- `results/figures/A-TMZ000_Scaled_roof_acc.png` — roof acceleration for scaled Tabas
- `results/figures/A-TMZ000_Scaled_ground_motion.png` — input motion
- Response CSVs in `results/figures/*.csv` allow direct comparison of simulation vs ambient-identified periods.

## Limitations

- soil–structure interaction and non-structural components are not modelled.
- Ambient records are short samples; full operational modal analysis requires longer datasets and outlier handling.
- ETABS–OpenSees translation is manual and specific to this building; generalization needs adapter work.

## Future Work

- Model updating against ambient-identified frequencies
- Automated damage-feature extraction and sensor placement optimization

## Author

Mohammad Shamsi — Sharif University of Technology, Structural Engineering
