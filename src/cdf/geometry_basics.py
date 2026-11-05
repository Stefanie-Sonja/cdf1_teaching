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