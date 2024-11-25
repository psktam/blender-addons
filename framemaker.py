import tempfile

import bpy
import numpy as np
from PIL import Image


def make_anim_sheet(
    frame_width: int, frame_height: int,
    output_fname: str,
    chroma_pct: float = 20.0
) -> None:
    """
    Make an animation sheet that turns the current model into a
    series of pixelated animation frames.
    """

    bpy.context.scene.render.resolution_x = frame_width
    bpy.context.scene.render.resolution_y = frame_height

    _, working_fname = tempfile.mkstemp(suffix=".png")
    bpy.context.scene.render.filepath = working_fname

    n_frames = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1

    # Pack the frames together in the most compact grid shape.
    grid_size = 1
    while grid_size ** 2 < n_frames:
        grid_size += 1

    sheet_width = grid_size * frame_width
    sheet_height = grid_size * frame_height
    output_image = Image.new("RGBA", (sheet_width, sheet_height))

    for frame_num in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
        bpy.context.scene.frame_set(frame_num)
        bpy.ops.render.render(False, write_still=True)
        frame_image = Image.open(working_fname)

        x_offset = (frame_num % grid_size) * frame_width
        y_offset = (frame_num // grid_size) * frame_height

        output_image.paste(frame_image, (x_offset, y_offset))

    # before saving the image, chroma out the background
    output_pixels = np.array(output_image)
    output_pixels_lab = rgb2lab(output_pixels[:, :, :3])

    chroma = output_pixels_lab[0, 0, :]
    norms = np.linalg.norm(output_pixels_lab - chroma[None, None, :], axis=2)
    print(norms.max())
    print(norms.min())
    chroma_mask = norms < chroma_pct
    output_pixels[chroma_mask] = np.array([0, 0, 0, 0])

    final_output_image = Image.fromarray(output_pixels)
    final_output_image.save(output_fname)


def snap_panorama(
        frame_width: int, frame_height: int,
        fname_prefix: str,
        chroma_pct: float = 20.0,
        file_ext: str = "pgn"
):
    camera_names = sorted([
        int(k.split("-")[1])
        for k in bpy.context.scene.objects.keys() if k.beginswith("view-")
    ])



# Color transformation formulae courtesy of https://www.easyrgb.com/en/math.php
# Transforming from RGB to CIE L*a*b* colorspace makes it easier to calculate
# differences in color that map more to how we perceive differences in color
def rgb2xyz(rgb):
    nrgb = rgb / 255

    positive_mask = nrgb > 0.04045
    nrgb[positive_mask] = ((nrgb[positive_mask] + 0.055)  / 1.055) ** 2.4
    negative_mask = ~positive_mask
    nrgb[negative_mask] = nrgb[negative_mask] / 12.92

    nrgb *= 100

    x = nrgb[:, :, 0] * 0.4124 + nrgb[:, :, 1] * 0.3576 + nrgb[:, :, 2] * 0.1805
    y = nrgb[:, :, 0] * 0.2126 + nrgb[:, :, 1] * 0.7152 + nrgb[:, :, 2] * 0.0722
    z = nrgb[:, :, 0] * 0.0193 + nrgb[:, :, 1] * 0.1192 + nrgb[:, :, 2] * 0.9505

    return np.array([x, y, z]).transpose(1, 2, 0)


def xyz2lab(xyz):
    # Observer = 2deg, Illuminant: D65
    ref = np.array([95.047, 100.0, 108.883])
    nxyz = xyz / ref[None, None, :]

    positive_mask = nxyz > 0.008856
    nxyz[positive_mask] = nxyz[positive_mask] ** (1.0 / 3.0)
    negative_mask = ~positive_mask
    nxyz[negative_mask] = (nxyz[negative_mask] * 7.787) + (16.0 / 116.0)

    cie_l = 116.0 * nxyz[:, :, 1] - 16.0
    cie_a = 500.0 * (nxyz[:, :, 0] - nxyz[:, :, 1])
    cie_b = 200.0 * (nxyz[:, :, 1] - nxyz[:, :, 2])

    return np.array([cie_l, cie_a, cie_b]).transpose(1, 2, 0)


def rgb2lab(rgb):
    return xyz2lab(rgb2xyz(rgb))
