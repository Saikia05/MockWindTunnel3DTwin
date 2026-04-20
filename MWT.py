"""

ONLY FOR FBX CONVERSION
fbx_converter.py
================
Load an FBX file (v7400 binary or ASCII), inspect its scene graph,
extract mesh geometry and materials, then export to OBJ and/or PLY.

"""

import os
import sys

# We attempt to import bpy to determine if this script is running INSIDE Blender's python environment
try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

if IN_BLENDER:
    # ---------------------------------------------------------
    # BLENDER EXPORTER LOGIC (Executes internally via Blender)
    # ---------------------------------------------------------
    def export_to_fbx(output_path):
        print(f"--- Starting export to {output_path} ---")
        
        try:
            # Ensure all objects are deselected, then select meshes and armatures
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.context.scene.objects:
                if obj.type in {'MESH', 'ARMATURE'}:
                    obj.select_set(True)
        except Exception as e:
            print(f"Error selecting objects: {e}")
            raise e
        
        try:
            # CAD-compatible FBX settings
            bpy.ops.export_scene.fbx(
                filepath=output_path,
                use_selection=True,                     
                global_scale=1.0,                       
                apply_unit_scale=True,                  
                apply_scale_options='FBX_SCALE_ALL',    
                use_mesh_modifiers=True,                
                mesh_smooth_type='FACE',                
                object_types={'MESH', 'ARMATURE'},      
                axis_forward='-Z',                      
                axis_up='Y',                            
                use_custom_props=True,                  
                bake_anim=False                         
            )
        except Exception as e:
            print(f"Error during FBX export operation: {e}")
            raise e
            
        print(f"--- Export finished successfully: {output_path} ---")

    if __name__ == "__main__":
        try:
            argv = sys.argv
            if "--" not in argv:
                raise ValueError("No custom arguments found after '--'.")
            
            args = argv[argv.index("--") + 1:]
            if not args:
                raise ValueError("Output path not provided.")
                
            output_filepath = os.path.abspath(args[0])
            export_to_fbx(output_filepath)
        except ValueError as ve:
            print(f"Usage Error: {ve}")
            sys.exit(1)
        except Exception as e:
            print(f"Critical error during custom export script execution: {e}")
            sys.exit(1)

