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
                    sourceMap: true,
                    includePaths: ['./node_modules/']
                },
                files: '<%= sass_files %>'
            },
            deploy: {
                options: {
                    outputStyle: 'compressed',
                    includePaths: ['./node_modules/']
                },
                files: '<%= sass_files %>'
            }
        },
        watch: {
            options: {
                // livereload: true,
                spawn: false
            },
            sass: {
                files: ['cscsite/assets/src/sass/**/*.scss'],
                tasks: ['sass:dev']
            }
        },
        // Arbitrary properties used in task configuration templates.
        sass_files: {
            'cscsite/assets/v1/css/center/staff.css': '<%= SASS_SRC %>/center/staff.scss',
        },
        SASS_SRC: 'cscsite/assets/src/sass',
    });

    // Register tasks here.
    grunt.registerTask('default', ['watch']);
    grunt.registerTask('build', ['sass:deploy']);
    // TODO: investigate grunt-concurrent
};