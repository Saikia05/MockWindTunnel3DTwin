"""

ONLY FOR FBX CONVERSION
fbx_converter.py
================
Load an FBX file (v7400 binary or ASCII), inspect its scene graph,
extract mesh geometry and materials, then export to OBJ and/or PLY.

Dependencies
------------
    pip install aspose-3d

Environment variable required on Linux (no system ICU):
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

Usage
-----
    # Basic: load + export both formats
    python fbx_converter.py wtblend.fbx

    # Export only OBJ
    python fbx_converter.py wtblend.fbx --format obj

    # Export only PLY
    python fbx_converter.py wtblend.fbx --format ply

    # Inspect scene without exporting
    python fbx_converter.py wtblend.fbx --inspect-only
"""

import os
import sys
import argparse

# ── Aspose.3D requires globalization invariant mode on non-Windows ──────────
os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")

try:
    import aspose.threed as a3d
except ImportError:
    sys.exit(
        "aspose-3d is not installed.\n"
        "Run:  pip install aspose-3d\n"
        "Then retry with:  DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 python fbx_converter.py ..."
    )

# Suppress the trial nag (does NOT remove export watermarks without a licence)
a3d.TrialException.set_suppress_trial_exception(True)


# ── Scene loading ────────────────────────────────────────────────────────────

def load_fbx(fbx_path: str) -> a3d.Scene:
    """Load an FBX file and return the Aspose Scene object."""
    if not os.path.isfile(fbx_path):
        sys.exit(f"File not found: {fbx_path}")

    print(f"Loading FBX: {fbx_path}")
    scene = a3d.Scene()
    scene.open(fbx_path)
    print("  ✓ Scene loaded\n")
    return scene


# ── Scene inspection ─────────────────────────────────────────────────────────

def _walk_node(node: a3d.Node, depth: int, results: dict) -> None:
    """Recursively walk the scene graph, collecting meshes and materials."""
    indent = "  " * depth
    entity_tags = ""

    for entity in node.entities:
        etype = type(entity).__name__
        entity_tags += f" <{etype}>"

        # Collect entity property summary
        props = {p.name: p.value for p in entity.properties}
        results["entities"].append({
            "node": node.name or "(unnamed)",
            "type": etype,
            "properties": props,
        })

    print(f"{indent}[{node.name or '(unnamed)'}]{entity_tags}")

    # Materials attached to this node
    for mat in node.materials:
        mat_props = {p.name: p.value for p in mat.properties}
        results["materials"].append({
            "node": node.name or "(unnamed)",
            "name": mat.name,
            "type": type(mat).__name__,
            "properties": mat_props,
        })
        print(f"{indent}  ↳ material: {mat.name!r}  ({type(mat).__name__})")

    for child in node.child_nodes:
        _walk_node(child, depth + 1, results)


def inspect_scene(scene: a3d.Scene) -> dict:
    """
    Print the scene hierarchy and return a dict with:
        {
            'entities': [...],   # list of entity info dicts
            'materials': [...],  # list of material info dicts
        }
    """
    results = {"entities": [], "materials": []}
    print("── Scene Graph ─────────────────────────────────────────")
    _walk_node(scene.root_node, 0, results)
    print()

    # Summary
    print(f"── Summary ─────────────────────────────────────────────")
    print(f"  Entities  : {len(results['entities'])}")
    print(f"  Materials : {len(results['materials'])}")

    if results["materials"]:
        print("\n── Material Details ────────────────────────────────────")
        for m in results["materials"]:
            print(f"  [{m['node']}] {m['name']!r}  ({m['type']})")
            for k, v in m["properties"].items():
                print(f"      {k} = {v}")
    print()

    return results


# ── Export helpers ────────────────────────────────────────────────────────────

def _make_output_path(fbx_path: str, extension: str) -> str:
    """Build the output path next to the source file."""
    base = os.path.splitext(fbx_path)[0]
    return f"{base}.{extension}"


def export_obj(scene: a3d.Scene, fbx_path: str, out_path: str | None = None) -> str:
    """
    Export the scene to Wavefront OBJ.

    The exporter writes both a .obj file and a companion .mtl file
    (material library) automatically.

    Returns the output path.
    """
    out_path = out_path or _make_output_path(fbx_path, "obj")
    print(f"Exporting OBJ → {out_path}")
    scene.save(out_path)
    print("  ✓ OBJ export complete\n")
    return out_path


