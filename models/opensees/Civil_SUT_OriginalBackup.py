# Steps in Openseespy projects:
# 1. Units, Dimensions and Geometries.
# 2. Coordinates of nodes.
# 3. Support conditions.
# 4. Materials.
# 5. Sections.
# 6. Transfer geometries.
# 7. Elements.
# 8. Define floors (Deck or Slab).
# 9. Define Loads.
# 10. 
from openseespy import opensees as ops
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import opsvis as opsv
import warnings

warnings.filterwarnings("ignore")
# 1. Units
# Unints:
m = 1.0       # m
N = 1.0       # N
Pa = 1.0      # Pa
s = 1.0       # s

kg = N * s**2 / m

MPa = Pa * 1e6
mm = m * 1e-3
cm = m * 1e-2

g = 9.81     # m/s^2
# Initial commands for model
# -------------------------- Start Model -------------------------- #
# Clean All the variables...
ops.wipe()
# model('basic', '-ndm', ndm, '-ndf', ndf=ndm*(ndm+1)/2)
ops.model('basic', '-ndm', 3, '-ndf', 6)  # 3D with 6 DOFs.
# 2. Geometry and Node Coordinates
# -------------------------- Nodes -------------------------- #
# node(nodeTag, *crds, '-ndf', ndf, '-mass', *mass, '-disp', *disp, '-vel', *vel, '-accel', *accel)
# Generated Excel file from ETABS model ----> Geometry.xlsx
Node_Data = pd.read_excel("Geometry.xlsx", sheet_name="Node")
NONE_Nodes = pd.read_excel("Geometry.xlsx", sheet_name="NONE_POINTS")["UNIQUENAME"].to_list()

Node_Data = Node_Data[
    ~Node_Data["UniqueName"].isin(NONE_Nodes)
].reset_index(drop=True)


for ID, X, Y, Z in zip(Node_Data["UniqueName"], Node_Data["X (m)"], Node_Data["Y (m)"], Node_Data["Z (m)"]):
    ops.node(ID, X, Y, Z)
# 3. Support Conditions
# -------------------------- Fixed Support -------------------------- #
# fix(nodeTag, *constrValues)
Fix_Nodes = pd.read_excel("Geometry.xlsx", sheet_name="FIX_Node")

for ID in Fix_Nodes["UniqueName"]:
    ops.fix(ID, 1, 1, 1, 1, 1, 1)  # Fixed Support
# Model 1 - ElasticBeamColumn
# 4. Material
# Concrete Material Properties:
fc = 28.5374 * MPa          # Concrete ----> Based on ETABS model
E_concrete = 4700 * np.sqrt(fc)
nu_concrete = 0.2
G_concrete = E_concrete /(2 * (1+ nu_concrete))
rho_concrete = 2490 * kg/m**3

# Steel Material Properties:
# uniaxialMaterial('Steel02', matTag, Fy, E0, b, *params, a1=a2*Fy/E0, a2=1.0, a3=a4*Fy/E0, a4=1.0, sigInit=0.0)
fy = 240 * MPa          # Steel ----> Based on ETABS model
fye = 1.1 * fy
fu = 370 * MPa
fue = 1.1 * fu
# E_steel = 210000 * MPa
E_steel = 1e20
nu_steel = 0.3
G_steel = E_steel /(2 * (1+ nu_steel))
rho_steel = 7850 * kg/m**3
b = 0.01  # Strain hardening ratio for Steel02 material
params = [15.0, 0.925, 0.15]  # Parameters for Steel02 material
a2 = 1.0
a1 = a2 * fy / E_steel
a4 = 1.0
a3 = a4 * fy / E_steel
sigInit = 0.0
MAT_TAG_STEEL = 1
ops.uniaxialMaterial('Steel02', MAT_TAG_STEEL, fy, E_steel, b, *params, a1, a2, a3, a4, sigInit)
# 5. Section
# Section Properties: (based on ETABS model)
Section_Data = pd.read_excel("Geometry.xlsx", sheet_name="SECTION_Properties")
# 6. Geometry Transform
def get_vecxz(node_i, node_j):
    """
    Calculate a suitable vecxz vector for a 3D OpenSees element.

    node_i, node_j:
        Global coordinates [X, Y, Z]

    Returns:
        vecxz = [vx, vy, vz]
    """

    xi = np.array(node_i, dtype=float)
    xj = np.array(node_j, dtype=float)

    # Local x-axis of the element
    x_local = xj - xi
    L = np.linalg.norm(x_local)

    if L == 0:
        raise ValueError("Element has zero length.")

    x_local = x_local / L

    # Candidate global reference vectors
    global_axes = [
        np.array([1.0, 0.0, 0.0]),  # Global X
        np.array([0.0, 1.0, 0.0]),  # Global Y
        np.array([0.0, 0.0, 1.0])   # Global Z
    ]

    # Choose the global axis that is LEAST parallel to local x
    dots = [abs(np.dot(x_local, axis)) for axis in global_axes]

    vecxz = global_axes[np.argmin(dots)]

    return vecxz.tolist()
