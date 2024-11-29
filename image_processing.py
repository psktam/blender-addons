import os
import re

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image


def make_spritesheets(individual_sprite_dir, output_dir):
    """
    Given a directory of individual sprites representing views of
    the same building(s), output sprite sheets for each view of
    all buildings, and try to keep them sorted by name.

    All sprite image filenames must end with the "-view-xx.png"
    suffix, where xx is any number.

    For example, if in the ``individual_sprite_dir``, you have
    some sprites named:
    - sprite-a-view-0.png
    - sprite-a-view-180.png
    - sprite-b-view-0.png
    - sprite-b-view-90.png
    - sprite-b-view-180.png
    - sprite-b-view-270.png

    This will output two sprite sheets:
    - view-0.png (containing sprites A and B)
    - view-90.png (containing only sprite B images)
    - view-180.png (containing sprites A and B)
    - view-270.png (containing only sprite B images)
    """

    # ---- Step 1: organize the files into their respective
    #      sprite sheets
    output_sheets = {}
    suffix_re = r"(.+)-view-(\d+)\.png$"

    for fname in os.listdir(individual_sprite_dir):
        re_result = re.search(suffix_re, fname)
        if not re_result:
            continue

        building_name = re_result[1]
        view_angle = int(re_result[2])

        buildings_array = output_sheets.setdefault(view_angle, [])
        buildings_array.append({"file": fname, "building": building_name})


    # ---- Step 2: generate the images, one at a time
    for view_angle, buildings_array in output_sheets.items():
        buildings_array = sorted(buildings_array, key=lambda s: s["building"])

        # First step: we have to make sure that the smallest image dimensions
        # can divide without remainder into the dimensions of larger images.
        loaded_images = [
            Image.open(os.path.join(individual_sprite_dir, spec["file"]))
            for spec in buildings_array
        ]
        smallest_width = min([img.size[0] for img in loaded_images])
        smallest_height = min([img.size[1] for img in loaded_images])

        if (
            any([(img.size[0] % smallest_width) > 0 for img in loaded_images]) or
            any([img.size[1] % smallest_height > 0 for img in loaded_images])
        ):
            raise ValueError(
                f"Dimensions of smallest image for view {view_angle} do not "
                f"evenly divide into the dimensions of all other images for "
                f"this view. Consider resizing your images. Narrowest width: "
                f"{smallest_width}, smallest height: {smallest_height}"
            )

        # Implement the naive row-packing algorithm as described in this
        # excellent blog by David Colson:
        # https://www.david-colson.com/2020/03/10/exploring-rect-packing.html
        # who ran into a very similar issue that I'm facing here. We have a little
        # bit of a wrinkle here in that we have to figure out the size of the
        # box we're packing our sprites into first.
        packing_order, sheet_size = _squarify([img.size for img in loaded_images])
        output_image = Image.new(mode="RGBA", size=sheet_size)

        anchor = (0, 0)
        for row in packing_order:
            max_height = 0
            for idx in row:
                img = loaded_images[idx]
                width, height = img.size
                output_image.paste(img, anchor)
                anchor = (anchor[0] + width, anchor[1])
                max_height = max([max_height, height])

            anchor = (0, anchor[1] + max_height)

        output_image.save(os.path.join(output_dir, f"view-{view_angle}.png"))


def _squarify(sizes):
    """
    Given a list of tuples of (width, height), return a list of lists
    of indices indicating how to pack these into a squarish box.
    """
    # Sort by width, then by height
    idx_array = list(range(len(sizes)))
    zipped = list(zip(sizes, idx_array))
    zipped = sorted(zipped, key=lambda e: e[0][0])
    zipped = sorted(zipped, key=lambda e: e[0][1])
    sizes, idx_array = zip(*zipped)

    min_unsquareness = float("inf")
    output_array = [idx_array]
    output_size = (
        max([size[0] for size in sizes]),
        max([size[1] for size in sizes])
    )
    for row_split in range(len(sizes), 0, -1):
        row_width = sum([sizes[idx][0] for idx in range(row_split)])

        current_sheet = []
        current_row = []
        current_row_width = 0
        current_height = 0

        max_height = 0
        max_width = 0
        for idx, (width, height) in zip(idx_array, sizes):
            max_height = max([max_height, height])
            current_row_width += width
            current_row.append(idx)

            if current_row_width >= row_width:
                current_sheet.append(current_row)
                current_height += max_height
                max_width = max([max_width, current_row_width])
                max_height = 0
                current_row = []
                current_row_width = 0

        if len(current_row) > 0:
            current_sheet.append(current_row)
            current_height += max_height

        # Now check how square this is.
        unsquareness = abs(max_width - current_height)
        if unsquareness > min_unsquareness:
            # Unsquareness is starting to increase, so break here.
            # Don't change the output sheet.
            break
        else:
            # Unsquareness is decreasing. Save this output sheet
            # and continue iterating.
            min_unsquareness = unsquareness
            output_array = current_sheet
            output_size = max_width, current_height
    return output_array, output_size


def _plot_rectangles(sizes, idx_array):
    anchor = (0, 0)
    fig, ax = plt.subplots()
    for row in idx_array:
        max_height = 0
        for idx in row:
            width, height = sizes[idx]
            patch = Rectangle(anchor, width, height, edgecolor="black")
            ax.add_patch(patch)
            anchor = (anchor[0] + width, anchor[1])
            max_height = max([max_height, height])

        anchor = (0, anchor[1] + max_height)
    ax.set_aspect("equal", adjustable="box")
    return fig, ax
