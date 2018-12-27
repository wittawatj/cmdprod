"""
Module containing convenient functions.
"""

def simple_object_hash(obj):
    """
    Turn an arbitrary object into a hash string. Use SHA1.
    """
    import hashlib
    obj_str = str(obj)
    hash_object = hashlib.sha1(obj_str.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig


