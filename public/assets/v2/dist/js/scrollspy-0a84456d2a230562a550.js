(window.webpackJsonp=window.webpackJsonp||[]).push([[21,22],{iKax:function(t,e,n){"use strict";n.r(e);var i=n("GtyH"),r=n.n(i),o=(n("1t7P"),n("LW0h"),n("hBpG"),n("jwue"),n("7xRU"),n("z84I"),n("M+/F"),n("tQbP"),n("daRM"),n("FtHn"),n("+KXO"),n("KqXw"),n("Ysgh"),n("+oxZ"),n("xx6O"));function s(t,e){var n=Object.keys(t);if(Object.getOwnPropertySymbols){var i=Object.getOwnPropertySymbols(t);e&&(i=i.filter((function(e){return Object.getOwnPropertyDescriptor(t,e).enumerable}))),n.push.apply(n,i)}return n}function l(t,e,n){return e in t?Object.defineProperty(t,e,{value:n,enumerable:!0,configurable:!0,writable:!0}):t[e]=n,t}function a(t,e){if(t!==e)throw new TypeError("Cannot instantiate an arrow function")}function c(t,e){for(var n=0;n<e.length;n++){var i=e[n];i.enumerable=i.enumerable||!1,i.configurable=!0,"value"in i&&(i.writable=!0),Object.defineProperty(t,i.key,i)}}var h="scrollspy",f=r.a.fn[h],u={offset:10,method:"auto",target:""},d={offset:"number",method:"string",target:"(string|element)"},g={ACTIVATE:"activate.bs.scrollspy",SCROLL:"scroll.bs.scrollspy",LOAD_DATA_API:"load.bs.scrollspy.data-api"},p="dropdown-item",_="active",m='[data-spy="scroll"]',v=".nav, .list-group",y=".nav-link",b=".nav-item",w=".list-group-item",E=".dropdown",O=".dropdown-item",T=".dropdown-toggle",S="offset",C="position",j=function(){function t(t,e){var n=this;this._element=t,this._scrollElement="BODY"===t.tagName?window:t,this._config=this._getConfig(e),this._selector=this._config.target+" "+y+","+this._config.target+" "+w+","+this._config.target+" "+O,this._offsets=[],this._targets=[],this._activeTarget=null,this._scrollHeight=0,r()(this._scrollElement).on(g.SCROLL,function(t){return a(this,n),this._process(t)}.bind(this)),this.refresh(),this._process()}var e,n,i,f=t.prototype;return f.refresh=function(){var t=this,e=this._scrollElement===this._scrollElement.window?S:C,n="auto"===this._config.method?e:this._config.method,i=n===C?this._getScrollTop():0;this._offsets=[],this._targets=[],this._scrollHeight=this._getScrollHeight(),[].slice.call(document.querySelectorAll(this._selector)).map(function(e){var s;a(this,t);var l=o.a.getSelectorFromElement(e);if(l&&(s=document.querySelector(l)),s){var c=s.getBoundingClientRect();if(c.width||c.height)return[r()(s)[n]().top+i,l]}return null}.bind(this)).filter(function(e){return a(this,t),e}.bind(this)).sort(function(e,n){return a(this,t),e[0]-n[0]}.bind(this)).forEach(function(e){a(this,t),this._offsets.push(e[0]),this._targets.push(e[1])}.bind(this))},f.dispose=function(){r.a.removeData(this._element,"bs.scrollspy"),r()(this._scrollElement).off(".bs.scrollspy"),this._element=null,this._scrollElement=null,this._config=null,this._selector=null,this._offsets=null,this._targets=null,this._activeTarget=null,this._scrollHeight=null},f._getConfig=function(t){if("string"!=typeof(t=function(t){for(var e=1;e<arguments.length;e++){var n=null!=arguments[e]?arguments[e]:{};e%2?s(Object(n),!0).forEach((function(e){l(t,e,n[e])})):Object.getOwnPropertyDescriptors?Object.defineProperties(t,Object.getOwnPropertyDescriptors(n)):s(Object(n)).forEach((function(e){Object.defineProperty(t,e,Object.getOwnPropertyDescriptor(n,e))}))}return t}({},u,{},"object"==typeof t&&t?t:{})).target){var e=r()(t.target).attr("id");e||(e=o.a.getUID(h),r()(t.target).attr("id",e)),t.target="#"+e}return o.a.typeCheckConfig(h,t,d),t},f._getScrollTop=function(){return this._scrollElement===window?this._scrollElement.pageYOffset:this._scrollElement.scrollTop},f._getScrollHeight=function(){return this._scrollElement.scrollHeight||Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)},f._getOffsetHeight=function(){return this._scrollElement===window?window.innerHeight:this._scrollElement.getBoundingClientRect().height},f._process=function(){var t=this._getScrollTop()+this._config.offset,e=this._getScrollHeight(),n=this._config.offset+e-this._getOffsetHeight();if(this._scrollHeight!==e&&this.refresh(),t>=n){var i=this._targets[this._targets.length-1];this._activeTarget!==i&&this._activate(i)}else{if(this._activeTarget&&t<this._offsets[0]&&this._offsets[0]>0)return this._activeTarget=null,void this._clear();for(var r=this._offsets.length;r--;){this._activeTarget!==this._targets[r]&&t>=this._offsets[r]&&(void 0===this._offsets[r+1]||t<this._offsets[r+1])&&this._activate(this._targets[r])}}},f._activate=function(t){var e=this;this._activeTarget=t,this._clear();var n=this._selector.split(",").map(function(n){return a(this,e),n+'[data-target="'+t+'"],'+n+'[href="'+t+'"]'}.bind(this)),i=r()([].slice.call(document.querySelectorAll(n.join(","))));i.hasClass(p)?(i.closest(E).find(T).addClass(_),i.addClass(_)):(i.addClass(_),i.parents(v).prev(y+", "+w).addClass(_),i.parents(v).prev(b).children(y).addClass(_)),r()(this._scrollElement).trigger(g.ACTIVATE,{relatedTarget:t})},f._clear=function(){var t=this;[].slice.call(document.querySelectorAll(this._selector)).filter(function(e){return a(this,t),e.classList.contains(_)}.bind(this)).forEach(function(e){return a(this,t),e.classList.remove(_)}.bind(this))},t._jQueryInterface=function(e){return this.each((function(){var n=r()(this).data("bs.scrollspy");if(n||(n=new t(this,"object"==typeof e&&e),r()(this).data("bs.scrollspy",n)),"string"==typeof e){if(void 0===n[e])throw new TypeError('No method named "'+e+'"');n[e]()}}))},e=t,i=[{key:"VERSION",get:function(){return"4.3.1"}},{key:"Default",get:function(){return u}}],(n=null)&&c(e.prototype,n),i&&c(e,i),t}();r()(window).on(g.LOAD_DATA_API,function(){a(this,void 0);for(var t=[].slice.call(document.querySelectorAll(m)),e=t.length;e--;){var n=r()(t[e]);j._jQueryInterface.call(n,n.data())}}.bind(void 0)),r.a.fn[h]=j._jQueryInterface,r.a.fn[h].Constructor=j,r.a.fn[h].noConflict=function(){return a(this,void 0),r.a.fn[h]=f,j._jQueryInterface}.bind(void 0);function A(){r()("body").scrollspy({offset:220,target:"#history-navigation"})}n.d(e,"launch",(function(){return A}))},xx6O:function(t,e,n){"use strict";n("7x/C"),n("lZm3"),n("iKE+"),n("KqXw"),n("DZ+c"),n("WNMA"),n("Ysgh"),n("tVqn");var i=n("GtyH"),r=n.n(i);function o(t,e){if(t!==e)throw new TypeError("Cannot instantiate an arrow function")}function s(t){var e=this,n=!1;return r()(this).one(l.TRANSITION_END,function(){o(this,e),n=!0}.bind(this)),setTimeout(function(){o(this,e),n||l.triggerTransitionEnd(this)}.bind(this),t),this}var l={TRANSITION_END:"bsTransitionEnd",getUID:function(t){do{t+=~~(1e6*Math.random())}while(document.getElementById(t));return t},getSelectorFromElement:function(t){var e=t.getAttribute("data-target");if(!e||"#"===e){var n=t.getAttribute("href");e=n&&"#"!==n?n.trim():""}try{return document.querySelector(e)?e:null}catch(t){return null}},getTransitionDurationFromElement:function(t){if(!t)return 0;var e=r()(t).css("transition-duration"),n=r()(t).css("transition-delay"),i=parseFloat(e),o=parseFloat(n);return i||o?(e=e.split(",")[0],n=n.split(",")[0],1e3*(parseFloat(e)+parseFloat(n))):0},reflow:function(t){return t.offsetHeight},triggerTransitionEnd:function(t){r()(t).trigger("transitionend")},supportsTransitionEnd:function(){return Boolean("transitionend")},isElement:function(t){return(t[0]||t).nodeType},typeCheckConfig:function(t,e,n){for(var i in n)if(Object.prototype.hasOwnProperty.call(n,i)){var r=n[i],o=e[i],s=o&&l.isElement(o)?"element":(a=o,{}.toString.call(a).match(/\s([a-z]+)/i)[1].toLowerCase());if(!new RegExp(r).test(s))throw new Error(t.toUpperCase()+': Option "'+i+'" provided type "'+s+'" but expected type "'+r+'".')}var a},findShadowRoot:function(t){if(!document.documentElement.attachShadow)return null;if("function"==typeof t.getRootNode){var e=t.getRootNode();return e instanceof ShadowRoot?e:null}return t instanceof ShadowRoot?t:t.parentNode?l.findShadowRoot(t.parentNode):null}};r.a.fn.emulateTransitionEnd=s,r.a.event.special[l.TRANSITION_END]={bindType:"transitionend",delegateType:"transitionend",handle:function(t){if(r()(t.target).is(this))return t.handleObj.handler.apply(this,arguments)}},e.a=l}}]);