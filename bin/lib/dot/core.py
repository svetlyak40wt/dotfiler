# coding: utf-8
from __future__ import absolute_import

import os
import re
import subprocess
import sys

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


def processor_real(actions, created_links, fs):
    new_created_links = created_links.copy()

    def mkdir(dir):
        fs.mkdir(dir)
        log_mkdir('Directory {0} was created.'.format(dir))

    def rm(dir):
        fs.rm(dir)
        new_created_links.pop(dir, None)
        log_rm('Symlink {0} was removed.'.format(dir))

    def link(source, target):
        fs.symlink(source, target)
        new_created_links[target] = source
        log_link('Symlink from {0} to {1} was created'.format(
            target, source))

    def already_linked(source, target):
        log_verbose('Symlink from {0} to {1} already exists'.format(
            target, source))

    def error(message):
        log_error(message)

    mapping = locals()
    for action in actions:
        mapping[action[0].replace('-', '_')](*action[1:])

    return new_created_links


def processor_dry(actions, created_links, fs):
    mapping = {'mkdir': (log_mkdir, 'Directory {0} will be created'),
               'link': (log_link, 'Symlink from  {1} to {0} will be created'),
               'already-linked': (
                   log_verbose, 'Symlink from {1} to {0} already exists'),
               'error': (log_error, '{0}'),
               'rm': (log_rm, 'Symlink {0} will be removed.')}
    for action in actions:
        func, fmt = mapping[action[0]]
        func(fmt.format(*action[1:]))

    return created_links