# 7. Define Elements
Col_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="COLUMN_Connectivity")
Beam_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="BEAM_Connectivity")
Brace_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="BRACE_Connectivity")
Section_Assign_Data = pd.read_excel("Geometry.xlsx", sheet_name="FRAME_Sections")
Section_Properties_Data = pd.read_excel("Geometry.xlsx", sheet_name="SECTION_Properties")
Frame_Release_Data = pd.read_excel("Geometry.xlsx", sheet_name="FRAME_Releases&PartialFixity")["UniqueName"]
# Fix some points for just truss elements:
Truss_Lable = Section_Assign_Data[Section_Assign_Data['Analysis Section'].astype(str).str.startswith('2L', na=False)]['Label'].tolist()
Truss_Only_Nodes = set()

for Lable in Truss_Lable:
    if Col_Ele_Data["ColumnBay"].isin([Lable]).any():
        I = Col_Ele_Data.loc[Col_Ele_Data["ColumnBay"] == Lable, "UniquePtI"].iloc[0]
        J = Col_Ele_Data.loc[Col_Ele_Data["ColumnBay"] == Lable, "UniquePtJ"].iloc[0]
    elif Brace_Ele_Data["BraceBay"].isin([Lable]).any():
        I = Brace_Ele_Data.loc[Brace_Ele_Data["BraceBay"] == Lable, "UniquePtI"].iloc[0]
        J = Brace_Ele_Data.loc[Brace_Ele_Data["BraceBay"] == Lable, "UniquePtJ"].iloc[0]
    else:
        I = Beam_Ele_Data.loc[Beam_Ele_Data["BeamBay"] == Lable, "UniquePtI"].iloc[0]
        J = Beam_Ele_Data.loc[Beam_Ele_Data["BeamBay"] == Lable, "UniquePtJ"].iloc[0]

    if not (
        Beam_Ele_Data["UniquePtI"].isin([I]).any()
        or
        Beam_Ele_Data["UniquePtJ"].isin([I]).any()
    ):
        Truss_Only_Nodes.add(I)

    if not (
        Beam_Ele_Data["UniquePtI"].isin([J]).any()
        or
        Beam_Ele_Data["UniquePtJ"].isin([J]).any()
    ):
        Truss_Only_Nodes.add(J)


print("Number of Truss-only nodes:", len(Truss_Only_Nodes))

for node in Truss_Only_Nodes:
    node = int(node)
    ops.fix(node, 0, 0, 0, 1, 1, 1)
# geomTransf(transfType, transfTag, *transfArgs)
# element('elasticBeamColumn', eleTag, *eleNodes, Area, E_mod, G_mod, Jxx, Iy, Iz, transfTag, <'-mass', mass>, <'-cMass'>)
# element('Truss', eleTag, *eleNodes, A, matTag, <'-rho', rho>, <'-cMass', cFlag>, <'-doRayleigh', rFlag>)

transfType_col = 'PDelta'
transfType_beam = 'Linear'
transfType_brace_and_truss = 'PDelta'  # Assuming braces also use PDelta; adjust as necessary

