import math
import time
import argparse


EPSILON = 1e-6


class Vector:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return f"Vector({self.x}, {self.y}, {self.z})"

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, value):
        if isinstance(value, Vector):
            return Vector(self.x * value.x, self.y * value.y, self.z * value.z)
        return Vector(self.x * value, self.y * value, self.z * value)

    def __truediv__(self, value):
        if isinstance(value, Vector):
            return Vector(self.x / value.x, self.y / value.y, self.z / value.z)
        return Vector(self.x / value, self.y / value, self.z / value)

    def cross(self, other):
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    @property
    def length_squared(self):
        return self.x**2 + self.y**2 + self.z**2

    @property
    def length(self):
        return math.sqrt(self.length_squared)

    def normalized(self):
        return self / self.length


class Triangle:
    def __init__(self, a: Vector, b: Vector, c: Vector):
        self.a = a
        self.b = b
        self.c = c
        self.normal = (b - a).cross(c - a).normalized()
        self.center = (a + b + c) / 3

    def __eq__(self, other):
        return (self.center - other.center).length_squared < EPSILON  # TODO: comparing centers can produce false positives, but it's fast

    def flip(self):
        return Triangle(self.a, self.c, self.b)


class Plane:
    def __init__(self, normal: Vector, d: float):
        self.normal = normal
        self.d = d

    @staticmethod
    def from_triangle(triangle: Triangle):
        normal = triangle.normal
        d = normal.dot(triangle.a)
        return Plane(normal, d)

    def distance(self, p: Vector):
        return self.normal.dot(p) - self.d

    def classify_point(self, p: Vector, epsilon=EPSILON):
        dist = self.distance(p)
        if dist >  epsilon: return  1  # in front
        if dist < -epsilon: return -1  # behind
        return 0  # on plane

    def coplanar(self, triangle: Triangle, epsilon=EPSILON):
        return abs(self.distance(triangle.a)) < epsilon and \
               abs(self.distance(triangle.b)) < epsilon and \
               abs(self.distance(triangle.c)) < epsilon


class AABB:
    def __init__(self, min_vert: Vector, max_vert: Vector):
        self.min = min_vert
        self.max = max_vert

    @staticmethod
    def from_vertices(vertices: list[Vector]):
        min_x = min(p.x for p in vertices)
        min_y = min(p.y for p in vertices)
        min_z = min(p.z for p in vertices)
        max_x = max(p.x for p in vertices)
        max_y = max(p.y for p in vertices)
        max_z = max(p.z for p in vertices)
        return AABB(Vector(min_x, min_y, min_z), Vector(max_x, max_y, max_z))

    def overlaps(self, other):
        return not (self.min.x > other.max.x or self.max.x < other.min.x or
                    self.min.y > other.max.y or self.max.y < other.min.y or
                    self.min.z > other.max.z or self.max.z < other.min.z)


class Mesh:
    def __init__(self, vertices: list[Vector], faces: list[tuple[int, int, int]]):
        self.vertices = vertices
        self.faces = faces
        self.triangles = [ Triangle(vertices[a], vertices[b], vertices[c]) for a, b, c in faces ]

    @staticmethod
    def from_obj(file_path: str):
        vertices = []
        faces = []
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('v '):
                    _, x, y, z = line.strip().split()
                    vertices.append(Vector(float(x), float(y), float(z)))
                    continue

                if line.startswith('f '):
                    _, *f = line.strip().split()
                    faces.append((
                        int(f[0].split('/')[0]) - 1,
                        int(f[1].split('/')[0]) - 1,
                        int(f[2].split('/')[0]) - 1
                    ))
                    continue

        return Mesh(vertices, faces)


class TetrahedronFace:
    def __init__(self, triangle: Triangle):
        self.triangle = triangle
        self.plane = Plane.from_triangle(triangle)


class Tetrahedron:
    def __init__(self, a: Vector, b: Vector, c: Vector, d: Vector):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.faces = [
            TetrahedronFace(Triangle(a, b, c)),
            TetrahedronFace(Triangle(a, d, b)),
            TetrahedronFace(Triangle(a, c, d)),
            TetrahedronFace(Triangle(b, d, c))
        ]
        self.aabb = AABB.from_vertices([a, b, c, d])

    def __repr__(self):
        return f"Tetrahedron({self.a}, {self.b}, {self.c}, {self.d}, volume={self.volume()})"

    def volume(self):
        return (self.b - self.a).dot((self.c - self.a).cross(self.d - self.a)) / 6

    def center(self):
        return (self.a + self.b + self.c + self.d) / 4

    def shrink(self, margin: float):
        center = self.center()
        def inset(v):
            d = v - center
            return center + d * (1.0 - margin / d.length)
        return Tetrahedron(inset(self.a), inset(self.b), inset(self.c), inset(self.d))


