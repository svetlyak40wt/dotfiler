import os.path

def exists(path):
    return os.path.lexists(path)

def is_symlink(path):
    return os.path.islink(path)

def get_symlink_target(path):
    return os.readlink(path)
