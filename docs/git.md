# `public/` Folder Is Subtree

Useful Links:

* https://medium.com/@porteneuve/mastering-git-subtrees-943d29a798ec

## Add subtree if no local files in main repo
git subtree add --prefix=public/ --squash frontend-remote master

## How to create subtree from existing directory:
```
git checkout -b split-frontend
git filter-branch --subdirectory-filter public/
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
# git push  <REMOTENAME> <LOCALBRANCHNAME>:<REMOTEBRANCHNAME>
# Push and track branch (see `-u` argument)
git push -u frontend-remote split-frontend:master
```

If no need pushing to split remote repo

```
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
git fetch frontend-remote
git checkout -b split-frontend frontend-remote/master
```

## Update main repo from subtree
git fetch frontend-remote
git merge -s subtree --squash frontend-remote/master    OR  git merge -X subtree=public/ --squash frontend-remote/master
??? git commit -m "Updated the plugin"

OR 

```
git subtree pull --prefix=public/ --squash frontend-remote master
```

OR 

```
git pull -s subtree <remotename> <branchname>
```

## Backporting to the subtree’s remote

```
# Add [To backport] in main repo for commits with files from subtree
# Create new branch before backporting
git checkout -b backport-plugin frontend-remote/master
# Manually apply commits (No idea why should use cherry-pick twice)
git cherry-pick -x master~3
git cherry-pick -x --strategy=subtree master
git push
```

OR 

```
# Backports all commits without exception that touched the subtree (can’t pick the relevant commits)
git subtree push --prefix=public/ frontend-remote master
```