eleTag_Column = 0
eleTag_Beam = 1000
eleTag_Brace_and_Truss = 5000



for i in range(Col_Ele_Data.shape[0]): 

    eleName = (Col_Ele_Data.loc[i, "ColumnBay"])
    # Create Section Properties for Column:
    section_name = Section_Assign_Data.loc[Section_Assign_Data["Label"] == eleName, "Analysis Section"].iloc[0]
    eleNodes = [int(Col_Ele_Data.loc[i, "UniquePtI"]), int(Col_Ele_Data.loc[i, "UniquePtJ"])]
    column_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]
    Jxx_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "J (m^4)"].iloc[0]
    Iy_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I33 (m^4)"].iloc[0]
    Iz_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I22 (m^4)"].iloc[0]

    # Create TransferTags for Column or Brace/Truss:
    UniqueName = Col_Ele_Data.loc[i, "UniqueName"]
    if UniqueName in Frame_Release_Data.values:
        eleTag_Brace_and_Truss += 1  # Unique element tag for each brace/truss
        cFlag = 0  # Set to 1 if you want consistent mass matrix, 0 for lumped mass
        rFlag = 0  # Set to 1 if you want to include Rayleigh
        ops.element('Truss', eleTag_Brace_and_Truss, *eleNodes, column_area, MAT_TAG_STEEL, '-rho', rho_steel, '-cMass', cFlag, '-doRayleigh', rFlag)

    else:
        eleTag_Column += 1
        UniquePtI = int(Col_Ele_Data.loc[i, "UniquePtI"])
        UniquePtJ = int(Col_Ele_Data.loc[i, "UniquePtJ"])
        node_i_coords = Node_Data.loc[Node_Data["UniqueName"] == UniquePtI, ["X (m)", "Y (m)", "Z (m)"]].values.flatten()
        node_j_coords = Node_Data.loc[Node_Data["UniqueName"] == UniquePtJ, ["X (m)", "Y (m)", "Z (m)"]].values.flatten()
        nodes = {
            UniquePtI: node_i_coords,
            UniquePtJ: node_j_coords
        }
        node_i = nodes[UniquePtI]
        node_j = nodes[UniquePtJ]
        vecxz_col = get_vecxz(node_i, node_j)
        transfTag_col = eleTag_Column  # Unique transfer tag for each column
        ops.geomTransf(transfType_col, transfTag_col, *vecxz_col)
        ops.element('elasticBeamColumn', eleTag_Column, *eleNodes, column_area, E_steel, G_steel, Jxx_col, Iy_col, Iz_col, transfTag_col, '-mass', 0.0)

for j in range(Beam_Ele_Data.shape[0]):
    
    eleName = (Beam_Ele_Data.loc[j, "BeamBay"])
    # Create Section Properties for Beam:
    section_name = Section_Assign_Data.loc[Section_Assign_Data["Label"] == eleName, "Analysis Section"].iloc[0]
    eleNodes = [int(Beam_Ele_Data.loc[j, "UniquePtI"]), int(Beam_Ele_Data.loc[j, "UniquePtJ"])]
    beam_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]
    Jxx_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "J (m^4)"].iloc[0]
    Iy_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I33 (m^4)"].iloc[0]
    Iz_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I22 (m^4)"].iloc[0]

    # Create TransferTags for Beam or Brace/Truss:
    UniqueName = Beam_Ele_Data.loc[j, "UniqueName"]
    if UniqueName in Frame_Release_Data.values:
        eleTag_Brace_and_Truss += 1  # Unique element tag for each brace/truss
        cFlag = 0  # Set to 1 if you want consistent mass matrix, 0 for lumped mass
        rFlag = 0  # Set to 1 if you want to include Rayleigh
        ops.element('Truss', eleTag_Brace_and_Truss, *eleNodes, beam_area, MAT_TAG_STEEL, '-rho', rho_steel, '-cMass', cFlag, '-doRayleigh', rFlag)

    else:
        eleTag_Beam += 1
        UniquePtI = int(Beam_Ele_Data.loc[j, "UniquePtI"])
        UniquePtJ = int(Beam_Ele_Data.loc[j, "UniquePtJ"])
        node_i_coords = Node_Data.loc[Node_Data["UniqueName"] == UniquePtI, ["X (m)", "Y (m)", "Z (m)"]].values.flatten()
        node_j_coords = Node_Data.loc[Node_Data["UniqueName"] == UniquePtJ, ["X (m)", "Y (m)", "Z (m)"]].values.flatten()
        nodes = {
            UniquePtI: node_i_coords,
            UniquePtJ: node_j_coords
        }
        node_i = nodes[UniquePtI]
        node_j = nodes[UniquePtJ]
        vecxz_beam = get_vecxz(node_i, node_j)
        transfTag_beam =  eleTag_Beam # Unique transfer tag for each beam
        ops.geomTransf(transfType_beam, transfTag_beam, *vecxz_beam)
        ops.element('elasticBeamColumn', eleTag_Beam, *eleNodes, beam_area, E_steel, G_steel, Jxx_beam, Iy_beam, Iz_beam, transfTag_beam, '-mass', 0.0)

