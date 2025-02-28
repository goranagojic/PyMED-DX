import json
import re
import os

from random import randint

from utils.logger import logger


current_dir = os.path.dirname(os.path.abspath(__file__))

def minify_json(json_str):
    """
    A simple method to minify json string by removing whitespaces from each line
    and deleting empty lines.
    :param json_str:
    :return:
    """
    striped_json = [line.strip() for line in json_str.split('\n') if line != ""]
    return "".join(striped_json)


def fisher_yates_shuffle(arr):
    """
    TODO
    :param arr:
    :return:
    """
    n = len(arr)
    for i in range(n-1, 0, -1):
        j = randint(0, i)
        arr[i], arr[j] = arr[j], arr[i]
    return arr


def load_js() -> str:
    """
    Loads JS code from a file and strips out any sourceMappingURL comment.
    Returns the JS code as a string for direct embedding into HTML <script> tags.
    """
    js_path = os.path.join(current_dir, '../js/simpleviewer.min.js')

    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove a line such as: //# sourceMappingURL=foo.js.map or //@ sourceMappingURL=...
    # This helps avoid 404 or console errors when the .map file is missing or not served.
    content = re.sub(r'^[ \t]*\/\/[#@]\s*sourceMappingURL=.*?$',
                     '',
                     content,
                     flags=re.MULTILINE)

    return content


import os
import pydicom
import numpy as np
from PIL import Image


def load_dicom(dicom_path):
    """
    Loads a single 2D image from a DICOM file if the modality is supported,
    and saves the extracted image as a PNG (or JPG) in the same directory.

    Parameters:
    dicom_path (str): Path to the DICOM file.

    Returns:
    np.ndarray: The 2D image array if successful, otherwise None.
    """
    logger.info(f"Loading DICOM file from '{dicom_path}.'")
    try:
        # Load the DICOM file
        dicom_data = pydicom.dcmread(dicom_path)

        # Check if the file contains image data
        if not hasattr(dicom_data, "pixel_array"):
            logger.error("Error: The DICOM file does not contain image data.")
            return None

        # List of supported single 2D image modalities
        supported_modalities = {"CR", "DX", "MG", "IO", "XA", "RF", "OP", "SM", "XC", "SC"}

        # Retrieve modality
        modality = dicom_data.get("Modality", "Unknown")

        if modality not in supported_modalities:
            logger.error(f"Error: Modality '{modality}' is not supported.")
            return None

        logger.info(f"Info: DICOM modality '{modality}' is supported. Loading image...")

        # Extract the image
        image = dicom_data.pixel_array

        # Ensure it is a 2D image
        if len(image.shape) > 3:
            logger.error("Error: The image is not a single 2D image.")
            return None

        # Convert the pixel data to 8-bit for saving as PNG or JPG
        min_val = image.min()
        max_val = image.max()
        if max_val > min_val:
            scaled_image = ((image - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:
            # All pixels have the same value
            scaled_image = np.zeros_like(image, dtype=np.uint8)

        # Build output path
        dir_name = os.path.dirname(dicom_path)
        base_name = os.path.splitext(os.path.basename(dicom_path))[0]
        output_filename = base_name + ".png"
        output_path = os.path.join(dir_name, output_filename)

        # Save the image
        Image.fromarray(scaled_image).save(output_path)
        logger.info(f"Saved extracted image to: '{output_path}.'")

        return image

    except Exception as e:
        print(f"Error: Failed to load DICOM file. {e}")
        return None


