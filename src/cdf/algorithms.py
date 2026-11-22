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
import random

def create_fractal_tree(
    base_point=None,
    base_plane=None,
    length=10.0,
    angle=25.0,
    length_factor=0.7,
    depth=8,
    branch_count=2,
):
    """
    Build a fractal (recursively branching) tree as a list of line segments.

    base_point    : Rhino.Geometry.Point3d -- start point of the trunk
    base_plane    : Rhino.Geometry.Plane   -- plane whose YAxis is the trunk
                     direction and ZAxis is the branching rotation axis
    length        : float -- trunk length
    angle         : float -- angle in degrees between sibling branches
    length_factor : float -- length multiplier applied at each new generation
    depth         : int   -- number of recursive branching generations
    branch_count  : int   -- number of branches spawned at each node

    Returns a list of Rhino.Geometry.Line.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if base_plane is None:
        base_plane = rg.Plane.WorldXY

    lines = []

    def _grow(start, direction, branch_length, remaining_depth):
        if remaining_depth <= 0 or branch_length <= 1e-6:
            return

        end = start + direction * branch_length
        lines.append(rg.Line(start, end))

        if branch_count <= 1:
            offsets = [0.0]
        else:
            span = angle * (branch_count - 1)
            offsets = [-span / 2.0 + i * angle for i in range(branch_count)]

        for offset in offsets:
            rotated_direction = rg.Vector3d(direction)
            rotated_direction.Rotate(math.radians(offset), base_plane.ZAxis)
            _grow(end, rotated_direction, branch_length * length_factor, remaining_depth - 1)

    _grow(base_point, base_plane.YAxis, length, depth)

    return lines


def create_crochet_pseudosphere(
    rounds=4,
    first_round=12,
    increase=3,
    base_chain=4,
    stitch_width=1.0,
    stitch_height=2.0,
    iterations=150,
    seed=1,
    max_stitches=1500,
):
    """Build a crocheted hyperbolic form ("pseudosphere") as a mesh.

    The function follows the crochet pattern step by step:
      1. a small ring made of chain stitches,
      2. a first round of double crochets into the ring,
      3. more rounds, where every stitch gets `increase` new stitches.

    Each stitch is one mesh vertex. After every new round the stitches are
    relaxed like small springs: a stitch wants to keep its width and its
    height, and two stitches cannot be in the same place. Each round has more
    stitches than a flat circle has room for, so the surface has to ruffle.

    Params:
        rounds (int): Number of rounds worked into the ring. Default 4.
            Stitch count is multiplied by `increase` every round, so keep
            this low (5 rounds with increase 3 is already 972 stitches).
        first_round (int): Stitches in the first round. Default 12.
        increase (int): New stitches worked into each stitch. Default 3.
            1 gives a tube, 2 gives soft ruffles, 3 gives dense ruffles.
        base_chain (int): Chain stitches in the starting ring. Default 4.
            Only sets the size of the hole in the middle.
        stitch_width (float): Width of one stitch. Default 1.0.
        stitch_height (float): Height of one round. Default 2.0
            (a double crochet is about twice as tall as it is wide).
        iterations (int): Relaxation steps after each round. Default 150.
            More steps give a smoother result but take longer.
        seed (int): Seed for the small random offsets that let the surface
            ruffle. Same seed gives the same shape. Default 1.
        max_stitches (int): Safety limit on stitches in a single round.
            Rounds that would exceed it are skipped, so the form stops
            growing instead of freezing Rhino. Default 1500.

    Returns:
        Rhino.Geometry.Mesh: The crocheted surface. Each vertex is the top
        of one stitch, each ring of vertices is one round.
    """
    rng = random.Random(seed)

    points = []    # [x, y, z] of every stitch
    fixed = []     # True for stitches that must not move (the starting ring)
    springs = []   # (i, j, rest_length, stiffness)
    linked = set() # pairs joined by a spring, these are skipped in collision
    faces = []     # (a, b, c) vertex indices

    def add_spring(i, j, rest, stiffness):
        springs.append((i, j, rest, stiffness))
        linked.add((min(i, j), max(i, j)))

    # ------------------------------------------------------------------
    # 1 + 2. Starting ring (the joined chain). It stays fixed at the origin.
    # ------------------------------------------------------------------
    ring_radius = base_chain * stitch_width / (2.0 * math.pi)
    ring = []
    for i in range(first_round):
        angle = 2.0 * math.pi * i / first_round
        points.append([ring_radius * math.cos(angle),
                       ring_radius * math.sin(angle),
                       0.0])
        fixed.append(True)
        ring.append(i)

    # ------------------------------------------------------------------
    # Relaxation: springs keep stitch sizes, collisions keep stitches apart.
    # ------------------------------------------------------------------
    collision_distance = 0.9 * stitch_width

    def relax(steps):
        for _ in range(steps):
            # springs
            for i, j, rest, stiffness in springs:
                a = points[i]
                b = points[j]
                dx = b[0] - a[0]
                dy = b[1] - a[1]
                dz = b[2] - a[2]
                length = math.sqrt(dx * dx + dy * dy + dz * dz)
                if length < 1e-9:
                    continue
                move = stiffness * (length - rest) / length
                if fixed[i] and fixed[j]:
                    continue
                if fixed[i]:
                    b[0] -= dx * move
                    b[1] -= dy * move
                    b[2] -= dz * move
                elif fixed[j]:
                    a[0] += dx * move
                    a[1] += dy * move
                    a[2] += dz * move
                else:
                    move *= 0.5
                    a[0] += dx * move
                    a[1] += dy * move
                    a[2] += dz * move
                    b[0] -= dx * move
                    b[1] -= dy * move
                    b[2] -= dz * move

            # collisions: sort stitches into a grid, compare only neighbours
            cell = collision_distance
            grid = {}
            for index, p in enumerate(points):
                key = (int(math.floor(p[0] / cell)),
                       int(math.floor(p[1] / cell)),
                       int(math.floor(p[2] / cell)))
                grid.setdefault(key, []).append(index)

            for (cx, cy, cz), members in grid.items():
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for oz in (-1, 0, 1):
                            others = grid.get((cx + ox, cy + oy, cz + oz))
                            if not others:
                                continue
                            for i in members:
                                for j in others:
                                    if j <= i:
                                        continue
                                    if fixed[i] and fixed[j]:
                                        continue
                                    if (i, j) in linked:
                                        continue
                                    a = points[i]
                                    b = points[j]
                                    dx = b[0] - a[0]
                                    dy = b[1] - a[1]
                                    dz = b[2] - a[2]
                                    d2 = dx * dx + dy * dy + dz * dz
                                    if d2 >= cell * cell or d2 < 1e-12:
                                        continue
                                    dist = math.sqrt(d2)
                                    push = (cell - dist) / dist
                                    if fixed[i]:
                                        b[0] += dx * push
                                        b[1] += dy * push
                                        b[2] += dz * push
                                    elif fixed[j]:
                                        a[0] -= dx * push
                                        a[1] -= dy * push
                                        a[2] -= dz * push
                                    else:
                                        push *= 0.5
                                        a[0] -= dx * push
                                        a[1] -= dy * push
                                        a[2] -= dz * push
                                        b[0] += dx * push
                                        b[1] += dy * push
                                        b[2] += dz * push

    # ------------------------------------------------------------------
    # 3 + 4. Work the rounds. Round 1 puts one stitch on each ring position,
    # every later round puts `increase` stitches into each stitch.
    # ------------------------------------------------------------------
    grow_from = {}  # stitch index -> index of the stitch it was worked into

    for round_index in range(rounds):
        per_stitch = 1 if round_index == 0 else increase
        if len(ring) * per_stitch > max_stitches:
            break  # next round would be too big, stop at the last one that fits
        new_ring = []
        children_of = []

        for parent in ring:
            p = points[parent]

            # growth direction: continue the line from grandparent to parent
            if parent in grow_from:
                g = points[grow_from[parent]]
                direction = [p[0] - g[0], p[1] - g[1], p[2] - g[2]]
            else:
                direction = [p[0], p[1], 0.0]
            size = math.sqrt(sum(c * c for c in direction)) or 1.0
            direction = [c / size for c in direction]

            children = []
            for _ in range(per_stitch):
                jitter = 0.3 * stitch_width
                points.append([
                    p[0] + direction[0] * stitch_height + rng.uniform(-jitter, jitter),
                    p[1] + direction[1] * stitch_height + rng.uniform(-jitter, jitter),
                    p[2] + direction[2] * stitch_height + rng.uniform(-jitter, jitter),
                ])
                fixed.append(False)
                child = len(points) - 1
                grow_from[child] = parent
                children.append(child)
                new_ring.append(child)
                # the post of the stitch
                add_spring(parent, child, stitch_height, 1.0)
            children_of.append(children)

        count = len(new_ring)
        for k in range(count):
            # top of the round: every stitch is one stitch_width wide
            add_spring(new_ring[k], new_ring[(k + 1) % count], stitch_width, 1.0)
            # weak spring to the stitch after next, keeps the round smooth
            if count > 4:
                add_spring(new_ring[k], new_ring[(k + 2) % count],
                           2.0 * stitch_width, 0.15)

        # faces between the old round and the new round
        parents = len(ring)
        for j in range(parents):
            children = children_of[j]
            next_parent = ring[(j + 1) % parents]
            next_child = children_of[(j + 1) % parents][0]
            for k in range(len(children) - 1):
                faces.append((ring[j], children[k], children[k + 1]))
            faces.append((ring[j], children[-1], next_child))
            faces.append((ring[j], next_child, next_parent))

        ring = new_ring
        relax(iterations)

    # ------------------------------------------------------------------
    # Build the Rhino mesh
    # ------------------------------------------------------------------
    mesh = rg.Mesh()
    for p in points:
        mesh.Vertices.Add(p[0], p[1], p[2])
    for a, b, c in faces:
        mesh.Faces.AddFace(a, b, c)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh



def create_crochet_hyperbolic_surface(
    base_chain=16,
    rows=3,
    increase=2,
    stitch_width=1.0,
    stitch_height=2.0,
    gravity=0.01,
    bending=0.5,
    iterations=300,
    seed=1,
    max_stitches=1500,
):
    """Build the crocheted hyperbolic surface (Example 2) as a mesh.

    The function follows the pseudocode CrochetHyperbolicSurface:
      1. crochet a chain of `base_chain` stitches (the base line),
      2. for every row, work `increase` double crochets into each stitch
         of the line below, then turn the work.

    Every row has `increase` times the stitches of the row before
    (16 -> 32 -> 64 -> 128 with the defaults). All rows run side by side,
    so they turn through the same angle around the centre: a row with 8x
    the stitches has to sit at 8x the radius. The chain is short and the
    last row is long, so the strip winds around itself into a spiral
    (about 3 turns with the defaults), and because the inner rows are
    short they hang down steeply while the outer rows spread out: a cone.

    The stitches are placed on that spiral row by row, then relaxed like
    small springs: a stitch keeps its width and height, two stitches can't
    be in the same place, the yarn resists bending away from the spiral,
    and gravity pulls everything down. Where the rows don't fit exactly,
    the surface ruffles. Only the first chain stitch (where the string is
    attached) is fixed.

    Params:
        base_chain (int): Chain stitches in the base line.
            Pseudocode: base_chain_stitch_count. Default 16.
        rows (int): Rows worked onto the chain. Default 3.
        increase (int): Double crochets worked into each stitch.
            Default 2 (every row doubles). 1 gives a flat strip.
        stitch_width (float): Width of one stitch. Default 1.0.
        stitch_height (float): Height of one row. Default 2.0
            (a double crochet is about twice as tall as it is wide).
        gravity (float): How far every stitch is pulled down per
            relaxation step. 0 = no gravity. Default 0.01.
        bending (float): Stiffness of the yarn against bending, 0 = completely
            floppy (the spiral collapses into small ruffles), 1 = stiff.
            Default 0.5.
        iterations (int): Relaxation steps after each row. Default 300.
        seed (int): Seed for the small random offsets that let the surface
            ruffle. Same seed gives the same shape. Default 1.
        max_stitches (int): Safety limit on stitches in a single row.
            Rows that would exceed it are skipped. Default 1500.

    Returns:
        Rhino.Geometry.Mesh: The crocheted surface. Each vertex is the top
        of one stitch, each line of vertices is one row.
    """
    rng = random.Random(seed)
    increase = max(1, int(increase))
    base_chain = max(2, int(base_chain))

    # ------------------------------------------------------------------
    # 0. Count the stitches of every line, like current_stitches_in_line
    #    in the pseudocode. Index 0 is the chain.
    # ------------------------------------------------------------------
    counts = [base_chain]
    for _ in range(rows):
        if counts[-1] * increase > max_stitches:
            break  # next row would be too big, stop at the last one that fits
        counts.append(counts[-1] * increase)
    row_total = len(counts) - 1

    # ------------------------------------------------------------------
    # The spiral plan. Every line turns through the same angle `sweep`
    # around the vertical axis; its radius is its length / sweep.
    # The sweep is chosen so that, on average, neighbouring lines are one
    # stitch_height apart.
    # ------------------------------------------------------------------
    lengths = [n * stitch_width for n in counts]
    if row_total > 0 and lengths[-1] > lengths[0]:
        sweep = (lengths[-1] - lengths[0]) / (row_total * stitch_height)
    else:
        sweep = 0.0  # increase = 1: no extra length, a flat strip

    radii = [length / sweep for length in lengths] if sweep else []

    # how far each line hangs below the chain: short gaps between radii
    # mean the stitch hangs down steeply, long gaps mean it lies flat
    drops = [0.0]
    for r in range(1, len(counts)):
        if sweep:
            gap = radii[r] - radii[r - 1]
            drops.append(drops[-1] + math.sqrt(max(stitch_height ** 2 - gap ** 2, 0.0)))
        else:
            drops.append(0.0)
    # one turn of the spiral sits below the previous one, with a small gap
    pitch = drops[-1] + stitch_width

    def plan(r, k):
        """Planned position of stitch k in line r."""
        t = (k + 0.5) / counts[r]  # 0..1 along the line
        if not sweep:
            return [t * lengths[0], r * stitch_height, 0.0]
        angle = sweep * t
        return [radii[r] * math.cos(angle),
                radii[r] * math.sin(angle),
                -pitch * angle / (2.0 * math.pi) - drops[r]]

    def distance(a, b):
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    points = []    # [x, y, z] of every stitch
    planned = []   # planned position of every stitch
    fixed = []     # True for stitches that must not move
    springs = []   # (i, j, rest_length, stiffness)
    linked = set() # pairs joined by a spring, these are skipped in collision
    faces = []     # (a, b, c) vertex indices

    def add_spring(i, j, rest, stiffness):
        springs.append((i, j, rest, stiffness))
        linked.add((min(i, j), max(i, j)))

    def add_line_springs(line):
        # every stitch is one stitch_width wide. The line is open: the last
        # stitch does NOT connect back to the first.
        n = len(line)
        for k in range(n - 1):
            add_spring(line[k], line[k + 1], stitch_width, 1.0)
            # bending: the stitch after next keeps its distance on the spiral
            if bending and k + 2 < n:
                rest = distance(planned[line[k]], planned[line[k + 2]])
                add_spring(line[k], line[k + 2], rest, bending)

    # ------------------------------------------------------------------
    # 1. Base line: the chain. Only the first stitch is fixed, it is where
    #    the ornament hangs from its string.
    # ------------------------------------------------------------------
    line = []
    for k in range(counts[0]):
        p = plan(0, k)
        points.append(list(p))
        planned.append(p)
        fixed.append(k == 0)
        line.append(k)
    add_line_springs(line)

    # ------------------------------------------------------------------
    # Relaxation: springs keep stitch sizes, collisions keep stitches
    # apart, gravity pulls down.
    # ------------------------------------------------------------------
    collision_distance = 0.9 * stitch_width

    def relax(steps):
        for _ in range(steps):
            # gravity
            if gravity:
                for index, p in enumerate(points):
                    if not fixed[index]:
                        p[2] -= gravity

            # springs
            for i, j, rest, stiffness in springs:
                if fixed[i] and fixed[j]:
                    continue
                a = points[i]
                b = points[j]
                dx = b[0] - a[0]
                dy = b[1] - a[1]
                dz = b[2] - a[2]
                length = math.sqrt(dx * dx + dy * dy + dz * dz)
                if length < 1e-9:
                    continue
                move = stiffness * (length - rest) / length
                if fixed[i]:
                    b[0] -= dx * move
                    b[1] -= dy * move
                    b[2] -= dz * move
                elif fixed[j]:
                    a[0] += dx * move
                    a[1] += dy * move
                    a[2] += dz * move
                else:
                    move *= 0.5
                    a[0] += dx * move
                    a[1] += dy * move
                    a[2] += dz * move
                    b[0] -= dx * move
                    b[1] -= dy * move
                    b[2] -= dz * move

            # collisions: sort stitches into a grid, compare only neighbours
            cell = collision_distance
            grid = {}
            for index, p in enumerate(points):
                key = (int(math.floor(p[0] / cell)),
                       int(math.floor(p[1] / cell)),
                       int(math.floor(p[2] / cell)))
                grid.setdefault(key, []).append(index)

            for (cx, cy, cz), members in grid.items():
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for oz in (-1, 0, 1):
                            others = grid.get((cx + ox, cy + oy, cz + oz))
                            if not others:
                                continue
                            for i in members:
                                for j in others:
                                    if j <= i:
                                        continue
                                    if fixed[i] and fixed[j]:
                                        continue
                                    if (i, j) in linked:
                                        continue
                                    a = points[i]
                                    b = points[j]
                                    dx = b[0] - a[0]
                                    dy = b[1] - a[1]
                                    dz = b[2] - a[2]
                                    d2 = dx * dx + dy * dy + dz * dz
                                    if d2 >= cell * cell or d2 < 1e-12:
                                        continue
                                    dist = math.sqrt(d2)
                                    push = (cell - dist) / dist
                                    if fixed[i]:
                                        b[0] += dx * push
                                        b[1] += dy * push
                                        b[2] += dz * push
                                    elif fixed[j]:
                                        a[0] -= dx * push
                                        a[1] -= dy * push
                                        a[2] -= dz * push
                                    else:
                                        push *= 0.5
                                        a[0] -= dx * push
                                        a[1] -= dy * push
                                        a[2] -= dz * push
                                        b[0] += dx * push
                                        b[1] += dy * push
                                        b[2] += dz * push

    # ------------------------------------------------------------------
    # 2. Hyperbolic expansion in rows: `increase` double crochets into
    #    each stitch of the line below, then turn the work.
    # ------------------------------------------------------------------
    grow_from = {}  # stitch index -> index of the stitch it was worked into

    for r in range(1, row_total + 1):
        new_line = []
        children_of = []

        for s, parent in enumerate(line):
            children = []
            for k in range(increase):
                # place the new stitch where the plan says, measured from
                # where its parent actually is after the last relaxation
                target = plan(r, s * increase + k)
                offset = [target[i] - planned[parent][i] for i in range(3)]
                jitter = 0.1 * stitch_width
                points.append([
                    points[parent][i] + offset[i] + rng.uniform(-jitter, jitter)
                    for i in range(3)
                ])
                planned.append(target)
                fixed.append(False)
                child = len(points) - 1
                grow_from[child] = parent
                children.append(child)
                new_line.append(child)
                # the post of the stitch
                add_spring(parent, child, stitch_height, 1.0)
                # bending across the rows: keep the stitch in line with the
                # stitch two rows below
                if bending and parent in grow_from:
                    grandparent = grow_from[parent]
                    rest = distance(planned[grandparent], target)
                    add_spring(grandparent, child, rest, bending)
            children_of.append(children)

        add_line_springs(new_line)

        # faces between the old line and the new line (no wrap-around)
        parents = len(line)
        for j in range(parents):
            children = children_of[j]
            for k in range(len(children) - 1):
                faces.append((line[j], children[k], children[k + 1]))
            if j + 1 < parents:
                next_parent = line[j + 1]
                next_child = children_of[j + 1][0]
                faces.append((line[j], children[-1], next_child))
                faces.append((line[j], next_child, next_parent))

        line = new_line
        # turn_work(): the next row is worked back along this line. For the
        # geometry the order doesn't matter, every stitch still sits on top
        # of the stitch it was worked into.
        relax(iterations)

    # ------------------------------------------------------------------
    # Build the Rhino mesh
    # ------------------------------------------------------------------
    mesh = rg.Mesh()
    for p in points:
        mesh.Vertices.Add(p[0], p[1], p[2])
    for a, b, c in faces:
        mesh.Faces.AddFace(a, b, c)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh

# ======================================================================
# Blooming algae -- combines the crocheted pseudosphere and the crocheted
# hyperbolic surface into a growing seaweed with ruffle blooms.
# Uses create_crochet_pseudosphere and create_crochet_hyperbolic_surface
# from this file as building blocks.
# ======================================================================

_ALGAE_CACHE = {}


def _mesh_to_lists(mesh):
    """Copy a Rhino mesh into plain Python lists (points, triangles)."""
    pts = []
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        pts.append([v.X, v.Y, v.Z])
    faces = []
    for i in range(mesh.Faces.Count):
        f = mesh.Faces[i]
        faces.append((f.A, f.B, f.C))
    return pts, faces


def _smooth(pts, faces, iterations):
    """Taubin smoothing: softens sharp folds without shrinking the shape."""
    if iterations <= 0:
        return pts
    neighbours = [set() for _ in pts]
    for a, b, c in faces:
        neighbours[a].update((b, c))
        neighbours[b].update((a, c))
        neighbours[c].update((a, b))
    pts = [list(p) for p in pts]
    for _ in range(iterations):
        for factor in (0.5, -0.53):
            new = []
            for i, p in enumerate(pts):
                nb = neighbours[i]
                if not nb:
                    new.append(p)
                    continue
                avg = [sum(pts[j][k] for j in nb) / len(nb) for k in range(3)]
                new.append([p[k] + factor * (avg[k] - p[k]) for k in range(3)])
            pts = new
    return pts


def _spiral_shape(rows, seed, smooth):
    """A hyperbolic spiral, hanging point at the origin, hanging down -Z.
    Scaled so the fully grown spiral (3 rows) is 1 unit long, so younger
    spirals are simply smaller."""
    key = ("spiral", rows, seed, smooth)
    if key not in _ALGAE_CACHE:
        ref_key = ("spiral_height", seed)
        if ref_key not in _ALGAE_CACHE:
            ref, _ = _mesh_to_lists(create_crochet_hyperbolic_surface(rows=3, seed=seed, iterations=150))
            zs = [p[2] for p in ref]
            _ALGAE_CACHE[ref_key] = max(zs) - min(zs)
        height = _ALGAE_CACHE[ref_key]
        pts, faces = _mesh_to_lists(create_crochet_hyperbolic_surface(rows=rows, seed=seed, iterations=150))
        x0, y0, z0 = pts[0]
        pts = [[(p[0] - x0) / height, (p[1] - y0) / height, (p[2] - z0) / height] for p in pts]
        _ALGAE_CACHE[key] = (_smooth(pts, faces, smooth), faces)
    return _ALGAE_CACHE[key]


def _ball_shape(rounds, seed, smooth):
    """A pseudosphere, centred at the origin, radius 1."""
    key = ("ball", rounds, seed, smooth)
    if key not in _ALGAE_CACHE:
        pts, faces = _mesh_to_lists(create_crochet_pseudosphere(rounds=rounds, seed=seed, iterations=80))
        n = float(len(pts))
        c = [sum(p[k] for p in pts) / n for k in range(3)]
        pts = [[p[k] - c[k] for k in range(3)] for p in pts]
        r = max(max(abs(v) for v in p) for p in pts) or 1.0
        pts = [[v / r for v in p] for p in pts]
        _ALGAE_CACHE[key] = (_smooth(pts, faces, smooth), faces)
    return _ALGAE_CACHE[key]


def _unit(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return [v[0] / length, v[1] / length, v[2] / length]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _rotation_from_to(a, b):
    """3x3 matrix that turns direction a into direction b (Rodrigues)."""
    a, b = _unit(a), _unit(b)
    v = _cross(a, b)
    c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    if math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) < 1e-9:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]] if c > 0 else [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
    k = 1.0 / (1.0 + c)
    vx = [[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]
    vx2 = [[sum(vx[i][m] * vx[m][j] for m in range(3)) for j in range(3)] for i in range(3)]
    return [[(1 if i == j else 0) + vx[i][j] + vx2[i][j] * k for j in range(3)] for i in range(3)]


class _MeshBuilder(object):
    """Collects many placed pieces into ONE Rhino mesh (fast to preview)."""

    def __init__(self):
        self.pts = []
        self.faces = []

    def add(self, shape, origin, direction=(0, 0, -1), length=1.0, spin=0.0):
        pts, faces = shape
        rot = _rotation_from_to([0, 0, -1], direction)
        cs, sn = math.cos(spin), math.sin(spin)
        offset = len(self.pts)
        for p in pts:
            # spin around the spiral's own axis, scale, turn, move
            q = [p[0] * cs - p[1] * sn, p[0] * sn + p[1] * cs, p[2]]
            q = [q[0] * length, q[1] * length, q[2] * length]
            q = [sum(rot[i][j] * q[j] for j in range(3)) for i in range(3)]
            self.pts.append([q[0] + origin[0], q[1] + origin[1], q[2] + origin[2]])
        for a, b, c in faces:
            self.faces.append((a + offset, b + offset, c + offset))

    def mesh(self):
        m = rg.Mesh()
        for p in self.pts:
            m.Vertices.Add(p[0], p[1], p[2])
        for a, b, c in self.faces:
            m.Faces.AddFace(a, b, c)
        m.Normals.ComputeNormals()
        m.Compact()
        return m


def create_blooming_algae(
    t=4.0,
    stalks=5,
    seed=11,
    blade_spacing=0.8,
    smooth=3,
):
    """Build the 'Blooming algae': a seaweed made of crocheted pieces,
    shown at growth time t.

    Building blocks (all from this file):
      - pseudosphere  -> holdfast at the bottom and the core of each bloom
      - hyperbolic spiral -> every blade along the stalks and every petal

    Growth rules (t = time, 0 .. 4, can be a decimal for animation):
      1. The holdfast grows one round per time step (max 4 rounds).
      2. Stalks start at different times and get longer as they age.
      3. Blades sit along each stalk every `blade_spacing`. Blades near the
         base are oldest: bigger and with 3 rows; young blades have 2 rows.
      4. Two time steps after a stalk starts, its tip forms a bud
         (pseudosphere). The bud opens: 5 petals, then 7 petals with 3 rows.

    Params:
        t (float): Growth time, 0 (holdfast only) to 4 (fully grown).
        stalks (int): Number of stalks. Default 5.
        seed (int): Random seed for the lean and sway of the stalks.
        blade_spacing (float): Distance between blades on a stalk. Default 0.8.
        smooth (int): Smoothing steps for the crocheted pieces (0 = raw).

    Returns:
        tuple: (holdfast, stalk_curves, blades, bloom_cores, petals)
            holdfast, blades, bloom_cores, petals are Rhino meshes,
            stalk_curves is a list of Rhino curves (pipe them in Grasshopper).
    """
    rng = random.Random(seed)
    holdfast = _MeshBuilder()
    blades = _MeshBuilder()
    cores = _MeshBuilder()
    petals = _MeshBuilder()
    stalk_curves = []

    # 1. holdfast: a pseudosphere that grows one round per time step
    rounds = max(1, min(4, int(t) + 1))
    holdfast.add(_ball_shape(rounds, 2, smooth), [0, 0, -0.35], length=0.45 + 0.1 * t)

    for i in range(stalks):
        lean = (i - (stalks - 1) / 2.0) * 0.34 + rng.uniform(-0.08, 0.08)
        depth = rng.uniform(-0.6, 0.6)
        phase = rng.uniform(0, 2 * math.pi)
        full = rng.uniform(6.5, 8.5)
        born = [0, 1, 0, 1, 2][i % 5]
        age = t - born
        if age < 0:
            continue

        # 2. the stalk: a swaying curve that gets longer with age
        length = full * min(1.0, 0.25 + 0.22 * age)
        pts = []
        for k in range(60):
            s = length * k / 59.0
            pts.append([math.sin(lean) * s + 0.35 * math.sin(s * 0.55 + phase) * (s / full),
                        depth * s / full + 0.2 * math.sin(s * 0.4 + phase),
                        math.cos(lean) * s])
        stalk_curves.append(rg.Curve.CreateInterpolatedCurve([rg.Point3d(*p) for p in pts], 3))

        # 3. blades along the stalk, alternating left and right
        has_bloom = age >= 2
        stop = length - (1.4 if has_bloom else 0.15)
        pos, j = 0.9, 0
        while pos < stop:
            k = int(pos / length * 59)
            p0 = pts[k]
            a, b = pts[min(k + 1, 59)], pts[max(k - 1, 0)]
            tangent = _unit([a[0] - b[0], a[1] - b[1], a[2] - b[2]])
            side = 1 if j % 2 == 0 else -1
            sideways = _cross(tangent, [0, 1, 0])
            out = _unit([sideways[n] * side + tangent[n] * 0.9 for n in range(3)])
            out[1] += rng.uniform(-0.3, 0.3)
            blade_age = (length - pos) / blade_spacing
            rows = 2 if blade_age < 3 else 3
            blades.add(_spiral_shape(rows, (i + j) % 3, smooth), p0, out,
                       0.8 + 0.16 * min(blade_age, 4.5), rng.uniform(0, 2 * math.pi))
            pos += blade_spacing
            j += 1

        tip = pts[-1]
        tangent = _unit([tip[n] - pts[-3][n] for n in range(3)])
        if not has_bloom:
            # growing tip: a small young blade
            blades.add(_spiral_shape(2, i % 3, smooth), tip, tangent, 0.7, phase)
            continue

        # 4. the bloom: bud (pseudosphere) that opens into petals
        bloom_age = int(age - 2)
        bloom_rng = random.Random(i)
        core_r = 0.32 + 0.08 * min(bloom_age, 3)
        centre = [tip[n] + tangent[n] * core_r * 0.6 for n in range(3)]
        cores.add(_ball_shape(min(bloom_age + 2, 4), 3 + i % 2, smooth), centre, length=core_r)
        if bloom_age < 1:
            continue
        u = _unit(_cross(tangent, [0, 1, 0.2]))
        v = _cross(tangent, u)
        count = 5 if bloom_age == 1 else 7
        rows = 2 if bloom_age < 2 else 3
        petal_len = 0.75 + 0.35 * min(bloom_age, 3)
        for k in range(count):
            a = 2 * math.pi * k / count + bloom_rng.uniform(-0.2, 0.2) + i
            d = _unit([math.cos(a) * u[n] + math.sin(a) * v[n] + tangent[n] * (0.9 - 0.15 * bloom_age)
                       for n in range(3)])
            start = [centre[n] + d[n] * core_r * 0.7 for n in range(3)]
            petals.add(_spiral_shape(rows, (k + i) % 3, smooth), start, d, petal_len,
                       bloom_rng.uniform(0, 2 * math.pi))

    return holdfast.mesh(), stalk_curves, blades.mesh(), cores.mesh(), petals.mesh()

# ======================================================================
# Crochet engine -- base functions to crochet ONE continuous piece.
#
# Every stitch is worked into stitches that already exist, like real
# crochet, and the whole piece relaxes together (springs, collisions,
# buoyancy). The building happens in Grasshopper: every function takes a
# piece, crochets one part onto a COPY of it and returns the new piece.
#
#   crochet_plan     THE DESIGN ALGORITHM: yarn length -> balanced plant
#   crochet_start    ring + first round                  (Example 1)
#   crochet_rounds   rounds with `increase` per stitch    (Example 1)
#   crochet_split    decrease, divide into one group per stalk
#   crochet_stalks   spiral rib tubes, lengths from the plan
#   crochet_leaves   fronds (low) and spiral leaves (high, Example 2)
#   crochet_flowers  centre round + ruffled petals        (Example 1 + 2)
#   crochet_show     coloured mesh + crochet lines, up to N stitches
#   crochet_pattern  the written crochet pattern
# ======================================================================
import copy as _copy

_UP = [0.0, 0.0, 1.0]


class _Pattern(object):
    """Writes the crochet pattern while the piece is built. Identical
    consecutive rounds are merged ("Rounds 3-12: ...")."""

    def __init__(self):
        self.lines = []      # [section, kind, first, last, text]
        self.count = {}

    def copy(self):
        new = _Pattern()
        new.lines = [list(line) for line in self.lines]
        new.count = dict(self.count)
        return new

    def note(self, section, text):
        self.lines.append([section, None, 0, 0, text])

    def add(self, section, kind, text):
        key = (section, kind)
        self.count[key] = self.count.get(key, 0) + 1
        n = self.count[key]
        last = self.lines[-1] if self.lines else None
        if last and last[0] == section and last[1] == kind and last[4] == text and last[3] == n - 1:
            last[3] = n
        else:
            self.lines.append([section, kind, n, n, text])

    def text(self):
        out, current = [], None
        for section, kind, a, b, text in self.lines:
            if section != current:
                out.append("")
                out.append(section.upper())
                current = section
            if kind is None:
                out.append("  " + text)
            elif a == b:
                out.append("  %s %d: %s" % (kind, a, text))
            else:
                out.append("  %ss %d-%d: %s" % (kind, a, b, text))
        return "\n".join(out).strip()


def _how(n_old, n_new):
    """Crochet instruction to go from n_old to n_new stitches (dc)."""
    if n_new == n_old:
        return "1 dc in each st (%d)" % n_new
    if n_new > n_old and n_new % n_old == 0:
        return "%d dc in each st (%d)" % (n_new // n_old, n_new)
    if n_new * 2 == n_old * 3:
        return "*1 dc in next st, 2 dc in next st* (%d)" % n_new
    if n_new > n_old:
        return "dc in each st, %d increases spread evenly (%d)" % (n_new - n_old, n_new)
    if n_old % n_new == 0:
        return "dc%dtog all around (%d)" % (n_old // n_new, n_new)
    if n_old > 2 * n_new:                              # needs 3 stitches together too
        three = n_old - 2 * n_new                      # dc3tog count, rest dc2tog
        return "%d x dc3tog and %d x dc2tog, spread evenly (%d)" % (three, n_new - three, n_new)
    two = n_old - n_new                                # dc2tog count, rest single dc
    return "%d x dc2tog and %d x dc, spread evenly (%d)" % (two, n_new - two, n_new)


class CrochetPiece(object):
    """A growing network of stitches: points, springs and faces, plus a
    snapshot after every round/row and the written pattern."""

    def __init__(self, stitch_width, stitch_height, buoyancy, iterations, seed):
        self.w = stitch_width
        self.h = stitch_height
        self.buoyancy = buoyancy
        self.iterations = iterations
        self.seed = seed
        self.rng = random.Random(seed)
        self.pts = []        # [x, y, z] of every stitch
        self.fixed = []      # True for the starting ring
        self.part = []       # 'hold', 'stalk', 'spiral', 'frond', 'core', 'petal'
        self.level = []      # round / row number inside its part
        self.col = []        # which column of posts a stitch belongs to
        self.parents = []    # stitches each stitch was worked into
        self.comp = []       # which component a stitch belongs to (e.g. 'stalk 2 leaf 1')
        self.current = "holdfast"
        self.springs = []    # (i, j, rest, stiffness)
        self.linked = set()
        self.faces = []
        self.rows = []       # every round / row: (stitch indices, closed) -> crochet lines
        self.snaps = []      # (points, stitch count, face count, label)
        self.pattern = _Pattern()
        self.front = None    # the open round of the holdfast
        self.hold_level = 0
        self.stalks = []     # one dict per stalk (its rounds, direction ...)
        self.plan = None     # the plan from crochet_plan()

    def copy(self):
        """A copy that can be changed without touching this piece (each
        Grasshopper component works on its own copy)."""
        new = CrochetPiece.__new__(CrochetPiece)
        new.__dict__.update(self.__dict__)
        new.pts = [list(p) for p in self.pts]
        for name in ("fixed", "part", "level", "col", "parents", "comp", "springs", "faces", "rows", "snaps"):
            setattr(new, name, list(getattr(self, name)))
        new.linked = set(self.linked)
        new.rng = random.Random()
        new.rng.setstate(self.rng.getstate())
        new.pattern = self.pattern.copy()
        new.front = list(self.front) if self.front else None
        new.stalks = _copy.deepcopy(self.stalks)
        return new

    # -- stitches ------------------------------------------------------
    def add_spring(self, i, j, rest, stiffness):
        self.springs.append((i, j, rest, stiffness))
        self.linked.add((min(i, j), max(i, j)))

    def ring(self, n, radius):
        """The starting chain, joined into a ring, lying on the ground."""
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            self.pts.append([radius * math.cos(a), radius * math.sin(a), 0.0])
            self.fixed.append(True)
            self.part.append("hold")
            self.level.append(0)
            self.col.append(k)
            self.parents.append([])
            self.comp.append(self.current)
            ring.append(len(self.pts) - 1)
        self.rows.append((list(ring), True))
        return ring

    def centre(self, line):
        n = float(len(line))
        return [sum(self.pts[i][k] for i in line) / n for k in range(3)]

    def mix(self, a, b, wb):
        return _unit([a[k] + wb * b[k] for k in range(3)])

    def continue_from(self, s):
        """Direction from the stitch below `s` to `s` (posts keep going)."""
        if self.parents[s]:
            g = self.parents[s][0]
            d = [self.pts[s][c] - self.pts[g][c] for c in range(3)]
        else:
            d = [self.pts[s][0], self.pts[s][1], 0.0]
        return _unit(d)

    def work(self, line, n_new, closed, part, level, direction, shift=0, new_columns=False):
        """Work one round (closed) or row (open) of n_new stitches into
        `line`. More stitches = increase, fewer = decrease (stitches worked
        together). `shift` starts the round one stitch further on."""
        n_old = len(line)
        old = line[shift:] + line[:shift] if shift else line
        new = []
        for k in range(n_new):
            a = (k * n_old) // n_new
            b = max(a + 1, ((k + 1) * n_old) // n_new)
            pars = [old[m % n_old] for m in range(a, b)]          # stitch(es) worked into
            base = [sum(self.pts[p][c] for p in pars) / len(pars) for c in range(3)]
            d = direction(pars[0])
            j = 0.3 * self.w
            self.pts.append([base[c] + d[c] * self.h + self.rng.uniform(-j, j) for c in range(3)])
            self.fixed.append(False)
            self.part.append(part)
            self.level.append(level)
            self.col.append(k if new_columns else self.col[pars[0]])
            self.parents.append(pars)
            self.comp.append(self.current)
            child = len(self.pts) - 1
            for p in pars:
                self.add_spring(p, child, self.h, 1.0)            # the post: one stitch tall
            new.append(child)
        for k in range(n_new if closed else n_new - 1):            # the top: one stitch wide
            self.add_spring(new[k], new[(k + 1) % n_new], self.w, 1.0)
            if n_new > 4 and (closed or k + 2 < n_new):
                self.add_spring(new[k], new[(k + 2) % n_new], 2 * self.w, 0.15)
        self._zip(old, new, closed)
        self.rows.append((list(new), closed))
        return new

    def _zip(self, old, new, closed):
        """Triangles between two lines with different stitch counts."""
        no, nn = len(old), len(new)
        i = j = 0
        end_i, end_j = (no, nn) if closed else (no - 1, nn - 1)
        while i < end_i or j < end_j:
            if j >= end_j or (i < end_i and (i + 1.0) / no < (j + 1.0) / nn):
                self.faces.append((old[i % no], old[(i + 1) % no], new[j % nn]))
                i += 1
            else:
                self.faces.append((old[i % no], new[(j + 1) % nn], new[j % nn]))
                j += 1

    # -- relaxation ----------------------------------------------------
    def relax(self, steps):
        cell = 0.9 * self.w
        pts, fixed, part = self.pts, self.fixed, self.part
        up, down = self.buoyancy, 0.5 * self.buoyancy
        for it in range(steps):
            for i, p in enumerate(pts):                 # holdfast sinks, the rest floats
                if not fixed[i]:
                    p[2] += -down if part[i] == "hold" else up
            for i, j, rest, stiffness in self.springs:   # stitch sizes
                if fixed[i] and fixed[j]:
                    continue
                a, b = pts[i], pts[j]
                dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                length = math.sqrt(dx * dx + dy * dy + dz * dz)
                if length < 1e-9:
                    continue
                move = stiffness * (length - rest) / length
                if fixed[i]:
                    b[0] -= dx * move; b[1] -= dy * move; b[2] -= dz * move
                elif fixed[j]:
                    a[0] += dx * move; a[1] += dy * move; a[2] += dz * move
                else:
                    move *= 0.5
                    a[0] += dx * move; a[1] += dy * move; a[2] += dz * move
                    b[0] -= dx * move; b[1] -= dy * move; b[2] -= dz * move
            if it % 2 == 0:                              # collisions
                grid = {}
                for idx, p in enumerate(pts):
                    key = (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)), int(math.floor(p[2] / cell)))
                    grid.setdefault(key, []).append(idx)
                for (cx, cy, cz), members in grid.items():
                    for ox in (-1, 0, 1):
                        for oy in (-1, 0, 1):
                            for oz in (-1, 0, 1):
                                others = grid.get((cx + ox, cy + oy, cz + oz))
                                if not others:
                                    continue
                                for i in members:
                                    for j in others:
                                        if j <= i or (fixed[i] and fixed[j]) or (i, j) in self.linked:
                                            continue
                                        a, b = pts[i], pts[j]
                                        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                                        d2 = dx * dx + dy * dy + dz * dz
                                        if d2 >= cell * cell or d2 < 1e-12:
                                            continue
                                        dist = math.sqrt(d2)
                                        push = (cell - dist) / dist
                                        if fixed[i]:
                                            b[0] += dx * push; b[1] += dy * push; b[2] += dz * push
                                        elif fixed[j]:
                                            a[0] -= dx * push; a[1] -= dy * push; a[2] -= dz * push
                                        else:
                                            push *= 0.5
                                            a[0] -= dx * push; a[1] -= dy * push; a[2] -= dz * push
                                            b[0] += dx * push; b[1] += dy * push; b[2] += dz * push
            for p in pts:                                 # the sea floor
                if p[2] < 0.0:
                    p[2] = 0.0

    def done(self, label, size):
        """Relax after a round/row and remember this moment."""
        self.relax(max(6, min(self.iterations, int(self.iterations * size / 24.0))))
        self.snaps.append(([list(p) for p in self.pts], len(self.pts), len(self.faces), label))



# ----------------------------------------------------------------------
# The fixed pattern (values from the class pseudocode) and what it costs
# ----------------------------------------------------------------------
YARN_PER_STITCH = 0.05        # metres of yarn per stitch; calibrate: crochet 20 dc, measure, divide by 20
_FIRST_ROUND = 12             # Example 1: 12 dc into the ring
_HOLDFAST = (2, 2)            # 2 rounds, 2 dc into each stitch
_STALK_ST = 6                 # stitches around a stalk
_TWIST = 0.5                  # spiral rib: shift every 2nd round
_LEAF_BASE = 4                # a leaf is worked along 4 rounds of the stalk
_SPIRAL = (4, 2)              # Example 2: 4 rows, 2 dc into each stitch
_FROND_ROWS = (6, 9, 12, 15)  # frond widens ...
_FROND_LOBES = ((5, 4, 3, 2), (5, 5, 4, 3, 2), (5, 4, 3, 2))   # ... then 3 lobes narrow to their tips
_FLOWER = (3, 6, 3, 2)        # centre 3 dc per st; 6 petals; 3 rows; 2 dc per st
_STALK_SHAPE = (1.0, 0.75, 0.55, 0.9, 0.65, 0.85, 0.7, 0.95)   # how extra yarn is shared by the stalks


def _gather_counts(n_from, n_to):
    """Stitch counts of the decrease rounds that close the bulb. If more than
    3 stitches would have to be worked together, close it over several
    rounds instead (e.g. 48 -> 24 -> 12 -> 6)."""
    counts, n = [], n_from
    while n != n_to:
        n = n_to if n <= 3 * n_to else max(n_to, n // 2)
        counts.append(n)
    return counts or [n_to]                            # always one round to divide into stalks


def crochet_costs():
    """Stitches needed for every part of the pattern (fixed)."""
    hold, n = 2 * _FIRST_ROUND, _FIRST_ROUND           # starting ring + round 1
    for _ in range(_HOLDFAST[0]):
        n *= _HOLDFAST[1]
        hold += n
    centre = _STALK_ST * _FLOWER[0]
    per_petal = centre // _FLOWER[1]
    return {
        "holdfast": hold,
        "stalk round": _STALK_ST,
        "holdfast front": n,                           # stitches in the last holdfast round
        "spiral leaf": sum(_LEAF_BASE * _SPIRAL[1] ** r for r in range(1, _SPIRAL[0] + 1)),
        "frond": sum(_FROND_ROWS) + sum(sum(lobe) for lobe in _FROND_LOBES),
        "flower centre": centre,
        "flower": centre + _FLOWER[1] * sum(per_petal * _FLOWER[3] ** r for r in range(1, _FLOWER[2] + 1)),
    }


# ----------------------------------------------------------------------
# THE DESIGN ALGORITHM: yarn length -> the best balanced plant
# ----------------------------------------------------------------------
class CrochetPlan(object):
    """The result of crochet_plan(). A plain object (not a dict), so
    Grasshopper passes it along a wire as ONE item."""

    def __init__(self, **values):
        self.__dict__.update(values)

    def __repr__(self):
        return "CrochetPlan(%d flowers, %d leaves, %.1f m)" % (
            self.flowers, self.spirals + self.fronds, self.yarn_length)


def crochet_plan(yarn_length=80.0, min_gap=3, min_stalk_rounds=8, max_stalk_rounds=28, max_stalks=8):
    """Decide how the yarn is spent.

    Rules:
      1. Every stalk carries one flower at its top -> flowers = stalks.
      2. Leaves: at least flowers + 1, at most 2 x flowers -> roughly as many
         leaves as flowers, but always more leaves.
      3. Leaf types are balanced: half fronds, half spiral leaves.
         Fronds (big, flat) sit low, spiral leaves sit high.
      4. Leaves are shared out evenly over the stalks. On a stalk, two
         components (leaf / leaf or leaf / flower) are at least `min_gap`
         rounds apart; a stalk has `min_stalk_rounds` .. `max_stalk_rounds`.
      5. Spend the yarn in this order:
           a. as MANY FLOWERS as fit (each with the minimum leaves),
           b. then as many EXTRA LEAVES as fit (up to 2 per flower),
           c. then LONGER STALKS (up to the maximum),
           d. what is left over is spare yarn.

    Returns a CrochetPlan used by all crochet_* functions, incl. a summary text.
    """
    cost = crochet_costs()
    budget = int(yarn_length / YARN_PER_STITCH)

    def layout(flowers, leaves):
        per_stalk = [leaves // flowers + (1 if i < leaves % flowers else 0) for i in range(flowers)]
        rounds = [max(min_stalk_rounds, 2 + k * (_LEAF_BASE + min_gap) + min_gap) for k in per_stalk]
        fronds = leaves // 2
        spirals = leaves - fronds
        need = (cost["holdfast"] + sum(_gather_counts(cost["holdfast front"], flowers * _STALK_ST))
                + flowers * cost["flower"]
                + spirals * cost["spiral leaf"] + fronds * cost["frond"] + sum(rounds) * cost["stalk round"])
        ok = all(r <= max_stalk_rounds for r in rounds)
        return {"flowers": flowers, "leaves": leaves, "per_stalk": per_stalk, "rounds": rounds,
                "spirals": spirals, "fronds": fronds, "need": need, "ok": ok}

    # 5a: most flowers
    best = None
    for flowers in range(1, max_stalks + 1):
        candidate = layout(flowers, flowers + 1)
        if candidate["ok"] and candidate["need"] <= budget:
            best = candidate
    enough = best is not None
    if not enough:
        best = layout(1, 2)
    # 5b: extra leaves
    if enough:
        for leaves in range(best["leaves"] + 1, 2 * best["flowers"] + 1):
            candidate = layout(best["flowers"], leaves)
            if candidate["ok"] and candidate["need"] <= budget:
                best = candidate
    # 5c: longer stalks, up to the maximum (tall stalks get more)
    rounds = list(best["rounds"])
    extra = max(0, budget - best["need"]) // cost["stalk round"]
    weights = [_STALK_SHAPE[k % len(_STALK_SHAPE)] for k in range(best["flowers"])]
    while extra > 0:
        room = [k for k in range(len(rounds)) if rounds[k] < max_stalk_rounds]
        if not room:
            break
        k = max(room, key=lambda q: weights[q] * max_stalk_rounds - rounds[q])
        rounds[k] += 1
        extra -= 1

    # leaf positions: spread evenly, at least min_gap rounds apart
    slots = []
    for k, (n_leaves, n_rounds) in enumerate(zip(best["per_stalk"], rounds)):
        free = n_rounds - 2 - min_gap - _LEAF_BASE * n_leaves
        gap = free / float(n_leaves) if n_leaves else 0
        for i in range(n_leaves):
            start = 2 + int(i * (_LEAF_BASE + gap))
            slots.append((start / float(n_rounds), k, start, i))
    # rule 3: the lowest leaves become fronds, the higher ones spiral leaves
    slots.sort()
    leaves = [[] for _ in rounds]
    for rank, (_, k, start, i) in enumerate(slots):
        leaves[k].append((start, "frond" if rank < best["fronds"] else "spiral", i))
    for k in range(len(leaves)):
        leaves[k].sort()

    stitches = (cost["holdfast"] + sum(_gather_counts(cost["holdfast front"], best["flowers"] * _STALK_ST))
                + best["flowers"] * cost["flower"]
                + best["spirals"] * cost["spiral leaf"] + best["fronds"] * cost["frond"]
                + sum(rounds) * cost["stalk round"])
    yellow = best["flowers"] * cost["flower centre"]
    coral = best["flowers"] * (cost["flower"] - cost["flower centre"])
    green = stitches - yellow - coral
    m = lambda st: st * YARN_PER_STITCH
    text = ["Yarn %.1f m = %d stitches (%.0f cm per stitch)" % (yarn_length, budget, YARN_PER_STITCH * 100)]
    if not enough:
        text.append("NOT ENOUGH YARN: the smallest plant needs %.1f m" % m(best["need"]))
    text += ["-> %d flowers, %d leaves (%d spiral, %d frond)" % (best["flowers"], best["leaves"],
                                                                best["spirals"], best["fronds"]),
             "-> %d stalks of %s rounds" % (len(rounds), " / ".join(str(r) for r in rounds)),
             "Uses %d stitches = %.1f m: green %.1f m, yellow %.1f m, coral %.1f m"
             % (stitches, m(stitches), m(green), m(yellow), m(coral))]
    if enough and budget > stitches:
        text.append("Spare yarn: %.1f m" % m(budget - stitches))
    return CrochetPlan(yarn_length=yarn_length, budget=budget, enough=enough,
                       flowers=best["flowers"], stalk_rounds=rounds, leaves=leaves,
                       spirals=best["spirals"], fronds=best["fronds"], stitches=stitches,
                       text="\n".join(text))


# ----------------------------------------------------------------------
# base functions, used one after the other in Grasshopper
# ----------------------------------------------------------------------
def crochet_start(plan=None, base_chain=4, stitch_width=1.0, stitch_height=2.0,
                  buoyancy=0.02, iterations=30, seed=1):
    """Start a piece for `plan` (default: crochet_plan()) (Example 1):
    chain `base_chain`, join into a ring, 12 dc into the ring."""
    if plan is None:
        plan = crochet_plan()
    if not hasattr(plan, "stalk_rounds"):
        raise TypeError("`plan` must come from the `plan` output of the PLAN component "
                        "(not `summary`), with the input set to No Type Hint. Got: %r" % (plan,))
    p = CrochetPiece(stitch_width, stitch_height, buoyancy, iterations, seed)
    p.plan = plan
    p.pattern.note("Materials", plan.text.replace("\n", "\n  "))
    sec = "Holdfast"
    line = p.ring(_FIRST_ROUND, base_chain * stitch_width / (2 * math.pi))
    p.pattern.note(sec, "Green yarn. Start: ch %d, join with a sl st into a ring." % base_chain)
    p.pattern.add(sec, "Round", "%d dc into the ring, join with sl st (%d)" % (_FIRST_ROUND, _FIRST_ROUND))
    p.front = p.work(line, _FIRST_ROUND, True, "hold", 1, lambda s: p.mix(p.continue_from(s), _UP, 0.3))
    p.hold_level = 1
    p.done("holdfast round 1", _FIRST_ROUND)
    return p


def crochet_rounds(piece, rounds=_HOLDFAST[0], increase=_HOLDFAST[1]):
    """Example 1 rule: `rounds` rounds with `increase` dc into each stitch."""
    p = piece.copy()
    for _ in range(rounds):
        n = len(p.front) * increase
        p.pattern.add("Holdfast", "Round", _how(len(p.front), n))
        p.hold_level += 1
        p.front = p.work(p.front, n, True, "hold", p.hold_level,
                         lambda s: p.mix(p.continue_from(s), _UP, 0.4))
        p.done("holdfast round %d" % p.hold_level, n)
    return p


def crochet_split(piece):
    """Decrease to (flowers x 6) stitches, the bulb closes, and divide the
    round into one group per stalk."""
    p = piece.copy()
    stalks = p.plan.flowers
    n = stalks * _STALK_ST
    counts = _gather_counts(len(p.front), n)
    for i, m in enumerate(counts):                     # decrease round(s): the bulb closes
        last = i == len(counts) - 1
        p.pattern.add("Holdfast", "Round", _how(len(p.front), m) + ("  -> the bulb closes" if last else ""))
        p.hold_level += 1
        p.front = p.work(p.front, m, True, "stalk" if last else "hold", 0 if last else p.hold_level,
                         lambda s: p.mix(p.continue_from(s), _UP, 1.5), new_columns=last)
        p.done("gather round", m)
    line = p.front
    p.pattern.note("Holdfast", "Divide this round into %d groups of %d st; each group becomes one stalk."
                   % (stalks, _STALK_ST))
    p.front = None
    p.stalks = []
    for k in range(stalks):
        group = line[k * _STALK_ST:(k + 1) * _STALK_ST]
        c = p.centre(group)
        lean = _unit([c[0], c[1], 0.0]) if stalks > 1 else [0.0, 0.0, 0.0]
        p.stalks.append({"ring": group, "rounds": [group], "first_col": p.col[group[0]],
                         "lean": lean, "side": [-lean[1], lean[0], 0.0],
                         "phase": p.rng.uniform(0, 2 * math.pi), "acc": 0.0})
    return p


def crochet_stalks(piece):
    """Spiral rib tubes (*FPdc, BPdc*), as many rounds as the plan says.
    On every 2nd round the round starts one stitch further on."""
    p = piece.copy()
    for k, st in enumerate(p.stalks):
        length = p.plan.stalk_rounds[k]
        sec = "Stalk %d (%d rounds)" % (k + 1, length)
        p.current = "stalk %d" % (k + 1)
        p.pattern.note(sec, ("Continue with group 1" if k == 0 else
                             "Join green yarn in the first st of group %d" % (k + 1))
                       + ", sl st to close it into a ring.")
        p.pattern.note(sec, "Spiral rib: on every 2. round start 1 st further on.")
        for r in range(length):
            st["acc"] += _TWIST
            shift = 1 if st["acc"] >= 1.0 else 0
            st["acc"] -= shift
            centre = p.centre(st["ring"])
            sway = 0.3 * math.sin(0.45 * len(st["rounds"]) + st["phase"])

            def tube_dir(s, centre=centre, sway=sway, st=st):
                d = p.mix(p.continue_from(s), _UP, 0.6)
                out = _unit([p.pts[s][n] - centre[n] for n in range(3)])
                ridge = 0.25 if p.col[s] % 2 == 0 else 0.0           # front-post ribs stand out
                return _unit([d[n] + 0.12 * st["lean"][n] + sway * st["side"][n] + ridge * out[n]
                              for n in range(3)])

            st["ring"] = p.work(st["ring"], _STALK_ST, True, "stalk", len(st["rounds"]), tube_dir, shift=shift)
            st["rounds"].append(st["ring"])
            p.pattern.add(sec, "Round", "*FPdc, BPdc* around (%d)" % _STALK_ST)
            p.done("stalk %d round %d" % (k + 1, len(st["rounds"]) - 1), _STALK_ST)
    return p


def crochet_leaves(piece):
    """The leaves where the plan put them: fronds low, spiral leaves high,
    each one turned a third further around the stalk."""
    p = piece.copy()
    for k, st in enumerate(p.stalks):
        rounds = st["rounds"]
        for j, (start, kind, side) in enumerate(p.plan.leaves[k]):
            target = st["first_col"] + (side * _STALK_ST) // 3 % _STALK_ST
            span = range(start, start + _LEAF_BASE)
            base = [next(s for s in rounds[r] if p.col[s] == target) for r in span]
            axis = dict((s, p.centre(rounds[r])) for s, r in zip(base, span))
            sec = "Stalk %d, leaf %d (%s)" % (k + 1, j + 1, kind)
            p.current = "stalk %d leaf %d" % (k + 1, j + 1)
            p.pattern.note(sec, "Join green yarn at the side of the stalk, round %d. Work along the side "
                                "of rounds %d-%d (4 row-ends = the base line)." % (start, start, start + 3))

            def out_dir(s, axis=axis):
                a = axis.get(s)
                return _unit([p.pts[s][n] - a[n] for n in range(3)]) if a else p.continue_from(s)

            label = "stalk %d leaf %d row %%d" % (k + 1, j + 1)
            if kind == "spiral":
                leaf = base
                for row in range(1, _SPIRAL[0] + 1):
                    n = len(leaf) * _SPIRAL[1]
                    p.pattern.add(sec, "Row", ("%d dc in each row-end (%d)" % (_SPIRAL[1], n)) if row == 1
                                  else _how(len(leaf), n) + ", turn")
                    leaf = p.work(leaf, n, False, "spiral", row, out_dir if row == 1 else p.continue_from)
                    p.done(label % row, n)
            else:
                _frond(p, base, out_dir, sec, label)
    return p


def _frond(p, base, out_dir, sec, label):
    """A frond like the seaweed prints: widens (6, 9, 12 st), splits into 3
    lobes, the lobes narrow to their tips (the middle one is longer)."""
    leaf = base
    for row, n in enumerate(_FROND_ROWS, 1):
        text = ("%d dc evenly into the 4 row-ends (%d)" % (n, n)) if row == 1 else _how(len(leaf), n)
        p.pattern.add(sec, "Row", text + ", turn")
        leaf = p.work(leaf, n, False, "frond", row, out_dir if row == 1 else p.continue_from)
        p.done(label % row, n)
    sizes = [lobe[0] for lobe in _FROND_LOBES]
    cuts = [sum(sizes[:i]) for i in range(len(sizes) + 1)]
    lobes = [leaf[cuts[i]:cuts[i + 1]] for i in range(len(sizes))]
    p.pattern.note(sec, "Divide into %d lobes (%s st). Work each lobe on its own, then fasten off:"
                   % (len(lobes), "/".join(str(s) for s in sizes)))
    leaf_centre = p.centre(leaf)
    for name, lobe, counts in zip("ABC", lobes, _FROND_LOBES):
        spread = _unit([p.centre(lobe)[q] - leaf_centre[q] for q in range(3)])
        for row, n in enumerate(counts, 1):
            p.pattern.add(sec, "Lobe %s row" % name, _how(len(lobe), n) + ", turn")
            lobe = p.work(lobe, n, False, "frond", 3 + row,
                          lambda s, spread=spread: p.mix(p.continue_from(s), spread, 0.35))
            p.done(label % (3 + row), n)


def crochet_flowers(piece):
    """A flower on top of every stalk: centre round, 3 dc per stitch
    (Example 1), then 6 petals in rows, 2 dc per stitch (Example 2)."""
    increase, petals, petal_rows, petal_increase = _FLOWER
    p = piece.copy()
    for k, st in enumerate(p.stalks):
        sec = "Stalk %d, flower" % (k + 1)
        p.current = "stalk %d flower centre" % (k + 1)
        ring = st["ring"]
        fc = p.centre(ring)
        n = len(ring) * increase
        p.pattern.note(sec, "Back at the top of the stalk, yellow yarn:")
        p.pattern.add(sec, "Round", _how(len(ring), n) + "  -> flower centre")
        ring = p.work(ring, n, True, "core", 0,
                      lambda s: p.mix(p.continue_from(s), _unit([p.pts[s][q] - fc[q] for q in range(3)]), 2.0))
        p.done("stalk %d flower centre" % (k + 1), n)
        groups = [ring[(i * n) // petals:((i + 1) * n) // petals] for i in range(petals)]
        p.pattern.note(sec, "Coral yarn. Divide into %d petals of %s st; work each petal in rows:"
                       % (petals, "/".join(str(len(g)) for g in groups)))
        fc2 = p.centre(ring)
        for row in range(1, petal_rows + 1):
            new_groups, size = [], 0
            for gi, g in enumerate(groups):
                p.current = "stalk %d petal %d" % (k + 1, gi + 1)
                m = len(g) * petal_increase
                new_groups.append(p.work(g, m, False, "petal", row,
                                         lambda s: p.mix(p.continue_from(s),
                                                         _unit([p.pts[s][q] - fc2[q] for q in range(3)]), 0.6)))
                size += m
            p.pattern.add(sec, "Petal row", _how(len(groups[0]), len(groups[0]) * petal_increase) + ", turn")
            groups = new_groups
            p.done("stalk %d petal row %d" % (k + 1, row), size)
        p.pattern.note(sec, "Fasten off after each petal, sl st to the next petal.")
        st["ring"] = ring
    return p


_PIECE_COLOURS = {
    "hold": (34, 120, 88), "stalk": (34, 120, 88), "spiral": (34, 120, 88), "frond": (34, 120, 88),
    "core": (242, 193, 78),
}


def crochet_show(piece, time=None, stitches=-1, smooth=2):
    """The piece at `time` (0 = first stitch, 1 = finished; for a video,
    animate a 0..1 slider) or up to `stitches` stitches (-1 = all), in crochet order:
    ONE mesh coloured per stitch (green / yellow centre / coral petals) and
    the crochet lines (the top of every round and row) as curves.
    Returns (mesh, lines, total, now)."""
    total = piece.snaps[-1][1]
    if time is not None:                         # time slider 0..1 -> stitches
        stitches = int(round(max(0.0, min(1.0, float(time))) * total))
    n = total if stitches is None or stitches < 0 else max(piece.snaps[0][1], min(int(stitches), total))
    snap = next(s for s in piece.snaps if s[1] >= n)
    pts = snap[0][:n]
    faces = [f for f in piece.faces[:snap[2]] if f[0] < n and f[1] < n and f[2] < n]
    if smooth:
        pts = _smooth(pts, faces, smooth)
    try:
        from System.Drawing import Color
    except Exception:
        Color = None
    mesh = rg.Mesh()
    for i, q in enumerate(pts):
        mesh.Vertices.Add(q[0], q[1], q[2])
        if Color is not None:
            if piece.part[i] == "petal":                 # coral, lighter towards the edge
                t = piece.level[i] / float(_FLOWER[2])
                rgb = tuple(int(a + (b - a) * t) for a, b in zip((226, 71, 94), (255, 170, 160)))
            else:
                rgb = _PIECE_COLOURS[piece.part[i]]
            mesh.VertexColors.Add(Color.FromArgb(*rgb))
    for a, b, c in faces:
        mesh.Faces.AddFace(a, b, c)
    mesh.Normals.ComputeNormals()

    lines = []
    for full, closed in piece.rows:
        row = [i for i in full if i < n]
        if len(row) < 2:
            continue
        corners = [rg.Point3d(pts[i][0], pts[i][1], pts[i][2]) for i in row]
        if closed and len(row) == len(full) and len(row) > 2:      # only finished rounds close
            corners.append(corners[0])
        lines.append(rg.PolylineCurve(corners))
    return mesh, lines, total, "stitch %d of %d: %s" % (n, total, snap[3])


def crochet_pattern(piece):
    """The written crochet pattern of the piece so far."""
    return piece.pattern.text()



"""
Assignment 2.2