def export_ply(scene: a3d.Scene, fbx_path: str, out_path: str | None = None) -> str:
    """
    Export the scene to Stanford PLY (ASCII).

    The PLY file includes per-vertex position, normal, and UV coordinates.

    Returns the output path.
    """
    out_path = out_path or _make_output_path(fbx_path, "ply")
    print(f"Exporting PLY → {out_path}")
    scene.save(out_path)
    print("  ✓ PLY export complete\n")
    return out_path


# ── OBJ parser (geometry read-back) ─────────────────────────────────────────

def parse_obj(obj_path: str) -> dict:
    """
    Parse a Wavefront OBJ file and return raw geometry:
        {
            'vertices'  : list of (x, y, z),
            'normals'   : list of (nx, ny, nz),
            'uvs'       : list of (u, v),
            'faces'     : list of face tuples, each element is
                          (vertex_idx, uv_idx, normal_idx)  (all 1-based),
            'groups'    : list of group/object names,
            'mtllib'    : material library filename or None,
        }
    """
    vertices, normals, uvs, faces = [], [], [], []
    groups, mtllib = [], None

    with open(obj_path, "r") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            tag = parts[0]

            if tag == "v":
                vertices.append(tuple(float(x) for x in parts[1:4]))

            elif tag == "vn":
                normals.append(tuple(float(x) for x in parts[1:4]))

            elif tag == "vt":
                uvs.append(tuple(float(x) for x in parts[1:3]))

            elif tag in ("g", "o"):
                groups.append(parts[1] if len(parts) > 1 else "")

            elif tag == "mtllib":
                mtllib = parts[1]

            elif tag == "f":
                # Each token: v  or  v/vt  or  v//vn  or  v/vt/vn
                face = []
                for token in parts[1:]:
                    indices = token.split("/")
                    vi  = int(indices[0])                                    if len(indices) > 0 and indices[0]  else None
                    vti = int(indices[1])                                    if len(indices) > 1 and indices[1]  else None
                    vni = int(indices[2])                                    if len(indices) > 2 and indices[2]  else None
                    face.append((vi, vti, vni))
                faces.append(face)

    return {
        "vertices": vertices,
        "normals":  normals,
        "uvs":      uvs,
        "faces":    faces,
        "groups":   groups,
        "mtllib":   mtllib,
    }


def parse_mtl(mtl_path: str) -> dict:
    """
    Parse a Wavefront MTL file and return a dict of material definitions:
        { material_name: { property: value, ... }, ... }

    Common properties extracted:
        Ka  - ambient colour  (r, g, b)
        Kd  - diffuse colour  (r, g, b)
        Ks  - specular colour (r, g, b)
        Ns  - specular exponent
        d   - dissolve (opacity)
        map_Kd - diffuse texture filename
    """
    materials: dict[str, dict] = {}
    current: dict | None = None

    with open(mtl_path, "r") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            tag = parts[0]

            if tag == "newmtl":
                name = parts[1] if len(parts) > 1 else "unnamed"
                current = {}
                materials[name] = current

            elif current is None:
                continue  # skip orphan lines before the first newmtl

            elif tag in ("Ka", "Kd", "Ks"):
                current[tag] = tuple(float(x) for x in parts[1:4])

            elif tag in ("Ns", "d", "Ni", "illum"):
                current[tag] = float(parts[1])

            elif tag.startswith("map_"):
                current[tag] = parts[1]

    return materials


# ── PLY parser (geometry read-back) ──────────────────────────────────────────

