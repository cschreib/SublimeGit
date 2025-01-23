# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .cmd import GitCmd
from .helpers import GitBranchHelper, GitErrorHelper

DELETE_BRANCH_CURRENT = 'The branch {branch} cannot be deleted because it is currently checked out. Please checkout another branch and try again.'
DELETE_BRANCH_UNMERGED = 'The branch {branch} is not fully merged. Are you sure you want to delete it?'
DELETE_BRANCHES = 'Are you sure you want to delete the following branches, which have all been fully merged in {parent_branch}?\n\n  {selected_branches}'
DELETE_BRANCHES_CURRENT = 'Are you sure you want to delete the following branches, which have all been fully merged in {parent_branch}?\n\n  {selected_branches}\n\nThe following branch will not be deleted since it is currently checked out:\n\n  {current_branch}'
DELETE_BRANCHES_CURRENT_ONLY = 'The following branch will not be deleted since it is currently checked out:\n\n  {current_branch}'
DELETE_BRANCHES_NO_BRANCH = 'No branch was found that is already merged in {parent_branch}.'

class GitBranchWindowCmd(GitCmd, GitBranchHelper, GitErrorHelper):
    pass

class GitDeleteBranch(WindowCommand, GitBranchWindowCmd):
    """
    Delete a specific branch.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branches = self.get_branches(repo)
        choices = []
        for current, name in branches:
            choices.append('%s %s' % ('*' if current else ' ', name))

        self.window.show_quick_panel(choices, partial(self.on_branch_selected, repo, branches), sublime.MONOSPACE_FONT)

    def on_branch_selected(self, repo, branches, idx):
        if idx == -1:
            return

        current, branch = branches[idx]

        if current:
            sublime.error_message(DELETE_BRANCH_CURRENT.format(branch=branch))
            return

        merged_branches = [n for _, n in self.get_branches(repo, merged=True)]

        flag = '-d'
        if branch not in merged_branches:
            msg = DELETE_BRANCH_UNMERGED.format(branch=branch)
            if not sublime.ok_cancel_dialog(msg, "Delete branch"):
                return

            flag = '-D'

        exit, stdout, stderr = self.git(['branch', flag, branch], cwd=repo)
        if exit == 0:
            sublime.status_message('Branch {} deleted'.format(branch))
        else:
            sublime.error_message(self.format_error_output(stdout, stderr))


class GitDeleteMergedBranches(WindowCommand, GitBranchWindowCmd):
    """
    Delete all branches that have been merged into another branch.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branches = self.get_branches(repo, remotes=True) + self.get_branches(repo)
        choices = []
        for current, name in branches:
            choices.append('%s %s' % ('*' if current else ' ', name))

        self.window.show_quick_panel(choices, partial(self.on_branch_selected, repo, branches), sublime.MONOSPACE_FONT)

    def on_branch_selected(self, repo, branches, idx):
        if idx == -1:
            return

        parent_branch = branches[idx][1]

        branches = self.get_branches(repo, merged=parent_branch)
        branches = [(c, n) for c, n in branches if n != parent_branch]

        selected_branches = [n for c, n in branches if not c]
        current_branch = [n for c, n in branches if c]

        selected_branches_str = "\n  ".join(selected_branches)
        current_branch_str = "\n  ".join(current_branch)

        if len(selected_branches) == 0:
            if len(current_branch) == 0:
                msg = DELETE_BRANCHES_NO_BRANCH.format(parent_branch=parent_branch)
            else:
                msg = DELETE_BRANCHES_CURRENT_ONLY.format(parent_branch=parent_branch, current_branch=current_branch_str)

            sublime.message_dialog(msg)
            return

        if len(current_branch) == 0:
            msg = DELETE_BRANCHES.format(parent_branch=parent_branch, selected_branches=selected_branches_str)
        else:
            msg = DELETE_BRANCHES_CURRENT.format(parent_branch=parent_branch, selected_branches=selected_branches_str, current_branch=current_branch_str)

        if not sublime.ok_cancel_dialog(msg, "Delete branches"):
            return

        exit, stdout, stderr = self.git(['branch', '-d'] + selected_branches, cwd=repo)
        if exit == 0:
            if len(selected_branches) > 1:
                sublime.status_message('{} branches deleted'.format(len(selected_branches)))
            else:
                for branch in selected_branches:
                    sublime.status_message('Branche {} deleted'.format(branch))
        else:
            sublime.error_message(self.format_error_output(stdout, stderr))
