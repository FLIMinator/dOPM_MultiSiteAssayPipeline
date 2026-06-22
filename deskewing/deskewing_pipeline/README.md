# dOPM Deskewing Pipeline

This folder contains YAML configs and wrapper scripts for validating the dOPM deskewing, bead-registration, and fusion pipeline.

The pipeline supports:

```text
1. Geometric-only deskew
2. Bead registration followed by bead-registered sample deskew
3. Fiji/BigStitcher fusion of BDV datasets
```

## Test data

The local validation configs assume the test data are unpacked here:

```text
D:\temp\test_data
```

Test data are available from:

```text
https://imperialcollegelondon.box.com/s/g2gcl5hudoosoxwfb4xcan5javiytj99
```

Expected layout:

```text
D:\temp\test_data
├── data
│   ├── spim_Time0000_Tile0000_angle0__WellF5.nd2
│   ├── spim_Time0000_Tile0000_angle70__WellF5.nd2
│   ├── spim_Time0000_Tile0001_angle0__WellF5.nd2
│   ├── spim_Time0000_Tile0001_angle70__WellF5.nd2
│   ├── spim_Time0000_Tile0002_angle0__WellF6.nd2
│   ├── spim_Time0000_Tile0002_angle70__WellF6.nd2
│   ├── spim_Time0001_Tile0000_angle0__WellF5.nd2
│   ├── spim_Time0001_Tile0000_angle70__WellF5.nd2
│   ├── spim_Time0001_Tile0001_angle0__WellF5.nd2
│   ├── spim_Time0001_Tile0001_angle70__WellF5.nd2
│   ├── spim_Time0001_Tile0002_angle0__WellF6.nd2
│   └── spim_Time0001_Tile0002_angle70__WellF6.nd2
├── v1
│   ├── spim_Time0000_Tile0000_angle0.nd2
│   └── spim_Time0000_Tile0000_angle70.nd2
└── v2
    ├── spim_Time0000_Tile0000_angle0__WellC2.nd2
    └── spim_Time0000_Tile0000_angle70__WellC2.nd2
```

The folders are used as follows:

```text
data/
    Sample data. The validation configs process WellF5.

v2/
    Bead data with a Well suffix: __WellC2.

v1/
    Bead data without a Well suffix. This is treated as one logical bead well, C2.
```

## Fiji

The configs require a local Fiji/ImageJ installation.

This pipeline was validated with Fiji/ImageJ 2.9.0 on Windows:

```text
https://downloads.imagej.net/fiji/releases/2.9.0/fiji-2.9.0-win64.zip
```

After unzipping Fiji, update `fiji_executable_path` in the YAML configs, for example:

```yaml
fiji_executable_path: C:\Users\User\Documents\GitHub\dopm_processing\fiji-2.9.0-win64\Fiji.app\ImageJ-win64.exe
```

Fiji is used for:

```text
1. Bead interest-point detection
2. Bead registration
3. BigStitcher fusion of BDV datasets
```

## Validation configs

Run all commands from the repository root.

### 1. Geometry-only deskew

Config:

```text
deskewing_pipeline\configs\test_pipeline.yaml
```

Run:

```powershell
python validate_test_output.py --config deskewing_pipeline\configs\test_pipeline.yaml --run-pipeline
```

This processes sample data from:

```text
D:\temp\test_data\data
```

and creates a geometric BDV dataset for:

```text
WellF5
```

Expected output:

```text
D:\temp\test_data\sample_output_F5_deskew\dataset_WellF5.xml
D:\temp\test_data\sample_output_F5_deskew\dataset_WellF5.h5
```

### 2. Bead-registered deskew using Well-tagged bead files

Config:

```text
deskewing_pipeline\configs\test_pipeline_with_beads.yaml
```

Run:

```powershell
python validate_test_output.py --config deskewing_pipeline\configs\test_pipeline_with_beads.yaml --run-pipeline
```

This uses bead files from:

```text
D:\temp\test_data\v2
```

and creates/registers:

```text
D:\temp\test_data\bead_output_C2\dataset_WellC2.xml
```

The sample data from `data/WellF5` are then converted using the bead registration transforms.

Expected registered sample output:

```text
D:\temp\test_data\sample_output_F5_deskew_with_beads\dataset_WellF5_registered.xml
D:\temp\test_data\sample_output_F5_deskew_with_beads\dataset_WellF5_registered.h5
```

### 3. Bead-registered deskew using well-less bead files

Config:

```text
deskewing_pipeline\configs\test_pipeline_with_beads_wellless.yaml
```

Run:

```powershell
python validate_test_output.py --config deskewing_pipeline\configs\test_pipeline_with_beads_wellless.yaml --run-pipeline
```

This uses bead files from:

```text
D:\temp\test_data\v1
```

These filenames do not contain a `WellXX` suffix, so the config enables:

```yaml
allow_wellless_filenames: true
```

and treats the folder as one logical bead well:

```yaml
bead_well_id: C2
```

Expected bead XML:

```text
D:\temp\test_data\bead_output_C2_wellless\dataset_WellC2.xml
```

## Important config fields

### Sample well

```yaml
pipeline_settings:
  well_id: F5
```

This is the sample well processed from `data/`.

### Bead well

```yaml
pipeline_settings:
  bead_well_id: C2
```

This is the logical bead well used for bead XML output naming.

### Well-less filenames

Use this only when the input folder contains one logical dataset and filenames do not include `WellXX`:

```yaml
allow_wellless_filenames: true
```

When disabled, filenames must include `_WellXX` or `__WellXX`.

### Bead calibration

The bead XML calibration/geometric rows are defined by `bead_data.hardcoded_vars`. These values are important and should be set deliberately.

Example:

```yaml
bead_data:
  type: "remote_scanning"
  hardcoded_vars:
    pix_x: 0.35
    mirror_tilt: 17.5
```

If `bead_data.hardcoded_vars` is not provided, the scripts may fall back to `deskewing.hardcoded_vars`.

## Output validation

`validate_test_output.py` checks:

```text
1. Bead BDV XML/H5 output, where relevant
2. Sample BDV XML/H5 output
3. Fused TIFF stacks, where fusion is configured
```

A successful full bead-registered run ends with:

```text
OK: All three modes validated successfully!
```

## Rerunning tests

If you want to force bead registration or fusion to rerun, delete the corresponding output folder before running validation again.

Examples:

```powershell
Remove-Item -Recurse -Force D:\temp\test_data\bead_output_C2
Remove-Item -Recurse -Force D:\temp\test_data\sample_output_F5_deskew_with_beads
```

