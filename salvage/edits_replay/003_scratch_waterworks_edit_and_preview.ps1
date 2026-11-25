$f='G:\GameDev\_claude_scratch\v130\waterworks.html'; $s=[IO.File]::ReadAllText($f)
$a='Hands off is a little ahead of the trend on average.'; if(!$s.Contains($a)){'MISSING'}; $s=$s.Replace($a,'Hands off averages a little ahead of the trend in this run.'); [IO.File]::WriteAllText($f,$s)
$d='G:\GameDev\_claude_scratch\v130\wwtest'; mkdir $d -Force | Out-Null
[IO.File]::WriteAllText("$d\index.html",'<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light;box-sizing:border-box}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'+$s+'</body></html>')
$p=Start-Process py -ArgumentList '-3','-m','http.server','8799','--bind','127.0.0.1','--directory',$d -WindowStyle Hidden -PassThru; $p.Id
