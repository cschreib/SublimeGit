# coding: utf-8
import os

import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import noop, find_view_by_settings, get_setting
from .cmd import GitCmd
from .helpers import GitLogHelper, GitStatusHelper

GIT_LOG_VIEW_TITLE_PREFIX = '*git-log*: '
GIT_LOG_VIEW_SYNTAX = 'Packages/SublimeGit/syntax/SublimeGit Log.tmLanguage'
GIT_LOG_VIEW_SETTINGS = {
    'translate_tabs_to_spaces': False,
    'draw_white_space': 'none',
    'word_wrap': False,
    'git_log': True,
}

GIT_LOG_ALL_SETTING = '*'


class GitLogCommand(WindowCommand, GitCmd):
    """
    Display the commit log for the current branch as a graph

    This displays the commit log for the current branch in a new window, formatted
    as a graph.
    """

    def run(self, refresh_only=False, file=None):
        repo = self.get_repo(silent=True if refresh_only else False)
        if not repo:
            return

        title = GIT_LOG_VIEW_TITLE_PREFIX
        if file:
            title += os.path.join(repo, file)
        else:
            title += repo

        file_setting = GIT_LOG_ALL_SETTING if file is None else file

        view = find_view_by_settings(self.window, git_view='log', git_repo=repo, git_file=file_setting)
        if not view and not refresh_only:
            view = self.window.new_file()

            view.set_name(title)
            view.set_syntax_file(GIT_LOG_VIEW_SYNTAX)
            view.set_scratch(True)
            view.set_read_only(True)

            view.settings().set('git_view', 'log')
            view.settings().set('git_repo', repo)
            view.settings().set('git_file', file_setting)
            view.settings().set('__vi_external_disable', get_setting('git_status_disable_vintageous') is True)

            for key, val in list(GIT_LOG_VIEW_SETTINGS.items()):
                view.settings().set(key, val)

        if view is not None:
            self.window.focus_view(view)
            view.run_command('git_log_refresh')


class GitLogCurrentFileCommand(TextCommand, GitCmd, GitStatusHelper):
    """
    Display the commit log for the current file as a graph

    This displays the commit log for the current file in a new window, formatted
    as a graph.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message("Cannot get the git log of an unsaved file.")
            return

        repo = self.get_repo()
        if not repo:
            return

        if not self.file_in_git(repo, filename):
            sublime.error_message("The file %s is not tracked by git." % filename.replace(repo, '').lstrip('/'))
            return

        self.view.window().run_command('git_log', {'file': filename})


class GitLogRefreshCommand(TextCommand, GitCmd, GitLogHelper):
    _lpop = False

    def is_visible(self):
        return False

    def run(self, edit):
        if not self.view.settings().get('git_view') == 'log':
            return

        repo = self.get_repo()
        if not repo:
            return

        file = self.view.settings().get('git_file')
        if file == GIT_LOG_ALL_SETTING:
            entries = self.get_graph_log(repo)
        else:
            entries = self.get_graph_log(repo, path=file, follow=True)

        if not entries:
            return

        max_subject_len = 80
        max_graph_len = max(len(e[0].strip()) for e in entries)
        max_author_len = max(len(e[4]) for e in entries if len(e) > 1)
        max_rel_date_len = max(len(e[7]) for e in entries if len(e) > 1)
        format_string = '{:<' + str(max_graph_len) + '} {:<' + str(max_subject_len) + '} {} {:<'+str(max_author_len)+'} {:<'+str(max_rel_date_len)+'} ({})\n'

        def truncate(subj):
            if len(subj) <= max_subject_len:
                return subj

            return subj[0:max_subject_len - 4] + '...'

        log = ''
        for e in entries:
            if len(e) > 1:
                log += format_string.format(e[0].strip(), truncate(e[1]), e[2][0:8], e[4], e[7], e[6])
            else:
                if e[0] != '...':
                    log += '{}\n'.format(e[0].strip())

        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), log)
        self.view.set_read_only(True)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(1))
        self.view.set_viewport_position((0.0, 0.0), False)


class GitQuickLogCommand(WindowCommand, GitCmd, GitLogHelper):
    """
    Display the commit log for the current branch and show the diff of the selected commit

    You will be asked which commit to inspect from the log. Commits will be sorted from
    latest to oldest. Once a commit is selected, the diff of this commit will be displayed
    in a new window.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        log = self.get_quick_log(repo)
        hashes, choices = self.format_quick_log(log)

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.window.run_command('git_show', {'obj': commit, 'repo': repo})

        self.window.show_quick_panel(choices, on_done)


class GitQuickLogCurrentFileCommand(TextCommand, GitCmd, GitLogHelper):
    """
    Display the commit log for the current file and show the diff of the selected commit

    You will be asked which commit to inspect from the log. Commits will be sorted from
    latest to oldest. Once a commit is selected, the diff of this commit will be displayed
    in a new window.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            self.view.window().show_quick_panel(['No log for file'], noop)

        repo = self.get_repo()
        if not repo:
            return

        log = self.get_quick_log(repo, path=filename, follow=True)
        hashes, choices = self.format_quick_log(log)

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.view.window().run_command('git_show', {'obj': commit, 'repo': repo})

        self.view.window().show_quick_panel(choices, on_done)
