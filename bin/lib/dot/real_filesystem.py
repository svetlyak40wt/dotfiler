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

    def symlink(self, source, link_name):
        try:
            import os
            os_symlink = getattr(os, "symlink", None)
            if callable(os_symlink):
                os_symlink(source, link_name)
            else:
                import ctypes
                csl = ctypes.windll.kernel32.CreateSymbolicLinkW
                csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
                csl.restype = ctypes.c_ubyte
                flags = 1 if os.path.isdir(source) else 0
                if csl(link_name, source, flags) == 0:
                    raise ctypes.WinError()
        except:
            print('CANT LINK: {1} -> {0}'.format(source, link_name))
            raise
