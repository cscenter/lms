import Cropper from 'cropperjs';
import $ from 'jquery';
import {createNotification, getCSRFToken, getTemplate} from './utils';

// profileAppInit - global dependency :<
const profileAppInit = window.profileAppInit;
// TODO: How to resolve FileAPI dependency?


const templates = {
    upload: getTemplate('templateUpload'),
    thumb: getTemplate('templateThumb')
};

const MESSAGE = {
    unknownError: "Неизвестная ошибка.",
    imgValidationError: "Изображение не удовлетворяет требованиям.",
    badRequest: "Неверный запрос.",
    uploadError: "Ошибка загрузки файла на сервер. Код: ",
    thumbDoneFail: "Ошибка создания превью. Код: ",
    thumbSuccess: "Превью успешно создано",
    imgDimensions: "Не удалось получить размеры изображения",
    preloadError: "Ошибка инициализации"
};

var imageData = profileAppInit.photo;

var photoValidation = {
    minWidth: 250,
    minHeight: 350,
    maxFileSize: 5, // Mb
    minThumbWidth: 170,
    minThumbHeight: 238

};

const xhrOpts = {
    url: `/users/${profileAppInit.user_id}/profile-update-image/`,
    headers: {
        'X-CSRFToken': getCSRFToken()
    }
};

// DOM elements
const uploadContainer = $("#user-photo-upload");
const modalHeader = $('.modal-header', uploadContainer);
const modalBody = $('.modal-body', uploadContainer);

