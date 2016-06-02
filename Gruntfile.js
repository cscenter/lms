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
                src: ['cscsite/assets/src/js/main.js'],
                dest: 'cscsite/assets/js/main.js'
            },
            profile_edit: {
                src: ['cscsite/assets/js/vendor/jasny.bootstrap/jasny-bootstrap.min.js',
                      'cscsite/assets/src/js/profile_edit.js'],
                dest: 'cscsite/assets/js/profile_edit.min.js'
            },
            staff_student_search: {
                src: ['cscsite/assets/src/js/staff/student_search.js'],
                dest: 'cscsite/assets/js/student_search.min.js'
            }
        },
        uglify: {
            main: {
                files: {'cscsite/assets/js/main.js': ['cscsite/assets/src/js/main.js']}
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
            }
        },
        watch: {
            options: {
                // livereload: true,
                spawn: false
            },
            javascript: {
                files: ['cscsite/assets/src/js/**/*.js'],
                tasks: ['concat']
            },
            sass: {
                files: ['cscsite/assets/src/sass/**/*.scss'],
                tasks: ['sass:dev']
            }
        },
        // Arbitrary properties used in task configuration templates.
        sass_files: {
            'cscsite/assets/css/center/style.css': 'cscsite/assets/src/sass/center/style.scss',
            'cscsite/assets/css/club/style.css': 'cscsite/assets/src/sass/club/style.scss'
        }
    });

    // Register tasks here.
    grunt.registerTask('default', ['watch']);
    grunt.registerTask('build', ['sass:deploy', 'concat', 'uglify']);
    // TODO: investigate grunt-concurrent
};