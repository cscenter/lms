(window.webpackJsonp=window.webpackJsonp||[]).push([[13],{nSwx:function(t,e,n){"use strict";n.r(e),n.d(e,"launch",(function(){return s}));n("jwue"),n("+KXO"),n("+oxZ"),n("tlNu");var i=n("GtyH"),a=n.n(i);function o(t,e){if(t!==e)throw new TypeError("Cannot instantiate an arrow function")}function s(){var t=this,e=window.achievementGrid;if("undefined"!==e){var n={};Object.keys(e).forEach(function(i){var a=this;o(this,t),e[i].forEach(function(t){o(this,a),n[t]=n[t]||[],n[t].push(i)}.bind(this))}.bind(this)),Object.keys(n).forEach(function(e){var i=this;o(this,t);var a=n[e],s=document.createElement("div");s.className="achievements",a.forEach(function(t){o(this,i);var e=document.createElement("div");e.className="achievements__item",e.setAttribute("data-toggle","tooltip"),e.setAttribute("title",window.ACHIEVEMENTS[t]),e.innerHTML='<svg class="sprite-img _'+t+'" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="#'+t+'"></use></svg>',s.appendChild(e)}.bind(this)),document.querySelector("#user-card-"+e+" .card__img").appendChild(s)}.bind(this)),a()('[data-toggle="tooltip"]').tooltip({animation:!1,placement:"auto",delay:{show:100,hide:0}}).click((function(t){t.preventDefault()}))}}}}]);