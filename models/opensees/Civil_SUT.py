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

# Audits - Node
print("Number of nodes (filtered):", len(Node_Data))
print("Number of base nodes:", len(pd.read_excel("Geometry.xlsx", sheet_name="FIX_Node")))
print("Z levels:", sorted(Node_Data["Z (m)"].unique()))

for ID, X, Y, Z in zip(Node_Data["UniqueName"], Node_Data["X (m)"], Node_Data["Y (m)"], Node_Data["Z (m)"]):
    ops.node(ID, X, Y, Z)
# 3. Support Conditions
# -------------------------- Fixed Support -------------------------- #
# fix(nodeTag, *constrValues)
Fix_Nodes = pd.read_excel("Geometry.xlsx", sheet_name="FIX_Node")

for ID in Fix_Nodes["UniqueName"]:
    ops.fix(ID, 1, 1, 1, 1, 1, 1)  # Fixed Support

# 3b. Diaphragm Masters (ETABS rigid diaphragm - Center of Mass)
# Story masses are diaphragm masses, not distributed independent masses
CenterMass_Data = pd.read_excel("Load.xlsx", sheet_name="Center of Mass")
Floor_Data = pd.read_excel("Geometry.xlsx", sheet_name="FLOOR_Connectivity")
# Masters at center of mass per diaphragm
Master_Tags = {}
next_tag = 9000
for story in ['Story1','Story2','Story3','Story4','Story5','Story6']:
    row = CenterMass_Data[CenterMass_Data["Story"]==story].iloc[0]
    tag = next_tag; next_tag += 1
    ops.node(tag, float(row["XCM (m)"]), float(row["YCM (m)"]), float(row["ZCM (m)"]))
    ops.fix(tag, 0, 0, 1, 1, 1, 1)  # UX,UY free (lateral), UZ,RX,RY,RZ fixed
    Master_Tags[story] = tag
for d in ['D7-1','D7-2']:
    row = CenterMass_Data[CenterMass_Data["Diaphragm"]==d].iloc[0]
    tag = next_tag; next_tag += 1
    ops.node(tag, float(row["XCM (m)"]), float(row["YCM (m)"]), float(row["ZCM (m)"]))
    ops.fix(tag, 0, 0, 1, 1, 1, 1)
    Master_Tags[d] = tag
print("Diaphragm masters:", Master_Tags)

# 3c. Constraints for other nodes - lateral model with secondary fixing
# Determine primary floor nodes (deg>1) vs secondary/hanging
from collections import Counter
Deg_Count = Counter()
Col_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="COLUMN_Connectivity")
Beam_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="BEAM_Connectivity")
Brace_Ele_Data = pd.read_excel("Geometry.xlsx", sheet_name="BRACE_Connectivity")
for _, r in Col_Ele_Data.iterrows():
    Deg_Count[int(r["UniquePtI"])] += 1
    Deg_Count[int(r["UniquePtJ"])] += 1
for _, r in Beam_Ele_Data.iterrows():
    Deg_Count[int(r["UniquePtI"])] += 1
    Deg_Count[int(r["UniquePtJ"])] += 1
for _, r in Brace_Ele_Data.iterrows():
    Deg_Count[int(r["UniquePtI"])] += 1
    Deg_Count[int(r["UniquePtJ"])] += 1
Floor_Nodes = set(Floor_Data["UniquePt1"].tolist() + Floor_Data["UniquePt2"].tolist() + Floor_Data["UniquePt3"].tolist() + Floor_Data["UniquePt4"].tolist())
Floor_Nodes = Floor_Nodes & set(Node_Data["UniqueName"])
Other_Nodes = Node_Data["UniqueName"].to_list()
for i in Fix_Nodes["UniqueName"]:
    if i in Other_Nodes:
        Other_Nodes.remove(i)
