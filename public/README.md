# Project Structure

```
app/templates/ <-- html should be places here
design/ - sources for logos and other long-term useful stuff
node_modules/  # Node.js dependencies
src/  # js and css files root directory
src/js
src/sass  # used scss dialect in fact
webpack/  # webpack configuration
```

# How to recreate dev environment (for Mac OS X)

1. Install `brew` package manager for Mac OS X. 

Check requirements first https://docs.brew.sh/Installation.html

Then go to https://brew.sh/ for one-liner installation script

2. You need python 3 version to be installed on your system and virtualenv plugin. Let's manage python versions and venvs with `pyenv` tool. Install it:

```
$ brew update
$ brew install pyenv
# Enable shims and autocompletion (don't forget to restart your shell after updating .bash_profile) 
$ echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
# Install 3.6.x to your system.
$ pyenv install 3.6.4
# Install plugin
$ brew install pyenv-virtualenv
# Enable auto-activation of virtualenvs
$ echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bash_profile
# Create new virtualenv, where `csc-frontend` - this is a name of new virtualenv
pyenv virtualenv 3.6.4 csc-frontend
# Activate it
pyenv activate csc-frontend
```

3. Install Node.js and package manager for it `npm`

4. After your virtualenv was activated, install python dependencies into it

```
cd <project root>
pip install -r requirements.txt
```

5. Install node dependencies from package.json

```
cd <project root>
npm i
```

# Run python dev server

```
./manage.py runserver 8000
```

`npm start` for live reloading.



```
npm install -g npm-check-updates
ncu  # shows what packages time to update.
```


TODO: browserify-incremental
TODO: replace autoprefixer with postcss?