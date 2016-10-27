0.5.0 (2016-10-27)
==================

Config file `.dotignore` was added and now it is possible
to extend ignore list with custom patterns. Thanks to
@TimothyEarley for the pull [#17](https://github.com/svetlyak40wt/dotfiler/pull/17).

Also, now `.gitmodules` is ignored by default.

0.4.3 (2016-01-14)
==================

* License files now are ignored (thanks to @alamaison).
* Added Windows support (thanks to @alamaison).
* Fixed issue #15 when some symlinks are not created because
parent directory already exists and not belong to any dotfiler's
environment.

0.4.2 (2015-09-09)
==================

* Fixed processing of filenames containing unicode symbols.
	
0.4.1 (2015-02-10)
==================

* Don't symlink `.gitignore` files.

0.4.0 (2015-02-09)
==================

* Don't create symlinks to files which starts from "news", "changelog' or "readme". Case is ignored.
  This allows to add changelogs and readmes into the [pluggable environments][envs].

0.3.0 (2014-11-25)
==================

* Fixed case when `~/Library` already exists and we need to symlink `~/.dotfiles/osx/Library/Keybinding` into it.
* Add [svetlyak40wt/dot-osx](https://github.com/svetlyak40wt/dot-osx) to the list of [available environments][envs].

0.2.0 (2014-04-02)
==================

* Now command `update` have `--skip-pull` option which is able
  to make huge impact to the update speed.

0.1.0 (2014-01-31)
==================

First full featured release. Right now it is able to:

* create symlinks to configs, spreaded among different environments;
* track if symlink target has disappeared;
* add new environments by url, pointing to a repository, or by github
  shortcut;
* show status of environments (uncommited/unpushed files).


[envs]: https://github.com/svetlyak40wt/dotfiler#environments
