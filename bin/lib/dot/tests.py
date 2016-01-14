# coding: utf-8
from .core import *
from .core import _normalize_url
from .virtual_fs import VirtualFS
from nose.tools import eq_


base_dir = '/home/art/.dotfiles'
home_dir = '/home/art'
create_tree = create_tree_from_text


class FakeFilesystem(object):
    def __init__(self, text):
        """Parses text into inner filestructure representation, which is dict
        path -> (is_dir, link_target)
        """

        def parse_line(line):
            line = line.split('->', 1)
            link_target = line[1].strip() if len(line) > 1 else None
            source = line[0].strip()
            is_dir = source.endswith('/')
            return source.rstrip('/'), (is_dir, link_target)

        lines = [line.strip() for line in text.split('\n')]
        lines = map(parse_line, lines)
        self.structure = dict(lines)

    def exists(self, path):
        return path in self.structure

    def is_symlink(self, path):
        return bool(self.structure.get(path, (None, False))[1])

    def get_symlink_target(self, path):
        return self.structure[path][1]

    def realpath(self, path):
        parts = path.split('/')
        for idx in range(1, len(parts) + 1):
            dirname = '/'.join(parts[:idx])
            if self.is_symlink(dirname):
                real_dirname = self.get_symlink_target(dirname)
                parts[:idx] = real_dirname.split('/')
        return '/'.join(parts)

    def rm(self, path):
        del self.structure[path]


def test_fakefs_realpath2():
    filesystem = FakeFilesystem("""
    /home/art/.zsh/ -> /home/art/.dotfiles/zsh/.zsh
    /home/art/.zsh/the-file
    """)
    eq_('/home/art/.dotfiles/zsh/.zsh/the-file',
        filesystem.realpath('/home/art/.zsh/the-file'))


# START: tests of test function for creation of the test
# directory tree from text description
# in production tree will be built from real filesystem


def test_create_tree_simple_file():
    text = """
    base/.zsh
    """
    tree = [File('.zsh', envs=['base'])]
    eq_(tree, create_tree(text))


def test_create_tree_empty_dir():
    text = """
    base/.zsh/
    """
    tree = [Dir('.zsh', envs=['base'], children=[])]
    eq_(tree, create_tree(text))


def test_create_tree_non_empty_dir():
    text = """
    base/.zshrc
    base/.bashrc
    """
    tree = [File('.bashrc', envs=['base']),
            File('.zshrc', envs=['base'])]
    eq_(tree, create_tree(text))


def test_create_tree_dir_with_subdir():
    text = """
    base/.zsh/aliases
    """
    tree = [Dir('.zsh', envs=['base'], children=[File('aliases', envs=['base'])])]
    eq_(tree, create_tree(text))

def test_create_tree_dir_with_two_files():
    text = """
    base/.zsh/aliases
    base/.zsh/functions
    """
    tree = [Dir('.zsh', envs=['base'], children=[
               File('aliases', envs=['base']),
               File('functions', envs=['base'])])]
    eq_(tree, create_tree(text))

def test_create_less_complex_tree():
    text = """
    base/.zsh/simple
    develop/.zsh/complex
    """
    tree = [Dir('.zsh', envs=['base', 'develop'], children=[
        File('complex', envs=['develop']),
        File('simple', envs=['base'])])]
    eq_(tree, create_tree(text))


def test_create_more_complex_tree():
    text = """
    base/.zsh/conf.d/simple
    base/.zsh/some-config
    develop/.zsh/conf.d/complex
    """
    tree = [Dir('.zsh', envs=['base', 'develop'], children=[
        Dir('conf.d', envs=['base', 'develop'], children=[
            File('complex', envs=['develop']),
            File('simple', envs=['base'])]),
        File('some-config', envs=['base'])])]
    eq_(tree, create_tree(text))


def test_create_more_complex_tree_with_one_more_file():
    text = """
    develop/.zshrc
    base/.zsh/conf.d/simple
    develop/.zsh/conf.d/complex
    """
    tree = [Dir('.zsh', envs=['base', 'develop'], children=[
                Dir('conf.d', envs=['base', 'develop'], children=[
                    File('complex', envs=['develop']),
                    File('simple', envs=['base'])])]),
            File('.zshrc', envs=['develop']),
    ]
    eq_(tree, create_tree(text))


def test_create_even_more_complex_tree():
    text = """
    base/.zshrc
    base/.zsh/aliases/simple
    develop/.emacsrc
    develop/.zsh/aliases/git
    """
    tree = [File('.emacsrc', envs=['develop']),
            Dir('.zsh', envs=['base', 'develop'], children=[
                Dir('aliases', envs=['base', 'develop'], children=[
                    File('git', envs=['develop']),
                    File('simple', envs=['base'])])]),
            File('.zshrc', envs=['base'])]
    eq_(tree, create_tree(text))

