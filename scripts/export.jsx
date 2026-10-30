#target audition
function AuCtl_saveWave(path){
    return AuCtl_activeWave().saveAs(path,true);
}
function AuCtl_saveConvertedWave(path,sampleRate,bitDepth){
    var d=AuCtl_activeWave();
    var sp=new WaveDocumentSaveAsParameters();
    var cv=new SampleTypeConvertParameters();
    cv.sampleRate=sampleRate;
    cv.bitDepth=bitDepth;
    cv.resampleQuality=100;
    cv.useDithering=true;
    sp.sampleTypeConversion=cv;
    return d.saveAsDocument(path,sp);
}