The floor is a square grid of count x count tiles of equal size.

Idea: a walker starts on a random cell of the floor grid and counts every
cell it visits. The count n and the slider k decide where it turns:
    n % k == 0 -> turn right
    n % k == 1 -> turn left
    otherwise  -> go straight
(k = 2 is the original even/odd rule.)
If the wanted direction is blocked it tries straight, then the other side.
If everything is blocked the cell becomes an end piece and the walker
jumps to the nearest free cell and starts a new line.
Every cell then gets a tile that shows how the walker passed through it:
a straight piece, a quarter-arc turn, or an end cap.
"""

import math
import random
import Rhino.Geometry as rg


# Headings, counter-clockwise: 0 = east (+x), 1 = north (+y),
# 2 = west (-x), 3 = south (-y). Turning right = heading - 1.
DIRECTIONS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def walker_turn(n, k):
    """The turn rule. Returns -1 (right), +1 (left) or 0 (straight)."""
    k = max(1, int(k))
    r = n % k
    if r == 0:
        return -1
    if r == 1 and k > 1:
        return 1
    return 0


def walk_floor_grid(count=12, k=2, seed=1):
    """Run the walker over a square count x count grid (pure logic).

    The walker starts on a random cell, heading in a random direction
    (both chosen by the seed), and its first step is straight.

    Params:
        count (int): Number of tiles per side (rows = columns).
        k (int): Turn rule, see walker_turn. 1 = spiral, 2 = even/odd.
        seed (int): Random seed for the start cell, the start direction
            and for ties when the walker jumps to a new free cell.

    Returns:
        dict: (col, row) -> {"n": visit count,
                             "in": heading the walker entered with or None,
                             "out": heading it left with or None,
                             "line": index of the line (0, 1, 2 ... after
                                     every jump)}
    """
    rows = cols = max(1, int(count))
    rng = random.Random(seed)

    def is_free(cell):
        c, r = cell
        return 0 <= c < cols and 0 <= r < rows and cell not in cells

    def step(cell, heading):
        dx, dy = DIRECTIONS[heading]
        return (cell[0] + dx, cell[1] + dy)

    cells = {}
    pos = (rng.randrange(cols), rng.randrange(rows))  # random start cell
    heading = rng.randrange(4)                        # random direction
    in_heading = None
    line = 0
    n = 1

    while True:
        cells[pos] = {"n": n, "in": in_heading, "out": None, "line": line}
        if len(cells) == rows * cols:
            break

        # 1. wanted turn, 2. straight, 3. the other side
        turn = 0 if n == 1 else walker_turn(n, k)  # first step: straight
        options = [turn, 0, -turn] if turn != 0 else [0, -1, 1]
        moved = False
        for t in options:
            new_heading = (heading + t) % 4
            nxt = step(pos, new_heading)
            if is_free(nxt):
                cells[pos]["out"] = new_heading
                heading, in_heading, pos = new_heading, new_heading, nxt
                moved = True
                break

        if not moved:
            # dead end: jump to the nearest free cell and start a new line
            free = [(c, r) for c in range(cols) for r in range(rows)
                    if (c, r) not in cells]
            pos = min(free, key=lambda f: (abs(f[0] - pos[0]) + abs(f[1] - pos[1]),
                                           rng.random()))
            in_heading = None
            line += 1
        n += 1

    return cells


def create_floor_grid(count=30, size=30.0, origin=None):
    """Square floor of count x count tiles, all the same size.

    Params:
        count (int): Tiles per side of the whole floor.
        size (float): Side length of one tile in cm. Fixed at 30 cm
            unless you pass another value.
        origin (rg.Point3d): Centre of the floor. Default: world origin,
            so the floor sits centred on Rhino's grid.

    Returns:
        list[rg.Rectangle3d]: One rectangle per cell, ordered row by row
        (index = row * count + col).
    """
    origin = origin or rg.Point3d(0, 0, 0)
    count = max(1, int(count))
    start = -count * size / 2.0  # lower-left corner, so the floor is centred
    tiles = []
    for r in range(count):
        for c in range(count):
            plane = rg.Plane(rg.Point3d(origin.X + start + c * size,
                                        origin.Y + start + r * size,
                                        origin.Z), rg.Vector3d.ZAxis)
            tiles.append(rg.Rectangle3d(plane, size, size))
    return tiles


def _edge_midpoint(center, half, side):
    dx, dy = DIRECTIONS[side]
    return rg.Point3d(center.X + dx * half, center.Y + dy * half, center.Z)


def _tile_center_size(tile):
    """Centre point and side length of one tile.

    Works for a Rectangle3d and for anything with a bounding box (a closed
    curve, a surface, ...), so the type hint on the Grasshopper input does
    not matter.
    """
    if tile is None:
        raise ValueError(
            "A tile is None. On the 'tiles' input set Type hint to "
            "'No Type Hint' (or Curve) and Access to 'List Access'.")
    if isinstance(tile, rg.Rectangle3d):
        return tile.Center, tile.Width
    bbox = tile.GetBoundingBox(True)
    return bbox.Center, bbox.Max.X - bbox.Min.X


def tile_kind(info):
    """What the walker did on one tile.

    Returns "straight", "right", "left", "start", "end" or "single"
    (isolated tile: the line starts and ends here).
    """
    h_in, h_out = info["in"], info["out"]
    if h_in is None and h_out is None:
        return "single"
    if h_in is None:
        return "start"
    if h_out is None:
        return "end"
    if h_out == h_in:
        return "straight"
    return "right" if h_out == (h_in - 1) % 4 else "left"


# Symbols, in local tile coordinates: 1 = tile size, (0, 0) = tile centre,
# +y = the way the walker came in, +x = its right-hand side.
# Every symbol is a circle in the middle of the tile:
#   right / left turn: thin circle, the quarter towards the turn filled
#   start of a line:   filled circle
#   end of a line:     empty circle
#   isolated tile:     empty circle with a small dot (start and end at once)
#   straight:          no symbol
CIRCLE_RADIUS = 0.3   # outer radius of the circle
CIRCLE_LINE = 0.04    # thickness of the circle outline (fraction of the tile size)
SYMBOL_LIFT = 0.01    # symbols sit this much above the floor (0.3 cm)


def symbol_shapes(kind):
    """The symbol for one tile kind as simple shape descriptions.

    ("ring", r, r_in) circle outline (circle with a hole)
    ("disc", r)       filled circle
    ("pie", side)     filled quarter of the circle, between the entry side
                      (behind) and the turn side: right (+1) or left (-1)
    """
    r, r_in = CIRCLE_RADIUS, CIRCLE_RADIUS - CIRCLE_LINE
    if kind == "right":
        return [("ring", r, r_in), ("pie", 1)]
    if kind == "left":
        return [("ring", r, r_in), ("pie", -1)]
    if kind == "start":
        return [("disc", r)]
    if kind == "end":
        return [("ring", r, r_in)]
    if kind == "single":
        return [("ring", r, r_in), ("disc", 0.06)]
    return []


def symbol_color(kind):
    """Colour index of a symbol: 1 for a left turn, 0 for everything else."""
    return 1 if kind == "left" else 0


def _planar(curves):
    """Filled planar surface from closed curves (inner curves become holes)."""
    from System.Collections.Generic import List
    loops = List[rg.Curve]()
    for crv in curves:
        loops.Add(crv)
    breps = rg.Brep.CreatePlanarBreps(loops, 0.001)
    if not breps:
        # fallback for a single closed curve
        brep = rg.Brep.CreatePlanarBreps(curves[0], 0.001) if len(curves) == 1 else None
        breps = brep
    return list(breps) if breps else []


def _circle(center, radius):
    """Closed circle curve (as NURBS, which every Rhino function accepts)."""
    return rg.Circle(rg.Plane(center, rg.Vector3d.ZAxis), radius).ToNurbsCurve()


def _symbol_surfaces(center, size, kind, heading):
    """Filled symbol surfaces for one tile, turned to the walker's direction."""
    fx, fy = DIRECTIONS[heading]                  # forward
    rx, ry = DIRECTIONS[(heading - 1) % 4]        # right-hand side
    # lift the symbols a little, so they are drawn on top of the tile surfaces
    center = rg.Point3d(center.X, center.Y, center.Z + SYMBOL_LIFT * size)
    to_world = lambda x, y: rg.Point3d(center.X + (x * rx + y * fx) * size,
                                       center.Y + (x * ry + y * fy) * size,
                                       center.Z)
    surfaces = []
    for shape in symbol_shapes(kind):
        if shape[0] == "pie":
            s = shape[1]
            rad = CIRCLE_RADIUS - CIRCLE_LINE     # fills the inside of the circle
            p_side = to_world(s * rad, 0.0)
            p_back = to_world(0.0, -rad)
            p_mid = to_world(s * rad * math.sqrt(0.5), -rad * math.sqrt(0.5))
            outline = rg.PolyCurve()
            outline.Append(rg.Line(center, p_side))
            outline.Append(rg.Arc(p_side, p_mid, p_back))
            outline.Append(rg.Line(p_back, center))
            surfaces += _planar([outline])
        elif shape[0] == "disc":
            surfaces += _planar([_circle(center, shape[1] * size)])
        elif shape[0] == "ring":
            surfaces += _planar([_circle(center, shape[1] * size),
                                 _circle(center, shape[2] * size)])
    return surfaces


