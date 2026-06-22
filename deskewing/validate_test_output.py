#!/usr/bin/env python3
"""Validation script for dOPM deskewing pipeline test runs."""

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import h5py
import yaml


def validate_maxproj_output(output_dir):
    """Validate maxproj mode output (TIFFs)."""
    if not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}")
        return False
    
    tiff_files = [f for f in os.listdir(output_dir) if f.lower().endswith('.tif')]
    print(f"OK: Max-projection output: {len(tiff_files)} TIFF files generated")
    
    if len(tiff_files) > 0:
        sample = tiff_files[0]
        print(f"  - Sample file: {sample}")
        return True
    return False


def validate_bdv_dataset(xml_file):
    """Validate that a BDV XML and its matching HDF5 file exist and are readable."""
    h5_file = os.path.splitext(xml_file)[0] + '.h5'

    xml_exists = os.path.exists(xml_file)
    h5_exists = os.path.exists(h5_file)

    if xml_exists:
        print(f"  - XML metadata: {xml_file}")
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            views = root.findall('.//ViewSetup')
            print(f"    └─ XML root: {root.tag}")
            print(f"    └─ Contains {len(views)} view setups")
        except Exception as e:
            print(f"    └─ XML parse error: {e}")
            return False
    else:
        print(f"  - ERROR: XML metadata not found: {xml_file}")
        return False

    if h5_exists:
        file_size_gb = os.path.getsize(h5_file) / (1024**3)
        print(f"  - HDF5 data: {h5_file}")
        print(f"    └─ Size: {file_size_gb:.2f} GB")

        try:
            with h5py.File(h5_file, 'r') as f:
                print(f"    └─ HDF5 structure: {list(f.keys())}")
                for time_key in list(f.keys())[:2]:
                    print(f"       - {time_key}: {list(f[time_key].keys())}")
        except Exception as e:
            print(f"    └─ HDF5 read error: {e}")
            return False
    else:
        print(f"  - ERROR: HDF5 data not found: {h5_file}")
        return False

    return xml_exists and h5_exists


def validate_deskew_output(output_dir, well_id, registered=False):
    """Validate deskew mode output (BDV dataset)."""
    if not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}")
        return False

    suffix = '_registered' if registered else ''
    xml_file = os.path.join(output_dir, f'dataset_Well{well_id}{suffix}.xml')

    print("OK: Deskew output:")
    return validate_bdv_dataset(xml_file)


def validate_bead_output(output_dir, xml_path):
    """Validate bead registration output as a BDV XML/H5 dataset."""
    if not os.path.isdir(output_dir):
        print(f"ERROR: Bead output directory does not exist: {output_dir}")
        return False

    if not xml_path:
        print("ERROR: No bead registration XML path was provided")
        return False

    print("OK: Bead registration BDV output:")
    return validate_bdv_dataset(xml_path)


def validate_fusion_output(output_dir):
    """Validate fusion mode output (fused TIFF stacks from Fiji)."""
    if not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}")
        return False
    
    tiff_files = [f for f in os.listdir(output_dir) if f.lower().endswith('.tif')]
    print(f"OK: Fusion output: {len(tiff_files)} fused TIFF stacks generated")
    
    if len(tiff_files) > 0:
        total_size_gb = sum(os.path.getsize(os.path.join(output_dir, f)) for f in tiff_files) / (1024**3)
        print(f"  - Total size: {total_size_gb:.2f} GB")
        print(f"  - Pattern: fused_tile_[tile]_fused_tp_[timepoint]_ch_[channel].tif")
        print(f"  - Sample files:")
        for f in sorted(tiff_files)[:5]:
            size_mb = os.path.getsize(os.path.join(output_dir, f)) / (1024**2)
            print(f"    └─ {f} ({size_mb:.1f} MB)")
        return True
    return False