for k in range(Brace_Ele_Data.shape[0]):
    eleTag_Brace_and_Truss += 1
    eleName = (Brace_Ele_Data.loc[k, "BraceBay"])
    # Create Section Properties for Brace:
    section_name = Section_Assign_Data.loc[Section_Assign_Data["Label"] == eleName, "Analysis Section"].iloc[0]
    eleNodes = [int(Brace_Ele_Data.loc[k, "UniquePtI"]), int(Brace_Ele_Data.loc[k, "UniquePtJ"])]
    brace_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]
    Jxx_brace = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "J (m^4)"].iloc[0]
    Iy_brace = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I33 (m^4)"].iloc[0]
    Iz_brace = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I22 (m^4)"].iloc[0]

    # Create TransferTags for Beam or Brace/Truss:
    UniqueName = Brace_Ele_Data.loc[k, "UniqueName"]
    if UniqueName in Frame_Release_Data.values:
        eleTag_Brace_and_Truss += 1  # Unique transfer tag for each brace/truss
        cFlag = 0  # Set to 1 if you want consistent mass matrix, 0 for lumped mass
        rFlag = 0  # Set to 1 if you want to include Rayleigh
        ops.element('Truss', eleTag_Brace_and_Truss, *eleNodes, brace_area, MAT_TAG_STEEL, '-rho', rho_steel, '-cMass', cFlag, '-doRayleigh', rFlag)
    else:
        print(f"Brace element {eleTag_Brace_and_Truss} with nodes {eleNodes} is not in Frame_Release_Data. Skipping.")
# ============================================================
# 3D INTERACTIVE OPENSEES MODEL VIEWER
# ============================================================

import plotly.graph_objects as go


