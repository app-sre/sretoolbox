"""
Utilities to transform data.
"""


def replace_values(obj, replace_map):
    """
    Deep replace of object values according to provided map.

    :param obj: the object to have the values replaced
    :param replace_map: the map of values with their replacements
    :return: obj with replaced values
    """
    if isinstance(obj, list):
        for key, value in enumerate(obj):
            obj[key] = replace_values(value, replace_map)

    elif isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_values(value, replace_map)

    elif obj in replace_map:
        return replace_map[obj]

    return obj
