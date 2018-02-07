# `public/` Folder Is Subtree

TL;DR;

```
git subtree pull --prefix=public/ --squash frontend-remote master
git subtree push --prefix=public/ frontend-remote master
```

Useful Links:

* https://medium.com/@porteneuve/mastering-git-subtrees-943d29a798ec

## Create subtree repo from subdirectory in main repo

Manually

```
git checkout -b split-frontend
git filter-branch --subdirectory-filter public/
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
# git push  <REMOTENAME> <LOCALBRANCHNAME>:<REMOTEBRANCHNAME>
# Push and track branch (see `-u` argument)
git push -u frontend-remote split-frontend:master
```

With git subtree (it worked for the first time, but doesn't later :<)

```
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
# Put public/ folder in a separate branch
git subtree split -P public/ -b split-frontend
git fetch frontend-remote
git branch -u frontend-remote/master split-frontend
```


## Add subtree

Manually (not tested with push/pull)

```
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
git fetch frontend-remote
git checkout -b split-frontend frontend-remote/master
git read-tree --prefix=public/ -u split-frontend
```

With git subtree

```
# Remove local files if neccessary
git rm -r public/
git add -u
git commit -m "Removing public/ directory"
git remote add frontend-remote git@github.com:cscenter/site-frontend.git
git subtree add --prefix=public/ --squash frontend-remote master
```

## Update main repo from subtree repo

```
git checkout split-frontend
git pull
git checkout master
```


```
git fetch frontend-remote
git checkout master
git merge -Xsubtree=public/ --squash --no-commit frontend-remote/master
git commit -m "Updated public/ from remote repo"
```

With git subtree

```
To make `subtree pull` work, you need to replace subdirectory with a subtree addition (merge your plugin history with main repo history)
git rm -r public/
git commit -m "Removing public/ for subtree replacement"
git subtree add --prefix=public/ --squash frontend-remote master
# Then git subtree pull --prefix=<subdirectory> <remote repo name> <branch name>
git subtree pull --prefix=public/ --squash frontend-remote master
```

OR 

```
git pull -s subtree <remotename> <branchname>
```

## Backporting to the subtree’s remote

Manually

```
git fetch frontend-remote
# Add [To backport] in main repo for commits with files from subtree for easier lookup
# Create new branch `backport` before backporting
git checkout -b backport frontend-remote/master
git cherry-pick -x --strategy=subtree -Xsubtree=public master~3
git push frontend-remote HEAD:master
```

With git subtree

```
# Backports all commits without exception that touched the subtree (can’t pick the relevant commits).
# So, make sure to push changes in public/ to separated commits
# Format: git subtree push --prefix=public <remote repo name> <branch name>
git subtree push --prefix=public/ frontend-remote master
```