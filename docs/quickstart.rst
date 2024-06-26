Quickstart
==========

Prerequisites
-------------

Sublime Text 2, 3, or 4
~~~~~~~~~~~~~~~~~~~~~~~
Needless to say, Sublime Text is required to use SublimeGit. Any version of Sublime Text 2, 3, or 4 should work.

Git
~~~
SublimeGit uses the Git command line interface, so you will need a recent version of Git. SublimeGit has been tested on Git 1.8+. To download a version of Git for your operating system, go to http://git-scm.com/downloads. If you are currently using version 1.7 or lower, some commands probably won't work.

You should make sure that git is accesible on your path. You can do this by running ``git --version`` in your terminal::

    $ git --version
    git version 1.8

.. note::
    If you start Sublime Text from the terminal (e.g. using the ``subl`` command on OS X) your path inside Sublime Text might be different from the path you get if you start Sublime Text by clicking on the application.

    To see your current path in Sublime Text, open up the console by selecting **View > Show Console** and execute the following python snippet:

    .. code-block:: python

        import os; print os.getenv('PATH')

    To verify that you have access to the Git executable from within Sublime Text, you can execute the following snippet, which will print ``0`` if everything worked as expected:

    .. code-block:: python

        import os; os.system('git --version')

    If this returns anything other than ``0`` you might need to explicitly set the path to your git executable. See the section :ref:`config-git-path` for information on how to do this.

.. _prereq-git-remote:

Git Configuration
~~~~~~~~~~~~~~~~~
For the moment, SublimeGit assumes that you have your environment set up so that commands working with remotes (e.g. pull, push and fetch) does not need to ask for user authentication. If that's not the case, and git asks for your username and password when pushing or pulling, then you will need to follow one of these fixes to make sure SublimeGit runs smoothly:

**SSH remotes:**
    When using SSH remotes with private keys which use passphrases, git will ask for the passphrase to authenticate. There is a safe way to make sure the passphrase is saved, and GitHub has a great guide to using it: https://help.github.com/articles/working-with-ssh-key-passphrases
**HTTPS remotes:**
    If you prefer HTTPS checkouts, then you will need to follow this guide: https://help.github.com/articles/set-up-git#password-caching

.. warning::
    It seems there can be some problems on Windows, especially when using git-bash and/or private keys with passphrases. For more information, and possible solution please see :ref:`remote-issues`

Installation
------------

There are many ways to install a package in Sublime Text, but we strongly recommend the use of `Package Control <http://wbond.net/sublime_packages/package_control>`_, which makes it easy to install and uninstall packages, as well as automatically keeping them up to date. If you are not already using it, you should give it a try.


Using Package Control
~~~~~~~~~~~~~~~~~~~~~

1. Open the Command Palette using **shift+command+p** (OS X) or **shift+ctrl+p** (Windows/Linux) or by selecting **Tools > Command Palette** from the menu bar.
2. Find and select the command **Package Control: Install Package**.
3. Find and select **SublimeGit**.
4. Restart Sublime Text.

.. note::
    When you select the **Install Packages** command, it might take a little while for the list of packages to show up. You should be able to see that Package Control is working by watching the spinner in the lower left corner of the window.

Installing From Package
~~~~~~~~~~~~~~~~~~~~~~~

1. Download the SublimeGit.zip file from https://release.sublimegit.net/SublimeGit.zip.
2. Unzip the package inside your Sublime Text package directory.

   - **Windows**: %APPDATA%\Sublime Text 2\Packages
   - **OS X**: ~/Library/Application Support/Sublime Text 2/Packages
   - **Linux**: ~/.config/sublime-text-2/Packages

3. Restart Sublime Text.

.. note::
    Note: If you are unsure where your Sublime Text package directory is, or it is hidden, you can browse to it by selecting **Preferences > Browse Packages** from within Sublime Text.

Configuration
-------------

SublimeGit comes with sensible defaults, so if you don't need to add a license, and you can execute the command **Git: Version**, you can skip straight to the :doc:`tutorial`.

.. _config-git-path:

Git Executable Path
~~~~~~~~~~~~~~~~~~~

To open the default settings for SublimeGit, go to **Preferences > Package Settings > SublimeGit > Settings - Default**. This will show the default settings for SublimeGit. But do not edit this file! Instead, open up **Preferences > Package Settings > SublimeGit > Settings - User** and copy over any settings you wish to change.

If git is not on your path, and it's not possible for you to put git on your path (such as in a very controlled environment where you don't have administrator rights), then you can change the **git_executables** settings to point directly at your git installation.

Be sure to copy the entire thing into your **Settings - User** file, and change the paths accordingly. Be aware that each item in the list will be quoted on its own.

After performing these changes, your user settings might look like this::

    {
        "git_executables": {
            "git": ["/usr/local/bin/git"],
            "git_flow": ["/usr/local/bin/git", "flow"],
            "legit": ["legit"]
        }
    }


If you don't use the extensions, there is no need to change their paths.

Enabling or Disabling Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don't use a plugin, it might be annoying that its commands keep showing up. Change the **git_extensions** setting to get rid of them. After disabling git-flow, your local settings file would look like this::

    {
        "git_extensions": {
            "git_flow": false,
            "legit": true
        }
    }


You will need to restart Sublime Text for these changes to take effect.


Using SublimeGit
----------------

Once you're all set up you should jump head-first into the :doc:`tutorial`, which will take you through some basics on using SublimeGit.

Alternatively, you can jump straight to the :doc:`commands`.