def plot_opensees_3d(
    show_nodes=True,
    show_node_labels=False,
    show_element_labels=False,
    node_size=3,
    line_width=4,
    show_supports=True
):

    # --------------------------------------------------------
    # 1. GET NODES
    # --------------------------------------------------------

    node_tags = ops.getNodeTags()

    node_coords = {}
    
    for node in node_tags:
        try:
            crd = ops.nodeCoord(node)

            # فقط 3D nodes
            if len(crd) >= 3:
                node_coords[node] = np.array(crd[:3], dtype=float)

        except:
            pass

    print(f"Number of nodes: {len(node_coords)}")


    # --------------------------------------------------------
    # 2. GET ELEMENTS
    # --------------------------------------------------------

    ele_tags = ops.getEleTags()

    print(f"Number of elements: {len(ele_tags)}")


    # --------------------------------------------------------
    # 3. CREATE FIGURE
    # --------------------------------------------------------

    fig = go.Figure()


    # --------------------------------------------------------
    # 4. ELEMENTS
    # --------------------------------------------------------

    for ele in ele_tags:

        try:
            nodes = ops.eleNodes(ele)

            if len(nodes) < 2:
                continue

            n1 = nodes[0]
            n2 = nodes[1]

            if n1 not in node_coords or n2 not in node_coords:
                continue

            x1, y1, z1 = node_coords[n1]
            x2, y2, z2 = node_coords[n2]

            # --------------------------------------------
            # ELEMENT LINE
            # --------------------------------------------

            fig.add_trace(
                go.Scatter3d(
                    x=[x1, x2],
                    y=[y1, y2],
                    z=[z1, z2],

                    mode="lines",

                    line=dict(
                        width=line_width
                    ),

                    hovertemplate=(
                        f"<b>Element {ele}</b><br>"
                        f"Node I: {n1}<br>"
                        f"Node J: {n2}<br>"
                        f"Length: "
                        f"{np.linalg.norm(node_coords[n2]-node_coords[n1]):.3f} m"
                        "<extra></extra>"
                    ),

                    showlegend=False
                )
            )


            # --------------------------------------------
            # ELEMENT LABEL
            # --------------------------------------------

            if show_element_labels:

                xm = (x1 + x2) / 2
                ym = (y1 + y2) / 2
                zm = (z1 + z2) / 2

                fig.add_trace(
                    go.Scatter3d(
                        x=[xm],
                        y=[ym],
                        z=[zm],

                        mode="text",

                        text=[str(ele)],

                        textfont=dict(
                            size=9
                        ),

                        showlegend=False
                    )
                )

        except Exception:
            continue


    # --------------------------------------------------------
    # 5. NODES
    # --------------------------------------------------------

    if show_nodes:

        X = []
        Y = []
        Z = []
        labels = []

        for node, coord in node_coords.items():

            X.append(coord[0])
            Y.append(coord[1])
            Z.append(coord[2])

            labels.append(str(node))


        fig.add_trace(
            go.Scatter3d(

                x=X,
                y=Y,
                z=Z,

                mode="markers",

                marker=dict(
                    size=node_size
                ),

                text=labels,

                hovertemplate=(
                    "<b>Node %{text}</b><br>"
                    "X = %{x:.3f} m<br>"
                    "Y = %{y:.3f} m<br>"
                    "Z = %{z:.3f} m"
                    "<extra></extra>"
                ),

                name="Nodes"
            )
        )


    # --------------------------------------------------------
    # 6. NODE LABELS
    # --------------------------------------------------------

    if show_node_labels:

        X = []
        Y = []
        Z = []
        labels = []

        for node, coord in node_coords.items():

            X.append(coord[0])
            Y.append(coord[1])
            Z.append(coord[2])

            labels.append(str(node))


        fig.add_trace(
            go.Scatter3d(

                x=X,
                y=Y,
                z=Z,

                mode="text",

                text=labels,

                textposition="top center",

                textfont=dict(
                    size=8
                ),

                showlegend=False
            )
        )


    # --------------------------------------------------------
    # 7. SUPPORTS
    # --------------------------------------------------------

    if show_supports:

        support_nodes = []

        for node in node_tags:

            try:

                # OpenSees nodeCoord
                crd = ops.nodeCoord(node)

                if len(crd) < 3:
                    continue

                # ------------------------------------------------
                # NOTE:
                # OpenSeesPy doesn't provide a simple universal
                # "get fixity" command.
                #
                # Therefore, if you have a list of base nodes,
                # put them here.
                # ------------------------------------------------

            except:
                continue


    # --------------------------------------------------------
    # 8. AXES / LAYOUT
    # --------------------------------------------------------

    fig.update_layout(

        title=dict(
            text="OpenSeesPy 3D Structural Model",
            x=0.5
        ),

        scene=dict(

            xaxis=dict(
                title="X (m)",
                showbackground=True,
                backgroundcolor="rgb(245,245,245)",
                gridcolor="white"
            ),

            yaxis=dict(
                title="Y (m)",
                showbackground=True,
                backgroundcolor="rgb(245,245,245)",
                gridcolor="white"
            ),

            zaxis=dict(
                title="Z (m)",
                showbackground=True,
                backgroundcolor="rgb(245,245,245)",
                gridcolor="white"
            ),

            aspectmode="data",

            camera=dict(
                eye=dict(
                    x=1.6,
                    y=1.6,
                    z=1.2
                )
            )
        ),

        margin=dict(
            l=0,
            r=0,
            b=0,
            t=50
        ),

        hovermode="closest"
    )


    # --------------------------------------------------------
    # 9. SHOW
    # --------------------------------------------------------


    return fig
