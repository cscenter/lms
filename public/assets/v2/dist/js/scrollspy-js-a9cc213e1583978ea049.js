(window.webpackJsonp=window.webpackJsonp||[]).push([[16],{"7xRU":function(t,e,i){"use strict";var r=i("ax0f"),n=i("g6a+"),s=i("N4z3"),o=i("NVHP"),l=[].join,c=n!=Object,a=o("join",",");r({target:"Array",proto:!0,forced:c||a},{join:function(t){return l.call(s(this),void 0===t?",":t)}})},hBpG:function(t,e,i){"use strict";var r=i("ax0f"),n=i("0FSu").find,s=i("7St7"),o=!0;"find"in[]&&Array(1).find((function(){o=!1})),r({target:"Array",proto:!0,forced:o},{find:function(t){return n(this,t,arguments.length>1?arguments[1]:void 0)}}),s("find")},iKax:function(t,e,i){"use strict";i.r(e);var r=i("GtyH"),n=i.n(r),s=(i("1t7P"),i("LW0h"),i("hBpG"),i("7xRU"),i("z84I"),i("M+/F"),i("tQbP"),i("daRM"),i("FtHn"),i("+KXO"),i("Ysgh"),i("+oxZ"),i("xx6O"));function o(t,e){var i=Object.keys(t);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(t);e&&(r=r.filter((function(e){return Object.getOwnPropertyDescriptor(t,e).enumerable}))),i.push.apply(i,r)}return i}function l(t,e,i){return e in t?Object.defineProperty(t,e,{value:i,enumerable:!0,configurable:!0,writable:!0}):t[e]=i,t}function c(t,e){if(t!==e)throw new TypeError("Cannot instantiate an arrow function")}function a(t,e){for(var i=0;i<e.length;i++){var r=e[i];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(t,r.key,r)}}var h="scrollspy",f=n.a.fn[h],u={offset:10,method:"auto",target:""},_={offset:"number",method:"string",target:"(string|element)"},g={ACTIVATE:"activate.bs.scrollspy",SCROLL:"scroll.bs.scrollspy",LOAD_DATA_API:"load.bs.scrollspy.data-api"},d="dropdown-item",p="active",v={DATA_SPY:'[data-spy="scroll"]',ACTIVE:".active",NAV_LIST_GROUP:".nav, .list-group",NAV_LINKS:".nav-link",NAV_ITEMS:".nav-item",LIST_ITEMS:".list-group-item",DROPDOWN:".dropdown",DROPDOWN_ITEMS:".dropdown-item",DROPDOWN_TOGGLE:".dropdown-toggle"},y="offset",m="position",b=function(){function t(t,e){var i=this;this._element=t,this._scrollElement="BODY"===t.tagName?window:t,this._config=this._getConfig(e),this._selector=this._config.target+" "+v.NAV_LINKS+","+this._config.target+" "+v.LIST_ITEMS+","+this._config.target+" "+v.DROPDOWN_ITEMS,this._offsets=[],this._targets=[],this._activeTarget=null,this._scrollHeight=0,n()(this._scrollElement).on(g.SCROLL,function(t){return c(this,i),this._process(t)}.bind(this)),this.refresh(),this._process()}var e,i,r,f=t.prototype;return f.refresh=function(){var t=this,e=this._scrollElement===this._scrollElement.window?y:m,i="auto"===this._config.method?e:this._config.method,r=i===m?this._getScrollTop():0;this._offsets=[],this._targets=[],this._scrollHeight=this._getScrollHeight(),[].slice.call(document.querySelectorAll(this._selector)).map(function(e){var o;c(this,t);var l=s.a.getSelectorFromElement(e);if(l&&(o=document.querySelector(l)),o){var a=o.getBoundingClientRect();if(a.width||a.height)return[n()(o)[i]().top+r,l]}return null}.bind(this)).filter(function(e){return c(this,t),e}.bind(this)).sort(function(e,i){return c(this,t),e[0]-i[0]}.bind(this)).forEach(function(e){c(this,t),this._offsets.push(e[0]),this._targets.push(e[1])}.bind(this))},f.dispose=function(){n.a.removeData(this._element,"bs.scrollspy"),n()(this._scrollElement).off(".bs.scrollspy"),this._element=null,this._scrollElement=null,this._config=null,this._selector=null,this._offsets=null,this._targets=null,this._activeTarget=null,this._scrollHeight=null},f._getConfig=function(t){if("string"!=typeof(t=function(t){for(var e=1;e<arguments.length;e++){var i=null!=arguments[e]?arguments[e]:{};e%2?o(i,!0).forEach((function(e){l(t,e,i[e])})):Object.getOwnPropertyDescriptors?Object.defineProperties(t,Object.getOwnPropertyDescriptors(i)):o(i).forEach((function(e){Object.defineProperty(t,e,Object.getOwnPropertyDescriptor(i,e))}))}return t}({},u,{},"object"==typeof t&&t?t:{})).target){var e=n()(t.target).attr("id");e||(e=s.a.getUID(h),n()(t.target).attr("id",e)),t.target="#"+e}return s.a.typeCheckConfig(h,t,_),t},f._getScrollTop=function(){return this._scrollElement===window?this._scrollElement.pageYOffset:this._scrollElement.scrollTop},f._getScrollHeight=function(){return this._scrollElement.scrollHeight||Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)},f._getOffsetHeight=function(){return this._scrollElement===window?window.innerHeight:this._scrollElement.getBoundingClientRect().height},f._process=function(){var t=this._getScrollTop()+this._config.offset,e=this._getScrollHeight(),i=this._config.offset+e-this._getOffsetHeight();if(this._scrollHeight!==e&&this.refresh(),t>=i){var r=this._targets[this._targets.length-1];this._activeTarget!==r&&this._activate(r)}else{if(this._activeTarget&&t<this._offsets[0]&&this._offsets[0]>0)return this._activeTarget=null,void this._clear();for(var n=this._offsets.length;n--;){this._activeTarget!==this._targets[n]&&t>=this._offsets[n]&&(void 0===this._offsets[n+1]||t<this._offsets[n+1])&&this._activate(this._targets[n])}}},f._activate=function(t){var e=this;this._activeTarget=t,this._clear();var i=this._selector.split(",").map(function(i){return c(this,e),i+'[data-target="'+t+'"],'+i+'[href="'+t+'"]'}.bind(this)),r=n()([].slice.call(document.querySelectorAll(i.join(","))));r.hasClass(d)?(r.closest(v.DROPDOWN).find(v.DROPDOWN_TOGGLE).addClass(p),r.addClass(p)):(r.addClass(p),r.parents(v.NAV_LIST_GROUP).prev(v.NAV_LINKS+", "+v.LIST_ITEMS).addClass(p),r.parents(v.NAV_LIST_GROUP).prev(v.NAV_ITEMS).children(v.NAV_LINKS).addClass(p)),n()(this._scrollElement).trigger(g.ACTIVATE,{relatedTarget:t})},f._clear=function(){var t=this;[].slice.call(document.querySelectorAll(this._selector)).filter(function(e){return c(this,t),e.classList.contains(p)}.bind(this)).forEach(function(e){return c(this,t),e.classList.remove(p)}.bind(this))},t._jQueryInterface=function(e){return this.each((function(){var i=n()(this).data("bs.scrollspy");if(i||(i=new t(this,"object"==typeof e&&e),n()(this).data("bs.scrollspy",i)),"string"==typeof e){if(void 0===i[e])throw new TypeError('No method named "'+e+'"');i[e]()}}))},e=t,r=[{key:"VERSION",get:function(){return"4.3.1"}},{key:"Default",get:function(){return u}}],(i=null)&&a(e.prototype,i),r&&a(e,r),t}();n()(window).on(g.LOAD_DATA_API,function(){c(this,void 0);for(var t=[].slice.call(document.querySelectorAll(v.DATA_SPY)),e=t.length;e--;){var i=n()(t[e]);b._jQueryInterface.call(i,i.data())}}.bind(void 0)),n.a.fn[h]=b._jQueryInterface,n.a.fn[h].Constructor=b,n.a.fn[h].noConflict=function(){return c(this,void 0),n.a.fn[h]=f,b._jQueryInterface}.bind(void 0);function O(){n()("body").scrollspy({offset:220,target:"#history-navigation"})}i.d(e,"launch",(function(){return O}))},tQbP:function(t,e,i){"use strict";var r=i("ax0f"),n=i("hpdy"),s=i("N9G2"),o=i("ct80"),l=i("NVHP"),c=[].sort,a=[1,2,3],h=o((function(){a.sort(void 0)})),f=o((function(){a.sort(null)})),u=l("sort");r({target:"Array",proto:!0,forced:h||!f||u},{sort:function(t){return void 0===t?c.call(s(this)):c.call(s(this),n(t))}})}}]);