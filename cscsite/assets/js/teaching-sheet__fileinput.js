$(function() {
    $("#input-id").fileinput({
        'showUpload':false,
        'language': 'ru',
        'previewFileType': 'text',
        'allowedFileTypes': ['text'],
        'allowedFileExtensions': ['txt', 'csv'],
        'showPreview': false,
        'showRemove': false,
        'maxFileCount': 1,
        browseIcon: '<i class="fa fa-folder-open"></i> &nbsp;',
        removeIcon: '<i class="fa fa-trash"></i> ',
        uploadIcon: '<i class="fa fa-upload"></i> ',
        cancelIcon: '<i class="fa fa-times-circle-o"></i> ',
        msgValidationErrorIcon: '<i class="fa fa-exclamation-circle"></i> '
    });
});