webpackJsonp([1],{SKEV:function(e,t,o){"use strict";function n(e){return e&&e.__esModule?e:{default:e}}var i=o("lbHh"),a=n(i);!function(e,t,o){var n={upload:e("#templateUpload").html(),thumb:e("#templateThumb").html()},i={unknownError:"Неизвестная ошибка.",badRequest:"Неверный запрос.",uploadError:"Ошибка загрузки файла на сервер. Код: ",thumbDoneFail:"Ошибка создания превью. Код: ",thumbSuccess:"Превью успешно создано",imgDimensions:"Не удалось получить размеры изображения",preloadError:"Ошибка инициализации"},r=o.photo,u={minWidth:250,minHeight:350,maxFileSize:5,minThumbWidth:170,minThumbHeight:238},l={url:"/profile-update-image/",data:{user_id:o.user_id},headers:{"X-CSRFToken":a.default.get("csrftoken")}},d=e("#user-photo-upload"),s=(e(".modal-header",d),e(".modal-body",d)),h={init:function(){if(void 0!==o.user_id){var t=e.Deferred(),n=t;e.each(o.preload,function(t,o){n=n.then(function(){return e.ajax({url:o,dataType:"script",cache:!0})})}),n.done(function(){e("a[href=#user-photo-upload]").click(function(){d.modal("toggle"),void 0===r&&h.uploadInit()}),d.one("shown.bs.modal",function(){void 0!==r&&h.thumbInit(r)})}).fail(function(){h.showError(i.preloadError)}),t.resolve()}},showError:function(t){e.jGrowl(t,{theme:"error",position:"bottom-right"})},showMessage:function(t){e.jGrowl(t,{position:"bottom-right"})},uploadInit:function(){var e=document.getElementById("simple-btn");FileAPI.event.off(e,"change",h.uploadValidate),s.html(n.upload),e=document.getElementById("simple-btn"),FileAPI.event.on(e,"change",h.uploadValidate)},uploadValidate:function(e){var t=FileAPI.getFiles(e);FileAPI.filterFiles(t,function(e,t){if(/^image/.test(e.type)&&t)return t.width>=u.minWidth&&t.height>=u.minHeight&&e.size<=u.maxFileSize*FileAPI.MB},function(e,o){e.length&&h.uploadProgress(t[0])})},enableLoadingState:function(){s.addClass("load-state")},disableLoadingState:function(){s.removeClass("load-state")},uploadProgress:function(e){var t=FileAPI.extend({},l,{files:{photo:e},upload:function(){h.enableLoadingState()},complete:function(t,o){if(t)h.uploadError(o);else{var n=JSON.parse(o.response);h.uploadSuccess(n,e)}}});FileAPI.upload(t)},uploadError:function(e){h.disableLoadingState();var t;switch(e.status){case 500:t=i.unknownError;break;case 403:t=i.badRequest;break;default:t=e.response}h.showError(i.uploadError+t)},uploadSuccess:function(e,t){1==e.success?FileAPI.getInfo(t,function(t,o){t?h.showError(i.imgDimensions):(e.width=o.width,e.height=o.height,r=e,h.thumbInit(e))}):h.showError(i.unknownError)},thumbInit:function(e){h.enableLoadingState(),e.url=e.url+"?"+(new Date).getTime();var t=new Image;t.onload=function(){h.cropperInit(e)},t.src=e.url},cropperInit:function(e){var o=s.width()-40,i=Math.min(e.width,o),a=Math.round(i/e.width*e.height);s.html(t.template(n.thumb,{url:e.url,width:i,height:a}));var r=s.find(".uploaded-img")[0],l=new Cropper(r,{viewMode:1,background:!0,responsive:!1,scalable:!1,autoCropArea:1,aspectRatio:5/7,dragMode:"move",guides:!1,movable:!1,rotatable:!1,zoomable:!1,zoomOnTouch:!1,zoomOnWheel:!1,minContainerWidth:250,minContainerHeight:250,offsetWidth:0,offsetHeight:0,minCropBoxWidth:u.minThumbWidth,minCropBoxHeight:u.minThumbHeight,built:function(){s.find(".-prev").click(function(){h.uploadInit()}),s.find(".save-crop-data").click(function(){h.thumbDone(l)}),h.setCropBox(l),h.disableLoadingState()}})},thumbDone:function(t){t.disable();var o=h.getCropBox(t),n=e.extend({crop_data:!0},o),a=e.extend(!0,{},l,{method:"POST",dataType:"json",data:n});e.ajax(a).done(function(e){t.enable(),1==e.success?h.thumbSuccess(t,e):h.showError(e.reason)}).fail(function(e){t.enable(),h.showError(i.thumbDoneFail+e.statusText)})},getCropBox:function(e){var t=e.getData(!0);return t},setCropBox:function(e){if(void 0!==r.cropbox){var t=r.cropbox;e.setData(t)}},thumbSuccess:function(t,o){t.enable(),e(".thumbnail-img img").attr("src",o.thumbnail),h.showMessage(i.thumbSuccess),d.modal("hide")}};e(function(){h.init()})}($,_,profileAppInit)}},["SKEV"]);