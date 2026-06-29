from PIL import Image

image_path = r"C:\Users\Hi\Downloads\Mall-Inspection-Demo-Floorplan.jpeg" # Replace with your image path

import cv2
import numpy as np

# Load image
image = cv2.imread(r"C:\Users\Hi\Downloads\Mall-Inspection-Demo-Floorplan.jpeg")

# Polygons
regions = [
    np.array([[112, 526], [195, 530], [193, 599], [110, 595]]),
    np.array([[680, 87], [743, 87], [741, 144], [686, 144]])
]

# Fill each polygon with white
for region in regions:
    cv2.fillPoly(image, [region], color=(255, 255, 255))

# Save result
cv2.imwrite("output-mall.png", image)