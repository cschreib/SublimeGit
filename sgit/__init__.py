# coding: utf-8

__version__ = '1.0.36'


# Import all the commands

from .util import GitPanelWriteCommand, GitPanelAppendCommand

from .repo import GitInitCommand, GitSwitchRepoCommand

from .custom import GitCustomCommand, GitCustomOutputCommand

from .diff import (GitDiffCommand, GitDiffCachedCommand, GitDiffRefreshCommand, GitDiffMoveCommand,
                   GitDiffChangeHunkSizeCommand, GitDiffStageUnstageHunkCommand, GitDiffCurrentFileCommand,
                   GitDiffCachedCurrentFileCommand, GitDiffEditHunkCommand, GitDiffDiscardHunkCommand,
                   GitDiffEventListener)

from .show import GitShowCommand, GitShowRefreshCommand

from .help import GitHelpCommand, GitVersionCommand

from .gc import GitGarbageCollectCommand

from .log import GitLogCommand, GitQuickLogCommand, GitQuickLogCurrentFileCommand

from .blame import (GitBlameCommand, GitBlameRefreshCommand, GitBlameShowCommand,
                    GitBlameBlameCommand)
from .blame import GitBlameEventListener

from .remote import (GitPublishCurrentBranchCommand, GitPullOtherBranchCommand,
                     GitFetchCommand, GitFetchSingleBranchCommand, GitPullCommand, GitPushCommand,
                     GitRemoteCommand, GitRemoteAddCommand)

from .status import (GitStatusCommand, GitStatusReplaceCommand, GitStatusRefreshCommand, GitQuickStatusCommand,
                     GitStatusMoveCommand, GitStatusStageCommand,
                     GitStatusUnstageCommand, GitStatusDiscardCommand,
                     GitStatusOpenFileCommand, GitStatusDiffCommand,
                     GitStatusIgnoreCommand, GitStatusStashCmd, GitStatusStashApplyCommand,
                     GitStatusStashPopCommand, GitStatusCheckoutCommand)
from .status import GitStatusBarEventListener, GitStatusEventListener

from .add import GitQuickAddCommand, GitAddCurrentFileCommand

from .commit import (GitCommitCommand, GitCommitAmendCommand, GitCommitTemplateCommand,
                     GitCommitPerformCommand, GitQuickCommitCommand, GitQuickCommitCurrentFileCommand,
                     GitCommitSaveCommand, GitCommitUndoCommand)
from .commit import GitCommitEventListener

from .stash import (GitStashCommand, GitSnapshotCommand,
                    GitStashApplyCommand, GitStashPopCommand)

from .tag import GitTagCommand, GitAddTagCommand

from .checkout import (GitCheckoutBranchCommand, GitCheckoutCommitCommand,
                       GitCheckoutNewBranchCommand, GitCheckoutCurrentFileCommand,
                       GitCheckoutTagCommand, GitCheckoutRemoteBranchCommand)

from .branch import (GitDeleteBranch, GitDeleteMergedBranches)

from .merge import GitMergeCommand, GitMergeAbortCommand, GitRebaseCommand

from .gitk import GitGitkCommand

from .sublimegit import (SublimeGitDocumentationCommand, SublimeGitVersionCommand)


# import plugins

from . import git_extensions
