webpackJsonp([0],{"0xfk":function(e,t,n){"use strict";Object.defineProperty(t,"__esModule",{value:!0});var r=n("K/Cg"),i=(n.n(r),n("jFpx")),o=(n.n(i),{launch:function(){$("img.lazy").lazyload({})}});t.default=o},"K/Cg":function(e,t,n){var r;!function(e){if(e.document){var t,n,r,i,o,a=e.document;a.querySelectorAll||(a.querySelectorAll=function(t){var n,r=a.createElement("style"),i=[];for(a.documentElement.firstChild.appendChild(r),a._qsa=[],r.styleSheet.cssText=t+"{x-qsa:expression(document._qsa && document._qsa.push(this))}",e.scrollBy(0,0),r.parentNode.removeChild(r);a._qsa.length;)(n=a._qsa.shift()).style.removeAttribute("x-qsa"),i.push(n);return a._qsa=null,i}),a.querySelector||(a.querySelector=function(e){var t=a.querySelectorAll(e);return t.length?t[0]:null}),a.getElementsByClassName||(a.getElementsByClassName=function(e){return e=String(e).replace(/^|\s+/g,"."),a.querySelectorAll(e)}),Object.keys||(Object.keys=function(e){if(e!==Object(e))throw TypeError("Object.keys called on non-object");var t,n=[];for(t in e)Object.prototype.hasOwnProperty.call(e,t)&&n.push(t);return n}),Array.prototype.forEach||(Array.prototype.forEach=function(e){if(void 0===this||null===this)throw TypeError();var t=Object(this),n=t.length>>>0;if("function"!=typeof e)throw TypeError();var r,i=arguments[1];for(r=0;r<n;r++)r in t&&e.call(i,t[r],r,t)}),n="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",(t=e).atob=t.atob||function(e){var t=0,r=[],i=0,o=0;if((e=(e=String(e)).replace(/\s/g,"")).length%4==0&&(e=e.replace(/=+$/,"")),e.length%4==1)throw Error("InvalidCharacterError");if(/[^+/0-9A-Za-z]/.test(e))throw Error("InvalidCharacterError");for(;t<e.length;)i=i<<6|n.indexOf(e.charAt(t)),24===(o+=6)&&(r.push(String.fromCharCode(i>>16&255)),r.push(String.fromCharCode(i>>8&255)),r.push(String.fromCharCode(255&i)),o=0,i=0),t+=1;return 12===o?(i>>=4,r.push(String.fromCharCode(255&i))):18===o&&(i>>=2,r.push(String.fromCharCode(i>>8&255)),r.push(String.fromCharCode(255&i))),r.join("")},t.btoa=t.btoa||function(e){e=String(e);var t,r,i,o,a,l,s,h=0,d=[];if(/[^\x00-\xFF]/.test(e))throw Error("InvalidCharacterError");for(;h<e.length;)o=(t=e.charCodeAt(h++))>>2,a=(3&t)<<4|(r=e.charCodeAt(h++))>>4,l=(15&r)<<2|(i=e.charCodeAt(h++))>>6,s=63&i,h===e.length+2?(l=64,s=64):h===e.length+1&&(s=64),d.push(n.charAt(o),n.charAt(a),n.charAt(l),n.charAt(s));return d.join("")},Object.prototype.hasOwnProperty||(Object.prototype.hasOwnProperty=function(e){var t=this.__proto__||this.constructor.prototype;return e in this&&(!(e in t)||t[e]!==this[e])}),function(){if("performance"in e==!1&&(e.performance={}),Date.now=Date.now||function(){return(new Date).getTime()},"now"in e.performance==!1){var t=Date.now();performance.timing&&performance.timing.navigationStart&&(t=performance.timing.navigationStart),e.performance.now=function(){return Date.now()-t}}}(),e.requestAnimationFrame||(e.webkitRequestAnimationFrame&&e.webkitCancelAnimationFrame?((o=e).requestAnimationFrame=function(e){return webkitRequestAnimationFrame(function(){e(o.performance.now())})},o.cancelAnimationFrame=o.webkitCancelAnimationFrame):e.mozRequestAnimationFrame&&e.mozCancelAnimationFrame?((i=e).requestAnimationFrame=function(e){return mozRequestAnimationFrame(function(){e(i.performance.now())})},i.cancelAnimationFrame=i.mozCancelAnimationFrame):((r=e).requestAnimationFrame=function(e){return r.setTimeout(e,1e3/60)},r.cancelAnimationFrame=r.clearTimeout))}}(this),r=function(){return function(e){var t={};function n(r){if(t[r])return t[r].exports;var i=t[r]={exports:{},id:r,loaded:!1};return e[r].call(i.exports,i,i.exports,n),i.loaded=!0,i.exports}return n.m=e,n.c=t,n.p="",n(0)}([function(e,t,n){e.exports=n(1)},function(e,t,n){(function(t){var r=n(2),i=n(3),o=n(6),a=n(7),l=n(8),s=n(9),h=n(10),d=n(11),c=n(12),u=n(15),f=a.extend,p=a.dimensionCheck,g=d.svg_ns,m={version:d.version,addTheme:function(e,t){return null!=e&&null!=t&&(v.settings.themes[e]=t),delete v.vars.cache.themeKeys,this},addImage:function(e,t){return s.getNodeArray(t).forEach(function(t){var n=s.newEl("img"),r={};r[v.setup.dataAttr]=e,s.setAttr(n,r),t.appendChild(n)}),this},setResizeUpdate:function(e,t){e.holderData&&(e.holderData.resizeUpdate=!!t,e.holderData.resizeUpdate&&A(e))},run:function(e){e=e||{};var n={},r=f(v.settings,e);v.vars.preempted=!0,v.vars.dataAttr=r.dataAttr||v.setup.dataAttr,n.renderer=r.renderer?r.renderer:v.setup.renderer,-1===v.setup.renderers.join(",").indexOf(n.renderer)&&(n.renderer=v.setup.supportsSVG?"svg":v.setup.supportsCanvas?"canvas":"html");var i=s.getNodeArray(r.images),o=s.getNodeArray(r.bgnodes),l=s.getNodeArray(r.stylenodes),h=s.getNodeArray(r.objects);return n.stylesheets=[],n.svgXMLStylesheet=!0,n.noFontFallback=!!r.noFontFallback,n.noBackgroundSize=!!r.noBackgroundSize,l.forEach(function(e){if(e.attributes.rel&&e.attributes.href&&"stylesheet"==e.attributes.rel.value){var t=e.attributes.href.value,r=s.newEl("a");r.href=t;var i=r.protocol+"//"+r.host+r.pathname+r.search;n.stylesheets.push(i)}}),o.forEach(function(e){if(t.getComputedStyle){var i=t.getComputedStyle(e,null).getPropertyValue("background-image"),o=e.getAttribute("data-background-src")||i,a=null,l=r.domain+"/",s=o.indexOf(l);if(0===s)a=o;else if(1===s&&"?"===o[0])a=o.slice(1);else{var h=o.substr(s).match(/([^\"]*)"?\)/);if(null!==h)a=h[1];else if(0===o.indexOf("url("))throw"Holder: unable to parse background URL: "+o}if(a){var d=w(a,r);d&&b({mode:"background",el:e,flags:d,engineSettings:n})}}}),h.forEach(function(e){var t={};try{t.data=e.getAttribute("data"),t.dataSrc=e.getAttribute(v.vars.dataAttr)}catch(e){}var i=null!=t.data&&0===t.data.indexOf(r.domain),o=null!=t.dataSrc&&0===t.dataSrc.indexOf(r.domain);i?y(r,n,t.data,e):o&&y(r,n,t.dataSrc,e)}),i.forEach(function(e){var t={};try{t.src=e.getAttribute("src"),t.dataSrc=e.getAttribute(v.vars.dataAttr),t.rendered=e.getAttribute("data-holder-rendered")}catch(e){}var i,o,l,s,h,d=null!=t.src,c=null!=t.dataSrc&&0===t.dataSrc.indexOf(r.domain),u=null!=t.rendered&&"true"==t.rendered;d?0===t.src.indexOf(r.domain)?y(r,n,t.src,e):c&&(u?y(r,n,t.dataSrc,e):(i=t.src,o=r,l=n,s=t.dataSrc,h=e,a.imageExists(i,function(e){e||y(o,l,s,h)}))):c&&y(r,n,t.dataSrc,e)}),this}},v={settings:{domain:"holder.js",images:"img",objects:"object",bgnodes:"body .holderjs",stylenodes:"head link.holderjs",themes:{gray:{bg:"#EEEEEE",fg:"#AAAAAA"},social:{bg:"#3a5a97",fg:"#FFFFFF"},industrial:{bg:"#434A52",fg:"#C2F200"},sky:{bg:"#0D8FDB",fg:"#FFFFFF"},vine:{bg:"#39DBAC",fg:"#1E292C"},lava:{bg:"#F8591A",fg:"#1C2846"}}},defaults:{size:10,units:"pt",scale:1/16}};function y(e,t,n,r){var i=w(n.substr(n.lastIndexOf(e.domain)),e);i&&b({mode:null,el:r,flags:i,engineSettings:t})}function w(e,t){var n={theme:f(v.settings.themes.gray,null),stylesheets:t.stylesheets,instanceOptions:t},r=e.indexOf("?"),o=[e];-1!==r&&(o=[e.slice(0,r),e.slice(r+1)]);var l=o[0].split("/");n.holderURL=e;var s=l[1],h=s.match(/([\d]+p?)x([\d]+p?)/);if(!h)return!1;if(n.fluid=-1!==s.indexOf("p"),n.dimensions={width:h[1].replace("p","%"),height:h[2].replace("p","%")},2===o.length){var d=i.parse(o[1]);if(a.truthy(d.ratio)){n.fluid=!0;var c=parseFloat(n.dimensions.width.replace("%","")),u=parseFloat(n.dimensions.height.replace("%",""));u=Math.floor(u/c*100),c=100,n.dimensions.width=c+"%",n.dimensions.height=u+"%"}if(n.auto=a.truthy(d.auto),d.bg&&(n.theme.bg=a.parseColor(d.bg)),d.fg&&(n.theme.fg=a.parseColor(d.fg)),d.bg&&!d.fg&&(n.autoFg=!0),d.theme&&n.instanceOptions.themes.hasOwnProperty(d.theme)&&(n.theme=f(n.instanceOptions.themes[d.theme],null)),d.text&&(n.text=d.text),d.textmode&&(n.textmode=d.textmode),d.size&&(n.size=d.size),d.font&&(n.font=d.font),d.align&&(n.align=d.align),d.lineWrap&&(n.lineWrap=d.lineWrap),n.nowrap=a.truthy(d.nowrap),n.outline=a.truthy(d.outline),a.truthy(d.random)){v.vars.cache.themeKeys=v.vars.cache.themeKeys||Object.keys(n.instanceOptions.themes);var p=v.vars.cache.themeKeys[0|Math.random()*v.vars.cache.themeKeys.length];n.theme=f(n.instanceOptions.themes[p],null)}}return n}function b(e){var t=e.mode,n=e.el,r=e.flags,i=e.engineSettings,o=r.dimensions,l=r.theme,h=o.width+"x"+o.height;t=null==t?r.fluid?"fluid":"image":t;if(null!=r.text&&(l.text=r.text,"object"===n.nodeName.toLowerCase())){for(var d=l.text.split("\\n"),c=0;c<d.length;c++)d[c]=a.encodeHtmlEntity(d[c]);l.text=d.join("\\n")}if(l.text){var u=l.text.match(/holder_([a-z]+)/g);null!==u&&u.forEach(function(e){"holder_dimensions"===e&&(l.text=l.text.replace(e,h))})}var g=r.holderURL,m=f(i,null);if(r.font&&(l.font=r.font,!m.noFontFallback&&"img"===n.nodeName.toLowerCase()&&v.setup.supportsCanvas&&"svg"===m.renderer&&(m=f(m,{renderer:"canvas"}))),r.font&&"canvas"==m.renderer&&(m.reRender=!0),"background"==t)null==n.getAttribute("data-background-src")&&s.setAttr(n,{"data-background-src":g});else{var y={};y[v.vars.dataAttr]=g,s.setAttr(n,y)}r.theme=l,n.holderData={flags:r,engineSettings:m},"image"!=t&&"fluid"!=t||s.setAttr(n,{alt:l.text?l.text+" ["+h+"]":h});var w={mode:t,el:n,holderSettings:{dimensions:o,theme:l,flags:r},engineSettings:m};"image"==t?(r.auto||(n.style.width=o.width+"px",n.style.height=o.height+"px"),"html"==m.renderer?n.style.backgroundColor=l.bg:(x(w),"exact"==r.textmode&&(n.holderData.resizeUpdate=!0,v.vars.resizableImages.push(n),A(n)))):"background"==t&&"html"!=m.renderer?x(w):"fluid"==t&&(n.holderData.resizeUpdate=!0,"%"==o.height.slice(-1)?n.style.height=o.height:null!=r.auto&&r.auto||(n.style.height=o.height+"px"),"%"==o.width.slice(-1)?n.style.width=o.width:null!=r.auto&&r.auto||(n.style.width=o.width+"px"),"inline"!=n.style.display&&""!==n.style.display&&"none"!=n.style.display||(n.style.display="block"),function(e){if(e.holderData){var t=p(e);if(t){var n=e.holderData.flags,r={fluidHeight:"%"==n.dimensions.height.slice(-1),fluidWidth:"%"==n.dimensions.width.slice(-1),mode:null,initialDimensions:t};r.fluidWidth&&!r.fluidHeight?(r.mode="width",r.ratio=r.initialDimensions.width/parseFloat(n.dimensions.height)):!r.fluidWidth&&r.fluidHeight&&(r.mode="height",r.ratio=parseFloat(n.dimensions.width)/r.initialDimensions.height),e.holderData.fluidConfig=r}else C(e)}}(n),"html"==m.renderer?n.style.backgroundColor=l.bg:(v.vars.resizableImages.push(n),A(n)))}function x(e){var n,r=e.mode,i=e.el,a=e.holderSettings,l=e.engineSettings;switch(l.renderer){case"svg":if(!v.setup.supportsSVG)return;break;case"canvas":if(!v.setup.supportsCanvas)return;break;default:return}var d={width:a.dimensions.width,height:a.dimensions.height,theme:a.theme,flags:a.flags},f=function(e){var t=v.defaults.size;parseFloat(e.theme.size)?t=e.theme.size:parseFloat(e.flags.size)&&(t=e.flags.size);switch(e.font={family:e.theme.font?e.theme.font:"Arial, Helvetica, Open Sans, sans-serif",size:(n=e.width,r=e.height,i=t,a=v.defaults.scale,l=parseInt(n,10),s=parseInt(r,10),d=Math.max(l,s),c=Math.min(l,s),u=.8*Math.min(c,d*a),Math.round(Math.max(i,u))),units:e.theme.units?e.theme.units:v.defaults.units,weight:e.theme.fontweight?e.theme.fontweight:"bold"},e.text=e.theme.text||Math.floor(e.width)+"x"+Math.floor(e.height),e.noWrap=e.theme.nowrap||e.flags.nowrap,e.align=e.theme.align||e.flags.align||"center",e.flags.textmode){case"literal":e.text=e.flags.dimensions.width+"x"+e.flags.dimensions.height;break;case"exact":if(!e.flags.exactDimensions)break;e.text=Math.floor(e.flags.exactDimensions.width)+"x"+Math.floor(e.flags.exactDimensions.height)}var n,r,i,a,l,s,d,c,u;var f=e.flags.lineWrap||v.setup.lineWrapRatio,p=e.width*f,g=p,m=new o({width:e.width,height:e.height}),y=m.Shape,w=new y.Rect("holderBg",{fill:e.theme.bg});if(w.resize(e.width,e.height),m.root.add(w),e.flags.outline){var b=new h(w.properties.fill);b=b.lighten(b.lighterThan("7f7f7f")?-.1:.1),w.properties.outline={fill:b.toHex(!0),width:2}}var x=e.theme.fg;if(e.flags.autoFg){var A=new h(w.properties.fill),S=new h("fff"),C=new h("000",{alpha:.285714});x=A.blendAlpha(A.lighterThan("7f7f7f")?C:S).toHex(!0)}var E=new y.Group("holderTextGroup",{text:e.text,align:e.align,font:e.font,fill:x});E.moveTo(null,null,1),m.root.add(E);var k=E.textPositionData=O(m);if(!k)throw"Holder: staging fallback not supported yet.";E.properties.leading=k.boundingBox.height;var T=null,F=null;function j(e,t,n,r){t.width=n,t.height=r,e.width=Math.max(e.width,t.width),e.height+=t.height}if(k.lineCount>1){var z,D=0,M=0,B=0;F=new y.Group("line"+B),"left"!==e.align&&"right"!==e.align||(g=e.width*(1-2*(1-f)));for(var L=0;L<k.words.length;L++){var R=k.words[L];T=new y.Text(R.text);var I="\\n"==R.text;!e.noWrap&&(D+R.width>=g||!0===I)&&(j(E,F,D,E.properties.leading),E.add(F),D=0,M+=E.properties.leading,B+=1,(F=new y.Group("line"+B)).y=M),!0!==I&&(T.moveTo(D,0),D+=k.spaceWidth+R.width,F.add(T))}if(j(E,F,D,E.properties.leading),E.add(F),"left"===e.align)E.moveTo(e.width-p,null,null);else if("right"===e.align){for(z in E.children)(F=E.children[z]).moveTo(e.width-F.width,null,null);E.moveTo(0-(e.width-p),null,null)}else{for(z in E.children)(F=E.children[z]).moveTo((E.width-F.width)/2,null,null);E.moveTo((e.width-E.width)/2,null,null)}E.moveTo(null,(e.height-E.height)/2,null),(e.height-E.height)/2<0&&E.moveTo(null,0,null)}else T=new y.Text(e.text),(F=new y.Group("line0")).add(T),E.add(F),"left"===e.align?E.moveTo(e.width-p,null,null):"right"===e.align?E.moveTo(0-(e.width-p),null,null):E.moveTo((e.width-k.boundingBox.width)/2,null,null),E.moveTo(null,(e.height-k.boundingBox.height)/2,null);return m}(d);function p(){var t=null;switch(l.renderer){case"canvas":t=u(f,e);break;case"svg":t=c(f,e);break;default:throw"Holder: invalid renderer: "+l.renderer}return t}if(null==(n=p()))throw"Holder: couldn't render placeholder";"background"==r?(i.style.backgroundImage="url("+n+")",l.noBackgroundSize||(i.style.backgroundSize=d.width+"px "+d.height+"px")):("img"===i.nodeName.toLowerCase()?s.setAttr(i,{src:n}):"object"===i.nodeName.toLowerCase()&&s.setAttr(i,{data:n,type:"image/svg+xml"}),l.reRender&&t.setTimeout(function(){var e=p();if(null==e)throw"Holder: couldn't render placeholder";"img"===i.nodeName.toLowerCase()?s.setAttr(i,{src:e}):"object"===i.nodeName.toLowerCase()&&s.setAttr(i,{data:e,type:"image/svg+xml"})},150)),s.setAttr(i,{"data-holder-rendered":!0})}function A(e){for(var t,n=0,r=(t=null==e||null==e.nodeType?v.vars.resizableImages:[e]).length;n<r;n++){var i=t[n];if(i.holderData){var o=i.holderData.flags,a=p(i);if(a){if(!i.holderData.resizeUpdate)continue;if(o.fluid&&o.auto){var l=i.holderData.fluidConfig;switch(l.mode){case"width":a.height=a.width/l.ratio;break;case"height":a.width=a.height*l.ratio}}var s={mode:"image",holderSettings:{dimensions:a,theme:o.theme,flags:o},el:i,engineSettings:i.holderData.engineSettings};"exact"==o.textmode&&(o.exactDimensions=a,s.holderSettings.dimensions=o.dimensions),x(s)}else C(i)}}}function S(){var e,n=[];Object.keys(v.vars.invisibleImages).forEach(function(t){e=v.vars.invisibleImages[t],p(e)&&"img"==e.nodeName.toLowerCase()&&(n.push(e),delete v.vars.invisibleImages[t])}),n.length&&m.run({images:n}),setTimeout(function(){t.requestAnimationFrame(S)},10)}function C(e){e.holderData.invisibleId||(v.vars.invisibleId+=1,v.vars.invisibleImages["i"+v.vars.invisibleId]=e,e.holderData.invisibleId=v.vars.invisibleId)}var E,k,T,F,O=(E=null,k=null,T=null,function(e){var t,n=e.root;if(v.setup.supportsSVG){var r=!1;null!=E&&E.parentNode===document.body||(r=!0),(E=l.initSVG(E,n.properties.width,n.properties.height)).style.display="block",r&&(k=s.newEl("text",g),t=null,T=document.createTextNode(t),s.setAttr(k,{x:0}),k.appendChild(T),E.appendChild(k),document.body.appendChild(E),E.style.visibility="hidden",E.style.position="absolute",E.style.top="-100%",E.style.left="-100%");var i=n.children.holderTextGroup.properties;s.setAttr(k,{y:i.font.size,style:a.cssProps({"font-weight":i.font.weight,"font-size":i.font.size+i.font.units,"font-family":i.font.family})}),T.nodeValue=i.text;var o=k.getBBox(),h=Math.ceil(o.width/n.properties.width),d=i.text.split(" "),c=i.text.match(/\\n/g);h+=null==c?0:c.length,T.nodeValue=i.text.replace(/[ ]+/g,"");var u=k.getComputedTextLength(),f=o.width-u,p=Math.round(f/Math.max(1,d.length-1)),m=[];if(h>1){T.nodeValue="";for(var y=0;y<d.length;y++)if(0!==d[y].length){T.nodeValue=a.decodeHtmlEntity(d[y]);var w=k.getBBox();m.push({text:d[y],width:w.width})}}return E.style.display="none",{spaceWidth:p,lineCount:h,boundingBox:o,words:m}}return!1});function j(){!function(e){v.vars.debounceTimer||e.call(this),v.vars.debounceTimer&&t.clearTimeout(v.vars.debounceTimer),v.vars.debounceTimer=t.setTimeout(function(){v.vars.debounceTimer=null,e.call(this)},v.setup.debounce)}(function(){A(null)})}for(var z in v.flags)v.flags.hasOwnProperty(z)&&(v.flags[z].match=function(e){return e.match(this.regex)});v.setup={renderer:"html",debounce:100,ratio:1,supportsCanvas:!1,supportsSVG:!1,lineWrapRatio:.9,dataAttr:"data-src",renderers:["html","canvas","svg"]},v.vars={preempted:!1,resizableImages:[],invisibleImages:{},invisibleId:0,visibilityCheckStarted:!1,debounceTimer:null,cache:{}},(F=s.newEl("canvas")).getContext&&-1!=F.toDataURL("image/png").indexOf("data:image/png")&&(v.setup.renderer="canvas",v.setup.supportsCanvas=!0),document.createElementNS&&document.createElementNS(g,"svg").createSVGRect&&(v.setup.renderer="svg",v.setup.supportsSVG=!0),v.vars.visibilityCheckStarted||(t.requestAnimationFrame(S),v.vars.visibilityCheckStarted=!0),r&&r(function(){v.vars.preempted||m.run(),t.addEventListener?(t.addEventListener("resize",j,!1),t.addEventListener("orientationchange",j,!1)):t.attachEvent("onresize",j),"object"==typeof t.Turbolinks&&t.document.addEventListener("page:change",function(){m.run()})}),e.exports=m}).call(t,function(){return this}())},function(e,t){e.exports="undefined"!=typeof window&&function(e){null==document.readyState&&document.addEventListener&&(document.addEventListener("DOMContentLoaded",function e(){document.removeEventListener("DOMContentLoaded",e,!1),document.readyState="complete"},!1),document.readyState="loading");var t=e.document,n=t.documentElement,r="load",i=!1,o="on"+r,a="complete",l="readyState",s="attachEvent",h="detachEvent",d="addEventListener",c="DOMContentLoaded",u="onreadystatechange",f="removeEventListener",p=d in t,g=i,m=i,v=[];function y(e){if(!m){if(!t.body)return x(y);for(m=!0;e=v.shift();)x(e)}}function w(e){(p||e.type===r||t[l]===a)&&(b(),y())}function b(){p?(t[f](c,w,i),e[f](r,w,i)):(t[h](u,w),e[h](o,w))}function x(e,t){setTimeout(e,+t>=0?t:1)}if(t[l]===a)x(y);else if(p)t[d](c,w,i),e[d](r,w,i);else{t[s](u,w),e[s](o,w);try{g=null==e.frameElement&&n}catch(e){}g&&g.doScroll&&function e(){if(!m){try{g.doScroll("left")}catch(t){return x(e,50)}b(),y()}}()}function A(e){m?x(e):v.push(e)}return A.version="1.4.0",A.isReady=function(){return m},A}(window)},function(e,t,n){var r=encodeURIComponent,i=decodeURIComponent,o=n(4),a=n(5),l=/(\w+)\[(\d+)\]/,s=/\w+\.\w+/;t.parse=function(e){if("string"!=typeof e)return{};if(""===(e=o(e)))return{};"?"===e.charAt(0)&&(e=e.slice(1));for(var t={},n=e.split("&"),r=0;r<n.length;r++){var a,h,d,c=n[r].split("="),u=i(c[0]);if(a=l.exec(u))t[a[1]]=t[a[1]]||[],t[a[1]][a[2]]=i(c[1]);else if(a=s.test(u)){for(a=u.split("."),h=t;a.length;)if((d=a.shift()).length){if(h[d]){if(h[d]&&"object"!=typeof h[d])break}else h[d]={};a.length||(h[d]=i(c[1])),h=h[d]}}else t[c[0]]=null==c[1]?"":i(c[1])}return t},t.stringify=function(e){if(!e)return"";var t=[];for(var n in e){var i=e[n];if("array"!=a(i))t.push(r(n)+"="+r(e[n]));else for(var o=0;o<i.length;++o)t.push(r(n+"["+o+"]")+"="+r(i[o]))}return t.join("&")}},function(e,t){(t=e.exports=function(e){return e.replace(/^\s*|\s*$/g,"")}).left=function(e){return e.replace(/^\s*/,"")},t.right=function(e){return e.replace(/\s*$/,"")}},function(e,t){var n=Object.prototype.toString;e.exports=function(e){switch(n.call(e)){case"[object Date]":return"date";case"[object RegExp]":return"regexp";case"[object Arguments]":return"arguments";case"[object Array]":return"array";case"[object Error]":return"error"}return null===e?"null":void 0===e?"undefined":e!=e?"nan":e&&1===e.nodeType?"element":null!=(t=e)&&(t._isBuffer||t.constructor&&"function"==typeof t.constructor.isBuffer&&t.constructor.isBuffer(t))?"buffer":typeof(e=e.valueOf?e.valueOf():Object.prototype.valueOf.apply(e));var t}},function(e,t){e.exports=function(e){var t=1;var n=function(e){t++,this.parent=null,this.children={},this.id=t,this.name="n"+t,void 0!==e&&(this.name=e),this.x=this.y=this.z=0,this.width=this.height=0};n.prototype.resize=function(e,t){null!=e&&(this.width=e),null!=t&&(this.height=t)},n.prototype.moveTo=function(e,t,n){this.x=null!=e?e:this.x,this.y=null!=t?t:this.y,this.z=null!=n?n:this.z},n.prototype.add=function(e){var t=e.name;if(void 0!==this.children[t])throw"SceneGraph: child already exists: "+t;this.children[t]=e,e.parent=this};var r=function(){n.call(this,"root"),this.properties=e};r.prototype=new n;var i=function(e,t){if(n.call(this,e),this.properties={fill:"#000000"},void 0!==t)!function(e,t){for(var n in t)e[n]=t[n]}(this.properties,t);else if(void 0!==e&&"string"!=typeof e)throw"SceneGraph: invalid node name"};i.prototype=new n;var o=function(){i.apply(this,arguments),this.type="group"};o.prototype=new i;var a=function(){i.apply(this,arguments),this.type="rect"};a.prototype=new i;var l=function(e){i.call(this),this.type="text",this.properties.text=e};l.prototype=new i;var s=new r;return this.Shape={Rect:a,Text:l,Group:o},this.root=s,this}},function(e,t){(function(e){t.extend=function(e,t){var n={};for(var r in e)e.hasOwnProperty(r)&&(n[r]=e[r]);if(null!=t)for(var i in t)t.hasOwnProperty(i)&&(n[i]=t[i]);return n},t.cssProps=function(e){var t=[];for(var n in e)e.hasOwnProperty(n)&&t.push(n+":"+e[n]);return t.join(";")},t.encodeHtmlEntity=function(e){for(var t=[],n=0,r=e.length-1;r>=0;r--)(n=e.charCodeAt(r))>128?t.unshift(["&#",n,";"].join("")):t.unshift(e[r]);return t.join("")},t.imageExists=function(e,t){var n=new Image;n.onerror=function(){t.call(this,!1)},n.onload=function(){t.call(this,!0)},n.src=e},t.decodeHtmlEntity=function(e){return e.replace(/&#(\d+);/g,function(e,t){return String.fromCharCode(t)})},t.dimensionCheck=function(e){var t={height:e.clientHeight,width:e.clientWidth};return!(!t.height||!t.width)&&t},t.truthy=function(e){return"string"==typeof e?"true"===e||"yes"===e||"1"===e||"on"===e||"✓"===e:!!e},t.parseColor=function(e){var t,n=e.match(/(^(?:#?)[0-9a-f]{6}$)|(^(?:#?)[0-9a-f]{3}$)/i);return null!==n?"#"!==(t=n[1]||n[2])[0]?"#"+t:t:null!==(n=e.match(/^rgb\((\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/))?t="rgb("+n.slice(1).join(",")+")":null!==(n=e.match(/^rgba\((\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0\.\d{1,}|1)\)$/))?t="rgba("+n.slice(1).join(",")+")":null},t.canvasRatio=function(){var t=1,n=1;if(e.document){var r=e.document.createElement("canvas");if(r.getContext){var i=r.getContext("2d");t=e.devicePixelRatio||1,n=i.webkitBackingStorePixelRatio||i.mozBackingStorePixelRatio||i.msBackingStorePixelRatio||i.oBackingStorePixelRatio||i.backingStorePixelRatio||1}}return t/n}}).call(t,function(){return this}())},function(e,t,n){(function(e){var r=n(9),i="http://www.w3.org/2000/svg";t.initSVG=function(e,t,n){var o,a,l=!1;e&&e.querySelector?null===(a=e.querySelector("style"))&&(l=!0):(e=r.newEl("svg",i),l=!0),l&&(o=r.newEl("defs",i),a=r.newEl("style",i),r.setAttr(a,{type:"text/css"}),o.appendChild(a),e.appendChild(o)),e.webkitMatchesSelector&&e.setAttribute("xmlns",i);for(var s=0;s<e.childNodes.length;s++)8===e.childNodes[s].nodeType&&e.removeChild(e.childNodes[s]);for(;a.childNodes.length;)a.removeChild(a.childNodes[0]);return r.setAttr(e,{width:t,height:n,viewBox:"0 0 "+t+" "+n,preserveAspectRatio:"none"}),e},t.svgStringToDataURI=function(t,n){return n?"data:image/svg+xml;charset=UTF-8;base64,"+btoa(e.unescape(encodeURIComponent(t))):"data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(t)},t.serializeSVG=function(t,n){if(e.XMLSerializer){var i=new XMLSerializer,o="",a=n.stylesheets;if(n.svgXMLStylesheet){for(var l=r.createXML(),s=a.length-1;s>=0;s--){var h=l.createProcessingInstruction("xml-stylesheet",'href="'+a[s]+'" rel="stylesheet"');l.insertBefore(h,l.firstChild)}l.removeChild(l.documentElement),o=i.serializeToString(l)}var d=i.serializeToString(t);return o+(d=d.replace(/\&amp;(\#[0-9]{2,}\;)/g,"&$1"))}}}).call(t,function(){return this}())},function(e,t){(function(e){t.newEl=function(t,n){if(e.document)return null==n?e.document.createElement(t):e.document.createElementNS(n,t)},t.setAttr=function(e,t){for(var n in t)e.setAttribute(n,t[n])},t.createXML=function(){if(e.DOMParser)return(new DOMParser).parseFromString("<xml />","application/xml")},t.getNodeArray=function(t){var n=null;return"string"==typeof t?n=document.querySelectorAll(t):e.NodeList&&t instanceof e.NodeList?n=t:e.Node&&t instanceof e.Node?n=[t]:e.HTMLCollection&&t instanceof e.HTMLCollection?n=t:t instanceof Array?n=t:null===t&&(n=[]),n=Array.prototype.slice.call(n)}}).call(t,function(){return this}())},function(e,t){var n=function(e,t){"string"==typeof e&&(this.original=e,"#"===e.charAt(0)&&(e=e.slice(1)),/[^a-f0-9]+/i.test(e)||(3===e.length&&(e=e.replace(/./g,"$&$&")),6===e.length&&(this.alpha=1,t&&t.alpha&&(this.alpha=t.alpha),this.set(parseInt(e,16)))))};n.rgb2hex=function(e,t,n){return[e,t,n].map(function(e){var t=(0|e).toString(16);return e<16&&(t="0"+t),t}).join("")},n.hsl2rgb=function(e,t,n){var r=e/60,i=(1-Math.abs(2*n-1))*t,o=i*(1-Math.abs(parseInt(r)%2-1)),a=n-i/2,l=0,s=0,h=0;return r>=0&&r<1?(l=i,s=o):r>=1&&r<2?(l=o,s=i):r>=2&&r<3?(s=i,h=o):r>=3&&r<4?(s=o,h=i):r>=4&&r<5?(l=o,h=i):r>=5&&r<6&&(l=i,h=o),l+=a,s+=a,h+=a,[l=parseInt(255*l),s=parseInt(255*s),h=parseInt(255*h)]},n.prototype.set=function(e){this.raw=e;var t=(16711680&this.raw)>>16,n=(65280&this.raw)>>8,r=255&this.raw,i=.2126*t+.7152*n+.0722*r,o=-.09991*t-.33609*n+.436*r,a=.615*t-.55861*n-.05639*r;return this.rgb={r:t,g:n,b:r},this.yuv={y:i,u:o,v:a},this},n.prototype.lighten=function(e){var t=255*(Math.min(1,Math.max(0,Math.abs(e)))*(e<0?-1:1))|0,r=Math.min(255,Math.max(0,this.rgb.r+t)),i=Math.min(255,Math.max(0,this.rgb.g+t)),o=Math.min(255,Math.max(0,this.rgb.b+t)),a=n.rgb2hex(r,i,o);return new n(a)},n.prototype.toHex=function(e){return(e?"#":"")+this.raw.toString(16)},n.prototype.lighterThan=function(e){return e instanceof n||(e=new n(e)),this.yuv.y>e.yuv.y},n.prototype.blendAlpha=function(e){e instanceof n||(e=new n(e));var t=e,r=t.alpha*t.rgb.r+(1-t.alpha)*this.rgb.r,i=t.alpha*t.rgb.g+(1-t.alpha)*this.rgb.g,o=t.alpha*t.rgb.b+(1-t.alpha)*this.rgb.b;return new n(n.rgb2hex(r,i,o))},e.exports=n},function(e,t){e.exports={version:"2.9.4",svg_ns:"http://www.w3.org/2000/svg"}},function(e,t,n){var r=n(13),i=n(8),o=n(11),a=n(7),l=o.svg_ns,s={element:function(e){var t=e.tag,n=e.content||"";return delete e.tag,delete e.content,[t,n,e]}};e.exports=function(e,t){var n,o=t.engineSettings.stylesheets.map(function(e){return'<?xml-stylesheet rel="stylesheet" href="'+e+'"?>'}).join("\n"),h="holder_"+Number(new Date).toString(16),d=e.root,c=d.children.holderTextGroup,u="#"+h+" text { "+(n=c.properties,a.cssProps({fill:n.fill,"font-weight":n.font.weight,"font-family":n.font.family+", monospace","font-size":n.font.size+n.font.units}))+" } ";c.y+=.8*c.textPositionData.boundingBox.height;var f=[];Object.keys(c.children).forEach(function(e){var t=c.children[e];Object.keys(t.children).forEach(function(e){var n=t.children[e],r=c.x+t.x+n.x,i=c.y+t.y+n.y,o=s.element({tag:"text",content:n.properties.text,x:r,y:i});f.push(o)})});var p,g,m,v,y=s.element({tag:"g",content:f}),w=null;if(d.children.holderBg.properties.outline){var b=d.children.holderBg.properties.outline;w=s.element({tag:"path",d:(p=d.children.holderBg.width,g=d.children.holderBg.height,m=b.width,v=m/2,["M",v,v,"H",p-v,"V",g-v,"H",v,"V",0,"M",0,v,"L",p,g-v,"M",0,g-v,"L",p,v].join(" ")),"stroke-width":b.width,stroke:b.fill,fill:"none"})}var x,A,S=(x=d.children.holderBg,A="rect",s.element({tag:A,width:x.width,height:x.height,fill:x.properties.fill})),C=[];C.push(S),b&&C.push(w),C.push(y);var E=s.element({tag:"g",id:h,content:C}),k=s.element({tag:"style",content:u,type:"text/css"}),T=s.element({tag:"defs",content:k}),F=s.element({tag:"svg",content:[T,E],width:d.properties.width,height:d.properties.height,xmlns:l,viewBox:[0,0,d.properties.width,d.properties.height].join(" "),preserveAspectRatio:"none"}),O=r(F);return O=o+O[0],i.svgStringToDataURI(O,"background"===t.mode)}},function(e,t,n){n(14);e.exports=function e(t,n,r){"use strict";var i,o,a,l,s,h,d,c,u,f,p,g,m=1,v=!0;function y(e,t){if(null!==t&&!1!==t&&void 0!==t)return"string"!=typeof t&&"object"!=typeof t?String(t):t}if(r=r||{},"string"==typeof t[0])t[0]=(s=t[0],h=s.match(/^[\w-]+/),d={tag:h?h[0]:"div",attr:{},children:[]},c=s.match(/#([\w-]+)/),u=s.match(/\$([\w-]+)/),f=s.match(/\.[\w-]+/g),c&&(d.attr.id=c[1],r[c[1]]=d),u&&(r[u[1]]=d),f&&(d.attr.class=f.join(" ").replace(/\./g,"")),s.match(/&$/g)&&(v=!1),d);else{if(!Array.isArray(t[0]))throw new Error("First element of array must be a string, or an array and not "+JSON.stringify(t[0]));m=0}for(;m<t.length;m++){if(!1===t[m]||null===t[m]){t[0]=!1;break}if(void 0!==t[m]&&!0!==t[m])if("string"==typeof t[m])v&&(t[m]=(p=t[m],String(p).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&apos;").replace(/</g,"&lt;").replace(/>/g,"&gt;"))),t[0].children.push(t[m]);else if("number"==typeof t[m])t[0].children.push(t[m]);else if(Array.isArray(t[m])){if(Array.isArray(t[m][0])){if(t[m].reverse().forEach(function(e){t.splice(m+1,0,e)}),0!==m)continue;m++}e(t[m],n,r),t[m][0]&&t[0].children.push(t[m][0])}else if("function"==typeof t[m])a=t[m];else{if("object"!=typeof t[m])throw new TypeError('"'+t[m]+'" is not allowed as a value.');for(o in t[m])t[m].hasOwnProperty(o)&&null!==t[m][o]&&!1!==t[m][o]&&("style"===o&&"object"==typeof t[m][o]?t[0].attr[o]=JSON.stringify(t[m][o],y).slice(2,-2).replace(/","/g,";").replace(/":"/g,":").replace(/\\"/g,"'"):t[0].attr[o]=t[m][o])}}if(!1!==t[0]){i="<"+t[0].tag;for(l in t[0].attr)t[0].attr.hasOwnProperty(l)&&(i+=" "+l+'="'+(g=t[0].attr[l],g||0===g?String(g).replace(/&/g,"&amp;").replace(/"/g,"&quot;"):"")+'"');i+=">",t[0].children.forEach(function(e){i+=e}),i+="</"+t[0].tag+">",t[0]=i}return r[0]=t[0],a&&a(t[0]),r}},function(e,t){"use strict";var n=/["'&<>]/;e.exports=function(e){var t,r=""+e,i=n.exec(r);if(!i)return r;var o="",a=0,l=0;for(a=i.index;a<r.length;a++){switch(r.charCodeAt(a)){case 34:t="&quot;";break;case 38:t="&amp;";break;case 39:t="&#39;";break;case 60:t="&lt;";break;case 62:t="&gt;";break;default:continue}l!==a&&(o+=r.substring(l,a)),l=a+1,o+=t}return l!==a?o+r.substring(l,a):o}},function(e,t,n){var r,i,o=n(9),a=n(7);e.exports=(r=o.newEl("canvas"),i=null,function(e){null==i&&(i=r.getContext("2d"));var t=a.canvasRatio(),n=e.root;r.width=t*n.properties.width,r.height=t*n.properties.height,i.textBaseline="middle";var o=n.children.holderBg,l=t*o.width,s=t*o.height;i.fillStyle=o.properties.fill,i.fillRect(0,0,l,s),o.properties.outline&&(i.strokeStyle=o.properties.outline.fill,i.lineWidth=o.properties.outline.width,i.moveTo(1,1),i.lineTo(l-1,1),i.lineTo(l-1,s-1),i.lineTo(1,s-1),i.lineTo(1,1),i.moveTo(0,1),i.lineTo(l,s-1),i.moveTo(0,s-1),i.lineTo(l,1),i.stroke());var h=n.children.holderTextGroup;i.font=h.properties.font.weight+" "+t*h.properties.font.size+h.properties.font.units+" "+h.properties.font.family+", monospace",i.fillStyle=h.properties.fill;for(var d in h.children){var c=h.children[d];for(var u in c.children){var f=c.children[u],p=t*(h.x+c.x+f.x),g=t*(h.y+c.y+f.y+h.properties.leading/2);i.fillText(f.properties.text,p,g)}}return r.toDataURL("image/png")})}])},e.exports=r(),"undefined"!=typeof Meteor&&"undefined"!=typeof Package&&(Holder=this.Holder)},jFpx:function(e,t){var n,r,i,o,a;n=jQuery,r=window,i=document,a=n(r),n.fn.lazyload=function(e){var t,l=this,s={threshold:0,failure_limit:0,event:"scroll",effect:"show",container:r,data_attribute:"original",skip_invisible:!1,appear:null,load:null,placeholder:"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAANSURBVBhXYzh8+PB/AAffA0nNPuCLAAAAAElFTkSuQmCC"};function h(){var e=0;l.each(function(){var t=n(this);if(!s.skip_invisible||t.is(":visible"))if(n.abovethetop(this,s)||n.leftofbegin(this,s));else if(n.belowthefold(this,s)||n.rightoffold(this,s)){if(++e>s.failure_limit)return!1}else t.trigger("appear"),e=0})}return e&&(o!==e.failurelimit&&(e.failure_limit=e.failurelimit,delete e.failurelimit),o!==e.effectspeed&&(e.effect_speed=e.effectspeed,delete e.effectspeed),n.extend(s,e)),t=s.container===o||s.container===r?a:n(s.container),0===s.event.indexOf("scroll")&&t.bind(s.event,function(){return h()}),this.each(function(){var e=this,t=n(e);e.loaded=!1,t.attr("src")!==o&&!1!==t.attr("src")||t.is("img")&&t.attr("src",s.placeholder),t.one("appear",function(){if(!this.loaded){if(s.appear){var r=l.length;s.appear.call(e,r,s)}n("<img />").bind("load",function(){var r=t.attr("data-"+s.data_attribute);t.hide(),t.is("img")?t.attr("src",r):t.css("background-image","url('"+r+"')"),t[s.effect](s.effect_speed),e.loaded=!0;var i=n.grep(l,function(e){return!e.loaded});if(l=n(i),s.load){var o=l.length;s.load.call(e,o,s)}}).attr("src",t.attr("data-"+s.data_attribute))}}),0!==s.event.indexOf("scroll")&&t.bind(s.event,function(){e.loaded||t.trigger("appear")})}),a.bind("resize",function(){h()}),/(?:iphone|ipod|ipad).*os 5/gi.test(navigator.appVersion)&&a.bind("pageshow",function(e){e.originalEvent&&e.originalEvent.persisted&&l.each(function(){n(this).trigger("appear")})}),n(i).ready(function(){h()}),this},n.belowthefold=function(e,t){return(t.container===o||t.container===r?(r.innerHeight?r.innerHeight:a.height())+a.scrollTop():n(t.container).offset().top+n(t.container).height())<=n(e).offset().top-t.threshold},n.rightoffold=function(e,t){return(t.container===o||t.container===r?a.width()+a.scrollLeft():n(t.container).offset().left+n(t.container).width())<=n(e).offset().left-t.threshold},n.abovethetop=function(e,t){return(t.container===o||t.container===r?a.scrollTop():n(t.container).offset().top)>=n(e).offset().top+t.threshold+n(e).height()},n.leftofbegin=function(e,t){return(t.container===o||t.container===r?a.scrollLeft():n(t.container).offset().left)>=n(e).offset().left+t.threshold+n(e).width()},n.inviewport=function(e,t){return!(n.rightoffold(e,t)||n.leftofbegin(e,t)||n.belowthefold(e,t)||n.abovethetop(e,t))},n.extend(n.expr[":"],{"below-the-fold":function(e){return n.belowthefold(e,{threshold:0})},"above-the-top":function(e){return!n.belowthefold(e,{threshold:0})},"right-of-screen":function(e){return n.rightoffold(e,{threshold:0})},"left-of-screen":function(e){return!n.rightoffold(e,{threshold:0})},"in-viewport":function(e){return n.inviewport(e,{threshold:0})},"above-the-fold":function(e){return!n.belowthefold(e,{threshold:0})},"right-of-fold":function(e){return n.rightoffold(e,{threshold:0})},"left-of-fold":function(e){return!n.rightoffold(e,{threshold:0})}})}});