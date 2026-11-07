"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import Rhino.Geometry as rg

def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_sphere(base_point=None, radius=5.0):
    """
    Build a sphere as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the sphere
    radius     : float -- sphere radius

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    sphere = rg.Sphere(base_point, radius)
    return sphere.ToBrep()

def create_box(base_point=None, width=10.0, depth=10.0, height=10.0):
    """
    Build a box as a Brep.

    base_point : Rhino.Geometry.Point3d -- corner of the box (default is origin)
    width      : float -- box width along the X-axis
    depth      : float -- box depth along the Y-axis
    height     : float -- box height along the Z-axis

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    corner1 = base_point
    corner2 = rg.Point3d(base_point.X + width, base_point.Y + depth, base_point.Z + height)
    box = rg.Box(rg.BoundingBox(corner1, corner2))
    return box.ToBrep()

def create_cylinder(base_point=None, height=10.0, radius=5.0):
    """
    Build a cylinder as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cylinder's base circle
    height     : float -- cylinder height along the base plane's normal (Z by default)
    radius     : float -- base circle radius

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    circle = rg.Circle(plane, radius)
    cylinder = rg.Cylinder(circle, height)
    return cylinder.ToBrep(True, True)

def create_ring(center=None, radius=10.0, thickness=0.5):
    """
    Build a closed ring (torus) lying flat in the XY plane.

    center    : Rhino.Geometry.Point3d -- center of the ring
    radius    : float -- radius from the center to the middle of the tube
    thickness : float -- radius of the tube cross-section

    Returns a Rhino.Geometry.Brep.
    """
    if center is None:
        center = rg.Point3d(0, 0, 0)

    plane = rg.Plane(center, rg.Vector3d.ZAxis)
    torus = rg.Torus(plane, radius, thickness)
    return rg.Brep.CreateFromSurface(torus.ToRevSurface())

def create_rod(p0, p1, radius):
    """
    Build a rod (cylinder) between two points.

    p0     : Rhino.Geometry.Point3d -- start point of the rod
    p1     : Rhino.Geometry.Point3d -- end point of the rod
    radius : float -- radius of the rod

    Returns a Rhino.Geometry.Brep.
    """
    if p0 is None or p1 is None:
        raise ValueError("Both p0 and p1 must be provided.")

    height = p0.DistanceTo(p1)
    direction = rg.Vector3d(p1 - p0)
    direction.Unitize()
    plane = rg.Plane(p0, direction)
    circle = rg.Circle(plane, radius)
    cylinder = rg.Cylinder(circle, height)
    return cylinder.ToBrep(True, True)

def create_star(center=None, outer_radius=5.0, inner_radius=2.0, n_points=5, thickness=0.5):
    """
    Build an upright star (extruded star outline) standing in the XZ plane.

    center       : Rhino.Geometry.Point3d -- center of the star
    outer_radius : float -- radius of the tips
    inner_radius : float -- radius of the inner corners
    n_points     : int   -- number of tips
    thickness    : float -- extrusion depth (along Y)

    Returns a Rhino.Geometry.Brep. The first tip points straight up (+Z).
    """
    if center is None:
        center = rg.Point3d(0, 0, 0)

    # plane: x = world X, y = world Z  -> star stands upright
    plane = rg.Plane(center, rg.Vector3d.XAxis, rg.Vector3d.ZAxis)
    pts = []
    for i in range(2 * n_points):
        r = outer_radius if i % 2 == 0 else inner_radius
        a = math.pi / 2 + math.pi * i / n_points
        pts.append(plane.PointAt(r * math.cos(a), r * math.sin(a)))
    pts.append(pts[0])

    outline = rg.Polyline(pts).ToNurbsCurve()
    extrusion = rg.Extrusion.Create(outline, thickness, True)
    return extrusion.ToBrep()

def create_loft(curves, closed=False):
    """
    Loft a surface through a list of curves (all with the same number of control points).

    curves : list of Rhino.Geometry.Curve -- section curves, bottom to top
    closed : bool -- close the loft back to the first curve

    Returns a Rhino.Geometry.Brep (or None if the loft fails).
    """
    breps = rg.Brep.CreateFromLoft(curves, rg.Point3d.Unset, rg.Point3d.Unset,
                                   rg.LoftType.Normal, closed)
    return breps[0] if breps else None

def boolean_difference(brep_a, brep_b):
    """
    Perform a boolean difference operation between two Breps.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- the second Brep to subtract from the first

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, 0.001)
    return result


def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies

def rotate(brep, angle_degrees, axis_point=None, axis_direction=None):
    """
    Rotate a Brep around a specified axis.

    brep : Rhino.Geometry.Brep -- the Brep to rotate
    angle_degrees : float -- rotation angle in degrees
    axis_point : Rhino.Geometry.Point3d -- a point on the rotation axis (default is origin)
    axis_direction : Rhino.Geometry.Vector3d or str -- direction of the rotation axis,
                     either a vector or "x", "y" or "z" (default is Z-axis)

    Returns a new Rhino.Geometry.Brep that is the rotated version of the input Brep.
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if axis_point is None:
        axis_point = rg.Point3d(0, 0, 0)
    if axis_direction is None:
        axis_direction = rg.Vector3d.ZAxis
    elif isinstance(axis_direction, str):
        axes = {"x": rg.Vector3d.XAxis, "y": rg.Vector3d.YAxis, "z": rg.Vector3d.ZAxis}
        key = axis_direction.strip().lower()
        if key not in axes:
            raise ValueError('axis_direction must be a vector or "x", "y" or "z".')
        axis_direction = axes[key]

    rotation_transform = rg.Transform.Rotation(math.radians(angle_degrees), axis_direction, axis_point)
    rotated_brep = brep.DuplicateBrep()
    rotated_brep.Transform(rotation_transform)
    return rotated_brep

def translate(brep, translation_vector):
    """
    Translate a Brep by a given vector.

    brep : Rhino.Geometry.Brep -- the Brep to translate
    translation_vector : Rhino.Geometry.Vector3d -- the translation vector

    Returns a new Rhino.Geometry.Brep that is the translated version of the input Brep.
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if translation_vector is None:
        raise ValueError("translation_vector must be provided.")

    translation_transform = rg.Transform.Translation(translation_vector)
    translated_brep = brep.DuplicateBrep()
    translated_brep.Transform(translation_transform)
    return translated_brep

def boolean_union(brep_a, brep_b):
    """
    Perform a boolean union operation between two Breps.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- the second Brep to union with the first

    Returns a list of Rhino.Geometry.Brep resulting from the union.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    result = rg.Brep.CreateBooleanUnion([brep_a, brep_b], 0.001)
    return result