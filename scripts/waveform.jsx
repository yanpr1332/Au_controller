#target audition
function AuCtl_activeWave(){
    var d=app.activeDocument;
    if(!d || d.reflect.name!="WaveDocument") throw "Active document is not WaveDocument";
    return d;
}
function AuCtl_openWave(path){
    return app.openDocument(new DocumentOpenParameter(path));
}
function AuCtl_addMarker(start,duration,name,type,description){
    return AuCtl_activeWave().addMarker(start,duration,name,type||"Cue",description||"");
}
function AuCtl_setPlayhead(samples){
    var d=AuCtl_activeWave(); d.playheadPosition=samples; return d.playheadPosition;
}