plot_opensees_3d()
# Mass Definition
# ============================================================
# MASS ASSIGNMENT BASED ON STORY MASS
# ============================================================


# ------------------------------------------------------------
# Read data
# ------------------------------------------------------------


Story_Mass_Data = pd.read_excel("Load.xlsx",sheet_name="Story Mass")


# ============================================================
# STORY DEFINITIONS
# ============================================================
# Story Name  ->  Z coordinate

Story_Z = {
    "Story1": 7.1,
    "Story2": 11.3,
    "Story3": 15.5,
    "Story4": 19.4,
    "Story5": 23.3,
    "Story6": 27.2,

}


# ============================================================
# MASS ASSIGNMENT
# ============================================================

for story_name, z_value in Story_Z.items():

    # --------------------------------------------------------
    # Find all nodes belonging to this story
    # --------------------------------------------------------

    Story_Nodes = Node_Data[np.isclose( Node_Data["Z (m)"], z_value, atol=1e-6)]

    # --------------------------------------------------------
    # Number of nodes
    # --------------------------------------------------------

    N_nodes = len(Story_Nodes)

    if N_nodes == 0:

        print(
            f"WARNING: No nodes found for {story_name} "
            f"at Z = {z_value}"
        )

        continue

    # --------------------------------------------------------
    # Find story mass
    # --------------------------------------------------------

    Mass_Row = Story_Mass_Data[Story_Mass_Data["Story"].astype(str).str.strip()== story_name]

    if len(Mass_Row) == 0:

        print(
            f"WARNING: No mass found for {story_name}"
        )

        continue

    Mass_Row = Mass_Row.iloc[0]

    # --------------------------------------------------------
    # Total story mass
    #
    # Excel:
    # ton
    #
    # OpenSees:
    # kg
    #
    # 1 ton = 1000 kg
    # --------------------------------------------------------

    Total_Mass_X = float(Mass_Row["UX"]) * 1000.0
    Total_Mass_Y = float(Mass_Row["UY"]) * 1000.0

    # --------------------------------------------------------
    # Equal mass per node
    # --------------------------------------------------------

    Mass_X = Total_Mass_X / N_nodes
    Mass_Y = Total_Mass_Y / N_nodes

    # --------------------------------------------------------
    # Assign mass
    # --------------------------------------------------------

    for UniqueName in Story_Nodes["UniqueName"]:

        ops.mass(int(UniqueName), Mass_X, Mass_Y, 0.0, 0.0, 0.0, 0.0)

    # --------------------------------------------------------
    # Print information
    # --------------------------------------------------------

    print("=" * 60)
    print(f"Story       : {story_name}")
    print(f"Z           : {z_value} m")
    print(f"Number nodes: {N_nodes}")
    print(f"Total UX    : {Total_Mass_X:.3f} kg")
    print(f"Total UY    : {Total_Mass_Y:.3f} kg")
    print(f"Mass/node X : {Mass_X:.6f} kg")
    print(f"Mass/node Y : {Mass_Y:.6f} kg")
    print("=" * 60)
# Modal Analysis
# -------------------------- Modal Analysis -------------------------- #
numModes = 6
eigenvalues = ops.eigen(numModes)
print(f"Eigenvalues = {eigenvalues}")
omega = np.sqrt(eigenvalues)
T = 2 * np.pi / omega

for i in range(numModes):
    print(f"Mode {i+1}: T = {T[i]:.3f} sec")

Lambda = np.diag(eigenvalues)

# -------------------------- End Modal Analysis -------------------------- #
# ============================================================
# MODAL ANALYSIS
# ============================================================

numModes = 6

try:

    eigenvalues = ops.eigen(
        '-fullGenLapack',
        numModes
    )

    omega = np.sqrt(eigenvalues)
    T = 2 * np.pi / omega

    for i in range(numModes):
        print(
            f"Mode {i+1}: "
            f"lambda = {eigenvalues[i]:.6e}, "
            f"omega = {omega[i]:.4f} rad/s, "
            f"T = {T[i]:.4f} sec"
        )