# END: creating tree tests


# START: Tests for different cases

def test_actions_simple_link():
    """Нет такого файла - сделать симлинк."""
    filesystem = FakeFilesystem("")
    tree = create_tree("base/.zshrc")
    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('link', '/home/art/.dotfiles/base/.zshrc', '/home/art/.zshrc')],
        actions)


def test_actions_already_linked():
    """Файл есть, это симлинк такой же как нужно создать - оставить как есть."""
    filesystem = FakeFilesystem("/home/art/.zshrc -> /home/art/.dotfiles/base/.zshrc")
    tree = create_tree("base/.zshrc")
    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('already-linked', '/home/art/.dotfiles/base/.zshrc', '/home/art/.zshrc')],
        actions)


def test_actions_link_only_parent_dir():
    """Если внутри директории файлы только одного окружения, то линкуется сама директория, а не файлы."""
    filesystem = FakeFilesystem("")
    tree = create_tree("""
    base/.zsh/aliases
    base/.zsh/functions
    """)
    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('link', '/home/art/.dotfiles/base/.zsh', '/home/art/.zsh')],
        actions)


def test_actions_link_separate_files_from_different_modules():
    """Если внутри директории файлы разных окружений, то директорию создаем, а файлы линкуем в нее. Для создания симлинка создаем все промежуточные директории."""
    filesystem = FakeFilesystem("")
    tree = create_tree("""
    base/.zsh/conf.d/aliases
    develop/.zsh/conf.d/git-completions
    """)
    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('mkdir', '/home/art/.zsh'),
         ('mkdir', '/home/art/.zsh/conf.d'),
         ('link', '/home/art/.dotfiles/base/.zsh/conf.d/aliases', '/home/art/.zsh/conf.d/aliases'),
         ('link', '/home/art/.dotfiles/develop/.zsh/conf.d/git-completions', '/home/art/.zsh/conf.d/git-completions')],
        actions)


def test_actions_same_file_in_different_evns_is_error():
    """Если один и тот же файл есть в разных окружениях, то они выдаем ошибку о конфликте."""
    filesystem = FakeFilesystem("")
    tree = create_tree("""
    base/.zsh/aliases
    develop/.zsh/aliases
    """)
    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('error', 'File .zsh/aliases exists in more then one environments: base, develop')],
        actions)


def test_actions_file_exists():
    """Файл есть и это не симлинк – сообщение об ошибке."""
    filesystem = FakeFilesystem("/home/art/.zshrc")
    tree = create_tree("base/.zshrc")

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('error', 'File /home/art/.zshrc already exists, can\'t make symlink instead of it.')],
        actions)


def test_actions_link_exists_and_its_not_to_dotfiles():
    """Симлинк есть и ведет не внутрь .dotfiles - показать сообщение об ошибке."""
    filesystem = FakeFilesystem("/home/art/.zshrc -> /home/art/.zsh/zshrc")
    tree = create_tree("base/.zshrc")

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('error', 'File /home/art/.zshrc is a symlink to /home/art/.zsh/zshrc, please, remove it manually if you really want to replace it.')],
        actions)


def test_actions_link_exists_and_it_is_to_some_other_dotfile():
    """Файл есть и это симлинк на что-то другое из .dotfiles - удалить старый симлинк и создать новый."""
    filesystem = FakeFilesystem("/home/art/.zshrc -> /home/art/.dotfiles/old/.zshrc")
    tree = create_tree("new/.zshrc")

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('rm', '/home/art/.zshrc'),
         ('link', '/home/art/.dotfiles/new/.zshrc', '/home/art/.zshrc')],
        actions)


def test_actions_intermediate_dir_is_symlink_to_outer_space():
    """Если промежуточная директория — симлинк, ведущий вовне, выводим сообщение об ошибке и больше не делаем ничего."""
    filesystem = FakeFilesystem("/home/art/.zsh/ -> /home/art/.other-dotfiles/.zsh")
    tree = create_tree("""
    base/.zsh/aliases
    develop/.zsh/git-completions
    """)

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('error', 'Intermediate directory /home/art/.zsh is a symlink to /home/art/.other-dotfiles/.zsh, please remove it manually.')],
        actions)