def separating_axis(axis: Vector, a: list[Vector], b: list[Vector]) -> bool:
    proj1 = [ axis.dot(v) for v in a ]
    proj2 = [ axis.dot(v) for v in b ]
    return (max(proj1) < min(proj2)) or (max(proj2) < min(proj1))

def separating_plane(tetra: Tetrahedron, plane: Plane, opposite: Vector, epsilon=0.0) -> bool:
    sign = plane.distance(tetra.a) > epsilon

    # Check all points on the same side of plane
    if ((plane.distance(tetra.b) > epsilon) != sign or
        (plane.distance(tetra.c) > epsilon) != sign or
        (plane.distance(tetra.d) > epsilon) != sign):
        return False

    # Opposite point should be on the other side
    return (plane.distance(opposite) > epsilon) != sign

def tetra_vs_tetra(t1: Tetrahedron, t2: Tetrahedron) -> bool:
    # Fast AABB check
    if not t1.aabb.overlaps(t2.aabb):
        return False

    # Face tests
    if (separating_plane(t1, t2.faces[0].plane, t2.d) or
        separating_plane(t1, t2.faces[1].plane, t2.c) or
        separating_plane(t1, t2.faces[2].plane, t2.b) or
        separating_plane(t1, t2.faces[3].plane, t2.a) or
        separating_plane(t2, t1.faces[0].plane, t1.d) or
        separating_plane(t2, t1.faces[1].plane, t1.c) or
        separating_plane(t2, t1.faces[2].plane, t1.b) or
        separating_plane(t2, t1.faces[3].plane, t1.a)):
        return False

    # Edge tests
    v1 = [ t1.a, t1.b, t1.c, t1.d ]
    v2 = [ t2.a, t2.b, t2.c, t2.d ]
    e1 = [ t1.b - t1.a, t1.c - t1.a, t1.d - t1.a, t1.c - t1.b, t1.d - t1.b, t1.d - t1.c ]
    e2 = [ t2.b - t2.a, t2.c - t2.a, t2.d - t2.a, t2.c - t2.b, t2.d - t2.b, t2.d - t2.c ]
    for a in e1:
        for b in e2:
            if separating_axis(a.cross(b), v1, v2):  # SAT
                return False

    return True


def tetra_vs_triangle(tetra: Tetrahedron, triangle: Triangle):
    # Vertices
    v1 = [ tetra.a, tetra.b, tetra.c, tetra.d ]
    v2 = [ triangle.a, triangle.b, triangle.c ]

    # Normal test
    if separating_axis(triangle.normal, v1, v2):
        return False

    # Face tests
    for face in tetra.faces:
        if separating_axis(face.plane.normal, v1, v2):
            return False

    # Edge tests
    e1 = [
        tetra.b - tetra.a,
        tetra.c - tetra.a,
        tetra.d - tetra.a,
        tetra.c - tetra.b,
        tetra.d - tetra.b,
        tetra.d - tetra.c
    ]
    e2 = [
        triangle.b - triangle.a,
        triangle.c - triangle.b,
        triangle.a - triangle.c
    ]
    for a in e1:
        for b in e2:
            if separating_axis(a.cross(b), v1, v2):
                return False
    return True


def tetra_vs_mesh(tetra: Tetrahedron, mesh: Mesh) -> bool:
    for triangle in mesh.triangles:
        if tetra_vs_triangle(tetra, triangle):
            return True
    return False


def is_valid_tetrahedron(mesh: Mesh, other_tetras: list[Tetrahedron], tetra: Tetrahedron) -> bool:
    # 1. Check if tetrahedron is degenerate
    if tetra.volume() < EPSILON:
        return False

    # 2. Check if tetra intersects any other tetrahedron
    shrunk_tetra = tetra.shrink(EPSILON)  # shrink to avoid false positives from shared faces
    for other in other_tetras:
        if tetra_vs_tetra(shrunk_tetra, other):
            return False

    # 3. Check if tetra intersects the mesh
    if tetra_vs_mesh(shrunk_tetra, mesh):
        return False

    return True


def is_face_closed(tetra: Tetrahedron, face: TetrahedronFace, mesh: Mesh, other_tetras: list[Tetrahedron]) -> bool:
    # 1. Check if face overlaps any other tetras faces
    for other_tetra in other_tetras:
        if other_tetra is tetra:
            continue  # ignore self

        for other_face in other_tetra.faces:
            if other_face.triangle == face.triangle:
                return True  # closed by other tetrahedron face

    # 2. Check if face laying on mesh surface
    def is_point_in_triangle(p: Vector, t: Triangle) -> bool:
        return (
            (t.b - t.a).cross(p - t.a).dot(t.normal) >= -EPSILON and
            (t.c - t.b).cross(p - t.b).dot(t.normal) >= -EPSILON and
            (t.a - t.c).cross(p - t.c).dot(t.normal) >= -EPSILON
        )
    for mesh_triangle in mesh.triangles:
        # Check if triangle is coplanar with mesh face
        if not face.plane.coplanar(mesh_triangle):
            continue

        # Check point in triangle
        if is_point_in_triangle(face.triangle.center, mesh_triangle):
            return True

    return False