primary_cnt = 0
secondary_cnt = 0
for nid in Other_Nodes:
    nid = int(nid)
    if nid in Floor_Nodes and Deg_Count[nid] > 1:
        ops.fix(nid, 0, 0, 1, 1, 1, 1)  # Primary floor - UX,UY free
        primary_cnt += 1
    else:
        ops.fix(nid, 1, 1, 1, 1, 1, 1)  # Secondary/hanging - fully fixed
        secondary_cnt += 1
print("Primary floor free (UX,UY):", primary_cnt)
print("Secondary fully fixed:", secondary_cnt)
# Diaphragm constraints - equalDOF UX,UY
for story in ['Story1','Story2','Story3','Story4','Story5','Story6']:
    slaves = set(Floor_Data[Floor_Data["Story"]==story]["UniquePt1"].tolist() + Floor_Data[Floor_Data["Story"]==story]["UniquePt2"].tolist() + Floor_Data[Floor_Data["Story"]==story]["UniquePt3"].tolist() + Floor_Data[Floor_Data["Story"]==story]["UniquePt4"].tolist())
    slaves = [int(n) for n in slaves if n in Floor_Nodes and Deg_Count[n] > 1]
    for s in slaves:
        ops.equalDOF(Master_Tags[story], s, 1, 2)
    print(f"Diaphragm {story} {len(slaves)} slaves -> master {Master_Tags[story]}")
khar = Floor_Data[Floor_Data["Story"]=="Kharposhteh"]
all_khar = set(khar["UniquePt1"].tolist() + khar["UniquePt2"].tolist() + khar["UniquePt3"].tolist() + khar["UniquePt4"].tolist())
all_khar = [n for n in all_khar if n in Floor_Nodes and Deg_Count[n] > 1]
# Split Kharposhteh by X<25 (west) vs east (ETABS D7-1/D7-2)
west = [n for n in all_khar if float(Node_Data[Node_Data["UniqueName"]==n]["X (m)"].iloc[0]) < 25]
east = [n for n in all_khar if float(Node_Data[Node_Data["UniqueName"]==n]["X (m)"].iloc[0]) >= 25]
for s in west:
    ops.equalDOF(Master_Tags['D7-1'], s, 1, 2)
for s in east:
    ops.equalDOF(Master_Tags['D7-2'], s, 1, 2)
print(f"Kharposhteh W {len(west)} -> D7-1, E {len(east)} -> D7-2")
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
E_steel = 210e9
# E_steel = 1e20  # Original bug - too stiff
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
# Col_Ele_Data, Beam_Ele_Data, Brace_Ele_Data already read for constraints
Section_Assign_Data = pd.read_excel("Geometry.xlsx", sheet_name="FRAME_Sections")
Section_Properties_Data = pd.read_excel("Geometry.xlsx", sheet_name="SECTION_Properties")
Frame_Release_Data = pd.read_excel("Geometry.xlsx", sheet_name="FRAME_Releases&PartialFixity")["UniqueName"]
# Correct section mapping: UniqueName -> Analysis Section (was Label -> first)
Sec_Map = dict(zip(Section_Assign_Data["UniqueName"], Section_Assign_Data["Analysis Section"]))
# geomTransf(transfType, transfTag, *transfArgs)
# element('elasticBeamColumn', eleTag, *eleNodes, Area, E_mod, G_mod, Jxx, Iy, Iz, transfTag, <'-mass', mass>, <'-cMass'>)
# element('Truss', eleTag, *eleNodes, A, matTag, <'-rho', rho>, <'-cMass', cFlag>, <'-doRayleigh', rFlag>)

transfType_col = 'PDelta'
transfType_beam = 'Linear'
transfType_brace_and_truss = 'PDelta'

eleTag_Column = 0
eleTag_Beam = 1000
eleTag_Brace_and_Truss = 5000



