# coding: utf-8
from __future__ import absolute_import

import os
import subprocess

from itertools import groupby
from .real_filesystem import RealFS
from .virtual_fs import VirtualFS
from .logging import (log_mkdir, log_link, log_verbose,
                      log_error, log_rm)


class File(object):
    def __init__(self, name, envs):
        self.name = name
        self.envs = envs

    def __repr__(self):
        return 'File: ({0})/{1}'.format(
            '|'.join(self.envs),
            self.name)

    def __eq__(self, right):
        return (isinstance(right, File) and
                self.name == right.name and
                self.envs == right.envs)
        
class Dir(object):
    def __init__(self, name, envs, children=None):
        self.name = name
        self.envs = list(set(envs))
        self.children = children or []

    def __repr__(self):
        return 'Dir: ({0})/{1}/[{2}]'.format(
            '|'.join(self.envs),
            self.name,
            ', '.join(map(repr, self.children)))

    def __eq__(self, right):
        return (isinstance(right, Dir) and
                self.name == right.name and
                self.envs == right.envs and
                self.children == right.children)


def processor_real(actions, fs):
    def mkdir(dir):
        fs.mkdir(dir)
        log_mkdir('Directory {0} was created.'.format(dir))

    def rm(dir):
        fs.rm(dir)
        log_rm('Symlink {0} was removed.'.format(dir))

    def link(source, target):
        fs.symlink(source, target)
        log_link('Symlink from {0} to {1} was created'.format(target, source))

    def already_linked(source, target):
        log_verbose('Symlink from {0} to {1} already exists'.format(target, source))

    def error(message):
        log_error(message)
        
    mapping = locals()
    for action in actions:
        mapping[action[0].replace('-', '_')](*action[1:])
        

def processor_dry(actions, fs):
    mapping = {'mkdir': (log_mkdir, 'Directory {0} will be created'),
               'link': (log_link, 'Symlink from  {1} to {0} will be created'),
               'already-linked': (log_verbose, 'Symlink from {1} to {0} already exists'),
               'error': (log_error, '{0}'),
               'rm': (log_rm, 'Symlink {0} will be removed.')}
    for action in actions:
        func, fmt = mapping[action[0]]
        func(fmt.format(*action[1:]))


def create_tree_from_text(text):
    head = lambda item: item[0]
    tail = lambda item: item[1:]

    # parse text
    lines = (line.strip() for line in text.split('\n'))
    lines = [line.split('/') for line in lines if line]
    lines.sort(key=lambda x: x[1:])

    # extract environments, they are first level directories
    envs = map(head, lines)
    lines = map(tail, lines)

    # now, each item in lines will be tuple, where second item it's env
    lines = zip(lines, envs)
    extract_envs = lambda lines: [line[1] for line in lines]

    def process(*lines):
        if not filter(lambda x: x[0][0], lines):
            return ()
        else:

            grouped = groupby(lines, key=lambda line: line[0][0]) # group by first path item
            # make it lists, not iterators
            grouped = [(key, list(items))
                        for key, items in grouped]

            # here is we are doing woodoo magick with items in pipeline
            grouped = [(key,
                        filter(lambda x: x[0], [(tail(item[0]), item[1]) for item in items]),
                        extract_envs(items))
                       for key, items in grouped]

            grouped = [Dir(key, envs, children=process(*reminder)) if reminder else File(key, envs)
                       for key, reminder, envs in grouped]
            grouped = filter(None, grouped)
            return grouped

    return process(*lines)

        
def create_tree_from_filesystem(base_dir, envs):
    ignored_dirs = ['.git']
    result = []

    base_dir_len = len(base_dir)

    text = u''
    for env in envs:
        env_path = os.path.join(base_dir, env)
        
        for root, dirs, files in os.walk(env_path):
            for filename in files:
                full_path = os.path.join(root, filename)
                text += full_path[base_dir_len + 1:]
                text += u'\n'
            dirs[:] = [d for d in dirs if d not in ignored_dirs]

    return create_tree_from_text(text)

    