def grow_tetra_face(face: TetrahedronFace, mesh: Mesh, other_tetras: list[Tetrahedron]) -> Tetrahedron | None:
    # Collect vertices laying in front of plane
    candidates = [vert for vert in mesh.vertices if face.plane.classify_point(vert) == -1]

    # Sort vertices by closest distance to face
    candidates.sort(key=lambda vert: (vert - face.triangle.center).length_squared)

    # Find valid tetrahedra built from base triangle to extend point
    for vert in candidates:
        tetra = Tetrahedron(face.triangle.a, face.triangle.c, face.triangle.b, vert)  # note: base triangle is flipped
        if is_valid_tetrahedron(mesh, other_tetras, tetra):
            return tetra

    return None


def tetrahedralize(mesh: Mesh, inward: bool) -> list[Tetrahedron]:
    """
    Input:
        Set of vertices and faces forming non-loose geometry.
    Output:
        Set of tetrahedrons forming a volumetric representation of the mesh.
    """
    tetrahedrons = []

    # Find the initial tetrahedron
    initial_triangle = mesh.triangles[0]
    if inward:
        initial_triangle = initial_triangle.flip()  # flip to point inward
    initial_tetra = grow_tetra_face(TetrahedronFace(initial_triangle), mesh, tetrahedrons)
    if initial_tetra is None:
        raise ValueError("Could not find initial tetrahedron")

    tetrahedrons.append(initial_tetra)

    # Grow unclosed tetrahedron faces recursively
    for tetra in tetrahedrons:  # note: `tetrahedron` array will grow during the loop
        for face in tetra.faces[1:]:  # first face is always closed by definition
            if not is_face_closed(tetra, face, mesh, tetrahedrons):
                grown_tetra = grow_tetra_face(face, mesh, tetrahedrons)
                if grown_tetra is not None:
                    tetrahedrons.append(grown_tetra)
                    print(f"Created tetrahedron #{len(tetrahedrons)}")

    return tetrahedrons


def validate(mesh: Mesh, tetrahedrons: list[Tetrahedron]):
    """
    Validate that tetrahedrons form a correct volumetric representation of a mesh
    """
    # Validate volume
    tetra_volume = sum(t.volume() for t in tetrahedrons)
    mesh_volume = sum(t.a.dot(t.b.cross(t.c)) / 6 for t in mesh.triangles)
    volume_diff = mesh_volume - tetra_volume
    if volume_diff > EPSILON:
        print(f"Volume mismatch: {tetra_volume} / {mesh_volume} "
              f"(diff: {volume_diff}, error: {volume_diff / mesh_volume * 100}%)")

    # Validate tetrahedrons intersection
    for i1 in range(len(tetrahedrons)):
        a = tetrahedrons[i1].shrink(EPSILON)
        for i2 in range(i1 + 1, len(tetrahedrons)):
            b = tetrahedrons[i2]
            if tetra_vs_tetra(a, b):
                print(f"Tetrahedron #{i1} intersects #{i2}")
                break

    # Validate mesh intersection
    for i, t in enumerate(tetrahedrons):
        if tetra_vs_mesh(t.shrink(EPSILON), mesh):
            print(f"Tetrahedron #{i} intersects the mesh")
            break


def save_tetras(tetras: list[Tetrahedron], path: str):
    with open(path, 'w') as file:
        for tetra in tetras:
            file.write(f"{tetra.a.x},{tetra.a.y},{tetra.a.z} {tetra.b.x},{tetra.b.y},{tetra.b.z} {tetra.c.x},{tetra.c.y},{tetra.c.z} {tetra.d.x},{tetra.d.y},{tetra.d.z}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input .obj file")
    parser.add_argument("-o", "--output", default="tetras.txt", help="Output file (default: tetras.txt)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip final result validation")
    parser.add_argument("--inward", action="store_true", help="Generate tetrahedrons covering the closed space of a model (if your model is a room)")
    args = parser.parse_args()

    mesh = Mesh.from_obj(args.input)

    start_time = time.perf_counter()
    tetras = tetrahedralize(mesh, args.inward)
    end_time = time.perf_counter()
    print(f"Generated {len(tetras)} tetrahedrons in {end_time - start_time:.2f} seconds")

    if not args.skip_validation:
        validate(mesh, tetras)

    save_tetras(tetras, args.output)


if __name__ == '__main__':
    main()
