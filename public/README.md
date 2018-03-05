# Project Structure

```
core/ django related files
docs/ some info how to recreate dev environment
gulp/ gulp tasks and configuration
templates/ <-- html should be places here
design/ - sources for logos and other long-term useful stuff
node_modules/  # Node.js dependencies (ignore it)
src/  # js and css files root directory
webpack/  # webpack configuration
assets/  # XXX: Contains mixed content (static and dynamic). Files inside dist/* are generated, do not edit it directly.
media/  # Put static which not directly related to layout or page (some dynamic stuff)
```



# Run python dev server

```
# Run dev server
$ ./manage.py runserver 8000
# Run static watcher
$ gulp
# Run webpack
npm start
```

TODO: browserify-incremental

TODO: replace autoprefixer with postcss?