def create_tree_from_text(text):
    head = lambda item: item[0]
    tail = lambda item: item[1:]

    # parse text
    lines = (line.strip() for line in text.split('\n'))
    lines = [line.split(os.sep) for line in lines if line]
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
    ignored_dirs = {'.git'}
    # read ignored files from file.
    ignored_files_config = os.path.join(base_dir, '.dotignore')
    ignored_files = []

    if os.path.isfile(ignored_files_config):
        with open(ignored_files_config) as f:
            for line in f:
                file_name = line.rstrip()
                # we only add non empty files and ignore comments starting with #
                if file_name and not file_name.startswith('#'):
                    ignored_files.append(file_name)

    ignored_files = '(' + "|".join(ignored_files) + ')$' #format for regex
    ignored_files_re = re.compile(ignored_files, re.I)

    base_dir_len = len(base_dir)
    text = u''
    for env in envs:
        env_path = os.path.join(base_dir, env)

        for root, dirs, files in os.walk(env_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            files[:] = [f for f in files if ignored_files_re.match(f) is None]

            for filename in files:
                full_path = os.path.join(root, filename)
                text += full_path[base_dir_len + 1:]
                text += u'\n'

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

        if len(list(filter(lambda a: a == action, actions))) == 0:
            actions.append(action)

    def push_actions(actions):
        for action in actions:
            push_action(*action)

    def walk(items, prefix=tuple()):
        """Returns tuples (path, env, alternatives) to where path is a
        path to a leaf item of the file tree or a
        directory with files from one env only.
        Alternatives, is the structure and could be tried in case
        when initial path already exists."""

        for item in items:
            new_prefix = prefix + (item.name,)
            children = getattr(item, 'children', [])

            if len(item.envs) > 1:
                if children:
                    for result in walk(children, prefix=new_prefix):
                        yield result
                else:
                    yield (prefix + (item.name,),
                           item.envs,
                           [])
            else:
                yield (new_prefix,
                       item.envs,
                       walk(children, prefix=new_prefix))

    def process(path, envs, alternatives):
        if len(envs) > 1:
            push_action('error', 'File {0} exists in more then one environments: {1}'.format(
                os.path.join(*path), ', '.join(envs)))
        else:
            source = os.path.join(base_dir, envs[0], *path)
            target = os.path.join(home_dir, *path)

            # log_verbose('Checking if {target} can be linked to {source}'.format(
            #     target=target,
            #     source=source))

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
                        alternatives = list(alternatives)
                        if alternatives:
                            for params in alternatives:
                                process(*params)
                        else:
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

    for item in walk(tree):
        process(*item)
    return actions


def create_actions_to_remove_broken_symlinks(created_links, fs):
    """Removes dangling symlinks, created during previous 'dot update' calls.
    This could happen when you remove or rename some file in the environment.
    """
    results = []

    for source, target in created_links.items():
        if fs.exists(source) \
           and fs.is_symlink(source) \
           and fs.realpath(source) == target \
           and not fs.exists(target):
            results.append(('rm', source))

    return results


def _get_envs(base_dir):
    """Searches installed environments in the base_dir.
    """
    ignored_dirs = ['.git', 'bin']
    envs = os.listdir(base_dir)
    envs = [env
            for env in envs
            if os.path.isdir(os.path.join(base_dir, env)) and env not in ignored_dirs]
    return envs


def _current_env_has_remote_upstream():
    """Returns True, if repository at CWD has at least one
    remote upstream."""
    if os.path.exists('.git'):
        process = subprocess.Popen(['git', 'remote'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   encoding='utf-8')
        stdout = process.stdout.read()
        return bool(stdout)
    return False


def make_pull(base_dir, env):
    pwd = os.getcwd()
    try:
        os.chdir(os.path.join(base_dir, env))
        if _current_env_has_remote_upstream():
            log_verbose('Making pull in "{0}":'.format(env))
            process = subprocess.Popen(['git', 'pull'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   encoding='utf-8')
            for line in process.stdout:
                log_verbose(' ' * 4 + line.strip())
    finally:
        os.chdir(pwd)


def update(base_dir, home_dir, args,
            processor=None,
            tree_builder=None):
    dry_run = args['--dry']
    envs = _get_envs(base_dir)

    if not args['--skip-pull']:
        for env in envs:
            make_pull(base_dir, env)

    # create a files tree
    if tree_builder is None:
        tree_builder = create_tree_from_filesystem
    tree = tree_builder(base_dir, envs)

    fs = RealFS()

    # now, generate 'rm' actions for broken symlinks, among created
    # during previous 'dot update' invocation
    created_links_filename = os.path.join(base_dir, '.created-links')
    if os.path.exists(created_links_filename):
        with open(created_links_filename) as f:
            created_links = dict((line.strip().split(' -> '))
                                 for line in f.readlines())
            remove_actions = create_actions_to_remove_broken_symlinks(created_links, fs)
    else:
        created_links = {}
        remove_actions = []

    # next, generate actions to create necessary symlinks
    actions = create_install_actions(base_dir, home_dir, tree, fs)

    if processor is None:
        processor = processor_dry if dry_run else processor_real

    created_links = processor(remove_actions + actions, created_links, fs)

    if not dry_run:
        with open(created_links_filename, 'w') as f:
            f.writelines('{0} -> {1}\n'.format(*item)
                         for item in sorted(created_links.items()))


def status(base_dir, home_dir, args):
    envs = _get_envs(base_dir)

    cwd = os.getcwd()

    try:
        for env in envs:
            full_path = os.path.join(base_dir, env)
            os.chdir(full_path)

            if os.path.exists('.git'):
                lines = []

                # check if it has remotes first, because if dont, than it is bad!
                if not _current_env_has_remote_upstream():
                    lines.append('This repository has no remote upstream.')

                # next check repository's status
                process = subprocess.Popen(['git', 'status', '--porcelain', '--branch'],
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           encoding='utf-8')
                stdout = process.stdout.read()
                if stdout:
                    def replace_ahead(line):
                        if line.startswith('##'):
                            match = re.match('^##.*\[ahead (.*?)].*$', line)
                            if match:
                                return 'Has {0} not pushed change(s).'.format(match.group(1))
                        else:
                            return line

                    new_lines = [line for line in stdout.split('\n')]
                    new_lines = map(replace_ahead, new_lines)
                    new_lines = filter(None, new_lines)
                    lines.extend(new_lines)

                # and finally, print all findings
                if lines:
                    print(env)
                    print('\n'.join('  ' + line for line in lines))
            else:
                print(env)
                print('  Is not version controlled.')

    finally:
        os.chdir(cwd)


def _normalize_url(url):
    """Returns tuple (real_url, env_name), using
    following rules:
    - if url has scheme, its returned as is.
    - if url is in the form username/repo, then
      we consider they are username/repo at the github
      and return full https url.
    - env_name is a last part of the path with removed
      '.git' suffix and 'dot[^-]*-' prefix.
    """

    # extract name
    name = url.rsplit('/', 1)[-1]
    name = re.sub(r'^dot[^-]*-', '', name)
    name = re.sub(r'\.git$', '', name)

    # check if this is a github shortcut
    match = re.match('^([^/:]+)/([^/]+)$', url)
    if match is not None:
        url = 'https://github.com/' + url
    return (url, name)


def _add_url(url):
    """Installs repo from given url at current dir.
    """
    url, env = _normalize_url(url)

    if os.path.exists(env):
        log_error('Environment "{0}" already exists.'.format(env))
    else:
        log_verbose('Cloning repository "{0} to "{1}" dir.'.format(url, env))
        process = subprocess.check_call(['git', 'clone', url, env])


def add(base_dir, home_dir, args):
    urls = args['<url>']

    original_cwd = os.getcwd()
    os.chdir(base_dir)

    try:
        for url in urls:
            _add_url(url)
    finally:
        os.chdir(original_cwd)


COMMANDS = dict(update=update,
                status=status,
                add=add)