def test_actions_intermediate_dir_is_symlink_to_other_dotfile_dir():
    """Если промежуточная директория симлинк и ведет внутрь dotfiles, удаляем его перед созданием директории."""
    filesystem = FakeFilesystem("/home/art/.zsh/ -> /home/art/.dotfiles/base/.zsh")
    tree = create_tree("""
    base/.zsh/aliases
    develop/.zsh/git-completions
    """)

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('rm', '/home/art/.zsh'),
         ('mkdir', '/home/art/.zsh'),
         ('link', '/home/art/.dotfiles/base/.zsh/aliases', '/home/art/.zsh/aliases'),
         ('link', '/home/art/.dotfiles/develop/.zsh/git-completions', '/home/art/.zsh/git-completions')],
        actions)


def test_actions_complex_example_where_intermediate_dir_is_symlink_to_other_dotfile_dir():
    """Если промежуточная директория симлинк и ведет внутрь dotfiles, но большая глубина вложенности."""
    filesystem = FakeFilesystem("""
    /home/art/.zsh/ -> /home/art/.dotfiles/base/.zsh
    /home/art/.zsh/conf.d/
    /home/art/.zsh/conf.d/aliases
    /home/art/.zsh/cache/
    /home/art/.zsh/cache/some-cached-data
    /home/art/.zsh/prompt_colors
    """)
    tree = create_tree("""
    base/.zsh/conf.d/aliases
    base/.zsh/cache/blah
    base/.zsh/prompt_colors
    develop/.zsh/conf.d/git-completions
    """)

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('rm', '/home/art/.zsh'),
         ('mkdir', '/home/art/.zsh'),
         ('link', '/home/art/.dotfiles/base/.zsh/cache', '/home/art/.zsh/cache'),
         ('mkdir', '/home/art/.zsh/conf.d'),
         ('link', '/home/art/.dotfiles/base/.zsh/conf.d/aliases', '/home/art/.zsh/conf.d/aliases'),
         ('link', '/home/art/.dotfiles/develop/.zsh/conf.d/git-completions', '/home/art/.zsh/conf.d/git-completions'),
         ('link', '/home/art/.dotfiles/base/.zsh/prompt_colors', '/home/art/.zsh/prompt_colors')],
        actions)


def test_actions_complex_example_where_intermediate_dir_exists_and_contains_some_files():
    """Если промежуточная директория существует и содержит файлы не контролируемые через dotfiler."""
    # this test was created to check issue #15
    # https://github.com/svetlyak40wt/dotfiler/issues/15

    filesystem = FakeFilesystem("""
    /home/art/.emacs.d/
    /home/art/.emacs.d/custom.el
    """)
    tree = create_tree("""
    base/.emacs.d/config/base.el
    base/.emacs.d/init.el
    """)

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('link',
          '/home/art/.dotfiles/base/.emacs.d/config',
          '/home/art/.emacs.d/config'),
         ('link',
          '/home/art/.dotfiles/base/.emacs.d/init.el',
          '/home/art/.emacs.d/init.el')],
        actions)


def test_fakefs_realpath():
    filesystem = FakeFilesystem("""
    /home/art/.zsh/alias -> /home/art/.dotfiles/base/.zsh/alias
    """)
    eq_('/home/art/.dotfiles/base/.zsh/alias',
        filesystem.realpath('/home/art/.zsh/alias'))


def test_actions_complex_when_dir_created_and_link_already_created_too():
    """Если промежуточная директория создана, и там уже есть симлинк, который ведет в
    нужное место внутри dotfiles, то нужно выводить already-linked."""
    filesystem = FakeFilesystem("""
    /home/art/.zsh/
    /home/art/.zsh/aliases  -> /home/art/.dotfiles/base/.zsh/aliases
    """)
    tree = create_tree("""
    base/.zsh/aliases
    develop/.zsh/git-completions
    """)

    actions = create_install_actions(base_dir, home_dir, tree, filesystem)
    eq_([('already-linked', '/home/art/.dotfiles/base/.zsh/aliases', '/home/art/.zsh/aliases'),
         ('link', '/home/art/.dotfiles/develop/.zsh/git-completions', '/home/art/.zsh/git-completions'),
     ], actions)


# END: Tests for different cases


# Start VirtualFS tests
def test_pass_is_symlink_and_get_symlink_target_to_underlying_fs():
    base_fs = FakeFilesystem("""
    /home/art/.zsh/ -> /home/art/.dotfiles/zsh
    """)
    fs = VirtualFS(base_fs)

    eq_(True, base_fs.is_symlink('/home/art/.zsh'))
    eq_(True, fs.is_symlink('/home/art/.zsh'))

    eq_('/home/art/.dotfiles/zsh', base_fs.get_symlink_target('/home/art/.zsh'))
    eq_('/home/art/.dotfiles/zsh', fs.get_symlink_target('/home/art/.zsh'))


