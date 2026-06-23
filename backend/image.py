from PIL import Image

image_path = r"C:\Users\Hi\Downloads\second_image_resized.png"  # Replace with your image path

import cv2
import numpy as np

# Load image
image = cv2.imread("input.png")

# Polygons
regions = [
    np.array([[915, 1182], [1015, 1182], [1015, 1240], [907, 1244]], dtype=np.int32),
    np.array([[650, 601], [737, 601], [737, 655], [637, 659]], dtype=np.int32)
]

# Fill each polygon with white
for region in regions:
    cv2.fillPoly(image, [region], color=(255, 255, 255))

# Save result
cv2.imwrite("output.png", image)