def parse_args():
    parser = argparse.ArgumentParser(description='Validate dOPM test outputs.')
    parser.add_argument('--config', help='Optional YAML config file to infer deskew and fusion paths')
    parser.add_argument('--run-pipeline', action='store_true',
                        help='Run the pipeline using the config before validation')
    parser.add_argument('--data-root', default=r'D:\temp\test_data',
                        help='Base folder for test data and generated outputs')
    parser.add_argument('--maxproj', default=None,
                        help='Raw max-projection output directory')
    parser.add_argument('--deskew', default=None,
                        help='Deskew BDV output directory')
    parser.add_argument('--bead-output', default=None,
                        help='Bead registration output directory')
    parser.add_argument('--registration-xml', default=None,
                        help='Path to bead BDV XML used for registration transforms')
    parser.add_argument('--fusion-xml', default=None,
                        help='Path to the BDV XML used by fusion')
    parser.add_argument('--fusion-binning', type=int, default=2,
                        help='Fusion binning factor used to determine output folder')
    parser.add_argument('--well-id', default='F5', help='Well identifier for deskew dataset')
    parser.add_argument('--processing-mode', default=None,
                        help='Explicit processing mode to use for validation')
    args = parser.parse_args()

    if args.maxproj is None:
        args.maxproj = os.path.join(args.data_root, 'sample_output_F5')
    if args.deskew is None:
        args.deskew = os.path.join(args.data_root, 'sample_output_F5_deskew')
    if args.bead_output is None:
        args.bead_output = os.path.join(args.data_root, 'bead_output')
    if args.registration_xml is None:
        args.registration_xml = os.path.join(args.bead_output, 'dataset_WellF5.xml')
    if args.fusion_xml is None:
        args.fusion_xml = None
    if args.processing_mode is None:
        args.processing_mode = None

    return args


def run_pipeline(config_path):
    root = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(root, 'deskewing_pipeline', 'scripts')

    register_script = os.path.join(scripts_dir, 'register_beads_pipeline.py')
    process_script = os.path.join(scripts_dir, 'process_plate.py')
    fuse_script = os.path.join(scripts_dir, 'fuse_plate.py')

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    processing_mode = config.get('processing', {}).get('mode', 'maxproj')
    registration_cfg = config.get('registration', {})
    fusion_cfg = config.get('fusion', {})
    reg_xml_path = registration_cfg.get('registered_bead_xml_path')
    auto_register = registration_cfg.get('auto_register', True)

    if processing_mode == 'deskew_with_beads':
        if not reg_xml_path:
            raise ValueError(
                'Config must specify registration.registered_bead_xml_path for deskew_with_beads mode. '
                'This should point to the bead BDV XML, for example bead_output/dataset_WellC2.xml.'
            )

        if os.path.exists(reg_xml_path):
            print(f"INFO: Using existing bead registration XML: {reg_xml_path}")
        elif auto_register:
            print(f"INFO: Bead registration XML not found at {reg_xml_path}")
            print("INFO: Running bead conversion and Fiji registration first.")
            subprocess.run([sys.executable, register_script, '--config', config_path], check=True)
            if not os.path.exists(reg_xml_path):
                raise FileNotFoundError(
                    f"Bead registration completed, but expected XML was not found: {reg_xml_path}"
                )
        else:
            raise FileNotFoundError(
                f"Registration XML not found: {reg_xml_path}. "
                "Set registration.auto_register: true or generate it first with register_beads_pipeline.py."
            )

    print(f"INFO: Running pipeline with config: {config_path}")
    subprocess.run([sys.executable, process_script, '--config', config_path], check=True)

    if processing_mode in {'deskew', 'deskew_with_beads'} and fusion_cfg.get('bdv_dataset_xml'):
        subprocess.run([sys.executable, fuse_script, '--config', config_path], check=True)
    else:
        print('INFO: No fusion step requested for this processing mode/config.')

    print('OK: Pipeline run complete.')


def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    values = {}
    data_cfg = config.get('data', {}) if config else {}
    fusion_cfg = config.get('fusion', {}) if config else {}
    processing_cfg = config.get('processing', {}) if config else {}
    bead_cfg = config.get('bead_data', {}) if config else {}
    registration_cfg = config.get('registration', {}) if config else {}

    if data_cfg.get('output_path'):
        values['deskew'] = data_cfg.get('output_path')
        if processing_cfg.get('mode') == 'maxproj':
            values['maxproj'] = data_cfg.get('output_path')

    if bead_cfg.get('output_path'):
        values['bead_output'] = bead_cfg.get('output_path')
    if registration_cfg.get('registered_bead_xml_path'):
        values['registration_xml'] = registration_cfg.get('registered_bead_xml_path')

    if fusion_cfg.get('binning') is not None:
        values['fusion_binning'] = fusion_cfg.get('binning')
    if fusion_cfg.get('bdv_dataset_xml'):
        values['fusion_xml'] = fusion_cfg.get('bdv_dataset_xml')

    pipeline_cfg = config.get('pipeline_settings', {}) if config else {}
    if pipeline_cfg.get('well_id'):
        values['well_id'] = pipeline_cfg.get('well_id')

    if processing_cfg.get('mode'):
        values['processing_mode'] = processing_cfg.get('mode')

    return values


