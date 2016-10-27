Dotfiler — the ultimate solution for managing dotfiles!
=======================================================

[![changelog](http://allmychanges.com/p/python/dotfiler/badge/)](http://allmychanges.com/p/python/dotfiler/?utm_source=badge)

It was inspired by [Zach Holman's dotfiles](https://github.com/holman/dotfiles) and
[homesick](https://github.com/technicalpickles/homesick), but was made according KISS priciple.

There are very few commands in dotfiler: `update`, `add` and `status`:

* `update` will make pull from all version controlled envs (env is a subdirectory inside
  the `~/.dotfiles` dir, where different configs and scripts could be placed. After that,
  `update` will make all that mumbo-jumbo, symlinking and removing old broken symlinks.
  If you want to see what will it do without but afraid to loose some files, just fire
  `dot update --dry --verbose`.
* `add` allows you to clone one or more repositories with configs. For example, this
  will clone my emacs's configs: `dot add svetlyak40wt/dot-emacs'. Of cause you could
  use full url, like that: <https://github.com/svetlyak40wt/dot-emacs> or
  <git@github.com:svetlyak40wt/dot-emacs.git>.
* `status` will show you if there are some uncommited changes in the envs, and even
  warn you if some of them aren't version controlled.

Installation
------------

1. Clone this project somewhere like `$HOME/.dotfiles` and add `$HOME/.dotfiles/bin` into
your `PATH`.
2. Then clone some config files into the `$HOME/.dotfiles` .
3. Run `dot update` to make all necessary symlinks.
4. Have a profit!

How does it work
----------------

From user's point of view — very simple. You just create a separate subdirectories, called "environments", put configs there and run `dot update`. Dotfiler will make all necessary symlinks automagickally. **What makes dotfiler better, than other solutions?** It's ability to merge files from different environments into one target dir. I'll give you example for a better understanding. 

Suppose, you have a `~/.zshrc` which sources all configs from `~/.zsh/`. And you want to separate every-day configs from the configs only needed on machines at your daily-job. In most config managers you will end upwith two separate repositories sharing part of zsh config. But dotfiler allows you to make a much clever thing — to separate zsh (actually any other configs too, if they may understand `include` instruction) into the different environments.

In this example, first environment, let's call it `base`, will contain file `base/.zsh/generic`. Second environment, called `atwork`, will have `atwork/.zsh/secret-settings`. Both of them, off cause could include other files, not only zsh configs. And most importantly, these environment now could be stored separately and installed to each machine separately. What does it meean? Right! Now, you could share you generic everyday configs on the GitHub, but keep daily-job's configs in a dry-n-safe-secret-private-repository. 

There is a way to add new environments using `dot add <url> <url>...`. Probably the process of adding environments on a fresh machine will be even more improved, when I introduce a concept of the meta-environments, which will make it possible to make one env depends on few another and to pull them during `dot add` procedure.

Get involved
------------

Don't hesitate to try dotfiler. Just install it and make your configs more structured.  Extract useful ones and share them in the GitHub, as I did. Then send me a link with a short description (or make a pull request), and I'll add you repositories to the end of this page. 

Dotfiler was developed in TDD, it's core functionality is fully tested, but that doesn't mean there isn't bugs. If you have found one, file the issue, or better, try to write a test for the use case, fix it and send as a pull request. To run all tests, install nose and run `nosetests bin/lib/dot`. 

More technical details
----------------------

If you are wondering, how does dotfiler work inside, I'll tell you. 

First of all, it walks through all files and all environments collecting all dirs, mentioned in more than one environment and files. If file with same filename exits in few environments, this is an error and `dot` will tell you they are conflicting. 

Having this dirs/files tree, it generates pairs source — target, where source is a file inside the environment dir and target is where it should be in your home dir. 

After this data is ready, `dot` generates one or more actions for each pair. Actions could be `rm`, `mkdir`, `link`, `already-linked` and `error`. Which action will be generated, depends on the current file system's state and previously generated actions. Here is a simple example:

This is a structure of the `~/.dotfiles` with two separate enviroments `zsh` and `emacs`:

```
.
├── emacs
│   └── .emacs.d
│       ├── .gitignore
│       ├── COPYING
│       ├── README.markdown
│       ├── art
│       │   ├── debian-changelog-mode.el
│       │   ├── lisp.el
│       │   ├── multiple.el
│       │   ├── my-org.el
│       │   ├── my-python.el
│       │   └── pymacs.el
│       ├── art.el
│       ├── changelog.md
│       ├── customizations.el
│       ├── init.el
│       ├── modules
│       │   ├── starter-kit-bindings.el
│       │   ├── starter-kit-eshell.el
│       │   ├── starter-kit-js.el
│       │   ├── starter-kit-lisp.el
│       │   ├── starter-kit-perl.el
│       │   └── starter-kit-ruby.el
│       ├── snippets
│       │   └── python-mode
│       │       └── pdb.yasnippet
│       ├── starter-kit-defuns.el
│       ├── starter-kit-misc.el
│       ├── starter-kit-pkg.el
│       ├── starter-kit.el
│       ├── tar.sh
│       ├── ubuntu -> art
│       ├── ubuntu.el -> art.el
│       ├── vagrant -> art
│       └── vagrant.el -> art.el
└── zsh
    ├── .bash_profile
    ├── .zsh
    │   ├── 00-options
    │   ├── 01-prompt-functions
    │   ├── 02-prompt-colors
    │   ├── 03-prompt
    │   ├── aliases
    │   ├── ash
    │   ├── dotfiler
    │   └── ssh-agent
    └── .zshrc
```

And here is result of `dot update`:

```
[art@art-osx:~/.dotfiles]% dot update
LINK    Symlink from /home/art/.bash_profile to /home/art/.dotfiles/zsh/.bash_profile was created
LINK    Symlink from /home/art/.emacs.d to /home/art/.dotfiles/emacs/.emacs.d was created
LINK    Symlink from /home/art/.zsh to /home/art/.dotfiles/zsh/.zsh was created
LINK    Symlink from /home/art/.zshrc to /home/art/.dotfiles/zsh/.zshrc was created
```

As you can see, dotfiler creates two symlinks to files and two to directories. But this was simple situation
when two environments contain no files to be symlinked into the same directory.

Here is another example, showing how config mergin works:

```
.
├── git
│   ├── .gitconfig
│   └── .zsh
│       ├── git-aliases
│       └── git-prompt
└── zsh
    ├── .bash_profile
    ├── .zsh
    │   ├── 00-options
    │   ├── 01-prompt-functions
    │   ├── 02-prompt-colors
    │   ├── 03-prompt
    │   ├── aliases
    │   ├── ash
    │   ├── dotfiler
    │   └── ssh-agent
    └── .zshrc
```

In this case, we have two environments and both of them have configs for zsh. For this situation,
dotfiler will try to create a directory `~/.zsh` and will make symlinks there:

```
[art@art-osx:~/.dotfiles]% dot update
LINK    Symlink from /home/art/.bash_profile to /home/art/.dotfiles/zsh/.bash_profile was created
LINK    Symlink from /home/art/.gitconfig to /home/art/.dotfiles/git/.gitconfig was created
MKDIR   Directory /home/art/.zsh was created.
LINK    Symlink from /home/art/.zsh/00-options to /home/art/.dotfiles/zsh/.zsh/00-options was created
LINK    Symlink from /home/art/.zsh/01-prompt-functions to /home/art/.dotfiles/zsh/.zsh/01-prompt-functions was created
LINK    Symlink from /home/art/.zsh/02-prompt-colors to /home/art/.dotfiles/zsh/.zsh/02-prompt-colors was created
LINK    Symlink from /home/art/.zsh/03-prompt to /home/art/.dotfiles/zsh/.zsh/03-prompt was created
LINK    Symlink from /home/art/.zsh/aliases to /home/art/.dotfiles/zsh/.zsh/aliases was created
LINK    Symlink from /home/art/.zsh/ash to /home/art/.dotfiles/zsh/.zsh/ash was created
LINK    Symlink from /home/art/.zsh/dotfiler to /home/art/.dotfiles/zsh/.zsh/dotfiler was created
LINK    Symlink from /home/art/.zsh/git-aliases to /home/art/.dotfiles/git/.zsh/git-aliases was created
LINK    Symlink from /home/art/.zsh/git-prompt to /home/art/.dotfiles/git/.zsh/git-prompt was created
LINK    Symlink from /home/art/.zsh/ssh-agent to /home/art/.dotfiles/zsh/.zsh/ssh-agent was created
LINK    Symlink from /home/art/.zshrc to /home/art/.dotfiles/zsh/.zshrc was created
```

Have you got the idea? Good! File an issue or (better) send a pull-request.

How to ignore some files
========================

Edit a config file `~/.dotfiles/.dotignore` and add any regex
patterns which you need.

Environments
------------

* [svetlyak40wt/dot-emacs](https://github.com/svetlyak40wt/dot-emacs) — my emacs config, based on [Emacs Starter Kit](http://github.com/technomancy/emacs-starter-kit).
* [svetlyak40wt/dot-zsh](https://github.com/svetlyak40wt/dot-zsh) — generic config for zsh, which sources all config files from `~/.zsh` directory.
* [svetlyak40wt/dot-tmux](https://github.com/svetlyak40wt/dot-tmux) — config and python wrapper for tmux.
* [svetlyak40wt/dot-git](https://github.com/svetlyak40wt/dot-git) — config and shell aliases for git.
* [svetlyak40wt/dot-helpers](https://github.com/svetlyak40wt/dot-helpers) — misc command line helpers (see repo's README for full list).
* [svetlyak40wt/dot-osx](https://github.com/svetlyak40wt/dot-osx) — OSX keybindings and settings.
* [svetlyak40wt/dot-python-dev](https://github.com/svetlyak40wt/dot-python-dev) – emacs, zsh and pudb settings for Python developement.
* [svetlyak40wt/dot-growl](https://github.com/svetlyak40wt/dot-growl) – A helper to use growl notifications from ssh sessions.
* [svetlyak40wt/dot-lisp](https://github.com/svetlyak40wt/dot-lisp) – Dotfiler's config for Lisp development. 
* [svetlyak40wt/dot-osbench](https://github.com/svetlyak40wt/dot-osbench) – A helper to setup PATH to [OSBench's](https://github.com/svetlyak40wt/osbench) bin directory.

