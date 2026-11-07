# mystica555.github.io

Source for [mystica555.github.io](https://mystica555.github.io/) — a single static page linking my GitHub projects, with links to both the live GitHub Pages site and the code tree where a project has one.

## Repository list

The project and fork cards in `index.html` are generated from the public GitHub API by `scripts/update_repos.py`. Edit the surrounding page freely; the contents between the `<!-- projects:start -->` / `<!-- projects:end -->` and `<!-- forks:start -->` / `<!-- forks:end -->` markers are replaced on each run.

The workflow in `.github/workflows/update-repos.yml` refreshes the cards daily and on manual dispatch, then commits any changes.

To refresh them locally:

```sh
GITHUB_TOKEN=$(gh auth token) python3 scripts/update_repos.py
```

TVPowerSync is pinned as the featured project via the `PINNED` tuple at the top of the script. Add a repository there to keep it at the front of the Projects grid.
