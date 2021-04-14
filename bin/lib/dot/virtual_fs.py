# coding: utf-8

class Node(dict):
    def __init__(self, full_path):
        super(Node, self).__init__()
        
        self.full_path = full_path
        # this it boolean
        self.deleted = False
        # this can be a link to a subtree
        self.symlink = None
        

class VirtualFS(object):
    """This class overrides some methods to simulate destructive operations
    """
    def __init__(self, real_fs):
        self._overlay = Node('')
        self._real_fs = real_fs

    def _split(self, path):
        """Returns path's parts except the first one which is empty string.
        Also, ignores double slashes."""
        return list(filter(None, path.split('/')))

    def _join(self, *args):
        """A little helper for convinience."""
        return '/'.join(args)

    def _create_path(self, path):
        parts = self._split(path)
        subtree = self._overlay

        for part in parts:
            subtree.setdefault(part, Node(subtree.full_path + '/' + part))
            subtree = subtree[part]
        return subtree

    def _find_path(self, path):
        """Searchs given path in the overlay.
        Returns None, if path not found in the overlay, but
        this None say nothing if the file is available on the
        underlying filesystem.
        """
        parts = self._split(path)
        subtree = self._overlay
        for part in parts:
            if part not in subtree:
                return None
            subtree = subtree[part]
        return subtree
        
    def rm(self, path):
        subtree = self._create_path(path)
        subtree.deleted = True
        # remove all children
        subtree.clear()

    def mkdir(self, path):
        parts = self._split(path)
        subtree = self._overlay

        for part in parts:
            subtree.setdefault(part, Node(subtree.full_path + '/' + part))
            subtree = subtree[part]

    def link(self, source, target):
        source = self._create_path(source)
        target = self._create_path(target)
        target.symlink = source

    def exists(self, path):
        parts = self._split(path)
        subtree = self._overlay
        
        for idx, part in enumerate(parts):
            if part in subtree:
                subtree = subtree[part]
                if subtree.deleted:
                    return False
                if subtree.symlink is not None:
                    subtree = subtree.symlink
            else:
                return self._real_fs.exists(self._join(subtree.full_path, *parts[idx:]))

        # if we found all parts in the tree
        return True

    def is_symlink(self, path):
        node = self._find_path(path)
        if node is None:
            return self._real_fs.is_symlink(path)
        return node.symlink is not None

    def get_symlink_target(self, path):
        node = self._find_path(path)
        if node is None:
            return self._real_fs.get_symlink_target(path)
            
        assert node.symlink is not None
        return node.symlink.full_path
    

    def realpath(self, path):
        parts = self._split(path)
        subtree = self._overlay
        for idx, part in enumerate(parts):
            if part not in subtree:
                return self._real_fs.realpath(
                    self._join(subtree.full_path, *parts[idx:]))

            subtree = subtree[part]
            if subtree.symlink is not None:
                subtree = subtree.symlink
        
        return subtree.full_path
