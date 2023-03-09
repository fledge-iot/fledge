# Contributing to Fledge

The project welcomes contributions of all types; documentation, code
changes, new plugins, scripts, just simply reports of the way you use Fledge
or suggestions of features you would like to see within Fledge.

The following is a set of guidelines for contributing to Fledge IoT
project and its plugins, which are hosted in
the [fledge-iot Organization](https://github.com/fledge-iot) on GitHub.

To give us feedback or make suggestions use the [Fledge Slack Channel](https://lfedge.slack.com/archives/CLJ7CNCAX).

If you find a security vulnerability within Fledge or any of it's plugins then we request that you inform us via email rather than by opening an issue in GitHub. This allows us to act on it without giving information that others might exploit. Any security vulnerability will be discussed at the project TSC and user will be informed of the need to upgrade via the Fledge slack channel. The email address to which vulnerabilities should be reported is security@dianomic.com.

## Pull requests

**Please ask first** before embarking on any significant work (e.g. implementing new features,
refactoring code etc.), otherwise you risk spending a lot of time working on something that might
already be underway or is unlikely to be merged into the project.

Join the Fledge slack channel on [LFEdge](https://lfedge.slack.com/archives/CLJ7CNCAX). This
will allow you to talk to the wider fledge community and discuss your
proposed changes and get help from the maintainers when needed.

Please adhere to the coding conventions used throughout the project and
limit your changes to functional rather than aesthetic changes to make
it as easy as possible to review your changes. We also encourage you to
comment your code changes for the same reason and for the benefit of those
that come after you.

Adhering to the following process is the best way to get your work included in the project:

1. [Fork](https://help.github.com/articles/fork-a-repo/) the project, clone your fork, and configure
   the remotes:

   ```bash
   # Clone your fork of the repo into the current directory
   git clone https://github.com/<your-username>/fledge-iot.git

   # Navigate to the newly cloned directory
   cd fledge-iot

   # Assign the original repo to a remote called "upstream"
   git remote add upstream https://github.com/fledge-iot/fledge.git
   ```

2. If you cloned a while ago, get the latest changes from upstream:

   ```bash
   git checkout main
   git pull --rebase upstream main
   ```

3. Create a new topic branch from `develop`, if you are working a particular issue from the Project Jira then the convention for branch names is to use the Jira name, otherwise choose a descriptive branch name that contains your GitHub username in order to help us track the changes.

   ```bash
   git checkout -b [branch-name]
   ```

4. Commit your changes in logical chunks. When you are ready to commit, make sure to write a Good
   Commit Message™.  Use [interactive rebase](https://help.github.com/articles/about-git-rebase)
   to group your commits into logical units of working before making them public.

   Note that every commit you make must be signed. By signing off your work you indicate that you
   are accepting the [Developer Certificate of Origin](https://developercertificate.org/).

   Use your real name (sorry, no pseudonyms or anonymous contributions). If you set your `user.name`
   and `user.email` git configs, you can sign your commit automatically with `git commit -s`.

5. Locally merge (or rebase) the upstream development branch into your topic branch:

   ```bash
   git pull --rebase upstream main
   ```

6. Push your topic branch up to your fork:

   ```bash
   git push origin [branch-name]
   ```

7. [Open a Pull Request](https://help.github.com/articles/using-pull-requests/) with a clear title
   and detailed description.

### Plugins

The above addresses the main Fledge repository, however plugins each have
a repository of their own which contains the code for the plugin and the
documentation for the plugin. If you wish to work on an existing plugin
then the process is similar to that above, just replace the fledge.git
repository with the fledge-{plugin-type}-{plugin-name}.git repository, for example

   ```bash
   # Clone your fork of the repo into the current directory
   git clone https://github.com/<your-username>/fledge-south-sinusoid.git

   # Navigate to the newly cloned directory
   cd fledge-south-sinusoid

   # Assign the original repo to a remote called "upstream"
   git remote add upstream https://github.com/fledge-iot/fledge-south-sinusoid.git
   ```

If you wish to create a new plugin then contact the maintainers and we
will create a blank base repository for you to add your code into.