except Exception as e:

    print("Eigenvalue analysis FAILED:")
    print(e)
# Time History Analysis
import os
import glob
import matplotlib.pyplot as plt
RECORD_FOLDER = "Scaled_Text_Records"
RESULT_FOLDER = "THA_Results"

os.makedirs(RESULT_FOLDER, exist_ok=True)

# Direction of earthquake excitation
# 1 = X
# 2 = Y
# 3 = Z
EQ_DIRECTION = 1

# Gravity acceleration
g = 9.81

# Convergence settings
MAX_ITER = 100
TOL = 1e-8
record_files = sorted(
    glob.glob(os.path.join(RECORD_FOLDER, "*.txt"))
)

print("=" * 70)
print(f"Number of earthquake records found: {len(record_files)}")
print("=" * 70)

if len(record_files) == 0:
    raise FileNotFoundError(
        f"No .txt files found in folder: {RECORD_FOLDER}"
    )

print("\nSaving model state after gravity analysis...")

ops.database("File", "GravityState.db")
ops.save(1)

print("Gravity state saved.")
def read_ground_motion(filename):

    data = np.loadtxt(filename)

    time = data[:, 0]
    acc_g = data[:, 1]

    # Convert g -> m/s²
    acc = acc_g * g

    # Calculate dt
    dt_array = np.diff(time)

    dt = np.median(dt_array)

    # Check whether dt is approximately constant
    if not np.allclose(
        dt_array,
        dt,
        rtol=1e-5,
        atol=1e-8
    ):
        print(
            f"WARNING: Non-uniform time step detected in {filename}"
        )

    return time, acc_g, acc, dt