def test_rm_file():
    base_fs = FakeFilesystem("""
    /home/art/.zsh/aliases
    """)
    fs = VirtualFS(base_fs)

    fs.rm('/home/art/.zsh/aliases')
    eq_(True, base_fs.exists('/home/art/.zsh/aliases'))
    eq_(False, fs.exists('/home/art/.zsh/aliases'))


def test_rm_dir():
    base_fs = FakeFilesystem("""
    /home/art/.zsh/aliases
    """)
    fs = VirtualFS(base_fs)

    fs.rm('/home/art/.zsh')
    eq_(True, base_fs.exists('/home/art/.zsh/aliases'))
    eq_(False, fs.exists('/home/art/.zsh'))
    eq_(False, fs.exists('/home/art/.zsh/aliases'))


def test_mkdir():
    base_fs = FakeFilesystem("""
    /home/art/.zsh/aliases
    """)
    fs = VirtualFS(base_fs)

    fs.mkdir('/home/art/.vim')
    eq_(False, base_fs.exists('/home/art/.vim'))
    eq_(True, fs.exists('/home/art/.vim'))


def test_ln_file():
    base_fs = FakeFilesystem("""
    /home/art/.zsh/
    /home/art/.dotfiles/zsh/aliases
    """)
    fs = VirtualFS(base_fs)

    fs.link('/home/art/.dotfiles/zsh/aliases', '/home/art/.zsh/aliases')
    eq_(False, base_fs.exists('/home/art/.zsh/aliases'))
    eq_(True, fs.exists('/home/art/.zsh/aliases'))
    eq_(True, fs.is_symlink('/home/art/.zsh/aliases'))
    eq_('/home/art/.dotfiles/zsh/aliases', fs.get_symlink_target('/home/art/.zsh/aliases'))


def test_ln_dir():
    base_fs = FakeFilesystem("""
    /home/art/.dotfiles/zsh/aliases
    """)
    fs = VirtualFS(base_fs)

    fs.link('/home/art/.dotfiles/zsh', '/home/art/.zsh')
    eq_(False, base_fs.exists('/home/art/.zsh'))
    eq_(True, fs.exists('/home/art/.zsh'))
    eq_(True, fs.exists('/home/art/.zsh/aliases'))
    eq_('/home/art/.dotfiles/zsh/aliases', fs.realpath('/home/art/.zsh/aliases'))


def test_url_normalizer():
    eq_(('https://github.com/svetlyak40wt/dot-tmux', 'tmux'),
        _normalize_url('https://github.com/svetlyak40wt/dot-tmux'))
    eq_(('git@github.com:svetlyak40wt/dot-tmux.git', 'tmux'),
        _normalize_url('git@github.com:svetlyak40wt/dot-tmux.git'))
    eq_(('https://github.com/svetlyak40wt/dot-tmux', 'tmux'),
        _normalize_url('svetlyak40wt/dot-tmux'))
    eq_(('git:git-private/dot-private.git', 'private'),
        _normalize_url('git:git-private/dot-private.git'))


def test_remove_broken_symlinks():
    """Symlink 'aliases' now missing from env 'zsh', so we have to remove it."""
    fs = FakeFilesystem("""
    # this symlink's target disappeared and symlink should be removed
    /home/art/.zsh/aliases -> /home/art/.dotfiles/zsh/.zsh/aliases

    # this symlink's target exists and it is ok
    /home/art/.zsh/functions -> /home/art/.dotfiles/zsh/.zsh/functions
    /home/art/.dotfiles/zsh/.zsh/functions

    # this symlink's target exists and but now it points to the different
    # file than it was after last 'dot update' call. Just ignore it.
    /home/art/.zsh/prompt -> /home/art/local/.zsh-prompt
    /home/art/local/.zsh-prompt
    """)

    created_links = {'/home/art/.zsh/aliases': '/home/art/.dotfiles/zsh/.zsh/aliases',
                     '/home/art/.zsh/functions': '/home/art/.dotfiles/zsh/.zsh/functions',
                     '/home/art/.zsh/prompt': '/home/art/.dotfiles/zsh/.zsh/prompt'}
    actions = create_actions_to_remove_broken_symlinks(created_links, fs)
    eq_([('rm', '/home/art/.zsh/aliases')], actions)


def test_osx_library_already_exists_and_we_should_symlink_into_it():
    """Symlink 'aliases' now missing from env 'zsh', so we have to remove it."""
    fs = FakeFilesystem("""
    # this symlink's target disappeared and symlink should be removed
    /home/art/Library
    """)

    tree = create_tree("""
    osx/Library/KeyBindings/DefaultKeyBinding.dict
    """)

    actions = create_install_actions(base_dir, home_dir, tree, fs)
    eq_([('link', '/home/art/.dotfiles/osx/Library/KeyBindings', '/home/art/Library/KeyBindings'),
     ], actions)
