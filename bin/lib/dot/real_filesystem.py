import os.path

def link_exists(path):
    return os.path.islink(path)

def exists(path):
    return os.path.lexists(path)
