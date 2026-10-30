#target audition
function AuCtl_batchFavorite(paths,favorite,outDir,suffix){
    var folder=new Folder(outDir); if(!folder.exists) folder.create();
    var count=0;
    for(var i=0;i<paths.length;i++){
        app.openDocument(new DocumentOpenParameter(paths[i]));
        var d=app.activeDocument;
        d.applyFavorite(favorite);
        while(d.isBusy){$.sleep(40);}
        var src=new File(paths[i]);
        var base=src.name.replace(/\.[^.]+$/,"");
        d.saveAs(folder.fsName+"/"+base+(suffix||"_processed")+".wav",true);
        $.sleep(400); d.closeDocument(); $.sleep(250); count++;
    }
    return count;
}
