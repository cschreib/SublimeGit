# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .cmd import GitCmd
from .helpers import GitBranchHelper

DELETE_BRANCHES = 'Are you sure you want to delete the following branches, which have all been fully merged in {parent_branch}?\n\n  {selected_branches}'
DELETE_BRANCHES_CURRENT = 'Are you sure you want to delete the following branches, which have all been fully merged in {parent_branch}?\n\n  {selected_branches}\n\nThe following branch will not be deleted since it is currently checked out:\n\n  {current_branch}'
DELETE_BRANCHES_CURRENT_ONLY = 'The following branch will not be deleted since it is currently checked out:\n\n  {current_branch}'
DELETE_BRANCHES_NO_BRANCH = 'No branch was found that is already merged in {parent_branch}.'

class GitBranchWindowCmd(GitCmd, GitBranchHelper):
    pass


class GitDeleteMergedBranches(WindowCommand, GitBranchWindowCmd):
    """
    Delete all branches that have been merged into another branch.
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

        self.git(['branch', '-d'] + selected_branches, cwd=repo)
