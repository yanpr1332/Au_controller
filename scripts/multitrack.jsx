#target audition
function AuCtl_findMultitrack(){
    for(var i=0;i<app.documents.length;i++){
        if(app.documents[i].reflect.name=="MultitrackDocument") return app.documents[i];
    }
    return null;
}
function AuCtl_track(index){
    var mt=AuCtl_findMultitrack(); if(!mt) throw "No MultitrackDocument";
    mt.activate(); return mt.audioTracks[index];
}
function AuCtl_moveClip(trackIndex,clipIndex,startSamples){
    var c=AuCtl_track(trackIndex).audioClips[clipIndex];
    c.startTime=startSamples; return c.startTime;
}
