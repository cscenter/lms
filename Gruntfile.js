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
                src: [
                    '<%= JS_VENDOR %>/md5.js',
                    '<%= JS_DEST %>/vendor/EpicEditor-v0.2.2/js/epiceditor.min.js',
                    '<%= JS_VENDOR %>/bootstrap.min.js',
                    '<%= JS_VENDOR %>/jquery.jgrowl.js',
                    '<%= JS_VENDOR %>/jquery.cookie.js',
                    '<%= JS_VENDOR %>/sweet-alerts/sweet-alert.min.js',
                    '<%= JS_SRC %>/main.js'
                ],
                dest: '<%= JS_RUNTIME %>/main.js'
            },
            interview: {
                src: ['<%= JS_VENDOR %>/jquery.barrating.min.js',
                      '<%= JS_SRC %>/interview.js'],
                dest: '<%= JS_RUNTIME %>/interview.js'
            },
            profile: {
                src: ['<%= JS_SRC %>/profile.js'],
                dest: '<%= JS_RUNTIME %>/profile.js'
            },
            profile_edit: {
                src: ['<%= JS_SRC %>/profile_edit.js'],
                dest: '<%= JS_RUNTIME %>/profile_edit.js'
            },
            staff_student_search: {
                src: ['<%= JS_SRC %>/staff/student_search.js'],
                dest: '<%= JS_RUNTIME %>/student_search.js'
            },
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
                    '<%= JS_SRC %>/gradebook.js'
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
            assignment_submission: {
                src: ['<%= JS_SRC %>/assignment-submission.js'],
                dest: '<%= JS_DEST %>/assignment-submission.js'
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
            raven_conf: {
                src: ['<%= JS_SRC %>/raven_conf.js'],
                dest: '<%= JS_DEST %>/raven_conf.js'
            },
        },
        // TODO: Make this task more generic after all src js will be moved to src folder
        uglify: {
            main: {
                files: {'<%= JS_DEST %>/main.js': ['<%= JS_RUNTIME %>/main.js']}
            },
            alumni: {
                files: {
                    '<%= JS_DEST %>/alumni.js': ['<%= JS_RUNTIME %>/alumni.js']
                }
            },
            interview: {
                files: {
                    '<%= JS_DEST %>/interview.js': ['<%= JS_RUNTIME %>/interview.js']
                }
            },
            profile: {
                files: {
                    '<%= JS_DEST %>/profile.js': ['<%= JS_RUNTIME %>/profile.js']
                }
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
            gradebook: {
                files: {
                    '<%= JS_DEST %>/gradebook.js': ['<%= JS_RUNTIME %>/gradebook.js']
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