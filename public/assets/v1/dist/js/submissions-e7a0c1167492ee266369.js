(window.webpackJsonp=window.webpackJsonp||[]).push([[13],{Uec8:function(n,t,i){"use strict";i.r(t);i("hBpG"),i("7xRU"),i("z84I"),i("7x/C"),i("JtPf");var e=i("aGAf"),o=$(".filters form"),c=$("#assignments-select"),s={launch:function(){s.initFiltersForm()},initFiltersForm:function(){i.e(1).then(i.bind(null,"O2Rl")).then((function(n){c.selectpicker({iconBase:"fa",tickIcon:"fa-check"}),c.on("loaded.bs.select",(function(n){$(this).closest(".filters").find(".loading").remove()}))})).catch((function(n){return Object(e.g)(n)})),o.on("submit",(function(){var n=$.map(c.find("option:selected"),(function(n,t){return $(n).val()})).join(",");return window.location=o.attr("action")+n,!1}))}};t.default=s}}]);