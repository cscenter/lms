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
                    // includePaths: ['bower_components/foundation/scss'],
                    outputStyle: 'compressed'
                },
                files: '<%= sass_files %>'
            }
        },
        concat: {
            main: {
                src: ['<%= JS_SRC %>/main.js'],
                dest: 'cscsite/assets/js/main.js'
            },
            profile_edit: {
                src: ['cscsite/assets/js/vendor/jasny.bootstrap/jasny-bootstrap.min.js',
                      '<%= JS_SRC %>/profile_edit.js'],
                dest: 'cscsite/assets/js/profile_edit.min.js'
            },
            staff_student_search: {
                src: ['<%= JS_SRC %>/staff/student_search.js'],
                dest: 'cscsite/assets/js/student_search.min.js'
            },
            club_teacher_gallery: {
                src: [
                    '<%= JS_SRC %>/vendor/jquery.magnific-popup/jquery.magnific-popup.min.js',
                    '<%= JS_SRC %>/club/teacher_detail_gallery.js'
                ],
                dest: 'cscsite/assets/js/club/gallery.min.js'
            }
        },
        uglify: {
            main: {
                files: {'cscsite/assets/js/main.js': ['<%= JS_SRC %>/main.js']}
            },
            profile_edit: {
                files: {
                    'cscsite/assets/js/profile_edit.min.js': ['cscsite/assets/js/profile_edit.min.js']
                }
            },
            staff_student_search: {
                files: {
                    'cscsite/assets/js/student_search.min.js': ['cscsite/assets/js/student_search.min.js']
                }
            },
            club_teacher_gallery: {
                files: {
                    'cscsite/assets/js/club/gallery.min.js': ['cscsite/assets/js/club/gallery.min.js']
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
                tasks: ['concat']
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
    });

    // Register tasks here.
    grunt.registerTask('default', ['watch']);
    grunt.registerTask('build', ['sass:deploy', 'concat', 'uglify']);
    // TODO: investigate grunt-concurrent
};