# MockWindTunnel3DTwin
A 3D environment of a mock wind tunnel, that produces visual information about velocity (customisable),  It can simulate airflow of any object, just like in real life.
Currently I have uploaded this project as FBX import format, supported by blender. The actual '.blend' file will be in a Drive link below.

# Here's a step-by-step of how FBX was converted to Python Mesh Code for various software supports, (MWT.py):

[wtblend.fbx]
 └─ Kaydara FBX binary (v7400, 6.4 MB)
    └─ Note: No system ICU on Linux → needed

Step 1 — Environment setup
 └─ DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1


Step 2 — Load FBX
 └─ a3d.Scene().open("wtblend.fbx")


Step 3 — Walk scene graph
 └─ _walk_node() → finds:
      • Area
      • Camera
      • Camera.001
      • DomainCube.004
      • Field

Step 4 — Extract entity properties
 ├─ Light → DecayType, CastLight, Exposure
 └─ Cameras → FocalLength, AspectWidth, Position

Step 5 — Export dispatch
 └─ scene.save(path) → format from extension

   Branch A → wtblend.obj
    ├─ 40 vertices
    ├─ 48 faces
    ├─ 48 normals
    ├─ 52 UVs
    └─ Group: DomainCube.004
       └─ Step 6a — parse_obj()
          • v, vn, vt, f, g, mtllib

   Branch B → wtblend.ply
    ├─ 40 vertices
    ├─ 48 faces
    ├─ ASCII format
    ├─ x/y/z, nx/ny/nz, u/v per vertex
    └─ Step 6b — parse_ply()
          • Header → element counts → data rows

Final Output
 └─ Python dicts → {vertices, faces, normals, UVs}Click any box to dive deeper into that step. Here's the plain-language walkthrough of each stage:
Step 1 — Environment setup. On Linux, Aspose.3D is built on .NET which expects a system ICU (Unicode) library. Setting DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 tells .NET to skip that requirement and run in culture-neutral mode — without it, the process aborts before any code runs.

Step 2 — Load FBX. a3d.Scene().open() reads the binary FBX format (Kaydara v7400) and deserialises it into an in-memory scene graph — a tree of Node objects each carrying Entity children and Material lists.

Step 3 — Walk the scene graph. _walk_node() recurses through every node using node.child_nodes. Your file had five nodes directly under RootNode: a light (Area), two cameras, one mesh cube (DomainCube.004), and a plane (Field).

Step 4 — Extract entity properties. Each entity exposes a properties collection of typed key-value pairs. The cameras had FocalLength, AspectWidth, Position, etc. The light had DecayType, CastLight. Materials came back empty — the mesh had no assigned material in the FBX.

Step 5 — Export dispatch. scene.save(path) infers the output format purely from the file extension — .obj triggers the Wavefront exporter, .ply triggers the Stanford exporter. No format enum needed.

Step 6a — OBJ parsing. parse_obj() reads the text file line by line, routing on the tag: v → vertex tuple, vn → normal, vt → UV, f → face (splits each v/vt/vn token), g → group name, mtllib → companion material file name.

Step 6b — PLY parsing. parse_ply() reads the ASCII header to learn the property names and element counts, then streams the data rows — vertex rows get zipped with the property list into dicts ({x, y, z, nx, ny, nz, u, v}), face rows unpack the leading count byte to get index lists.

Final output — both parsers return plain Python dicts with lists of tuples/dicts you can feed directly into NumPy, Open3D, trimesh, or any downstream 3D pipeline.



Also provided 
# Link to the file:
Due to GitHub's upload limit, the '.blend' file could not be uploaded, Here's a drive link to access the file. 
https://drive.google.com/drive/folders/1lL1tW7kZAnEFQINzHvIbh2cY8C4nHWQb

# Walkthrough-Video:
https://jumpshare.com/share/ehzXqNyyiKNQxFtWWtXF
