(window.webpackJsonp=window.webpackJsonp||[]).push([[10],{MSmY:function(t,a,e){"use strict";e.r(a),e.d(a,"launch",(function(){return n}));e("hBpG"),e("vrRf"),e("tVqn");var i=e("aGAf");function n(){!function(){if($("#course-detail-page").length>0){var t=$("#course-detail-page__tablist");window.onpopstate=function(a){var e;null!==a.state&&"target"in a.state&&(e=a.state.target),void 0===e&&(e=-1!==window.location.hash.indexOf("#news-")?"#course-news":"#course-about"),t.find("li").removeClass("active").find("a").blur(),t.find('a[data-target="'+e+'"]').tab("show").hover()};var a=t.find("li.active:first a:first");"#course-news"===a.data("target")&&r(a.get(0)),t.on("click","a",(function(t){if(t.preventDefault(),!$(this).parent("li").hasClass("active")){var a=$(this).data("target");"#course-news"===a&&r(this),window.history&&history.pushState&&history.pushState({target:a},"",$(this).attr("href"))}}))}}()}function r(t){var a=$(t);a.data("has-unread")&&$.ajax({url:a.data("notifications-url"),method:"POST",data:{csrfmiddlewaretoken:Object(i.c)()},xhrFields:{withCredentials:!0}}).done((function(e){e.updated&&a.text(t.firstChild.nodeValue.trim()),a.data("has-unread",!1)}))}}}]);