for i in range(Col_Ele_Data.shape[0]): 

    # Create Section Properties for Column:
    section_name = Sec_Map[int(Col_Ele_Data.loc[i, "UniqueName"])]
    eleNodes = [int(Col_Ele_Data.loc[i, "UniquePtI"]), int(Col_Ele_Data.loc[i, "UniquePtJ"])]
    column_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]
    Jxx_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "J (m^4)"].iloc[0]
    Iy_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I33 (m^4)"].iloc[0]
    Iz_col = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I22 (m^4)"].iloc[0]

    # Columns: always elasticBeamColumn (release is pinned-pinned, not Truss)
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
    transfTag_col = eleTag_Column
    ops.geomTransf(transfType_col, transfTag_col, *vecxz_col)
    ops.element('elasticBeamColumn', eleTag_Column, *eleNodes, column_area, E_steel, G_steel, Jxx_col, Iy_col, Iz_col, transfTag_col, '-mass', 0.0)

for j in range(Beam_Ele_Data.shape[0]):
    
    # Create Section Properties for Beam:
    section_name = Sec_Map[int(Beam_Ele_Data.loc[j, "UniqueName"])]
    eleNodes = [int(Beam_Ele_Data.loc[j, "UniquePtI"]), int(Beam_Ele_Data.loc[j, "UniquePtJ"])]
    beam_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]
    Jxx_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "J (m^4)"].iloc[0]
    Iy_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I33 (m^4)"].iloc[0]
    Iz_beam = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "I22 (m^4)"].iloc[0]

    # Beams: always elasticBeamColumn
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
    transfTag_beam =  eleTag_Beam
    ops.geomTransf(transfType_beam, transfTag_beam, *vecxz_beam)
    ops.element('elasticBeamColumn', eleTag_Beam, *eleNodes, beam_area, E_steel, G_steel, Jxx_beam, Iy_beam, Iz_beam, transfTag_beam, '-mass', 0.0)

for k in range(Brace_Ele_Data.shape[0]):
    eleTag_Brace_and_Truss += 1
    eleName = (Brace_Ele_Data.loc[k, "BraceBay"])
    section_name = Sec_Map[int(Brace_Ele_Data.loc[k, "UniqueName"])]
    eleNodes = [int(Brace_Ele_Data.loc[k, "UniquePtI"]), int(Brace_Ele_Data.loc[k, "UniquePtJ"])]
    brace_area = Section_Properties_Data.loc[Section_Properties_Data["Name"] == section_name, "Area (m^2)"].iloc[0]

    # Braces: always Truss (two-force, M+T released)
    cFlag = 0
    rFlag = 0
    ops.element('Truss', eleTag_Brace_and_Truss, *eleNodes, brace_area, MAT_TAG_STEEL, '-rho', rho_steel, '-cMass', cFlag, '-doRayleigh', rFlag)

print("Number of elements:", len(ops.getEleTags()))
print("Columns:", len(Col_Ele_Data), "Beams:", len(Beam_Ele_Data), "Braces:", len(Brace_Ele_Data))
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
# MASS ASSIGNMENT BASED ON STORY MASS - Diaphragm Masters
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
    "Kharposhteh": 31.8,
}


# ============================================================
# MASS ASSIGNMENT - Masters only
# ============================================================

for story_name in ["Story1","Story2","Story3","Story4","Story5","Story6"]:
    Mass_Row = Story_Mass_Data[Story_Mass_Data["Story"].astype(str).str.strip()== story_name].iloc[0]
    Total_Mass_X = float(Mass_Row["UX"]) * 1000.0
    Total_Mass_Y = float(Mass_Row["UY"]) * 1000.0
    tag = Master_Tags[story_name]
    ops.mass(tag, Total_Mass_X, Total_Mass_Y, 0.0, 0.0, 0.0, 0.0)
    print("=" * 60)
    print(f"Story       : {story_name}")
    print(f"Master      : {tag}")
    print(f"Total UX    : {Total_Mass_X:.3f} kg")
    print(f"Total UY    : {Total_Mass_Y:.3f} kg")
    print("=" * 60)
