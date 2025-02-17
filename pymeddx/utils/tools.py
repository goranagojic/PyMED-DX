import json
import re
import os

from random import randint
from utils.medical_viewer import MEDICAL_VIEWER_MINIFIED_JS, MEDICAL_VIEWER_JS

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
