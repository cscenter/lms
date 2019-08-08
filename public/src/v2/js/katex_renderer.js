import katex from "katex";
import renderMathInElement from "katex/dist/contrib/auto-render.js";

let katexOptions = {
    delimiters: [
        {left: "$$", right: "$$", display: true},
        {left: "\\[", right: "\\]", display: true},
        {left: "$", right: "$", display: false},
        {left: "\\(", right: "\\)", display: false}
    ]
};

export function renderMath(domElement, options=null) {
    if (options === null) {
        options = {};
    }
    var html = katex.renderToString("c = \\pm\\sqrt{a^2 + b^2}", {
        throwOnError: false
    });
    console.log(html);

    renderMathInElement(domElement, {...katexOptions, ...options});
}
