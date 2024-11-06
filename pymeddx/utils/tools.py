import json
import re

from random import randint


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
