webpackJsonp([7],{Tap1:function(t,o,e){"use strict";Object.defineProperty(o,"__esModule",{value:!0});var i=e("0iPh"),n=e.n(i),r=e("mwlq"),a=n()("#o-sidebar"),s=n()(".footer"),f=n()(".assignment-comment"),c=n()("#submission-comment-model-form"),m=void 0,u={Launch:function(){u.initCommentModal(),u.initStickySidebar()},initCommentModal:function(){c.modal({show:!1}),c.on("shown.bs.modal",function(t){var o=n()(t.target).find("textarea").get(0);m=r.default.init(o),c.css("opacity","1")}),n()(".__edit",f).click(function(t){t.preventDefault();var o=n()(this);n.a.get(this.href,function(t){c.css("opacity","0"),n()(".inner",c).html(t),c.modal("toggle")}).error(function(t){403===t.status&&(n.a.jGrowl("Доступ запрещён. Вероятно, время редактирования комментария истекло.",{position:"bottom-right",theme:"error"}),o.remove())})}),c.on("submit","form",u.submitEventHandler)},submitEventHandler:function(t){t.preventDefault();var o=t.target;return n.a.ajax({url:o.action,type:"POST",data:n()(o).serialize()}).done(function(t){if(1===t.success){c.modal("hide");var o=f.filter(function(){return n()(this).data("id")==t.id}),e=n()(".ubertext",o);e.html(t.html),r.default.render(e.get(0)),n.a.jGrowl("Комментарий успешно сохранён.",{position:"bottom-right"})}else n.a.jGrowl("Комментарий не был сохранён.",{position:"bottom-right",theme:"error"})}).error(function(){n.a.jGrowl("Комментарий не был сохранён.",{position:"bottom-right",theme:"error"})}),!1},initStickySidebar:function(){var t=a.offset().top-20;s.offset().top-75-t>500&&(a.affix({offset:{top:t,bottom:s.outerHeight(!0)}}),a.affix("checkPosition"))}};n()(document).ready(function(){u.Launch()})}},["Tap1"]);