let fn = {
    init: function() {
        if (profileAppInit.user_id === undefined) {
            return;
        }

        let deferred = $.Deferred(),
            chained = deferred;
        $.each(profileAppInit.preload, function(i, url) {
             chained = chained.then(function() {
                 return $.ajax({
                     url: url,
                     dataType: "script",
                     cache: true,
                 });
             });
        });
        chained.done(function() {
            $("a[href='#user-photo-upload']").click(function () {
                uploadContainer.modal('toggle');
                if (imageData === null) {
                    fn.uploadInit();
                }
            });
            uploadContainer.one('shown.bs.modal', function () {
                // Image dimensions is dynamic and we can't get them
                // for cropper inside hidden div (w x h will be
                // 0x0 px before display. Due to that, init cropper
                // once only when modal visible.
                if (imageData !== null) {
                    fn.thumbInit(imageData);
                }
            });
        }).fail(function() {
            createNotification(MESSAGE.preloadError, 'error');
        });
        deferred.resolve();
    },

    uploadInit: function () {
        let uploadBtn = document.getElementById('simple-btn');
        // Should I remove it manually?
        FileAPI.event.off(uploadBtn, 'change', fn.uploadValidate);
        modalBody.html(templates.upload());
        uploadBtn = document.getElementById('simple-btn');
        FileAPI.event.on(uploadBtn, 'change', fn.uploadValidate);
    },

    uploadValidate: function (evt) {
        let files = FileAPI.getFiles(evt);

        FileAPI.filterFiles(files, function (file, info) {
            if (/^image/.test(file.type) && info) {
                return info.width >= photoValidation.minWidth &&
                        info.height >= photoValidation.minHeight &&
                        file.size <= photoValidation.maxFileSize * FileAPI.MB;
            }
        }, function (list, other/**Array*/) {
            if (list.length) {
                fn.uploadProgress(files[0]);
            } else {
                // Let them read restrictions again.
                createNotification(MESSAGE.imgValidationError, 'error');
            }
        });
    },

    enableLoadingState: function() {
        modalBody.addClass("load-state");
    },

    disableLoadingState: function() {
        modalBody.removeClass("load-state");
    },

    uploadProgress: function (file) {
        // Try to upload selected image to server
        var opts = FileAPI.extend({}, xhrOpts, {
            files: {
                photo: file
            },
            // before upload event
            upload: function () {
                fn.enableLoadingState();
            },
            // after upload event
            complete: function (err, xhr) {
                if (err) {
                    fn.uploadError(xhr);
                } else {
                    var data = JSON.parse(xhr.response);
                    fn.uploadSuccess(data, file);
                }
            }
        });
        FileAPI.upload(opts);
    },

    uploadError: function (xhr) {
        fn.disableLoadingState();
        var code;
        switch (xhr.status) {
            case 500:
                code = MESSAGE.unknownError;
                break;
            case 403:
                code = MESSAGE.badRequest;
                break;
            default:
                code = xhr.response;
        }
        createNotification(MESSAGE.uploadError + code, 'error');
    },

    uploadSuccess: function (data, file) {
        if (data.success == true) {
            // Get image file dimensions
            FileAPI.getInfo(file, function (err, info) {
                if ( !err ) {
                    data.width = info.width;
                    data.height = info.height;
                    // Don't forget to update it
                    imageData = data;
                    fn.thumbInit(data);
                } else {
                    createNotification(MESSAGE.imgDimensions, 'error');
                }
            });
        } else {
            createNotification(MESSAGE.unknownError, 'error');
        }
    },

    thumbInit: function (data) {
        fn.enableLoadingState();
        // prevent caching img
        data.url = data.url + '?' + (new Date()).getTime();
        // Now preload it before Cropper initialized. Cropper do xhr request
        // and we want to use browser cache in that case.
        var image = new Image();
        image.onload = function () { fn.cropperInit(data); };
        image.src = data.url;
    },

    cropperInit: function (data) {
        // Calculate img dimensions based on modal body width
        const modalWidth = modalBody.width() - 40; // 40px for padding
        const propWidth = Math.min(data.width, modalWidth);
        const propHeight = Math.round((propWidth / data.width) * data.height);
        modalBody.html(templates.thumb({
            url: data.url,
            width: propWidth,
            height: propHeight
        }));
        let image = modalBody.find(".uploaded-img")[0];
        let cropper = new Cropper(image, {
            viewMode: 1,
            background: true,
            responsive: false,
            scalable: false,
            autoCropArea: 1,
// {#                        autoCrop: false,#}
            aspectRatio: 5 / 7,
            dragMode: 'move',
            guides: false,
            movable: false,
            rotatable: false,
            zoomable: false,
            zoomOnTouch: false,
            zoomOnWheel: false,
            minContainerWidth: 250,
            minContainerHeight: 250,
            offsetWidth: 0,
            offsetHeight: 0,
            minCropBoxWidth: photoValidation.minThumbWidth,
            minCropBoxHeight: photoValidation.minThumbHeight,
            ready: function() {
                // handlers
                modalBody.find('.-prev').click(function () {
                    fn.uploadInit();
                });
                modalBody.find('.save-crop-data').click(function () {
                    fn.thumbDone(cropper);
                });
                fn.setCropBox(cropper);
                fn.disableLoadingState();
            }
            //preview: '.thumbnail-img',
        });
    },

    thumbDone: function (cropper) {
        cropper.disable();
        var cropBox = fn.getCropBox(cropper);

        var data = $.extend({ "crop_data": true }, cropBox);
        var opts = $.extend(true, {}, xhrOpts, {
            method: "POST",
            dataType: 'json',
            data: data
        });
        $.ajax(opts).done(function (data) {
            cropper.enable();
            if (data.success == true) {
                fn.thumbSuccess(cropper, data);
            } else {
                createNotification(data.reason, 'error');
            }
        }).fail(function (xhr) {
            cropper.enable();
            createNotification(MESSAGE.thumbDoneFail + xhr.statusText, 'error');
        });
    },

    // Calculate cropbox data relative to img
    getCropBox: function(cropper) {
        var cropBox = cropper.getData(true);
        return cropBox;
    },

    // Calculate cropbox data relative to canvas
    setCropBox: function(cropper) {
        if (imageData.cropbox !== undefined) {
            var cropBox = imageData.cropbox;
            cropper.setData(cropBox);
        }
    },

    thumbSuccess: function(cropper, data) {
        cropper.enable();
        $('.thumbnail-img img').attr("src", data.thumbnail);
        createNotification(MESSAGE.thumbSuccess);
        uploadContainer.modal("hide");
    }
};

// document.ready
$(function () {
    fn.init();
});
