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
            club_teacher_gallery: {
                src: [
                    '<%= JS_VENDOR %>/jquery.magnific-popup/jquery.magnific-popup.min.js',
                    '<%= JS_SRC %>/club/teacher_detail_gallery.js'
                ],
                dest: '<%= JS_RUNTIME %>/club/gallery.js'
            },
            fileinput: {
                src: [
                    '<%= JS_VENDOR %>/bootstrap-fileinput/fileinput.min.js',
                    '<%= JS_VENDOR %>/bootstrap-fileinput/fileinput_locale_ru.js'
                ],
                dest: '<%= JS_RUNTIME %>/fileinput.js'
            },
            gradebook: {
                src: [
                    // TODO: Investigate how to remove duplicates (see `fileinput` target)
                    '<%= JS_VENDOR %>/bootstrap-fileinput/fileinput.min.js',
                    '<%= JS_VENDOR %>/bootstrap-fileinput/fileinput_locale_ru.js',
                    '<%= JS_VENDOR %>/jquery.arrow-increment.min.js',
                    '<%= JS_SRC %>/teaching/gradebook.js'
                ],
                dest: '<%= JS_RUNTIME %>/gradebook.js'
            },
            faq: {
                src: ['<%= JS_SRC %>/faq.js'],
                dest: '<%= JS_DEST %>/faq.js'
            },
            alumni: {
                src: [
                    '<%= JS_VENDOR %>/holder.min.js',
                    '<%= JS_VENDOR %>/jquery.lazyload.min.js',
                    '<%= JS_SRC %>/alumni.js'
                ],
                dest: '<%= JS_RUNTIME %>/alumni.js'
            },
            assignment_submissions: {
                src: ['<%= JS_SRC %>/assignment-submissions.js'],
                dest: '<%= JS_DEST %>/assignment-submissions.js'
            },
            diplomas: {
                src: [
                    '<%= JS_SRC %>/diplomas.js',
                ],
                dest: '<%= JS_DEST %>/diplomas.js'
            },
            application: {
                src: ['<%= JS_SRC %>/application.js'],
                dest: '<%= JS_DEST %>/application.js'
            },
            projects_report: {
                src: [
                    '<%= JS_SRC %>/center/projects_report.js'
                ],
                dest: '<%= JS_RUNTIME %>/center/projects_report.js'
            },
            raven_conf: {
                src: ['<%= JS_SRC %>/raven_conf.js'],
                dest: '<%= JS_DEST %>/raven_conf.js'
            },
        },
        // TODO: Make this task more generic after all src js will be moved to src folder
        uglify: {
            alumni: {
                files: {
                    '<%= JS_DEST %>/alumni.js': ['<%= JS_RUNTIME %>/alumni.js']
                }
            },
            club_teacher_gallery: {
                files: {
                    '<%= JS_DEST %>/club/gallery.js': ['<%= JS_RUNTIME %>/club/gallery.js']
                }
            },
            gradebook: {
                files: {
                    '<%= JS_DEST %>/gradebook.js': ['<%= JS_RUNTIME %>/gradebook.js']
                }
            },
            projects_report: {
                files: {
                    '<%= JS_DEST %>/projects_report.js': ['<%= JS_RUNTIME %>/center/projects_report.js']
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
            'cscsite/assets/css/center/staff.css': '<%= SASS_SRC %>/center/staff.scss',
            'cscsite/assets/css/center/style.css': '<%= SASS_SRC %>/center/style.scss',
            'cscsite/assets/css/club/style.css': '<%= SASS_SRC %>/club/style.scss',
            'cscsite/assets/css/magnific-popup.css': '<%= SASS_SRC %>/jquery.magnific-popup/main.scss',
        },
        SASS_SRC: 'cscsite/assets/src/sass',
        JS_SRC: 'cscsite/assets/src/js',
        JS_VENDOR: 'cscsite/assets/src/js/vendor',
        JS_RUNTIME: 'cscsite/assets/_builds/js',
        JS_DEST: 'cscsite/assets/js',
    });

    // Register tasks here.
    grunt.registerTask('default', ['watch']);
    grunt.registerTask('build', ['sass:deploy', 'concat', 'uglify']);
    // TODO: investigate grunt-concurrent
};