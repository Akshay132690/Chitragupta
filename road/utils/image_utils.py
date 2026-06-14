import cv2
import numpy as np


def make_overlay(image, mask, threshold=0.3, color=(255, 0, 0)):
    """
    image: RGB image (H, W, 3)
    mask:  float mask (H, W) in [0,1]
    """

    overlay = image.copy()

    binary = (mask > threshold)

    overlay[binary] = color

    return overlay


def make_heatmap(mask):
    """
    mask: float mask (H, W)
    """

    heat = (mask * 255).astype(np.uint8)
    heat = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)

    return heat
