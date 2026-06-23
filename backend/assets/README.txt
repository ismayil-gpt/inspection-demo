CivGuard AI — Reference Assets
================================

Place TWO files here for the OpenCV compliance engine to work:

  1. reference_floor_plan.png
     The labeled "original" floor plan image exported from Roboflow.
     This is the image that contains all fire-safety symbols in their
     correct positions. The engine crops templates from this image.

  2. annotations.json
     The Roboflow COCO JSON export for that same image.
     Export from Roboflow: Dataset → Export → COCO JSON.

The system uses these to detect whether the same symbols appear
in any new_building floor plan submitted through the portal.

SYMBOL CLASSES expected in annotations.json:
  - Fire Extinguishers
  - Fire Extinguishers and alarm  (counts as both extinguisher + alarm)
  - Fire alarm
  - Emergency Exit
  - Lift
  - Stairs

If these files are missing, the backend automatically falls back
to the demo mode analyser (form-data-based) for new_building submissions.
A message will be logged to the backend terminal.
