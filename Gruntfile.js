module.exports = function (grunt) {
    // load all grunt tasks matching the ['grunt-*', '@*/grunt-*'] patterns
    require('load-grunt-tasks')(grunt);

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        // Task configuration goes here.
        sass: {
            dev: {
                options: {
                    sourceMap: true
                },
                files: '<%= sass_files %>'
            },
            deploy: {
                options: {
                    outputStyle: 'compressed'
                },
                files: '<%= sass_files %>'
            }
        },
        concat: {
            main: {
                src: ['<%= JS_SRC %>/main.js'],
                dest: '<%= JS_RUNTIME %>/main.js'
            },
            profile_edit: {
                src: ['<%= JS_SRC %>/vendor/jasny.bootstrap/jasny-bootstrap.min.js',
                      '<%= JS_SRC %>/profile_edit.js'],
                dest: '<%= JS_RUNTIME %>/profile_edit.js'
            },
            staff_student_search: {
                src: ['<%= JS_SRC %>/staff/student_search.js'],
                dest: '<%= JS_RUNTIME %>/student_search.js'
            },
            club_teacher_gallery: {
                src: [
                    '<%= JS_SRC %>/vendor/jquery.magnific-popup/jquery.magnific-popup.min.js',
                    '<%= JS_SRC %>/club/teacher_detail_gallery.js'
                ],
                dest: '<%= JS_RUNTIME %>/club/gallery.js'
            }
        },
        uglify: {
            main: {
                files: {'<%= JS_DEST %>/main.js': ['<%= JS_RUNTIME %>/main.js']}
            },
            profile_edit: {
                files: {
                    '<%= JS_DEST %>/profile_edit.js': ['<%= JS_RUNTIME %>/profile_edit.js']
                }
            },
            staff_student_search: {
                files: {
                    '<%= JS_DEST %>/student_search.js': ['<%= JS_RUNTIME %>/student_search.js']
                }
            },
            club_teacher_gallery: {
                files: {
                    '<%= JS_DEST %>/club/gallery.js': ['<%= JS_RUNTIME %>/club/gallery.js']
                }
            },
        },
        watch: {
            options: {
                // livereload: true,
                spawn: false
            },
            javascript: {
                files: ['<%= JS_SRC %>/**/*.js'],
                tasks: ['concat', 'uglify']
            },
            sass: {
                files: ['cscsite/assets/src/sass/**/*.scss'],
                tasks: ['sass:dev']
            }
        },
        // Arbitrary properties used in task configuration templates.
        sass_files: {
            'cscsite/assets/css/center/style.css': '<%= SASS_SRC %>/center/style.scss',
            'cscsite/assets/css/club/style.css': '<%= SASS_SRC %>/club/style.scss',
            'cscsite/assets/css/magnific-popup.css': '<%= SASS_SRC %>/jquery.magnific-popup/main.scss',
        },
        SASS_SRC: 'cscsite/assets/src/sass',
        JS_SRC: 'cscsite/assets/src/js',
        JS_RUNTIME: 'cscsite/assets/_builds/js',
        JS_DEST: 'cscsite/assets/js',
    });

    // Register tasks here.
    grunt.registerTask('default', ['watch']);
    grunt.registerTask('build', ['sass:deploy', 'concat', 'uglify']);
    // TODO: investigate grunt-concurrent
};