if __name__ == '__main__':
    args = parse_args()

    if args.config:
        cfg_values = load_config(args.config)
        args.deskew = cfg_values.get('deskew', args.deskew)
        args.maxproj = cfg_values.get('maxproj', args.maxproj)
        args.bead_output = cfg_values.get('bead_output', args.bead_output)
        args.registration_xml = cfg_values.get('registration_xml', args.registration_xml)
        args.fusion_binning = cfg_values.get('fusion_binning', args.fusion_binning)
        args.processing_mode = cfg_values.get('processing_mode', None)
        args.fusion_xml = cfg_values.get('fusion_xml', None)
        args.well_id = cfg_values.get('well_id', args.well_id)

    mode = getattr(args, 'processing_mode', None) or 'maxproj'

    if args.run_pipeline:
        if not args.config:
            raise ValueError('Running the pipeline requires --config to be specified.')
        run_pipeline(args.config)

    if args.fusion_xml:
        fusion_output_dir = os.path.join(os.path.dirname(args.fusion_xml), f'fused_binning_{args.fusion_binning}')
    else:
        fusion_output_dir = os.path.join(args.deskew, f'fused_binning_{args.fusion_binning}')

    print("=" * 60)
    print("dOPM Deskewing Pipeline - Comprehensive Validation Report")
    print("=" * 60)

    if mode == 'maxproj':
        print("\n1.  MAX-PROJECTION MODE (Raw ND2 → TIFFs)")
        print("-" * 60)
        maxproj_ok = validate_maxproj_output(args.maxproj)

        print("\n" + "=" * 60)
        if maxproj_ok:
            print("OK: Max-projection output validated successfully!")
        else:
            print("WARNING: Max-projection validation failed")
            raise SystemExit(1)

    elif mode == 'deskew':
        print("\n1.  DESKEW MODE (ND2 → BDV dataset with geometry)")
        print("-" * 60)
        deskew_ok = validate_deskew_output(args.deskew, args.well_id)

        print("\n2.  FUSION MODE (BDV dataset → fused TIFF stacks via Fiji)")
        print("-" * 60)
        fusion_ok = validate_fusion_output(fusion_output_dir)

        print("\n" + "=" * 60)
        if deskew_ok and fusion_ok:
            print("OK: Deskew + fusion validated successfully!")
        else:
            print("WARNING: Validation completed with issues:")
            if not deskew_ok:
                print("  - Deskew validation failed")
            if not fusion_ok:
                print("  - Fusion validation failed")
            raise SystemExit(1)

    elif mode == 'deskew_with_beads':
        print("\n1.  BEAD REGISTRATION MODE")
        print("-" * 60)
        bead_ok = validate_bead_output(args.bead_output, args.registration_xml)

        print("\n2.  DESKEW MODE (ND2 → BDV dataset with geometry + bead transforms)")
        print("-" * 60)
        deskew_ok = validate_deskew_output(args.deskew, args.well_id, registered=True)

        print("\n3.  FUSION MODE (BDV dataset → fused TIFF stacks via Fiji)")
        print("-" * 60)
        fusion_ok = validate_fusion_output(fusion_output_dir)

        print("\n" + "=" * 60)
        if bead_ok and deskew_ok and fusion_ok:
            print("OK: Bead registration, registered deskew and fusion validated successfully!")
        else:
            print("WARNING: Validation completed with issues:")
            if not bead_ok:
                print("  - Bead registration validation failed")
            if not deskew_ok:
                print("  - Registered deskew validation failed")
            if not fusion_ok:
                print("  - Fusion validation failed")
            raise SystemExit(1)

    else:
        print(f"\nWARNING: Unknown processing mode: {mode}. Skipping validation.")
        sys.exit(1)
