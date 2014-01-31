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
        try:
            os.symlink(source, target)
        except:
            print 'CANT LINK: {1} -> {0}'.format(source, target)
            raise
