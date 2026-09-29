#!/usr/bin/env python3
"""The foal in 3D, made and rendered with Blender (the bpy Python module).

    python3 foal3d.py                         # output/foal_3d.png, 1920x1080
    python3 foal3d.py --preview               # small and fast
"""
import argparse
import math
from pathlib import Path

import bpy  # first: it makes Blender's own modules (bmesh, mathutils) importable
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
TARGET = Vector((0, -0.1, 1.22))  # the camera and the lights look here


def srgb(r, g, b):
    """0-255 screen color -> Blender's linear color."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return lin(r), lin(g), lin(b)


def material(name, color, rough=0.5, sheen=0.0, coat=0.0, glow=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Sheen Weight"].default_value = sheen
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Alpha"].default_value = alpha
    if glow:
        p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = glow
    return m


def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def ball(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = size if isinstance(size, tuple) else (size, size, size)
    return finish(obj, name, mat)


def cone(name, loc, size, mat, rot):
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=1, radius2=0, depth=2, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = size
    return finish(obj, name, mat)


def on_surface(center, radii, x, z, lift=0.0):
    """Point on the front (-Y) of an ellipsoid, and the surface direction there."""
    cx, cy, cz = center
    rx, ry, rz = radii
    inside = max(1e-4, 1 - ((x - cx) / rx) ** 2 - ((z - cz) / rz) ** 2)
    y = cy - ry * math.sqrt(inside)
    normal = Vector(((x - cx) / rx ** 2, (y - cy) / ry ** 2, (z - cz) / rz ** 2)).normalized()
    return Vector((x, y, z)) + lift * normal, normal


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 6
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for i, p in enumerate(points):
        spline.points[i].co = (*p, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def star(name, loc, normal, size, mat):
    bm = bmesh.new()
    verts = []
    for i in range(10):
        r = size if i % 2 == 0 else size * 0.45
        a = math.radians(90 + i * 36)
        verts.append(bm.verts.new((r * math.cos(a), 0, r * math.sin(a))))
    bm.faces.new(verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (-math.atan2(normal.z, -normal.y), 0, 0)  # face the same way as the forehead
    obj.modifiers.new("thick", "SOLIDIFY").thickness = 0.012
    obj.data.materials.append(mat)
    return obj


def backdrop(mat):
    """Floor that curves up into a wall: a seamless photo-studio background."""
    profile = [(-8 + i * 10 / 29, 0.0) for i in range(30)]
    profile += [(2 + 3 * math.cos(math.radians(a)), 3 + 3 * math.sin(math.radians(a))) for a in range(-87, 1, 3)]
    profile += [(5.0, 3 + i) for i in range(1, 9)]
    bm = bmesh.new()
    rows = [[bm.verts.new((x, y, z)) for x in (-14, 14)] for y, z in profile]
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    mesh = bpy.data.meshes.new("backdrop")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("backdrop", mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, "backdrop", mat)


def aim(obj, target=TARGET):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, loc, power, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = power, size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    aim(obj)


def build_foal():
    body = material("chestnut", srgb(214, 128, 78), rough=0.55, sheen=0.5)
    mane = material("mane", srgb(160, 80, 44), rough=0.5, sheen=0.4)
    muzzle = material("muzzle", srgb(250, 216, 184), rough=0.6, sheen=0.3)
    hoof = material("hoof", srgb(96, 74, 66), rough=0.35, coat=0.3)
    pink = material("ear", srgb(255, 180, 192), rough=0.6)
    eye = material("eye", srgb(30, 26, 40), rough=0.05, coat=1.0)
    shine = material("shine", (1, 1, 1), rough=0.2, glow=6.0)
    dark = material("nostril", srgb(120, 70, 55), rough=0.6)
    mouth = material("mouth", srgb(120, 30, 50), rough=0.5)
    blush = material("blush", srgb(255, 120, 140), rough=0.7, alpha=0.75)
    white = material("star", srgb(255, 255, 255), rough=0.4)

    for x, y, top in ((0.24, 0.3, 0.8), (-0.24, 0.3, 0.8), (0.22, -0.2, 0.78), (-0.22, -0.2, 0.78)):
        ball("leg", (x, y, top / 2 + 0.06), (0.105, 0.105, top / 2), body)
        ball("hoof", (x, y - 0.01, 0.075), (0.122, 0.122, 0.08), hoof)
    ball("body", (0, 0.06, 0.9), (0.42, 0.56, 0.36), body)
    ball("neck", (0, -0.12, 1.22), (0.22, 0.22, 0.3), body, rot=(math.radians(-15), 0, 0))
    for i, (x, y, z, r) in enumerate(((0.28, 0.52, 0.98, 0.1), (0.34, 0.58, 0.88, 0.11), (0.39, 0.62, 0.77, 0.115),
                                      (0.42, 0.64, 0.66, 0.11), (0.42, 0.64, 0.56, 0.1), (0.4, 0.62, 0.47, 0.085))):
        ball(f"tail{i}", (x, y, z), r, mane)

    head_c, head_r = (0, -0.25, 1.64), (0.46, 0.42, 0.44)
    ball("head", head_c, head_r, body)
    muzzle_c, muzzle_r = (0, -0.55, 1.45), (0.34, 0.27, 0.24)
    ball("muzzle", muzzle_c, muzzle_r, muzzle)
    for side in (-1, 1):
        ear_rot = (math.radians(-10), math.radians(side * 25), 0)
        ball("ear", (side * 0.3, -0.22, 2.08), (0.13, 0.07, 0.22), body, ear_rot)
        ball("ear_in", (side * 0.297, -0.275, 2.09), (0.08, 0.03, 0.15), pink, ear_rot)
    tufts = [(-0.14, -0.42, 1.99, 0.12), (-0.04, -0.47, 2.04, 0.13), (0.08, -0.46, 2.03, 0.13),
             (0.17, -0.41, 1.97, 0.11), (0.22, -0.48, 1.89, 0.08), (0.2, -0.53, 1.83, 0.06),  # forelock
             (0, -0.24, 2.1, 0.13), (0, -0.06, 2.1, 0.13), (0.05, 0.1, 2.02, 0.12)]            # top of the head
    for k in range(7):  # down the neck
        p = k / 6
        tufts.append((0.24 + 0.1 * math.sin(math.pi * p), 0.02 + 0.16 * p, 1.95 - 0.78 * p, 0.14 - 0.035 * p))
    for i, (x, y, z, r) in enumerate(tufts):
        ball(f"mane{i}", (x, y, z), r, mane)

    for side in (-1, 1):
        pos, n = on_surface(head_c, head_r, side * 0.17, 1.7, lift=-0.02)
        ball("eye", tuple(pos), (0.085, 0.05, 0.11), eye)
        hp, _ = on_surface(head_c, head_r, side * 0.17 - 0.03, 1.745, lift=0.028)
        ball("shine", tuple(hp), 0.024, shine)
        hp2, _ = on_surface(head_c, head_r, side * 0.17 + 0.03, 1.655, lift=0.022)
        ball("shine2", tuple(hp2), 0.011, shine)
        bp, _ = on_surface(head_c, head_r, side * 0.3, 1.5, lift=-0.005)
        ball("blush", tuple(bp), (0.095, 0.022, 0.055), blush, rot=(0, 0, math.radians(-side * 30)))
        npos, _ = on_surface(muzzle_c, muzzle_r, side * 0.1, 1.48, lift=-0.01)
        ball("nostril", tuple(npos), (0.035, 0.02, 0.045), dark)
    smile = []
    for i in range(13):
        x = -0.09 + 0.18 * i / 12
        p, _ = on_surface(muzzle_c, muzzle_r, x, 1.36 + 0.035 * (x / 0.09) ** 2, lift=0.002)
        smile.append(tuple(p))
    tube("smile", smile, 0.012, mouth)
    sp, sn = on_surface(head_c, head_r, 0, 1.87, lift=0.004)
    star("star", sp, sn, 0.065, white)


def main():
    ap = argparse.ArgumentParser(description="Render the 3D foal.")
    ap.add_argument("--preview", action="store_true", help="small and fast")
    ap.add_argument("--out", default=str(ROOT / "output" / "foal_3d.png"))
    args = ap.parse_args()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    build_foal()
    backdrop(material("studio", srgb(190, 225, 255), rough=0.85))

    cam_data = bpy.data.cameras.new("camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("camera", cam_data)
    bpy.context.collection.objects.link(cam)
    az, el, dist = math.radians(22), math.radians(8), 6.6
    cam.location = TARGET + Vector((dist * math.sin(az) * math.cos(el), -dist * math.cos(az) * math.cos(el),
                                    dist * math.sin(el)))
    aim(cam)
    scene.camera = cam
    light("key", (-2.6, -3.2, 4.2), 260, 3.0, (1.0, 0.96, 0.9))
    light("fill", (3.2, -2.6, 2.0), 110, 3.0, (0.9, 0.95, 1.0))
    light("rim", (0.5, 3.0, 3.6), 300, 2.0)

    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*srgb(200, 228, 255), 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24 if args.preview else 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (960, 540) if args.preview else (1920, 1080)
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = args.out
    bpy.ops.render.render(write_still=True)
    print("saved", args.out)


if __name__ == "__main__":
    main()
