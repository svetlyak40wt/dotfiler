import os.path


class RealFS(object):
    def exists(self, path):
        return os.path.lexists(path)

    def is_symlink(self, path):
        return os.path.islink(path)

    def get_symlink_target(self, path):
        return os.readlink(path)

    def realpath(self, path):
        return os.path.realpath(path)

    def rm(self, path):
        os.unlink(path)

    def mkdir(self, path):
        os.mkdir(path)

    def symlink(self, source, target):
        os.symlink(source, target)