def parse_ply(ply_path: str) -> dict:
    """
    Parse an ASCII PLY file.

    Returns:
        {
            'vertices': list of dicts  {x, y, z, nx, ny, nz, u, v, ...},
            'faces'   : list of lists  [vertex_indices, ...],
        }
    """
    vertices, faces = [], []
    n_verts = n_faces = 0
    vertex_props: list[str] = []
    in_header = True
    parsing = None  # 'vertex' | 'face'
    parsed_verts = parsed_faces = 0

    with open(ply_path, "r") as fh:
        for raw in fh:
            line = raw.strip()

            if in_header:
                parts = line.split()
                if line == "end_header":
                    in_header = False
                    parsing = "vertex"
                elif parts[0] == "element":
                    if parts[1] == "vertex":
                        n_verts = int(parts[2])
                    elif parts[1] == "face":
                        n_faces = int(parts[2])
                elif parts[0] == "property" and parsing == "vertex":
                    # track vertex property order (skip list properties)
                    if parts[1] != "list":
                        vertex_props.append(parts[-1])
                elif line.startswith("element"):
                    pass
                # Track which element we're describing
                if parts[0] == "element":
                    parsing = parts[1]
                continue

            # Data section
            if parsed_verts < n_verts:
                vals = list(map(float, line.split()))
                vertices.append(dict(zip(vertex_props, vals)))
                parsed_verts += 1
                if parsed_verts == n_verts:
                    parsing = "face"

            elif parsed_faces < n_faces:
                nums = list(map(int, line.split()))
                count = nums[0]
                faces.append(nums[1: 1 + count])
                parsed_faces += 1

    return {"vertices": vertices, "faces": faces}


# ── Report helper ────────────────────────────────────────────────────────────

def print_geometry_report(geo: dict, fmt: str) -> None:
    """Print a human-readable summary of parsed geometry."""
    print(f"── {fmt.upper()} Geometry Report ──────────────────────────────")
    if fmt == "obj":
        print(f"  Vertices  : {len(geo['vertices'])}")
        print(f"  Normals   : {len(geo['normals'])}")
        print(f"  UVs       : {len(geo['uvs'])}")
        print(f"  Faces     : {len(geo['faces'])}")
        print(f"  Groups    : {geo['groups']}")
        print(f"  MTL file  : {geo['mtllib']}")
        if geo["vertices"]:
            v = geo["vertices"][0]
            print(f"  First vertex : {v}")
        if geo["faces"]:
            print(f"  First face   : {geo['faces'][0]}")
    elif fmt == "ply":
        print(f"  Vertices  : {len(geo['vertices'])}")
        print(f"  Faces     : {len(geo['faces'])}")
        if geo["vertices"]:
            print(f"  First vertex : {geo['vertices'][0]}")
        if geo["faces"]:
            print(f"  First face   : {geo['faces'][0]}")
    print()


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an FBX file to OBJ and/or PLY using Aspose.3D"
    )
    parser.add_argument("fbx", help="Path to the input .fbx file")
    parser.add_argument(
        "--format",
        choices=["obj", "ply", "both"],
        default="both",
        help="Export format (default: both)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for output files (default: same directory as input)",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Only inspect the scene; do not export",
    )
    args = parser.parse_args()

    # ── Load ────────────────────────────────────────────────────────────────
    scene = load_fbx(args.fbx)

    # ── Inspect ─────────────────────────────────────────────────────────────
    inspect_scene(scene)

    if args.inspect_only:
        return

    # ── Build output paths ──────────────────────────────────────────────────
    base_name = os.path.splitext(os.path.basename(args.fbx))[0]
    out_dir   = args.out_dir or os.path.dirname(os.path.abspath(args.fbx))
    os.makedirs(out_dir, exist_ok=True)

    obj_path = os.path.join(out_dir, f"{base_name}.obj")
    ply_path = os.path.join(out_dir, f"{base_name}.ply")

    # ── Export ──────────────────────────────────────────────────────────────
    if args.format in ("obj", "both"):
        export_obj(scene, args.fbx, obj_path)
        geo = parse_obj(obj_path)
        print_geometry_report(geo, "obj")

        # Also parse companion MTL if present
        mtl_path = os.path.join(out_dir, geo["mtllib"]) if geo["mtllib"] else None
        if mtl_path and os.path.isfile(mtl_path):
            materials = parse_mtl(mtl_path)
            print(f"── MTL Materials ({len(materials)}) ─────────────────────────────")
            for name, props in materials.items():
                print(f"  {name!r}: {props}")
            print()

    if args.format in ("ply", "both"):
        export_ply(scene, args.fbx, ply_path)
        geo = parse_ply(ply_path)
        print_geometry_report(geo, "ply")

    print("Done.")


if __name__ == "__main__":
    main()
