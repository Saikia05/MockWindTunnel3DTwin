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
    # =========================================================================
    # 1. BLENDER EXPORTER LOGIC (Executes internally via Blender)
    # =========================================================================
    def export_to_fbx(output_path):
        print(f"--- Starting export to {output_path} ---")
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.context.scene.objects:
                if obj.type in {'MESH', 'ARMATURE'}:
                    obj.select_set(True)
        except Exception as e:
            print(f"Error selecting objects: {e}")
            raise e
        
        try:
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
    # =========================================================================
    # 2. AGENT WRAPPER LOGIC (Executes normally via host machine)
    # =========================================================================
    import argparse
    import subprocess
    from pathlib import Path

    class BlenderNotFoundError(Exception): pass
    class InvalidBlendFileError(Exception): pass
    class ExportFailedError(Exception): pass
    class OutputDirectoryError(Exception): pass

    def locate_blender(custom_path=None):
        if custom_path:
            if not os.path.exists(custom_path):
                raise BlenderNotFoundError(f"Provided Blender path does not exist: {custom_path}")
            return custom_path
        return "blender"

    def is_valid_blend_file(filepath: Path) -> bool:
        return filepath.is_file() and filepath.suffix.lower() == ".blend"

    def ensure_output_directory(output_path: Path):
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise OutputDirectoryError(f"Permission denied creating directory: {output_path}")
        except Exception as e:
            raise OutputDirectoryError(f"Failed to create directory {output_path}: {e}")

    def convert_blend_to_fbx(input_path: Path, output_path: Path, blender_path: str, script_path: Path) -> str:
        print(f"[*] Processing: {input_path}")
        if not is_valid_blend_file(input_path):
            raise InvalidBlendFileError(f"Invalid input file: {input_path}")
            
        command = [blender_path, "-b", str(input_path), "-P", str(script_path), "--", str(output_path)]
        
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            msg = f"[+] Successfully converted to: {output_path}"
            print(msg)
            return msg
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to convert {input_path}\n--- stderr ---\n{e.stderr.strip()}")
            raise ExportFailedError(f"Blender subprocess failed with code {e.returncode}")
        except FileNotFoundError:
            raise BlenderNotFoundError("Blender executable not found. Make sure it's in your system PATH.")
        except PermissionError:
            raise ExportFailedError(f"Permission denied when trying to execute/write: {input_path} -> {output_path}")

    def batch_convert_directory(input_dir: Path, output_dir: Path, blender_path: str, script_path: Path) -> str:
        try:
            blend_files = list(input_dir.rglob("*.blend"))
            if not blend_files:
                msg = f"[*] No .blend files found in directory: {input_dir}"
                print(msg)
                return msg
                
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
            
            final_msg = f"[*] Batch conversion finished. Converted {success_count}/{len(blend_files)} files."
            print(final_msg)
            return final_msg
        except PermissionError:
            err_msg = f"[-] Permission denied reading directory: {input_dir}"
            print(err_msg)
            return err_msg

    # =========================================================================
    # 3. LLM AI AGENT CHAT LOGIC
    # =========================================================================
    try:
        from langchain_core.tools import tool
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        from langchain_core.prompts import ChatPromptTemplate
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False

    if LANGCHAIN_AVAILABLE:
        @tool
        def convert_blend_models(directory_path: str, output_directory: str = None) -> str:
            """Finds all .blend files in the given directory_path and converts them to CAD-compatible .fbx files.
            If output_directory is provided, the FBX files will be saved there. Otherwise, they are saved next to the original files.
            """
            input_dir = Path(directory_path)
            if not input_dir.exists():
                return f"Error: Directory does not exist: {directory_path}"
                
            out_dir = Path(output_directory) if output_directory else None
            current_script = Path(__file__).resolve()
            
            try:
                blender_path = locate_blender()
                if input_dir.is_file():
                    output_file = out_dir if out_dir else input_dir.with_suffix(".fbx")
                    return convert_blend_to_fbx(input_dir, output_file, blender_path, current_script)
                else:
                    return batch_convert_directory(input_dir, out_dir, blender_path, current_script)
            except Exception as e:
                return f"Tool execution failed under the hood. Error: {str(e)}"

        def get_llm():
            if os.environ.get("OPENAI_API_KEY"):
                try:
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI(model="gpt-4o", temperature=0)
                except ImportError:
                    pass
            if os.environ.get("GOOGLE_API_KEY"):
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
                except ImportError:
                    pass
            print("[!] Environment lacks API keys (OPENAI_API_KEY / GOOGLE_API_KEY) or pip packages.")
            sys.exit(1)

        def run_ai_agent():
            llm = get_llm()
            tools = [convert_blend_models]
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an intelligent 3D pipeline assistant. You help users convert Blender files. Use the 'convert_blend_models' tool to do so. Be friendly, give a summary of the tool output, and don't make up file names if they aren't provided by the tool output."),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])
            agent = create_tool_calling_agent(llm, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            
            print("\n" + "="*50)
            print(" Blender-to-FBX AI Agent ".center(50, "="))
            print("="*50)
            print("I can autonomously find and convert .blend files for you.")
            print("(Type 'exit' to quit)\n")
            
            while True:
                try:
                    user_input = input("You: ")
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    if not user_input.strip():
                        continue
                        
                    response = agent_executor.invoke({"input": user_input})
                    print(f"\nAI: {response['output']}\n")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n[Agent Runtime Error]: {e}\n")

    # =========================================================================
    # MAIN CLI ENTRY POINT
    # =========================================================================
    def main():
        parser = argparse.ArgumentParser(description="Agent to convert .blend files to highly compatible CAD .fbx files.")
        parser.add_argument("input", nargs="?", help="Path to a .blend file or a directory. If omitted, launches AI Chat.")
        parser.add_argument("-o", "--output", help="Optional output path (file or directory).")
        parser.add_argument("--blender-path", help="Path to the Blender executable.", default=None)
        parser.add_argument("--ai", action="store_true", help="Force launch the interactive LLM AI chat agent.")
        
        args = parser.parse_args()
        
        # If no input arg provided or --ai is explicitly passed, boot into LLM mode
        if args.ai or not args.input:
            if not LANGCHAIN_AVAILABLE:
                print("[!] AI Chat requires LangChain. Install via:")
                print("pip install langchain langchain-core langchain-openai")
                sys.exit(1)
            run_ai_agent()
            return
            
        # Normal CLI Execution
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
            print(f"\n[Error - Missing Dependency] {e}"); sys.exit(1)
        except InvalidBlendFileError as e:
            print(f"\n[Error - Invalid Input] {e}"); sys.exit(2)
        except OutputDirectoryError as e:
            print(f"\n[Error - I/O Issues] {e}"); sys.exit(3)
        except ExportFailedError as e:
            print(f"\n[Error - Process Failed] {e}"); sys.exit(4)
        except Exception as e:
            print(f"\n[Unexpected Error] {e}"); sys.exit(5)
                
    if __name__ == "__main__":
        main()