def create_install_actions(base_dir, home_dir, tree, filesystem):
    actions = []
    vfs = VirtualFS(filesystem)

    def push_action(action, *args):
        action = (action,) + args
        
        # each destructive action is applied to the
        # virtual filesystem to get actual view
        if action[0] in ('rm', 'mkdir', 'link'):
            getattr(vfs, action[0])(*action[1:])
            
        if len(filter(lambda a: a == action, actions)) == 0:
            actions.append(action)

    def push_actions(actions):
        for action in actions:
            push_action(*action)
        
    def walk(items):
        """Returns tuples (path, env) to where path is a
        path to a leaf item of the file tree or a
        directory with files from one env only."""
        for item in items:
            children = getattr(item, 'children', None)

            if children and len(item.envs) > 1:
                for path, envs in walk(children):
                    yield ((item.name,) + path,
                           envs)
            else:
                yield ((item.name,), item.envs)

    for path, envs in walk(tree):
        if len(envs) > 1:
            push_action('error', 'File {0} exists in more then one environments: {1}'.format(
                os.path.join(*path), ', '.join(envs)))
        else:
            
            source = os.path.join(base_dir, envs[0], *path)
            target = os.path.join(home_dir, *path)


            if True:
                exists = vfs.exists(target)
                is_symlink = exists and vfs.is_symlink(target)

                target_dir = os.path.dirname(target)
                in_symlinked_directory = vfs.realpath(target_dir) != target_dir
                
                realpath = vfs.realpath(target)
                already_linked = exists and realpath == source

                symlink_target = vfs.get_symlink_target(target) if is_symlink else None
                symlink_outside_base_dir = is_symlink and not symlink_target.startswith(base_dir)
                symlink_to_some_other_dotfile = (is_symlink
                                                 and symlink_target.startswith(base_dir)
                                                 and symlink_target != source)
                


                if already_linked and not in_symlinked_directory:
                    push_action('already-linked', source, target)

                elif symlink_outside_base_dir:
                    push_action('error', 'File {0} is a symlink to {1}, please, remove it manually if you really want to replace it.'.format(
                        target, symlink_target))

                elif not exists or symlink_to_some_other_dotfile or in_symlinked_directory:
                    # now, add actions to create all intermediate directories
                    # but only if there isn't such actions already
                    mkdirs = []
                    for i in range(1, len(path)):
                        dirname = os.path.join(home_dir, *path[:-i])

                        if vfs.exists(dirname):
                            if vfs.is_symlink(dirname):
                                symlink_target = vfs.get_symlink_target(dirname)
                                if symlink_target.startswith(base_dir):
                                    push_action('rm', dirname)
                                    push_action('mkdir', dirname)
                                else:
                                    push_action('error', 'Intermediate directory {0} is a symlink to {1}, please remove it manually.'.format(
                                        dirname, symlink_target))
                                    break
                        else:
                            action = ('mkdir', dirname)
                            if action not in actions:
                                mkdirs.insert(0, action)

                    if not actions or actions[-1][0] != 'error':
                        push_actions(mkdirs)
                        
                        if symlink_to_some_other_dotfile:
                            push_action('rm', target)
                            
                        push_action('link', source, target)
                else:
                    ################## Other actions
                    already_exists_but_not_symlink = exists and not is_symlink


                    if symlink_to_some_other_dotfile:
                        # TODO REMOVE
                        push_action('rm', target)
                        push_action('link', source, target)


                    if already_exists_but_not_symlink:
                        push_action('error', 'File {0} already exists, can\'t make symlink instead of it.'.format(target))



            if False:
                # для файлов, которые не внутри засимлинканой директории
                if vfs.exists(target) and vfs.realpath(target) == target:
                    # если сам файл не является симлинком, то это ошибка
                    if not vfs.is_symlink(target):
                        # TODO: REMOVE
                        push_action('error', 'File {0} already exists, can\'t make symlink instead of it.'.format(target))
                    else:
                        symlink_target = vfs.get_symlink_target(target)
                        if symlink_target.startswith(base_dir):
                            if symlink_target == source:
                                # TODO: REMOVE
                                push_action('already-linked', source, target)
                            else:
                                # TODO: REMOVE
                                push_action('rm', target)
                                push_action('link', source, target)
                        else:
                            # TODO: REMOVE
                            push_action('error', 'File {0} is a symlink to {1}, please, remove it manually if you really want to replace it.'.format(
                                target, symlink_target))
                else:
                    # TODO: REMOVE
                    # now, add actions to create all intermediate directories
                    # but only if there isn't such actions already
                    mkdirs = []
                    for i in range(1, len(path)):
                        dirname = os.path.join(home_dir, *path[:-i])

                        if vfs.exists(dirname):
                            if vfs.is_symlink(dirname):
                                symlink_target = vfs.get_symlink_target(dirname)
                                if symlink_target.startswith(base_dir):
                                    push_action('rm', dirname)
                                    push_action('mkdir', dirname)
                                else:
                                    push_action('error', 'Intermediate directory {0} is a symlink to {1}, please remove it manually.'.format(
                                        dirname, symlink_target))
                                    break
                        else:
                            action = ('mkdir', dirname)
                            if action not in actions:
                                mkdirs.insert(0, action)

                    if not actions or actions[-1][0] != 'error':
                        push_actions(mkdirs)
                        push_action('link', source, target)
    return actions


def _get_envs(base_dir):
    """Searches installed environments in the base_dir.
    """
    ignored_dirs = ['.git', 'bin']
    envs = os.listdir(base_dir)
    envs = [env
            for env in envs
            if os.path.isdir(os.path.join(base_dir, env)) and env not in ignored_dirs]
    return envs

    
def update(base_dir, home_dir, args,
            processor=None,
            tree_builder=None):
    envs = _get_envs(base_dir)
    
    # create a files tree
    if tree_builder is None:
        tree_builder = create_tree_from_filesystem
    tree = tree_builder(base_dir, envs)

    fs = RealFS()
    actions = create_install_actions(base_dir, home_dir, tree, fs)
    if processor is None:
        processor = processor_dry if args['--dry'] else processor_real
    processor(actions, fs)


def status(base_dir, home_dir, args):
    envs = _get_envs(base_dir)

    cwd = os.getcwd()

    try:
        for env in envs:
            full_path = os.path.join(base_dir, env)
            os.chdir(full_path)

            if os.path.exists('.git'):
                process = subprocess.Popen(['git', 'status', '--porcelain'],
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout = process.stdout.read()
                if stdout:
                    print env
                    print '\n'.join('  ' + line
                                    for line in stdout.split('\n'))
            else:
                print env
                print '  Is not version controlled.'

    finally:
        os.chdir(cwd)
        

COMMANDS = dict(update=update,
                status=status)
