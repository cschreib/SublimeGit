# coding: utf-8
from functools import partial
import logging

import sublime
from sublime_plugin import WindowCommand

from .util import StatusSpinner, noop, get_setting
from .cmd import GitCmd
from .helpers import GitRemoteHelper


NO_REMOTES = u"No remotes have been configured. Remotes can be added with the Git: Add Remote command. Do you want to add a remote now?"
DELETE_REMOTE = u"Are you sure you want to delete the remote %s?"

NO_ORIGIN_REMOTE = u"You are not on any branch and no origin has been configured. Please check out a branch and run Git: Remote Add to add a remote."
NO_BRANCH_REMOTES = u"No remotes have been configured for the branch %s and no origin exists. Please run Git: Remote Add to add a remote."

CURRENT_NO_UPSTREAM = u"No upstream currently is currently specified for {branch}. Do you want to set the upstream to {merge} on {remote}?"
CURRENT_DIFFERENT_UPSTREAM = u"The upstream for {branch} is currently set to {branch_merge} on {branch_remote}. Do you want to change it to {merge} on {remote}?"

NO_UPSTREAM = u"No upstream is configured for your current branch. Do you want to run Git: Publish Current Branch?"
NO_TRACKING = u"No tracking information is configured for your current branch. Do you want to run Git: Pull Other Branch?"

FORCE_PUSH = (u"It is discouraged to rewrite history which has already been pushed. "
              u"Are you sure you want to force your local changes on the remote? "
              u"Any remote commit not in your local branch will be lost.")

REMOTE_DIVERGED = (u"Your local branch and the remote have diverged. Please run Git: Pull to attempt to merge remote changes, "
                   u"or Git: Force Push to discard the remote changes entirely.")

REMOTE_SHOW_TITLE_PREFIX = '*git-remote*: '

logger = logging.getLogger('SublimeGit.remote')


class GitFetchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Fetches git objects from the remote repository

    If there is only one remote configured, this remote will be
    used for fetching. If there are multiple remotes, you will be
    asked to select the remote to fetch from.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)

        if len(choices) > 1:
            choices.append(['+ All', 'Fetch from all configured remotes', 'git fetch --all'])

            def on_done(idx):
                if idx == -1:
                    return
                if idx == len(choices) - 1:
                    self.on_remote(repo)
                else:
                    self.on_remote(repo, choices[idx][0])

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, remote=choices[0][0])

    def on_remote(self, repo, remote=None):
        self.panel = self.window.get_output_panel('git-fetch')
        self.panel_shown = False

        thread = self.git_async(['fetch', '-v', remote if remote else '--all'], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Fetching from %s" % (remote if remote else "all remotes"))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-fetch'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitFetchSingleBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Fetches git objects for a single branch from the remote repository

    If there is only one remote configured, this remote will be
    used for fetching. If there are multiple remotes, you will be
    asked to select the remote to fetch from.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)

        if len(choices) > 1:
            def on_done(idx):
                if idx == -1:
                    return
                remote = choices[idx][0]
                self.on_remote(repo, remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, choices[0][0])

    def on_remote(self, repo, remote):
        remote_branches = self.get_remote_branches(repo, remote)
        if not remote_branches:
            return sublime.error_message("No branches on remote %s" % remote)

        choices = self.format_quick_branches(remote_branches)

        def on_done(idx):
            if idx == -1:
                return
            branch = choices[idx][0]
            self.on_remote_branch(repo, remote, branch)

        sublime.set_timeout(partial(self.window.show_quick_panel, choices, on_done), 50)

    def on_remote_branch(self, repo, remote, branch):
        self.panel = self.window.get_output_panel('git-pull')
        self.panel_shown = False

        cmd = ['fetch', remote, '%s:%s' % (branch, branch)]

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Fetching %s from %s" % (branch, remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-pull'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitPublishCurrentBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Push the current branch as a new or existing branch on a remote

    This is the command to use if you are pushing a branch to a remote
    for the first time, or to a different remote than the configured upstream.
    Will push the current branch to a specified branch on the selected remote,
    creating the remote branch if it doesn't already exist.

    If there is only one remote configured, that will be used, otherwise you
    will be asked to select a remote. If there are no remotes, you will be asked
    to add one.

    You will be asked to supply a name to use for the branch on the
    remote. By default, the current branch name will be suggested.

    .. warning::

        Trying to push when in a detached head state will give an error
        message. This is not generally something you want to do.

    .. note::

        This command shares a lot of similarities with the excellent
        git-publish command, which can be found at
        https://github.com/gavinbeatty/git-publish.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        if not branch:
            return sublime.error_message("You really shouldn't push a detached head")

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)

        if len(choices) > 1:
            def on_done(idx):
                if idx == -1:
                    return
                branch_remote = choices[idx][0]
                self.on_remote(repo, branch, branch_remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, branch, choices[0][0])

    def on_remote(self, repo, branch, remote):
        def on_done(rbranch):
            rbranch = rbranch.strip()
            if not rbranch:
                return
            self.on_remote_branch(repo, branch, remote, rbranch)

        self.window.show_input_panel('Remote branch:', branch, on_done, noop, noop)

    def on_remote_branch(self, repo, branch, remote, merge):
        cmd = ['push', '-v', remote, '%s:%s' % (branch, merge)]

        branch_remote, branch_merge = self.get_branch_upstream(repo, branch)
        if remote != branch_remote or branch_merge != ("refs/heads/%s" % merge):
            if branch_remote == '' or branch_merge == '':
                msg = CURRENT_NO_UPSTREAM.format(branch=branch, remote=remote, merge=merge)
            else:
                msg = CURRENT_DIFFERENT_UPSTREAM.format(branch=branch, branch_remote=branch_remote,
                                                        branch_merge=branch_merge, remote=remote, merge=merge)
            if sublime.ok_cancel_dialog(msg, "Set Upstream"):
                cmd.append('--set-upstream')

        self.panel = self.window.get_output_panel('git-push')
        self.panel_shown = False

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pushing %s to %s" % (branch, remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-push'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitPullOtherBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Pull a given remote branch into the current branch

    This is very similar to the Merge command, except that the merged branch
    is fetched from the remote before merging. This ensures that the merged
    branch is up-to-date with the remote.

    If there is only one remote configured, that will be used, otherwise you
    will be asked to select a remote. If there are no remotes, you will be asked
    to add one.

    You will be asked to supply the name of the remote branch to merge.

    .. warning::

        Trying to pull when in a detached head state will give an error
        message. This is not generally something you want to do.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        if not branch:
            return sublime.error_message("Cannot pull in a detached head state")

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)

        if len(choices) > 1:
            def on_done(idx):
                if idx == -1:
                    return
                remote = choices[idx][0]
                self.on_remote(repo, branch, remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, branch, choices[0][0])

    def on_remote(self, repo, branch, remote):
        remote_branches = self.get_remote_branches(repo, remote)
        if not remote_branches:
            return sublime.error_message("No branches on remote %s" % remote)

        choices = self.format_quick_branches(remote_branches)

        def on_done(idx):
            if idx == -1:
                return
            branch = choices[idx][0]
            self.on_remote_branch(repo, branch, remote, branch)

        sublime.set_timeout(partial(self.window.show_quick_panel, choices, on_done), 50)

    def on_remote_branch(self, repo, branch, remote, merge):
        self.panel = self.window.get_output_panel('git-pull')
        self.panel_shown = False

        cmd = ['pull']

        extra_flags = get_setting('git_merge_flags')
        if isinstance(extra_flags, list):
            cmd.extend(extra_flags)

        cmd.extend(['-v', remote, '%s:%s' % (branch, merge)])

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pulling %s from %s" % (merge, remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-pull'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitPushCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Push the current branch on the tracked remote

    This is the command to use if you are pushing a branch that already tracks
    a remote branch, and you just want to update this remote branch with your
    local changes.

    If the current branch does not yet track a remote branch, you will be asked
    if you want to use the "Publish Current Branch" command instead, which will
    set up branch tracking before pushing.

    .. warning::

        Trying to push when in a detached head state will give an error
        message. This is not generally something you want to do.
    """

    def run(self, force=False):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        if not branch:
            return sublime.error_message("You really shouldn't push a detached head")

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        branch_remote, branch_merge = self.get_branch_upstream(repo, branch)
        if not branch_remote or not branch_merge:
            if sublime.ok_cancel_dialog(NO_UPSTREAM, 'Yes'):
                self.window.run_command('git_publish_current_branch')
            return

        remote_ahead, _ = self.get_remote_commit_differences(repo, branch_remote, branch)
        logger.warning('{}'.format(remote_ahead))
        if remote_ahead != 0:
            if force:
                if not sublime.ok_cancel_dialog(FORCE_PUSH, 'Force Push'):
                    return
            else:
                return sublime.error_message(REMOTE_DIVERGED)

        self.panel = self.window.get_output_panel('git-push')
        self.panel_shown = False

        cmd = ['push', '-v']
        if force:
            cmd += ['--force']

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pushing to %s" % (branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-push'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitPullCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Pull the tracked remote branch into the current branch

    This is the command to use if the current branch has been modified on the
    remote since it was last pulled, and you want to update your local branch
    to match the latest version on the remote.

    If there is only one remote configured, that will be used, otherwise you
    will be asked to select a remote. If there are no remotes, you will be asked
    to add one.

    If the current branch does not yet track a remote branch, you will be asked
    if you want to use the "Pull Other Branch" command instead, which allows you
    to pull any other branch from the remote into the current branch.

    .. warning::

        Trying to pull when in a detached head state will give an error
        message. This is not generally something you want to do.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        if not branch:
            return sublime.error_message("You really shouldn't push a detached head")

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        branch_remote, branch_merge = self.get_branch_upstream(repo, branch)
        if not branch_remote or not branch_merge:
            if sublime.ok_cancel_dialog(NO_TRACKING, 'Yes'):
                self.window.run_command('git_pull_other_branch')
            return

        self.panel = self.window.get_output_panel('git-pull')
        self.panel_shown = False

        thread = self.git_async(['pull', '-v'], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pulling from %s" % (branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-pull'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})


class GitRemoteAddCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Add a named git remote at a given URL

    You will be asked to provide the name and url of the remote (see below).
    Press ``enter`` to select the value. If you want to cancel, press ``esc``.

    After completion, the Git: Remote command will be run, to allow for
    further management of remotes.

    **Name:**
        The name of the remote. By convention, the name *origin* is used
        for the "main" remote. Therefore, if your repository does not
        have any remotes, the initial suggestion for the name will be *origin*.
    **Url:**
        The git url of the remote repository, in any format that git understands.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes(repo)
        initial = 'origin' if not remotes else ''

        self.window.show_input_panel('Name:', initial, partial(self.on_name, repo), noop, noop)

    def on_name(self, repo, name):
        name = name.strip()
        # todo: check if name exists
        if not name:
            # todo: error message?
            return

        self.window.show_input_panel('Url:', '', partial(self.on_url, repo, name), noop, noop)

    def on_url(self, repo, name, url):
        url = url.strip()
        if not url:
            # todo: error message?
            return

        self.git(['remote', 'add', name, url], cwd=repo)
        self.window.run_command('git_remote')


class GitRemoteCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Manage git remotes

    Presents s list of remotes, including their push and pull urls.
    Select the remote to perform an action on it. After an action has
    been performed, the list will show up again to allow for further
    editing of remotes. To cancel, press ``esc``.

    Available actions:

    **Show**
        Show information about the remote. This includes the
        push and pull urls, the current HEAD, the branches tracked,
        and the local branches which are set up for push and pull.

        The result will be displayed in a panel in the bottom of
        the Sublime Text window.

    **Rename**
        Rename the selected remote. An input field will appear
        allowing you to write a new name for the remote. If a new
        name is not provided, or ``esc`` is pressed, the action
        will be aborted.

    **Remove**
        Remove the selected remote. All remote-tracking branches,
        and configuration for the remote is removed. You will be
        asked for confirmation before removing the remote.

    **Set URL**
        Change the URL for the selected remote. An input fiels
        will appear allowing you to specify a new URL. The given
        URL will be used for both the push and pull URL. If a new
        URL isn't specified, or ``esc`` is pressed, the URL will
        not be updated.

    **Prune**
        Delete all stale remote-tracking branches for the selected
        remote. Any remote-tracking branches in the local repository
        which are no longer in the remote repository will be removed.

    """

    SHOW = 'Show'
    RENAME = 'Rename'
    RM = 'Remove'
    SET_URL = 'Set URL'
    PRUNE = 'Prune'

    REMOTE_ACTIONS = [
        [SHOW, 'git remote show <name>'],
        [RENAME, 'git remote rename <old> <new>'],
        [RM, 'git remote rm <name>'],
        [SET_URL, 'git remote set-url <name> <newurl>'],
        [PRUNE, 'git remote prune <name>'],
    ]

    ACTION_CALLBACKS = {
        SHOW: 'show_remote',
        RM: 'remove_remote',
        RENAME: 'rename_remote',
        SET_URL: 'remote_set_url',
        PRUNE: 'prune_remote'
    }

    def run(self, repo=None):
        repo = repo or self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)
        self.window.show_quick_panel(choices, partial(self.remote_panel_done, repo, choices))

    def reset(self, repo):
        self.window.run_command('git_remote', {'repo': repo})

    def remote_panel_done(self, repo, choices, idx):
        if idx != -1:
            remote = choices[idx][0]

            def on_remote():
                self.window.show_quick_panel(self.REMOTE_ACTIONS, partial(self.action_panel_done, repo, remote))

            sublime.set_timeout(on_remote, 50)

    def action_panel_done(self, repo, remote, idx):
        if idx != -1:
            action = self.REMOTE_ACTIONS[idx][0]
            callback = self.ACTION_CALLBACKS[action]
            func = getattr(self, callback, None)
            if func:
                func(repo, remote)

    def show_remote(self, repo, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'show', remote], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Showing %s" % remote)
        runner.start()
        self.reset(repo)

    def remove_remote(self, repo, remote):
        if sublime.ok_cancel_dialog(DELETE_REMOTE % remote, "Delete"):
            self.git(['remote', 'rm', remote], cwd=repo)
        self.reset(repo)

    def rename_remote(self, repo, remote):
        def on_done(new_name):
            new_name = new_name.strip()
            if new_name:
                self.git(['remote', 'rename', remote, new_name], cwd=repo)
            self.reset(repo)

        self.window.show_input_panel('Name:', remote, on_done, noop, self.reset)

    def remote_set_url(self, repo, remote):
        url = self.get_remote_url(repo, remote)
        self.window.show_input_panel('Url:', url, partial(self.on_url, repo, remote), noop, self.reset)

    def on_url(self, repo, remote, url):
        url = url.strip()
        if url:
            self.git(['remote', 'set-url', remote, url], cwd=repo)
        self.reset(repo)

    def prune_remote(self, repo, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'prune', remote], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pruning %s" % remote)
        runner.start()
        self.reset(repo)

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-remote'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
