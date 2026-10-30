#target audition
function AuCtl_applyFavoriteAndWait(name, timeoutMs){
    var d=AuCtl_activeWave();
    var ok=d.applyFavorite(name);
    var waited=0, limit=timeoutMs||30000;
    while(d.isBusy && waited<limit){$.sleep(40);waited+=40;}
    return {ok:ok,busy:d.isBusy,waited:waited};
}
