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
            }
        },
        uglify: {
            main: {
                files: {'cscsite/assets/js/main.js': ['cscsite/assets/src/js/main.js']}
            }
        },
        watch: {
            options: {
                // livereload: true,
                spawn: false
            },
            // javascript: {
            //     files: ['myproject/static/js/app/**/*.js'],
            //     tasks: ['concat']
            // },
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