else:
    # ---------------------------------------------------------
    # AGENT WRAPPER LOGIC (Executes normally via host machine)
    # ---------------------------------------------------------
    import argparse
    import subprocess
    from pathlib import Path

    # 1. Custom Error Types (Four or five error handlers)
    class BlenderNotFoundError(Exception):
        """Raised when the Blender executable cannot be located."""
        pass
        
    class InvalidBlendFileError(Exception):
        """Raised when the input file is not a valid or accessible .blend file."""
        pass
        
    class ExportFailedError(Exception):
        """Raised when the Blender subprocess returns an error code."""
        pass

    class OutputDirectoryError(Exception):
        """Raised when there is a permissions or path issue with the output directory."""
        pass

    # 2. Convenient Tools / Helper Functions
    def locate_blender(custom_path=None):
        """Utility to find the blender executable."""
        if custom_path:
            if not os.path.exists(custom_path):
                raise BlenderNotFoundError(f"Provided Blender path does not exist: {custom_path}")
            return custom_path
        return "blender"

    def is_valid_blend_file(filepath: Path) -> bool:
        """Utility to check if a file is explicitly a .blend file."""
        return filepath.is_file() and filepath.suffix.lower() == ".blend"

    def ensure_output_directory(output_path: Path):
        """Utility to ensure output directories exist, with error handling."""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise OutputDirectoryError(f"Permission denied creating directory: {output_path}")
        except Exception as e:
            raise OutputDirectoryError(f"Failed to create directory {output_path}: {e}")

    def convert_blend_to_fbx(input_path: Path, output_path: Path, blender_path: str, script_path: Path):
        """Core utility function for doing a single conversion."""
        print(f"[*] Processing: {input_path}")
        
        if not is_valid_blend_file(input_path):
            raise InvalidBlendFileError(f"Invalid input file (not a .blend file or doesn't exist): {input_path}")
            
        command = [
            blender_path,
            "-b",                    
            str(input_path),         
            "-P",                    
            str(script_path),
            "--",                    
            str(output_path)         
        ]
        
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            print(f"[+] Successfully converted to: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to convert {input_path}")
            print(f"--- stderr ---\n{e.stderr.strip()}")
            raise ExportFailedError(f"Blender subprocess failed with code {e.returncode}")
        except FileNotFoundError:
            raise BlenderNotFoundError("Blender executable not found. Make sure it's in your system PATH or provide it manually.")
        except PermissionError:
            raise ExportFailedError(f"Permission denied when trying to execute/write: {input_path} -> {output_path}")

    def batch_convert_directory(input_dir: Path, output_dir: Path, blender_path: str, script_path: Path):
        """Utility function to batch convert an entire directory."""
        try:
            blend_files = list(input_dir.rglob("*.blend"))
            if not blend_files:
                print(f"[*] No .blend files found in directory: {input_dir}")
                return
                
            print(f"[*] Found {len(blend_files)} .blend files.")
            
            if output_dir:
                ensure_output_directory(output_dir)
                
            success_count = 0
            for blend_file in blend_files:
                out_file = (output_dir / blend_file.with_suffix(".fbx").name) if output_dir else blend_file.with_suffix(".fbx")
                try:
                    convert_blend_to_fbx(blend_file, out_file, blender_path, script_path)
                    success_count += 1
                except (InvalidBlendFileError, ExportFailedError) as e:
                    print(f"    [!] Skipping {blend_file.name} due to error: {e}")
            
            print(f"[*] Batch conversion finished. Converted {success_count}/{len(blend_files)} files.")
        except PermissionError:
            print(f"[-] Permission denied reading directory: {input_dir}")

    # Main Entry Point
    def main():
        parser = argparse.ArgumentParser(description="Agent to convert .blend files to highly compatible CAD .fbx files.")
        parser.add_argument("input", help="Path to a .blend file or a directory containing .blend files.")
        parser.add_argument("-o", "--output", help="Optional output path (file or directory). Defaults to the same location as input.")
        parser.add_argument("--blender-path", help="Path to the Blender executable if not in system PATH.", default=None)
        
        args = parser.parse_args()
        input_path = Path(args.input)
        current_script = Path(__file__).resolve()
            
        try:
            blender_path = locate_blender(args.blender_path)
            
            if not input_path.exists():
                raise InvalidBlendFileError(f"Input path does not exist: {input_path}")
                
            if input_path.is_file():
                output_file = Path(args.output) if args.output else input_path.with_suffix(".fbx")
                if args.output and Path(args.output).is_dir():
                    output_file = Path(args.output) / input_path.with_suffix(".fbx").name
                    
                ensure_output_directory(output_file.parent)
                convert_blend_to_fbx(input_path, output_file, blender_path, current_script)
                
            elif input_path.is_dir():
                out_dir = Path(args.output) if args.output else None
                batch_convert_directory(input_path, out_dir, blender_path, current_script)
                
        except BlenderNotFoundError as e:
            print(f"\n[Error - Missing Dependency] {e}")
            sys.exit(1)
        except InvalidBlendFileError as e:
            print(f"\n[Error - Invalid Input] {e}")
            sys.exit(2)
        except OutputDirectoryError as e:
            print(f"\n[Error - I/O Issues] {e}")
            sys.exit(3)
        except ExportFailedError as e:
            print(f"\n[Error - Extraction Process Failed] {e}")
            sys.exit(4)
        except Exception as e:
            print(f"\n[Unexpected Error] An unhandled exception occurred: {e}")
            sys.exit(5)
                
    if __name__ == "__main__":
        main()
