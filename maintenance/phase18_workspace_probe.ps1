param([switch]$Restore)
$ErrorActionPreference='Stop'
if(Get-Process -Name 'Adobe Premiere Pro' -ErrorAction SilentlyContinue){throw 'Premiere must be fully exited'}
$layoutRoot='C:\Users\LENOVO\Documents\Adobe\Premiere Pro\26.0\Profile-LENOVO\Layouts'
$backupRoot='D:\computer\Adobe\Audition\Au_controller\backups\phase18_pr_layouts'
if(-not $Restore){
 if(Test-Path -LiteralPath $backupRoot){throw 'Probe backup already exists'}
 New-Item -ItemType Directory -Path $backupRoot | Out-Null
 foreach($name in @('UserWorkspace.xml','WorkspaceConfig.xml')){
  $source=Join-Path $layoutRoot $name
  if(Test-Path -LiteralPath $source){
   $resolved=(Resolve-Path -LiteralPath $source).Path
   if([IO.Path]::GetDirectoryName($resolved) -ne $layoutRoot){throw 'Unexpected layout path'}
   Move-Item -LiteralPath $resolved -Destination (Join-Path $backupRoot $name)
  }
 }
}else{
 foreach($name in @('UserWorkspace.xml','WorkspaceConfig.xml')){
  $saved=Join-Path $backupRoot $name
  $target=Join-Path $layoutRoot $name
  if(Test-Path -LiteralPath $saved){
   if(Test-Path -LiteralPath $target){
    $generated=Join-Path $backupRoot ($name+'.generated')
    if(Test-Path -LiteralPath $generated){throw 'Generated backup exists'}
    Move-Item -LiteralPath $target -Destination $generated
   }
   Copy-Item -LiteralPath $saved -Destination $target
  }
 }
}
Write-Output ('Layout probe restore='+$Restore)
