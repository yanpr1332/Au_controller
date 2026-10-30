(function () {
    "use strict";
    var session = String(Date.now()) + "_" + String(Math.floor(Math.random() * 1000000));
    var sequence = 0;
    function record(stage, detail) {
        var bridge = window.__adobe_cep__;
        if (!bridge || typeof bridge.evalScript !== "function") { return; }
        var body = document.body;
        var computed = body ? window.getComputedStyle(body) : null;
        var data = {
            stage: stage, detail: String(detail || ""), readyState: document.readyState,
            width: window.innerWidth, height: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio,
            bodyWidth: body ? body.clientWidth : null,
            bodyHeight: body ? body.clientHeight : null,
            background: computed ? computed.backgroundColor : null,
            visibility: computed ? computed.visibility : null
        };
        var path = "D:/computer/Adobe/Audition/Au_controller/tests/receipts/cep_page_" + session + "_" + (++sequence) + ".json";
        var script = '(function(){try{var f=new File(' + JSON.stringify(path) + ');' +
            'f.encoding="UTF8";if(!f.open("w"))return "OPEN_FAILED";' +
            'f.write(' + JSON.stringify(JSON.stringify(data)) + ');f.close();return "RECORDED";' +
            '}catch(e){return "ERROR:"+e;}})()';
        try { bridge.evalScript(script, function (result) {
            if (window.console) { console.log("Inspector diagnostic " + stage + ": " + result); }
        }); } catch (error) { if (window.console) { console.error(error); } }
    }
    window.addEventListener("error", function (event) { record("error", event.message); });
    document.addEventListener("DOMContentLoaded", function () {
        record("dom-ready");
        var bridge = window.__adobe_cep__;
        if ((!window.innerWidth || !window.innerHeight) && bridge && typeof bridge.resizeContent === "function") {
            try {
                bridge.resizeContent(540, 440);
                window.setTimeout(function () { record("after-content-resize"); }, 500);
            } catch (error) { record("resize-error", error.message); }
        }
        // One bounded reflow/repaint request; does not imply native presentation succeeded.
        document.body.style.transform = "translateZ(0)";
        window.requestAnimationFrame(function () {
            document.body.style.transform = "none";
            record("repaint-requested");
        });
    });
    window.addEventListener("load", function () { record("loaded"); });
    window.addEventListener("resize", function () { record("resized"); });
}());
