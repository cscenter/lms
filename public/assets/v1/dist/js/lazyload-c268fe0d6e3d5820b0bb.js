(window.webpackJsonp=window.webpackJsonp||[]).push([[13],{NXli:function(e,t,n){"use strict";n.r(t),n.d(t,"launch",(function(){return r}));n("hmhZ"),n("Z8x7");function r(){$("img.lazy").lazyload({})}},Z8x7:function(e,t){
/*!
 * Lazy Load - jQuery plugin for lazy loading images
 *
 * Copyright (c) 2007-2015 Mika Tuupola
 *
 * Licensed under the MIT license:
 *   http://www.opensource.org/licenses/mit-license.php
 *
 * Project home:
 *   http://www.appelsiini.net/projects/lazyload
 *
 * Version:  1.9.7
 *
 */
!function(e,t,n,r){var i=e(t);e.fn.lazyload=function(r){var o,a=this,s={threshold:0,failure_limit:0,event:"scroll",effect:"show",container:t,data_attribute:"original",skip_invisible:!1,appear:null,load:null,placeholder:"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAANSURBVBhXYzh8+PB/AAffA0nNPuCLAAAAAElFTkSuQmCC"};function l(){var t=0;a.each((function(){var n=e(this);if(!s.skip_invisible||n.is(":visible"))if(e.abovethetop(this,s)||e.leftofbegin(this,s));else if(e.belowthefold(this,s)||e.rightoffold(this,s)){if(++t>s.failure_limit)return!1}else n.trigger("appear"),t=0}))}return r&&(void 0!==r.failurelimit&&(r.failure_limit=r.failurelimit,delete r.failurelimit),void 0!==r.effectspeed&&(r.effect_speed=r.effectspeed,delete r.effectspeed),e.extend(s,r)),o=void 0===s.container||s.container===t?i:e(s.container),0===s.event.indexOf("scroll")&&o.bind(s.event,(function(){return l()})),this.each((function(){var t=this,n=e(t);t.loaded=!1,void 0!==n.attr("src")&&!1!==n.attr("src")||n.is("img")&&n.attr("src",s.placeholder),n.one("appear",(function(){if(!this.loaded){if(s.appear){var r=a.length;s.appear.call(t,r,s)}e("<img />").bind("load",(function(){var r=n.attr("data-"+s.data_attribute);n.hide(),n.is("img")?n.attr("src",r):n.css("background-image","url('"+r+"')"),n[s.effect](s.effect_speed),t.loaded=!0;var i=e.grep(a,(function(e){return!e.loaded}));if(a=e(i),s.load){var o=a.length;s.load.call(t,o,s)}})).attr("src",n.attr("data-"+s.data_attribute))}})),0!==s.event.indexOf("scroll")&&n.bind(s.event,(function(){t.loaded||n.trigger("appear")}))})),i.bind("resize",(function(){l()})),/(?:iphone|ipod|ipad).*os 5/gi.test(navigator.appVersion)&&i.bind("pageshow",(function(t){t.originalEvent&&t.originalEvent.persisted&&a.each((function(){e(this).trigger("appear")}))})),e(n).ready((function(){l()})),this},e.belowthefold=function(n,r){return(void 0===r.container||r.container===t?(t.innerHeight?t.innerHeight:i.height())+i.scrollTop():e(r.container).offset().top+e(r.container).height())<=e(n).offset().top-r.threshold},e.rightoffold=function(n,r){return(void 0===r.container||r.container===t?i.width()+i.scrollLeft():e(r.container).offset().left+e(r.container).width())<=e(n).offset().left-r.threshold},e.abovethetop=function(n,r){return(void 0===r.container||r.container===t?i.scrollTop():e(r.container).offset().top)>=e(n).offset().top+r.threshold+e(n).height()},e.leftofbegin=function(n,r){return(void 0===r.container||r.container===t?i.scrollLeft():e(r.container).offset().left)>=e(n).offset().left+r.threshold+e(n).width()},e.inviewport=function(t,n){return!(e.rightoffold(t,n)||e.leftofbegin(t,n)||e.belowthefold(t,n)||e.abovethetop(t,n))},e.extend(e.expr[":"],{"below-the-fold":function(t){return e.belowthefold(t,{threshold:0})},"above-the-top":function(t){return!e.belowthefold(t,{threshold:0})},"right-of-screen":function(t){return e.rightoffold(t,{threshold:0})},"left-of-screen":function(t){return!e.rightoffold(t,{threshold:0})},"in-viewport":function(t){return e.inviewport(t,{threshold:0})},"above-the-fold":function(t){return!e.belowthefold(t,{threshold:0})},"right-of-fold":function(t){return e.rightoffold(t,{threshold:0})},"left-of-fold":function(t){return!e.rightoffold(t,{threshold:0})}})}(jQuery,window,document)},hmhZ:function(e,t,n){var r,i;
/*!

Holder - client side image placeholders
Version 2.9.6+fblyy
© 2018 Ivan Malopinsky - http://imsky.co

Site:     http://holderjs.com
Issues:   https://github.com/imsky/holder/issues
License:  MIT

*/
!function(e){if(e.document){var t,n,r=e.document;r.querySelectorAll||(r.querySelectorAll=function(t){var n,i=r.createElement("style"),o=[];for(r.documentElement.firstChild.appendChild(i),r._qsa=[],i.styleSheet.cssText=t+"{x-qsa:expression(document._qsa && document._qsa.push(this))}",e.scrollBy(0,0),i.parentNode.removeChild(i);r._qsa.length;)(n=r._qsa.shift()).style.removeAttribute("x-qsa"),o.push(n);return r._qsa=null,o}),r.querySelector||(r.querySelector=function(e){var t=r.querySelectorAll(e);return t.length?t[0]:null}),r.getElementsByClassName||(r.getElementsByClassName=function(e){return e=String(e).replace(/^|\s+/g,"."),r.querySelectorAll(e)}),Object.keys||(Object.keys=function(e){if(e!==Object(e))throw TypeError("Object.keys called on non-object");var t,n=[];for(t in e)Object.prototype.hasOwnProperty.call(e,t)&&n.push(t);return n}),Array.prototype.forEach||(Array.prototype.forEach=function(e){if(null==this)throw TypeError();var t=Object(this),n=t.length>>>0;if("function"!=typeof e)throw TypeError();var r,i=arguments[1];for(r=0;r<n;r++)r in t&&e.call(i,t[r],r,t)}),n="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",(t=e).atob=t.atob||function(e){var t=0,r=[],i=0,o=0;if((e=(e=String(e)).replace(/\s/g,"")).length%4==0&&(e=e.replace(/=+$/,"")),e.length%4==1)throw Error("InvalidCharacterError");if(/[^+/0-9A-Za-z]/.test(e))throw Error("InvalidCharacterError");for(;t<e.length;)i=i<<6|n.indexOf(e.charAt(t)),24===(o+=6)&&(r.push(String.fromCharCode(i>>16&255)),r.push(String.fromCharCode(i>>8&255)),r.push(String.fromCharCode(255&i)),o=0,i=0),t+=1;return 12===o?(i>>=4,r.push(String.fromCharCode(255&i))):18===o&&(i>>=2,r.push(String.fromCharCode(i>>8&255)),r.push(String.fromCharCode(255&i))),r.join("")},t.btoa=t.btoa||function(e){e=String(e);var t,r,i,o,a,s,l,h=0,d=[];if(/[^\x00-\xFF]/.test(e))throw Error("InvalidCharacterError");for(;h<e.length;)o=(t=e.charCodeAt(h++))>>2,a=(3&t)<<4|(r=e.charCodeAt(h++))>>4,s=(15&r)<<2|(i=e.charCodeAt(h++))>>6,l=63&i,h===e.length+2?(s=64,l=64):h===e.length+1&&(l=64),d.push(n.charAt(o),n.charAt(a),n.charAt(s),n.charAt(l));return d.join("")},Object.prototype.hasOwnProperty||(Object.prototype.hasOwnProperty=function(e){var t=this.__proto__||this.constructor.prototype;return e in this&&(!(e in t)||t[e]!==this[e])}),
// @license http://opensource.org/licenses/MIT
function(){if("performance"in e==!1&&(e.performance={}),Date.now=Date.now||function(){return(new Date).getTime()},"now"in e.performance==!1){var t=Date.now();performance.timing&&performance.timing.navigationStart&&(t=performance.timing.navigationStart),e.performance.now=function(){return Date.now()-t}}}(),e.requestAnimationFrame||(e.webkitRequestAnimationFrame&&e.webkitCancelAnimationFrame?function(e){e.requestAnimationFrame=function(t){return webkitRequestAnimationFrame((function(){t(e.performance.now())}))},e.cancelAnimationFrame=e.webkitCancelAnimationFrame}(e):e.mozRequestAnimationFrame&&e.mozCancelAnimationFrame?function(e){e.requestAnimationFrame=function(t){return mozRequestAnimationFrame((function(){t(e.performance.now())}))},e.cancelAnimationFrame=e.mozCancelAnimationFrame}(e):function(e){e.requestAnimationFrame=function(t){return e.setTimeout(t,1e3/60)},e.cancelAnimationFrame=e.clearTimeout}(e))}}(this),r=function(){return function(e){var t={};function n(r){if(t[r])return t[r].exports;var i=t[r]={exports:{},id:r,loaded:!1};return e[r].call(i.exports,i,i.exports,n),i.loaded=!0,i.exports}return n.m=e,n.c=t,n.p="",n(0)}([function(e,t,n){e.exports=n(1)},function(e,t,n){(function(t){var r=n(2),i=n(3),o=n(6),a=n(7),s=n(8),l=n(9),h=n(10),d=n(11),c=n(12),u=n(15),f=a.extend,p=a.dimensionCheck,g=d.svg_ns,m={version:d.version,addTheme:function(e,t){return null!=e&&null!=t&&(v.settings.themes[e]=t),delete v.vars.cache.themeKeys,this},addImage:function(e,t){return l.getNodeArray(t).forEach((function(t){var n=l.newEl("img"),r={};r[v.setup.dataAttr]=e,l.setAttr(n,r),t.appendChild(n)})),this},setResizeUpdate:function(e,t){e.holderData&&(e.holderData.resizeUpdate=!!t,e.holderData.resizeUpdate&&S(e))},run:function(e){e=e||{};var n={},r=f(v.settings,e);v.vars.preempted=!0,v.vars.dataAttr=r.dataAttr||v.setup.dataAttr,n.renderer=r.renderer?r.renderer:v.setup.renderer,-1===v.setup.renderers.join(",").indexOf(n.renderer)&&(n.renderer=v.setup.supportsSVG?"svg":v.setup.supportsCanvas?"canvas":"html");var i=l.getNodeArray(r.images),o=l.getNodeArray(r.bgnodes),s=l.getNodeArray(r.stylenodes),h=l.getNodeArray(r.objects);return n.stylesheets=[],n.svgXMLStylesheet=!0,n.noFontFallback=!!r.noFontFallback,n.noBackgroundSize=!!r.noBackgroundSize,s.forEach((function(e){if(e.attributes.rel&&e.attributes.href&&"stylesheet"==e.attributes.rel.value){var t=e.attributes.href.value,r=l.newEl("a");r.href=t;var i=r.protocol+"//"+r.host+r.pathname+r.search;n.stylesheets.push(i)}})),o.forEach((function(e){if(t.getComputedStyle){var i=t.getComputedStyle(e,null).getPropertyValue("background-image"),o=e.getAttribute("data-background-src")||i,a=null,s=r.domain+"/",l=o.indexOf(s);if(0===l)a=o;else if(1===l&&"?"===o[0])a=o.slice(1);else{var h=o.substr(l).match(/([^\"]*)"?\)/);if(null!==h)a=h[1];else if(0===o.indexOf("url("))throw"Holder: unable to parse background URL: "+o}if(a){var d=w(a,r);d&&b({mode:"background",el:e,flags:d,engineSettings:n})}}})),h.forEach((function(e){var t={};try{t.data=e.getAttribute("data"),t.dataSrc=e.getAttribute(v.vars.dataAttr)}catch(e){}var i=null!=t.data&&0===t.data.indexOf(r.domain),o=null!=t.dataSrc&&0===t.dataSrc.indexOf(r.domain);i?y(r,n,t.data,e):o&&y(r,n,t.dataSrc,e)})),i.forEach((function(e){var t={};try{t.src=e.getAttribute("src"),t.dataSrc=e.getAttribute(v.vars.dataAttr),t.rendered=e.getAttribute("data-holder-rendered")}catch(e){}var i=null!=t.src,o=null!=t.dataSrc&&0===t.dataSrc.indexOf(r.domain),s=null!=t.rendered&&"true"==t.rendered;i?0===t.src.indexOf(r.domain)?y(r,n,t.src,e):o&&(s?y(r,n,t.dataSrc,e):function(e,t,n,r,i){a.imageExists(e,(function(e){e||y(t,n,r,i)}))}(t.src,r,n,t.dataSrc,e)):o&&y(r,n,t.dataSrc,e)})),this}},v={settings:{domain:"holder.js",images:"img",objects:"object",bgnodes:"body .holderjs",stylenodes:"head link.holderjs",themes:{gray:{bg:"#EEEEEE",fg:"#AAAAAA"},social:{bg:"#3a5a97",fg:"#FFFFFF"},industrial:{bg:"#434A52",fg:"#C2F200"},sky:{bg:"#0D8FDB",fg:"#FFFFFF"},vine:{bg:"#39DBAC",fg:"#1E292C"},lava:{bg:"#F8591A",fg:"#1C2846"}}},defaults:{size:10,units:"pt",scale:1/16}};function y(e,t,n,r){var i=w(n.substr(n.lastIndexOf(e.domain)),e);i&&b({mode:null,el:r,flags:i,engineSettings:t})}function w(e,t){var n={theme:f(v.settings.themes.gray,null),stylesheets:t.stylesheets,instanceOptions:t},r=e.indexOf("?"),o=[e];-1!==r&&(o=[e.slice(0,r),e.slice(r+1)]);var s=o[0].split("/");n.holderURL=e;var l=s[1],h=l.match(/([\d]+p?)x([\d]+p?)/);if(!h)return!1;if(n.fluid=-1!==l.indexOf("p"),n.dimensions={width:h[1].replace("p","%"),height:h[2].replace("p","%")},2===o.length){var d=i.parse(o[1]);if(a.truthy(d.ratio)){n.fluid=!0;var c=parseFloat(n.dimensions.width.replace("%","")),u=parseFloat(n.dimensions.height.replace("%",""));u=Math.floor(u/c*100),c=100,n.dimensions.width=c+"%",n.dimensions.height=u+"%"}if(n.auto=a.truthy(d.auto),d.bg&&(n.theme.bg=a.parseColor(d.bg)),d.fg&&(n.theme.fg=a.parseColor(d.fg)),d.bg&&!d.fg&&(n.autoFg=!0),d.theme&&n.instanceOptions.themes.hasOwnProperty(d.theme)&&(n.theme=f(n.instanceOptions.themes[d.theme],null)),d.text&&(n.text=d.text),d.textmode&&(n.textmode=d.textmode),d.size&&parseFloat(d.size)&&(n.size=parseFloat(d.size)),d.font&&(n.font=d.font),d.align&&(n.align=d.align),d.lineWrap&&(n.lineWrap=d.lineWrap),n.nowrap=a.truthy(d.nowrap),n.outline=a.truthy(d.outline),a.truthy(d.random)){v.vars.cache.themeKeys=v.vars.cache.themeKeys||Object.keys(n.instanceOptions.themes);var p=v.vars.cache.themeKeys[0|Math.random()*v.vars.cache.themeKeys.length];n.theme=f(n.instanceOptions.themes[p],null)}}return n}function b(e){var t=e.mode,n=e.el,r=e.flags,i=e.engineSettings,o=r.dimensions,s=r.theme,h=o.width+"x"+o.height;if(t=null==t?r.fluid?"fluid":"image":t,null!=r.text&&(s.text=r.text,"object"===n.nodeName.toLowerCase())){for(var d=s.text.split("\\n"),c=0;c<d.length;c++)d[c]=a.encodeHtmlEntity(d[c]);s.text=d.join("\\n")}if(s.text){var u=s.text.match(/holder_([a-z]+)/g);null!==u&&u.forEach((function(e){"holder_dimensions"===e&&(s.text=s.text.replace(e,h))}))}var g=r.holderURL,m=f(i,null);if(r.font&&(s.font=r.font,!m.noFontFallback&&"img"===n.nodeName.toLowerCase()&&v.setup.supportsCanvas&&"svg"===m.renderer&&(m=f(m,{renderer:"canvas"}))),r.font&&"canvas"==m.renderer&&(m.reRender=!0),"background"==t)null==n.getAttribute("data-background-src")&&l.setAttr(n,{"data-background-src":g});else{var y={};y[v.vars.dataAttr]=g,l.setAttr(n,y)}r.theme=s,n.holderData={flags:r,engineSettings:m},"image"!=t&&"fluid"!=t||l.setAttr(n,{alt:s.text?s.text+" ["+h+"]":h});var w={mode:t,el:n,holderSettings:{dimensions:o,theme:s,flags:r},engineSettings:m};"image"==t?(r.auto||(n.style.width=o.width+"px",n.style.height=o.height+"px"),"html"==m.renderer?n.style.backgroundColor=s.bg:(x(w),"exact"==r.textmode&&(n.holderData.resizeUpdate=!0,v.vars.resizableImages.push(n),S(n)))):"background"==t&&"html"!=m.renderer?x(w):"fluid"==t&&(n.holderData.resizeUpdate=!0,"%"==o.height.slice(-1)?n.style.height=o.height:null!=r.auto&&r.auto||(n.style.height=o.height+"px"),"%"==o.width.slice(-1)?n.style.width=o.width:null!=r.auto&&r.auto||(n.style.width=o.width+"px"),"inline"!=n.style.display&&""!==n.style.display&&"none"!=n.style.display||(n.style.display="block"),function(e){if(e.holderData){var t=p(e);if(t){var n=e.holderData.flags,r={fluidHeight:"%"==n.dimensions.height.slice(-1),fluidWidth:"%"==n.dimensions.width.slice(-1),mode:null,initialDimensions:t};r.fluidWidth&&!r.fluidHeight?(r.mode="width",r.ratio=r.initialDimensions.width/parseFloat(n.dimensions.height)):!r.fluidWidth&&r.fluidHeight&&(r.mode="height",r.ratio=parseFloat(n.dimensions.width)/r.initialDimensions.height),e.holderData.fluidConfig=r}else E(e)}}(n),"html"==m.renderer?n.style.backgroundColor=s.bg:(v.vars.resizableImages.push(n),S(n)))}function x(e){var n,r=e.mode,i=e.el,a=e.holderSettings,s=e.engineSettings;switch(s.renderer){case"svg":if(!v.setup.supportsSVG)return;break;case"canvas":if(!v.setup.supportsCanvas)return;break;default:return}var d={width:a.dimensions.width,height:a.dimensions.height,theme:a.theme,flags:a.flags},f=function(e){var t=v.defaults.size;switch(parseFloat(e.theme.size)?t=e.theme.size:parseFloat(e.flags.size)&&(t=e.flags.size),e.font={family:e.theme.font?e.theme.font:"Arial, Helvetica, Open Sans, sans-serif",size:A(e.width,e.height,t,v.defaults.scale),units:e.theme.units?e.theme.units:v.defaults.units,weight:e.theme.fontweight?e.theme.fontweight:"bold"},e.text=e.theme.text||Math.floor(e.width)+"x"+Math.floor(e.height),e.noWrap=e.theme.nowrap||e.flags.nowrap,e.align=e.theme.align||e.flags.align||"center",e.flags.textmode){case"literal":e.text=e.flags.dimensions.width+"x"+e.flags.dimensions.height;break;case"exact":if(!e.flags.exactDimensions)break;e.text=Math.floor(e.flags.exactDimensions.width)+"x"+Math.floor(e.flags.exactDimensions.height)}var n=e.flags.lineWrap||v.setup.lineWrapRatio,r=e.width*n,i=r,a=new o({width:e.width,height:e.height}),s=a.Shape,l=new s.Rect("holderBg",{fill:e.theme.bg});if(l.resize(e.width,e.height),a.root.add(l),e.flags.outline){var d=new h(l.properties.fill);d=d.lighten(d.lighterThan("7f7f7f")?-.1:.1),l.properties.outline={fill:d.toHex(!0),width:2}}var c=e.theme.fg;if(e.flags.autoFg){var u=new h(l.properties.fill),f=new h("fff"),p=new h("000",{alpha:.285714});c=u.blendAlpha(u.lighterThan("7f7f7f")?p:f).toHex(!0)}var g=new s.Group("holderTextGroup",{text:e.text,align:e.align,font:e.font,fill:c});g.moveTo(null,null,1),a.root.add(g);var m=g.textPositionData=z(a);if(!m)throw"Holder: staging fallback not supported yet.";g.properties.leading=m.boundingBox.height;var y=null,w=null;function b(e,t,n,r){t.width=n,t.height=r,e.width=Math.max(e.width,t.width),e.height+=t.height}if(m.lineCount>1){var x,S=0,C=0,E=0;w=new s.Group("line"+E),"left"!==e.align&&"right"!==e.align||(i=e.width*(1-2*(1-n)));for(var k=0;k<m.words.length;k++){var T=m.words[k];y=new s.Text(T.text);var F="\\n"==T.text;!e.noWrap&&(S+T.width>=i||!0===F)&&(b(g,w,S,g.properties.leading),g.add(w),S=0,C+=g.properties.leading,E+=1,(w=new s.Group("line"+E)).y=C),!0!==F&&(y.moveTo(S,0),S+=m.spaceWidth+T.width,w.add(y))}if(b(g,w,S,g.properties.leading),g.add(w),"left"===e.align)g.moveTo(e.width-r,null,null);else if("right"===e.align){for(x in g.children)(w=g.children[x]).moveTo(e.width-w.width,null,null);g.moveTo(0-(e.width-r),null,null)}else{for(x in g.children)(w=g.children[x]).moveTo((g.width-w.width)/2,null,null);g.moveTo((e.width-g.width)/2,null,null)}g.moveTo(null,(e.height-g.height)/2,null),(e.height-g.height)/2<0&&g.moveTo(null,0,null)}else y=new s.Text(e.text),(w=new s.Group("line0")).add(y),g.add(w),"left"===e.align?g.moveTo(e.width-r,null,null):"right"===e.align?g.moveTo(0-(e.width-r),null,null):g.moveTo((e.width-m.boundingBox.width)/2,null,null),g.moveTo(null,(e.height-m.boundingBox.height)/2,null);return a}(d);function p(){var t=null;switch(s.renderer){case"canvas":t=u(f,e);break;case"svg":t=c(f,e);break;default:throw"Holder: invalid renderer: "+s.renderer}return t}if(null==(n=p()))throw"Holder: couldn't render placeholder";"background"==r?(i.style.backgroundImage="url("+n+")",s.noBackgroundSize||(i.style.backgroundSize=d.width+"px "+d.height+"px")):("img"===i.nodeName.toLowerCase()?l.setAttr(i,{src:n}):"object"===i.nodeName.toLowerCase()&&l.setAttr(i,{data:n,type:"image/svg+xml"}),s.reRender&&t.setTimeout((function(){var e=p();if(null==e)throw"Holder: couldn't render placeholder";"img"===i.nodeName.toLowerCase()?l.setAttr(i,{src:e}):"object"===i.nodeName.toLowerCase()&&l.setAttr(i,{data:e,type:"image/svg+xml"})}),150)),l.setAttr(i,{"data-holder-rendered":!0})}function A(e,t,n,r){var i=parseInt(e,10),o=parseInt(t,10),a=Math.max(i,o),s=Math.min(i,o),l=.8*Math.min(s,a*r);return Math.round(Math.max(n,l))}function S(e){for(var t,n=0,r=(t=null==e||null==e.nodeType?v.vars.resizableImages:[e]).length;n<r;n++){var i=t[n];if(i.holderData){var o=i.holderData.flags,a=p(i);if(a){if(!i.holderData.resizeUpdate)continue;if(o.fluid&&o.auto){var s=i.holderData.fluidConfig;switch(s.mode){case"width":a.height=a.width/s.ratio;break;case"height":a.width=a.height*s.ratio}}var l={mode:"image",holderSettings:{dimensions:a,theme:o.theme,flags:o},el:i,engineSettings:i.holderData.engineSettings};"exact"==o.textmode&&(o.exactDimensions=a,l.holderSettings.dimensions=o.dimensions),x(l)}else E(i)}}}function C(){var e,n=[];Object.keys(v.vars.invisibleImages).forEach((function(t){e=v.vars.invisibleImages[t],p(e)&&"img"==e.nodeName.toLowerCase()&&(n.push(e),delete v.vars.invisibleImages[t])})),n.length&&m.run({images:n}),setTimeout((function(){t.requestAnimationFrame(C)}),10)}function E(e){e.holderData.invisibleId||(v.vars.invisibleId+=1,v.vars.invisibleImages["i"+v.vars.invisibleId]=e,e.holderData.invisibleId=v.vars.invisibleId)}var k,T,F,O,z=(k=null,T=null,F=null,function(e){var t,n=e.root;if(v.setup.supportsSVG){var r=!1;null!=k&&k.parentNode===document.body||(r=!0),(k=s.initSVG(k,n.properties.width,n.properties.height)).style.display="block",r&&(T=l.newEl("text",g),t=null,F=document.createTextNode(t),l.setAttr(T,{x:0}),T.appendChild(F),k.appendChild(T),document.body.appendChild(k),k.style.visibility="hidden",k.style.position="absolute",k.style.top="-100%",k.style.left="-100%");var i=n.children.holderTextGroup.properties;l.setAttr(T,{y:i.font.size,style:a.cssProps({"font-weight":i.font.weight,"font-size":i.font.size+i.font.units,"font-family":i.font.family})});var o=l.newEl("textarea");o.innerHTML=i.text,F.nodeValue=o.value;var h=T.getBBox(),d=Math.ceil(h.width/n.properties.width),c=i.text.split(" "),u=i.text.match(/\\n/g);d+=null==u?0:u.length,F.nodeValue=i.text.replace(/[ ]+/g,"");var f=T.getComputedTextLength(),p=h.width-f,m=Math.round(p/Math.max(1,c.length-1)),y=[];if(d>1){F.nodeValue="";for(var w=0;w<c.length;w++)if(0!==c[w].length){F.nodeValue=a.decodeHtmlEntity(c[w]);var b=T.getBBox();y.push({text:c[w],width:b.width})}}return k.style.display="none",{spaceWidth:m,lineCount:d,boundingBox:h,words:y}}return!1});function j(){!function(e){v.vars.debounceTimer||e.call(this),v.vars.debounceTimer&&t.clearTimeout(v.vars.debounceTimer),v.vars.debounceTimer=t.setTimeout((function(){v.vars.debounceTimer=null,e.call(this)}),v.setup.debounce)}((function(){S(null)}))}for(var D in v.flags)v.flags.hasOwnProperty(D)&&(v.flags[D].match=function(e){return e.match(this.regex)});v.setup={renderer:"html",debounce:100,ratio:1,supportsCanvas:!1,supportsSVG:!1,lineWrapRatio:.9,dataAttr:"data-src",renderers:["html","canvas","svg"]},v.vars={preempted:!1,resizableImages:[],invisibleImages:{},invisibleId:0,visibilityCheckStarted:!1,debounceTimer:null,cache:{}},(O=l.newEl("canvas")).getContext&&-1!=O.toDataURL("image/png").indexOf("data:image/png")&&(v.setup.renderer="canvas",v.setup.supportsCanvas=!0),document.createElementNS&&document.createElementNS(g,"svg").createSVGRect&&(v.setup.renderer="svg",v.setup.supportsSVG=!0),v.vars.visibilityCheckStarted||(t.requestAnimationFrame(C),v.vars.visibilityCheckStarted=!0),r&&r((function(){v.vars.preempted||m.run(),t.addEventListener?(t.addEventListener("resize",j,!1),t.addEventListener("orientationchange",j,!1)):t.attachEvent("onresize",j),"object"==typeof t.Turbolinks&&t.document.addEventListener("page:change",(function(){m.run()}))})),e.exports=m}).call(t,function(){return this}())},function(e,t){e.exports="undefined"!=typeof window&&
/*!
	 * onDomReady.js 1.4.0 (c) 2013 Tubal Martin - MIT license
	 *
	 * Specially modified to work with Holder.js
	 */
function(e){null==document.readyState&&document.addEventListener&&(document.addEventListener("DOMContentLoaded",(function e(){document.removeEventListener("DOMContentLoaded",e,!1),document.readyState="complete"}),!1),document.readyState="loading");var t=e.document,n=t.documentElement,r="addEventListener"in t,i=!1,o=!1,a=[];function s(e){if(!o){if(!t.body)return d(s);for(o=!0;e=a.shift();)d(e)}}function l(e){(r||"load"===e.type||"complete"===t.readyState)&&(h(),s())}function h(){r?(t.removeEventListener("DOMContentLoaded",l,!1),e.removeEventListener("load",l,!1)):(t.detachEvent("onreadystatechange",l),e.detachEvent("onload",l))}function d(e,t){setTimeout(e,+t>=0?t:1)}if("complete"===t.readyState)d(s);else if(r)t.addEventListener("DOMContentLoaded",l,!1),e.addEventListener("load",l,!1);else{t.attachEvent("onreadystatechange",l),e.attachEvent("onload",l);try{i=null==e.frameElement&&n}catch(e){}i&&i.doScroll&&function e(){if(!o){try{i.doScroll("left")}catch(t){return d(e,50)}h(),s()}}()}function c(e){o?d(e):a.push(e)}return c.version="1.4.0",c.isReady=function(){return o},c}(window)},function(e,t,n){var r=encodeURIComponent,i=decodeURIComponent,o=n(4),a=n(5),s=/(\w+)\[(\d+)\]/,l=/\w+\.\w+/;t.parse=function(e){if("string"!=typeof e)return{};if(""===(e=o(e)))return{};"?"===e.charAt(0)&&(e=e.slice(1));for(var t={},n=e.split("&"),r=0;r<n.length;r++){var a,h,d,c=n[r].split("="),u=i(c[0]);if(a=s.exec(u))t[a[1]]=t[a[1]]||[],t[a[1]][a[2]]=i(c[1]);else if(a=l.test(u)){for(a=u.split("."),h=t;a.length;)if((d=a.shift()).length){if(h[d]){if(h[d]&&"object"!=typeof h[d])break}else h[d]={};a.length||(h[d]=i(c[1])),h=h[d]}}else t[c[0]]=null==c[1]?"":i(c[1])}return t},t.stringify=function(e){if(!e)return"";var t=[];for(var n in e){var i=e[n];if("array"!=a(i))t.push(r(n)+"="+r(e[n]));else for(var o=0;o<i.length;++o)t.push(r(n+"["+o+"]")+"="+r(i[o]))}return t.join("&")}},function(e,t){(t=e.exports=function(e){return e.replace(/^\s*|\s*$/g,"")}).left=function(e){return e.replace(/^\s*/,"")},t.right=function(e){return e.replace(/\s*$/,"")}},function(e,t){var n=Object.prototype.toString;e.exports=function(e){switch(n.call(e)){case"[object Date]":return"date";case"[object RegExp]":return"regexp";case"[object Arguments]":return"arguments";case"[object Array]":return"array";case"[object Error]":return"error"}return null===e?"null":void 0===e?"undefined":e!=e?"nan":e&&1===e.nodeType?"element":null!=(t=e)&&(t._isBuffer||t.constructor&&"function"==typeof t.constructor.isBuffer&&t.constructor.isBuffer(t))?"buffer":typeof(e=e.valueOf?e.valueOf():Object.prototype.valueOf.apply(e));var t}},function(e,t){e.exports=function(e){var t=1,n=function(e){t++,this.parent=null,this.children={},this.id=t,this.name="n"+t,void 0!==e&&(this.name=e),this.x=this.y=this.z=0,this.width=this.height=0};n.prototype.resize=function(e,t){null!=e&&(this.width=e),null!=t&&(this.height=t)},n.prototype.moveTo=function(e,t,n){this.x=null!=e?e:this.x,this.y=null!=t?t:this.y,this.z=null!=n?n:this.z},n.prototype.add=function(e){var t=e.name;if(void 0!==this.children[t])throw"SceneGraph: child already exists: "+t;this.children[t]=e,e.parent=this};var r=function(){n.call(this,"root"),this.properties=e};r.prototype=new n;var i=function(e,t){if(n.call(this,e),this.properties={fill:"#000000"},void 0!==t)!function(e,t){for(var n in t)e[n]=t[n]}(this.properties,t);else if(void 0!==e&&"string"!=typeof e)throw"SceneGraph: invalid node name"};i.prototype=new n;var o=function(){i.apply(this,arguments),this.type="group"};o.prototype=new i;var a=function(){i.apply(this,arguments),this.type="rect"};a.prototype=new i;var s=function(e){i.call(this),this.type="text",this.properties.text=e};s.prototype=new i;var l=new r;return this.Shape={Rect:a,Text:s,Group:o},this.root=l,this}},function(e,t){(function(e){t.extend=function(e,t){var n={};for(var r in e)e.hasOwnProperty(r)&&(n[r]=e[r]);if(null!=t)for(var i in t)t.hasOwnProperty(i)&&(n[i]=t[i]);return n},t.cssProps=function(e){var t=[];for(var n in e)e.hasOwnProperty(n)&&t.push(n+":"+e[n]);return t.join(";")},t.encodeHtmlEntity=function(e){for(var t=[],n=0,r=e.length-1;r>=0;r--)(n=e.charCodeAt(r))>128?t.unshift(["&#",n,";"].join("")):t.unshift(e[r]);return t.join("")},t.imageExists=function(e,t){var n=new Image;n.onerror=function(){t.call(this,!1)},n.onload=function(){t.call(this,!0)},n.src=e},t.decodeHtmlEntity=function(e){return e.replace(/&#(\d+);/g,(function(e,t){return String.fromCharCode(t)}))},t.dimensionCheck=function(e){var t={height:e.clientHeight,width:e.clientWidth};return!(!t.height||!t.width)&&t},t.truthy=function(e){return"string"==typeof e?"true"===e||"yes"===e||"1"===e||"on"===e||"✓"===e:!!e},t.parseColor=function(e){var t,n=e.match(/(^(?:#?)[0-9a-f]{6}$)|(^(?:#?)[0-9a-f]{3}$)/i);return null!==n?"#"!==(t=n[1]||n[2])[0]?"#"+t:t:null!==(n=e.match(/^rgb\((\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/))?t="rgb("+n.slice(1).join(",")+")":null!==(n=e.match(/^rgba\((\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0\.\d{1,}|1)\)$/))?t="rgba("+n.slice(1).join(",")+")":null},t.canvasRatio=function(){var t=1,n=1;if(e.document){var r=e.document.createElement("canvas");if(r.getContext){var i=r.getContext("2d");t=e.devicePixelRatio||1,n=i.webkitBackingStorePixelRatio||i.mozBackingStorePixelRatio||i.msBackingStorePixelRatio||i.oBackingStorePixelRatio||i.backingStorePixelRatio||1}}return t/n}}).call(t,function(){return this}())},function(e,t,n){(function(e){var r=n(9),i="http://www.w3.org/2000/svg";t.initSVG=function(e,t,n){var o,a,s=!1;e&&e.querySelector?null===(a=e.querySelector("style"))&&(s=!0):(e=r.newEl("svg",i),s=!0),s&&(o=r.newEl("defs",i),a=r.newEl("style",i),r.setAttr(a,{type:"text/css"}),o.appendChild(a),e.appendChild(o)),e.webkitMatchesSelector&&e.setAttribute("xmlns",i);for(var l=0;l<e.childNodes.length;l++)8===e.childNodes[l].nodeType&&e.removeChild(e.childNodes[l]);for(;a.childNodes.length;)a.removeChild(a.childNodes[0]);return r.setAttr(e,{width:t,height:n,viewBox:"0 0 "+t+" "+n,preserveAspectRatio:"none"}),e},t.svgStringToDataURI=function(t,n){return n?"data:image/svg+xml;charset=UTF-8;base64,"+btoa(e.unescape(encodeURIComponent(t))):"data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(t)},t.serializeSVG=function(t,n){if(e.XMLSerializer){var i=new XMLSerializer,o="",a=n.stylesheets;if(n.svgXMLStylesheet){for(var s=r.createXML(),l=a.length-1;l>=0;l--){var h=s.createProcessingInstruction("xml-stylesheet",'href="'+a[l]+'" rel="stylesheet"');s.insertBefore(h,s.firstChild)}s.removeChild(s.documentElement),o=i.serializeToString(s)}var d=i.serializeToString(t);return o+(d=d.replace(/\&amp;(\#[0-9]{2,}\;)/g,"&$1"))}}}).call(t,function(){return this}())},function(e,t){(function(e){t.newEl=function(t,n){if(e.document)return null==n?e.document.createElement(t):e.document.createElementNS(n,t)},t.setAttr=function(e,t){for(var n in t)e.setAttribute(n,t[n])},t.createXML=function(){if(e.DOMParser)return(new DOMParser).parseFromString("<xml />","application/xml")},t.getNodeArray=function(t){var n=null;return"string"==typeof t?n=document.querySelectorAll(t):e.NodeList&&t instanceof e.NodeList?n=t:e.Node&&t instanceof e.Node?n=[t]:e.HTMLCollection&&t instanceof e.HTMLCollection?n=t:t instanceof Array?n=t:null===t&&(n=[]),n=Array.prototype.slice.call(n)}}).call(t,function(){return this}())},function(e,t){var n=function(e,t){"string"==typeof e&&(this.original=e,"#"===e.charAt(0)&&(e=e.slice(1)),/[^a-f0-9]+/i.test(e)||(3===e.length&&(e=e.replace(/./g,"$&$&")),6===e.length&&(this.alpha=1,t&&t.alpha&&(this.alpha=t.alpha),this.set(parseInt(e,16)))))};n.rgb2hex=function(e,t,n){return[e,t,n].map((function(e){var t=(0|e).toString(16);return e<16&&(t="0"+t),t})).join("")},n.hsl2rgb=function(e,t,n){var r=e/60,i=(1-Math.abs(2*n-1))*t,o=i*(1-Math.abs(parseInt(r)%2-1)),a=n-i/2,s=0,l=0,h=0;return r>=0&&r<1?(s=i,l=o):r>=1&&r<2?(s=o,l=i):r>=2&&r<3?(l=i,h=o):r>=3&&r<4?(l=o,h=i):r>=4&&r<5?(s=o,h=i):r>=5&&r<6&&(s=i,h=o),s+=a,l+=a,h+=a,[s=parseInt(255*s),l=parseInt(255*l),h=parseInt(255*h)]},n.prototype.set=function(e){this.raw=e;var t=(16711680&this.raw)>>16,n=(65280&this.raw)>>8,r=255&this.raw,i=.2126*t+.7152*n+.0722*r,o=-.09991*t-.33609*n+.436*r,a=.615*t-.55861*n-.05639*r;return this.rgb={r:t,g:n,b:r},this.yuv={y:i,u:o,v:a},this},n.prototype.lighten=function(e){var t=Math.min(1,Math.max(0,Math.abs(e)))*(e<0?-1:1)*255|0,r=Math.min(255,Math.max(0,this.rgb.r+t)),i=Math.min(255,Math.max(0,this.rgb.g+t)),o=Math.min(255,Math.max(0,this.rgb.b+t)),a=n.rgb2hex(r,i,o);return new n(a)},n.prototype.toHex=function(e){return(e?"#":"")+this.raw.toString(16)},n.prototype.lighterThan=function(e){return e instanceof n||(e=new n(e)),this.yuv.y>e.yuv.y},n.prototype.blendAlpha=function(e){e instanceof n||(e=new n(e));var t=e,r=t.alpha*t.rgb.r+(1-t.alpha)*this.rgb.r,i=t.alpha*t.rgb.g+(1-t.alpha)*this.rgb.g,o=t.alpha*t.rgb.b+(1-t.alpha)*this.rgb.b;return new n(n.rgb2hex(r,i,o))},e.exports=n},function(e,t){e.exports={version:"2.9.6",svg_ns:"http://www.w3.org/2000/svg"}},function(e,t,n){var r=n(13),i=n(8),o=n(11),a=n(7),s=o.svg_ns,l=function(e){var t=e.tag,n=e.content||"";return delete e.tag,delete e.content,[t,n,e]};e.exports=function(e,t){var n,o=t.engineSettings.stylesheets.map((function(e){return'<?xml-stylesheet rel="stylesheet" href="'+e+'"?>'})).join("\n"),h="holder_"+Number(new Date).toString(16),d=e.root,c=d.children.holderTextGroup,u="#"+h+" text { "+(n=c.properties,a.cssProps({fill:n.fill,"font-weight":n.font.weight,"font-family":n.font.family+", monospace","font-size":n.font.size+n.font.units}))+" } ";c.y+=.8*c.textPositionData.boundingBox.height;var f=[];Object.keys(c.children).forEach((function(e){var t=c.children[e];Object.keys(t.children).forEach((function(e){var n=t.children[e],r=c.x+t.x+n.x,i=c.y+t.y+n.y,o=l({tag:"text",content:n.properties.text,x:r,y:i});f.push(o)}))}));var p,g,m,v,y=l({tag:"g",content:f}),w=null;if(d.children.holderBg.properties.outline){var b=d.children.holderBg.properties.outline;w=l({tag:"path",d:(p=d.children.holderBg.width,g=d.children.holderBg.height,m=b.width,v=m/2,["M",v,v,"H",p-v,"V",g-v,"H",v,"V",0,"M",0,v,"L",p,g-v,"M",0,g-v,"L",p,v].join(" ")),"stroke-width":b.width,stroke:b.fill,fill:"none"})}var x,A=(x=d.children.holderBg,l({tag:"rect",width:x.width,height:x.height,fill:x.properties.fill})),S=[];S.push(A),b&&S.push(w),S.push(y);var C=l({tag:"g",id:h,content:S}),E=l({tag:"style",content:u,type:"text/css"}),k=l({tag:"defs",content:E}),T=l({tag:"svg",content:[k,C],width:d.properties.width,height:d.properties.height,xmlns:s,viewBox:[0,0,d.properties.width,d.properties.height].join(" "),preserveAspectRatio:"none"}),F=r(T);return/\&amp;(x)?#[0-9A-Fa-f]/.test(F[0])&&(F[0]=F[0].replace(/&amp;#/gm,"&#")),F=o+F[0],i.svgStringToDataURI(F,"background"===t.mode)}},function(e,t,n){n(14),e.exports=function e(t,n,r){"use strict";var i,o,a,s,l,h,d,c,u,f,p,g=1,m=!0;function v(e,t){if(null!==t&&!1!==t&&void 0!==t)return"string"!=typeof t&&"object"!=typeof t?String(t):t}function y(e){return e||0===e?String(e).replace(/&/g,"&amp;").replace(/"/g,"&quot;"):""}if(r=r||{},"string"==typeof t[0])t[0]=(l=t[0],h=l.match(/^[\w-]+/),d={tag:h?h[0]:"div",attr:{},children:[]},c=l.match(/#([\w-]+)/),u=l.match(/\$([\w-]+)/),f=l.match(/\.[\w-]+/g),c&&(d.attr.id=c[1],r[c[1]]=d),u&&(r[u[1]]=d),f&&(d.attr.class=f.join(" ").replace(/\./g,"")),l.match(/&$/g)&&(m=!1),d);else{if(!Array.isArray(t[0]))throw new Error("First element of array must be a string, or an array and not "+JSON.stringify(t[0]));g=0}for(;g<t.length;g++){if(!1===t[g]||null===t[g]){t[0]=!1;break}if(void 0!==t[g]&&!0!==t[g])if("string"==typeof t[g])m&&(t[g]=(p=t[g],String(p).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&apos;").replace(/</g,"&lt;").replace(/>/g,"&gt;"))),t[0].children.push(t[g]);else if("number"==typeof t[g])t[0].children.push(t[g]);else if(Array.isArray(t[g])){if(Array.isArray(t[g][0])){if(t[g].reverse().forEach((function(e){t.splice(g+1,0,e)})),0!==g)continue;g++}e(t[g],n,r),t[g][0]&&t[0].children.push(t[g][0])}else if("function"==typeof t[g])a=t[g];else{if("object"!=typeof t[g])throw new TypeError('"'+t[g]+'" is not allowed as a value.');for(o in t[g])t[g].hasOwnProperty(o)&&null!==t[g][o]&&!1!==t[g][o]&&("style"===o&&"object"==typeof t[g][o]?t[0].attr[o]=JSON.stringify(t[g][o],v).slice(2,-2).replace(/","/g,";").replace(/":"/g,":").replace(/\\"/g,"'"):t[0].attr[o]=t[g][o])}}if(!1!==t[0]){for(s in i="<"+t[0].tag,t[0].attr)t[0].attr.hasOwnProperty(s)&&(i+=" "+s+'="'+y(t[0].attr[s])+'"');i+=">",t[0].children.forEach((function(e){i+=e})),i+="</"+t[0].tag+">",t[0]=i}return r[0]=t[0],a&&a(t[0]),r}},function(e,t){
/*!
	 * escape-html
	 * Copyright(c) 2012-2013 TJ Holowaychuk
	 * Copyright(c) 2015 Andreas Lubbe
	 * Copyright(c) 2015 Tiancheng "Timothy" Gu
	 * MIT Licensed
	 */
"use strict";var n=/["'&<>]/;e.exports=function(e){var t,r=""+e,i=n.exec(r);if(!i)return r;var o="",a=0,s=0;for(a=i.index;a<r.length;a++){switch(r.charCodeAt(a)){case 34:t="&quot;";break;case 38:t="&amp;";break;case 39:t="&#39;";break;case 60:t="&lt;";break;case 62:t="&gt;";break;default:continue}s!==a&&(o+=r.substring(s,a)),s=a+1,o+=t}return s!==a?o+r.substring(s,a):o}},function(e,t,n){var r,i,o=n(9),a=n(7);e.exports=(r=o.newEl("canvas"),i=null,function(e){null==i&&(i=r.getContext("2d"));var t=a.canvasRatio(),n=e.root;r.width=t*n.properties.width,r.height=t*n.properties.height,i.textBaseline="middle";var o=n.children.holderBg,s=t*o.width,l=t*o.height;i.fillStyle=o.properties.fill,i.fillRect(0,0,s,l),o.properties.outline&&(i.strokeStyle=o.properties.outline.fill,i.lineWidth=o.properties.outline.width,i.moveTo(1,1),i.lineTo(s-1,1),i.lineTo(s-1,l-1),i.lineTo(1,l-1),i.lineTo(1,1),i.moveTo(0,1),i.lineTo(s,l-1),i.moveTo(0,l-1),i.lineTo(s,1),i.stroke());var h=n.children.holderTextGroup;for(var d in i.font=h.properties.font.weight+" "+t*h.properties.font.size+h.properties.font.units+" "+h.properties.font.family+", monospace",i.fillStyle=h.properties.fill,h.children){var c=h.children[d];for(var u in c.children){var f=c.children[u],p=t*(h.x+c.x+f.x),g=t*(h.y+c.y+f.y+h.properties.leading/2);i.fillText(f.properties.text,p,g)}}return r.toDataURL("image/png")})}])},e.exports=r(),i=this,"undefined"!=typeof Meteor&&"undefined"!=typeof Package&&(Holder=i.Holder)}}]);