for d in ['D7-1','D7-2']:
    row = CenterMass_Data[CenterMass_Data["Diaphragm"]==d].iloc[0]
    m = float(row["Mass X (ton)"])*1000.0
    tag = Master_Tags[d]
    ops.mass(tag, m, m, 0.0, 0.0, 0.0, 0.0)
    print("=" * 60)
    print(f"Story       : Kharposhteh {d}")
    print(f"Master      : {tag}")
    print(f"Total UX    : {m:.3f} kg")
    print("=" * 60)
# Modal Analysis
# -------------------------- Modal Analysis -------------------------- #
numModes = 12
# With diaphragm, independent DOFs = 8 masters *2 =16, so request <16
try:
    eigenvalues = ops.eigen(numModes)
except:
    numModes = 8
    eigenvalues = ops.eigen(numModes)
print(f"Eigenvalues = {eigenvalues}")
omega = np.sqrt(eigenvalues)
T = 2 * np.pi / omega

for i in range(numModes):
    print(f"Mode {i+1}: T = {T[i]:.3f} sec")

Lambda = np.diag(eigenvalues)

# -------------------------- End Modal Analysis -------------------------- #
# ============================================================
# MODAL ANALYSIS - Participation
# ============================================================

totalM = float(Story_Mass_Data["UX"].sum()*1000)
master_masses = {}
for s in ['Story1','Story2','Story3','Story4','Story5','Story6']:
    master_masses[Master_Tags[s]] = float(Story_Mass_Data[Story_Mass_Data["Story"]==s]["UX"].iloc[0])*1000
for d in ['D7-1','D7-2']:
    master_masses[Master_Tags[d]] = float(CenterMass_Data[CenterMass_Data["Diaphragm"]==d]["Mass X (ton)"].iloc[0])*1000
print("="*60)
print("Modal Participation (diaphragm masters):")
print("="*60)
cumX = 0; cumY = 0
for mode in range(1, numModes+1):
    phiMrX = 0; phiMphiX = 0; phiMrY = 0; phiMphiY = 0
    for nid, mass in master_masses.items():
        try: phix = ops.nodeEigenvector(int(nid), mode, 1)
        except: phix = 0
        try: phiy = ops.nodeEigenvector(int(nid), mode, 2)
        except: phiy = 0
        phiMrX += mass*phix; phiMphiX += mass*phix*phix
        phiMrY += mass*phiy; phiMphiY += mass*phiy*phiy
    effX = (phiMrX**2)/phiMphiX if phiMphiX>1e-12 else 0
    effY = (phiMrY**2)/phiMphiY if phiMphiY>1e-12 else 0
    cumX += effX; cumY += effY
    print(f"Mode {mode:2d} T={T[mode-1]:.3f}s effX {effX/totalM*100:5.1f}% effY {effY/totalM*100:5.1f}% cumX {cumX/totalM*100:5.1f}% cumY {cumY/totalM*100:5.1f}%")

# ============================================================
# MODAL ANALYSIS
# ============================================================

numModes = 12
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
PLOTS_FOLDER = os.path.join(RESULT_FOLDER, "Plots")

os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(PLOTS_FOLDER, exist_ok=True)

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


