# Model Tetrahedralizer

A Python tool for generating a set of tetrahedrons representing the volume of a 3D model.

## Usage

```bash
python tetrahedralize.py [-h] [-o OUTPUT] [--skip-validation] [--inward] input

options:
  -o, --output OUTPUT  Output file (default: tetras.txt)
  --skip-validation    Skip final result validation
  --inward             Generate tetrahedrons in
```

## Overview

### The Idea

**Model tetrahedralization** is the process of decomposing a non-convex 3D mesh into a set of tetrahedra.

Just as the shape of 3D model is represented by triangles, volume can be represented by tetrahedrons.

Tetrahedrons can be quite useful:
- They are always convex, which makes them easier to work with
- They are well-suited for collision detection algorithms such as GJK
- They can be used for space partitioning (similar to BSP trees)
- Theoretically, skeletal animation can be applied to tetrahedral meshes in the same way as we animate 3D models

### The Problem

However, the **model tetrahedralization** - is a complex problem which has no reliable solution yet.

Existing approaches like [Delaunay tetrahedralization](https://www.cs.purdue.edu/homes/tamaldey/course/531/Delaunay%283D%29.pdf) often generate many unnecessary tetrahedra, which makes them less usable for realtime simulations.

### The Solution

My approach is:

1. Select an arbitrary triangle on the 3D model - this is the initial face of our tetrahedral mesh
2. "Grow" it into a tetrahedron by finding the closest vertex to the face center
3. Repeat the process recursively for newly formed faces

## Disclaimer

**Please note that all code in this repository is not production-ready solution. This approach is not sufficiently tested and optimized to be reliable and stable for every possible geometry. I'm just experimenting and sharing the results in public domain.**
