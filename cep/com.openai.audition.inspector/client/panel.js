(function(){
"use strict";
const target=document.getElementById("result");
function run(src){
 const api=window.__adobe_cep__;
 if(!api||typeof api.evalScript!=="function"){target.textContent="Not running in an Adobe CEP host";return;}
 api.evalScript(src,function(value){target.textContent=String(value);});
}
document.getElementById("status").addEventListener("click",function(){
 run('(function(){var active="none";if(app.documents.length>0){try{active=app.activeDocument.displayName;}catch(e){active="unavailable";}}return "Audition "+app.version+" | open docs="+app.documents.length+" | active="+active;})()');
});
document.getElementById("dictionary").addEventListener("click",function(){
 run('(function(){var o=app,refl=o.reflect,a=[];for(var i=0;i<refl.methods.length;i++)a.push(refl.methods[i].name);return "Application methods:\\n"+a.join("\\n");})()');
});
document.getElementById("commands").addEventListener("click",function(){
 run('(function(){var a=["Edit.SelectAll","Edit.Copy","File.Save","File.SaveAs","Edit.InsertIntoNewSession"];var o=[];for(var i=0;i<a.length;i++){try{o.push(a[i]+" = "+app.isCommandEnabled(a[i]));}catch(e){o.push(a[i]+" : "+e);}}return o.join("\\n");})()');
});
target.textContent="CEP interface staged; host installation and launch not yet tested.";
})();
/* Read-only host-load receipt for Audition 26 CEP integration verification.
   No files or projects are changed except this fixed QA receipt path. */
(function () {
    "use strict";
    var bridge = window.__adobe_cep__;
    if (!bridge || typeof bridge.evalScript !== "function") { return; }
    var jsx = '(function(){try{' +
        'var f=new File("D:/computer/Adobe/Audition/Au_controller/tests/receipts/phase04_cep_host_loaded.txt");' +
        'f.encoding="UTF8";if(!f.open("w"))return "FILE_OPEN_FAILED";' +
        'f.writeln("HOST="+app.name);f.writeln("VERSION="+app.version);' +
        'f.writeln("DOCUMENTS="+app.documents.length);' +
        'f.writeln("REFLECT_CLASS="+app.reflect.name);' +
        'f.close();return "HOST_RECIPT_CREATED";' +
        '}catch(e){return "ERROR:"+e;}})()';
    bridge.evalScript(jsx, function (value) {
        document.getElementById("result").textContent =
          "CEP host handshake: " + String(value);
    });
})();
