$(function() {
    $("#input-id").fileinput({
        'showUpload':false,
        'language': 'ru',
        'previewFileType': 'text',
        'allowedFileTypes': ['text'],
        'allowedFileExtensions': ['txt', 'csv'],
        'showPreview': false,
        'showRemove': false,
        'maxFileCount': 1
    });
});