def create_walker_pattern(tiles, k=2, seed=1):
    """Run the walker and draw one tile motif into every grid cell.

    Params:
        tiles (list[rg.Rectangle3d]): Output of create_floor_grid.
        k, seed (int): See walk_floor_grid.

    Returns:
        tuple: (curves, tile_types, lines, colors, symbols, symbol_colors)
            curves (list[rg.Curve]): The walker's track (lines and arcs).
            tile_types (list[str]): Per cell: "straight", "right", "left",
                "start", "end" or "single", ordered like tiles.
            lines (list[int]): Per cell: index of the line it belongs to.
            colors (list[int]): Per cell: 1 for a turn (right or left),
                0 for everything else. Index into a list of two colours.
            symbols (list[rg.Brep]): Filled symbol surfaces: a circle with
                the quarter towards the turn filled (right or left turn),
                a filled circle where a line starts, an empty circle where
                it ends. Straight tiles get no symbol.
            symbol_colors (list[int]): Per symbol: 1 for a left turn, 0 for
                everything else. Index into a list of two colours.
    """
    if tiles is None or len(tiles) == 0:
        raise ValueError("No tiles: connect the Grid component to 'tiles'.")
    tiles = list(tiles)
    count = int(round(math.sqrt(len(tiles))))  # square grid: read size from tiles
    if count * count != len(tiles):
        raise ValueError("Got {} tiles, which is not a square grid. Set the "
                         "'tiles' input to 'List Access'.".format(len(tiles)))
    cells = walk_floor_grid(count, k, seed)
    curves, tile_types, lines, colors = [], [], [], []
    symbols, symbol_colors = [], []

    for idx, tile in enumerate(tiles):
        c, r = idx % count, idx // count
        info = cells[(c, r)]
        center, size = _tile_center_size(tile)
        half = size / 2.0
        kind = tile_kind(info)

        # edge the walker came in through / leaves through
        sides = []
        if info["in"] is not None:
            sides.append((info["in"] + 2) % 4)
        if info["out"] is not None:
            sides.append(info["out"])

        if kind == "straight":
            curves.append(rg.LineCurve(_edge_midpoint(center, half, sides[0]),
                                       _edge_midpoint(center, half, sides[1])))
        elif kind in ("right", "left"):
            a, b = sides
            corner = rg.Point3d(center.X + (DIRECTIONS[a][0] + DIRECTIONS[b][0]) * half,
                                center.Y + (DIRECTIONS[a][1] + DIRECTIONS[b][1]) * half,
                                center.Z)
            p0 = _edge_midpoint(center, half, a)
            p1 = _edge_midpoint(center, half, b)
            # middle of the quarter arc, on the diagonal towards the centre
            to_center = rg.Vector3d(center - corner)
            to_center.Unitize()
            mid = corner + to_center * half
            curves.append(rg.ArcCurve(rg.Arc(p0, mid, p1)))
        elif len(sides) == 1:
            # the line just stops in the middle of the tile
            curves.append(rg.LineCurve(_edge_midpoint(center, half, sides[0]), center))

        # symbol, turned so that "forward" is the way the walker came in
        heading = info["in"] if info["in"] is not None else (info["out"] or 0)
        new = _symbol_surfaces(center, size, kind, heading)
        symbols.extend(new)
        symbol_colors.extend([symbol_color(kind)] * len(new))

        tile_types.append(kind)
        lines.append(info["line"])
        colors.append(1 if kind in ("right", "left") else 0)

    return curves, tile_types, lines, colors, symbols, symbol_colors