def run_time_history(record_file):

    record_name = os.path.splitext(
        os.path.basename(record_file)
    )[0]

    print("\n")
    print("=" * 70)
    print(f"Running record: {record_name}")
    print("=" * 70)

    # --------------------------------------------------------
    # Restore model to post-gravity state
    # --------------------------------------------------------

    ok_restore = ops.restore(1)

    if ok_restore != 0:
        print("WARNING: ops.restore returned:", ok_restore)

    # --------------------------------------------------------
    # Read record
    # --------------------------------------------------------

    time, acc_g, acc, dt = read_ground_motion(record_file)

    n_steps = len(acc)

    total_time = time[-1]

    print(f"dt           = {dt:.6f} sec")
    print(f"Steps        = {n_steps}")
    print(f"Duration     = {total_time:.3f} sec")
    print(f"PGA          = {np.max(np.abs(acc_g)):.4f} g")
    print(f"PGA           = {np.max(np.abs(acc)):.4f} m/s²")

    # --------------------------------------------------------
    # Create unique tags
    # --------------------------------------------------------

    timeSeriesTag = 10000
    patternTag = 10000

    # --------------------------------------------------------
    # Create Path TimeSeries
    # --------------------------------------------------------

    ops.timeSeries(
        "Path",
        timeSeriesTag,
        "-dt", dt,
        "-values", *acc,
        "-factor", 1.0
    )

    # --------------------------------------------------------
    # Apply ground motion
    # --------------------------------------------------------

    ops.pattern(
        "UniformExcitation",
        patternTag,
        EQ_DIRECTION,
        "-accel",
        timeSeriesTag
    )

    # --------------------------------------------------------
    # Analysis configuration
    # --------------------------------------------------------

    ops.wipeAnalysis()

    # Constraints
    ops.constraints("Transformation")

    # DOF numbering
    ops.numberer("RCM")

    # System solver
    ops.system("UmfPack")

    # Convergence test
    ops.test(
        "NormDispIncr",
        TOL,
        MAX_ITER,
        0,
        2
    )

    # Nonlinear solution algorithm
    ops.algorithm("NewtonLineSearch")

    # Newmark integration
    gamma = 0.5
    beta = 0.25

    ops.integrator(
        "Newmark",
        gamma,
        beta
    )

    # Transient analysis
    ops.analysis("Transient")

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    results = {
        "time": [],
        "max_disp": [],
        "max_vel": [],
        "max_acc": []
    }

    # --------------------------------------------------------
    # Run analysis
    # --------------------------------------------------------

    success = True

    for step in range(n_steps):

        ok = ops.analyze(1, dt)

        if ok != 0:

            print(
                f"\nWARNING: Analysis failed at step "
                f"{step + 1}/{n_steps}"
            )

            print(
                f"Time = {ops.getTime():.6f} sec"
            )

            success = False
            break

        # ----------------------------------------------------
        # Collect response
        # ----------------------------------------------------

        current_time = ops.getTime()

        node_disp = []
        node_vel = []
        node_acc = []

        # Get all node tags
        node_tags = ops.getNodeTags()

        for node in node_tags:

            try:

                disp = ops.nodeDisp(node, EQ_DIRECTION)
                vel = ops.nodeVel(node, EQ_DIRECTION)
                acc_node = ops.nodeAccel(node, EQ_DIRECTION)

                node_disp.append(abs(disp))
                node_vel.append(abs(vel))
                node_acc.append(abs(acc_node))

            except:
                pass

        # Maximum response among all nodes
        if len(node_disp) > 0:

            results["time"].append(current_time)
            results["max_disp"].append(max(node_disp))
            results["max_vel"].append(max(node_vel))
            results["max_acc"].append(max(node_acc))

    # --------------------------------------------------------
    # Convert results to DataFrame
    # --------------------------------------------------------

    results_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    result_file = os.path.join(
        RESULT_FOLDER,
        f"{record_name}_response.csv"
    )

    results_df.to_csv(
        result_file,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    if success and len(results_df) > 0:

        max_disp = results_df["max_disp"].max()
        max_vel = results_df["max_vel"].max()
        max_acc = results_df["max_acc"].max()

        print("\nAnalysis SUCCESS")

        print(f"Maximum displacement = {max_disp:.6e} m")
        print(f"Maximum velocity     = {max_vel:.6e} m/s")
        print(f"Maximum acceleration = {max_acc:.6e} m/s²")

        print(f"Results saved to:")
        print(result_file)

    else:

        max_disp = np.nan
        max_vel = np.nan
        max_acc = np.nan

        print("\nAnalysis FAILED")

    # --------------------------------------------------------
    # Remove earthquake pattern
    # --------------------------------------------------------

    try:
        ops.remove("loadPattern", patternTag)
    except:
        pass

    return {
        "Record": record_name,
        "dt": dt,
        "Duration": total_time,
        "Steps": n_steps,
        "PGA_g": np.max(np.abs(acc_g)),
        "Max_Displacement_m": max_disp,
        "Max_Velocity_m_s": max_vel,
        "Max_Acceleration_m_s2": max_acc,
        "Success": success
    }


# ============================================================
# 6. RUN ALL EARTHQUAKE RECORDS
# ============================================================

summary = []

for record_file in record_files:

    try:

        result = run_time_history(record_file)

        summary.append(result)

    except Exception as e:

        print("\nERROR:")
        print(record_file)
        print(e)

        summary.append({
            "Record": os.path.splitext(
                os.path.basename(record_file)
            )[0],
            "dt": np.nan,
            "Duration": np.nan,
            "Steps": np.nan,
            "PGA_g": np.nan,
            "Max_Displacement_m": np.nan,
            "Max_Velocity_m_s": np.nan,
            "Max_Acceleration_m_s2": np.nan,
            "Success": False
        })


# ============================================================
# 7. SUMMARY TABLE
# ============================================================

summary_df = pd.DataFrame(summary)

summary_file = os.path.join(
    RESULT_FOLDER,
    "THA_Summary.xlsx"
)

summary_df.to_excel(
    summary_file,
    index=False
)

print("\n")
print("=" * 70)
print("ALL EARTHQUAKE RECORDS COMPLETED")
print("=" * 70)

print(summary_df)

print("\nSummary saved to:")
print(summary_file)