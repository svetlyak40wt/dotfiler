# coding: utf-8
from .core import *
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
            return source, (is_dir, link_target)
                
        lines = [line.strip() for line in text.split('\n')]
        lines = map(parse_line, lines)
        self.structure = dict(lines)

    def link_exists(self, path):
        return self.structure.get(path, (None, False))[1]

    def exists(self, path):
        return path in self.structure



# START tests of test function for creation of the test
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
        File('simple', envs=['base']),
        File('complex', envs=['develop'])])]
    eq_(tree, create_tree(text))


def test_create_more_complex_tree():
    text = """
    base/.zsh/conf.d/simple
    develop/.zsh/conf.d/complex
    """
    tree = [Dir('.zsh', envs=['base', 'develop'], children=[
        Dir('conf.d', envs=['base', 'develop'], children=[
            File('simple', envs=['base']),
            File('complex', envs=['develop'])])])]
    eq_(tree, create_tree(text))


def test_create_more_complex_tree_with_one_more_file():
    text = """
    develop/.zshrc
    base/.zsh/conf.d/simple
    develop/.zsh/conf.d/complex
    """
    tree = [Dir('.zsh', envs=['base', 'develop'], children=[
                Dir('conf.d', envs=['base', 'develop'], children=[
                    File('simple', envs=['base']),
                    File('complex', envs=['develop'])])]),
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
                    File('simple', envs=['base']),
                    File('git', envs=['develop'])])]),
            File('.zshrc', envs=['base'])]
    eq_(tree, create_tree(text))

# END creating tree tests


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