def run_time_history(record_file, record_index):

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

    # ops.restore returns None on success in this OpenSeesPy version - do not treat None as failure
    try:
        ops.restore(1)
    except Exception as e:
        print(f"WARNING: ops.restore failed: {e}")

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

    timeSeriesTag = 10000 + record_index
    patternTag = 20000 + record_index

    print(f"TimeSeries tag = {timeSeriesTag}")
    print(f"Pattern tag    = {patternTag}")

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
        # --------------------------------------------------------

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
    # Plots for this record
    # --------------------------------------------------------

    if success and len(results_df) > 0:
        try:
            # 1. Ground motion
            plt.figure(figsize=(10, 4))
            plt.plot(time, acc, linewidth=0.8)
            plt.xlabel("Time (s)")
            plt.ylabel("Ground Acceleration (m/s2)")
            plt.title(f"Ground Motion - {record_name}")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(PLOTS_FOLDER, f"{record_name}_ground_motion.png"), dpi=150)
            plt.close()
            # 2. Roof displacement (master Story6 / D7-1)
            roof_master = Master_Tags.get('Story6', Master_Tags.get('D7-1'))
            # Roof displacement already in max_disp, but also plot master displacement if available
            plt.figure(figsize=(10, 4))
            plt.plot(results["time"], results["max_disp"], linewidth=0.8, label="Max Displacement")
            plt.xlabel("Time (s)")
            plt.ylabel("Roof Displacement (m)")
            plt.title(f"Roof Displacement - {record_name}")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(PLOTS_FOLDER, f"{record_name}_roof_disp.png"), dpi=150)
            plt.close()
            # 3. Roof velocity
            plt.figure(figsize=(10, 4))
            plt.plot(results["time"], results["max_vel"], linewidth=0.8, color="green")
            plt.xlabel("Time (s)")
            plt.ylabel("Roof Velocity (m/s)")
            plt.title(f"Roof Velocity - {record_name}")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(PLOTS_FOLDER, f"{record_name}_roof_vel.png"), dpi=150)
            plt.close()
            # 4. Roof acceleration
            plt.figure(figsize=(10, 4))
            plt.plot(results["time"], results["max_acc"], linewidth=0.8, color="red")
            plt.xlabel("Time (s)")
            plt.ylabel("Roof Acceleration (m/s2)")
            plt.title(f"Roof Acceleration - {record_name} (relative)")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(PLOTS_FOLDER, f"{record_name}_roof_acc.png"), dpi=150)
            plt.close()
        except Exception as e:
            print(f"WARNING: Plot failed for {record_name}: {e}")

    # --------------------------------------------------------
    # Remove earthquake pattern and timeSeries
    # --------------------------------------------------------

    try:
        ops.remove("loadPattern", patternTag)
    except:
        pass
    try:
        ops.remove("timeSeries", timeSeriesTag)
    except:
        pass
    # Clear analysis to avoid recorder interference
    try:
        ops.wipeAnalysis()
    except:
        pass

    return {
        "Record": record_name,
        "dt": dt,
        "Duration": total_time,
        "Steps": n_steps,
        "PGA_g": np.max(np.abs(acc_g)),
        "PGA_m_s2": np.max(np.abs(acc)),
        "Max_Displacement_m": max_disp,
        "Max_Velocity_m_s": max_vel,
        "Max_Acceleration_m_s2": max_acc,
        "Success": success,
        "Failure_Reason": "" if success else "Analysis failed",
        "TimeSeriesTag": timeSeriesTag,
        "PatternTag": patternTag
    }


# ============================================================
# 6. RUN ALL EARTHQUAKE RECORDS
# ============================================================

summary = []

for idx, record_file in enumerate(record_files):

    try:

        result = run_time_history(record_file, idx)

        summary.append(result)

    except Exception as e:

        print("\nERROR:")
        print(record_file)
        print(e)
        import traceback
        traceback.print_exc()

        failure_reason = str(e)
        if "tag: 10000" in failure_reason or "could not add timeseries" in failure_reason.lower():
            failure_reason = "TimeSeries tag collision - " + failure_reason
        elif "tag:" in failure_reason.lower():
            failure_reason = "Tag collision - " + failure_reason

        summary.append({
            "Record": os.path.splitext(
                os.path.basename(record_file)
            )[0],
            "dt": np.nan,
            "Duration": np.nan,
            "Steps": np.nan,
            "PGA_g": np.nan,
            "PGA_m_s2": np.nan,
            "Max_Displacement_m": np.nan,
            "Max_Velocity_m_s": np.nan,
            "Max_Acceleration_m_s2": np.nan,
            "Success": False,
            "Failure_Reason": failure_reason,
            "TimeSeriesTag": 10000 + idx,
            "PatternTag": 20000 + idx
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
