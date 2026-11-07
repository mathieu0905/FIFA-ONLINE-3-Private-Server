$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
$taskRoot='D:\fifaol3\npc-peer-market\clean-training'
$taskPython='D:\FO3ID\server\.venv\Scripts\python.exe'
while (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'clean-training\\collect_source.py' }) { Start-Sleep -Seconds 5 }
if (-not (Test-Path -LiteralPath "$taskRoot\regional-source.json")) { throw 'Source collection failed; training must not start.' }
& $taskPython -X utf8 "$taskRoot\summarize_source.py" *> "$taskRoot\source-summary.log"
& $taskPython -X utf8 "$taskRoot\prepare_clean.py" *> "$taskRoot\prepare.log"
& $taskPython -X utf8 "$taskRoot\prepare_trainer.py" *> "$taskRoot\prepare-trainer.log"
$taskUpload=@('data.npz','data-meta.json','encoder.json','split-indices.json','encoding-probes.json','cleaning-report.json','train_clean_gpu.py','launch_remote.sh') | ForEach-Object { Join-Path $taskRoot $_ }
& scp -q -o BatchMode=yes -o ConnectTimeout=12 -o StrictHostKeyChecking=yes @taskUpload 'zhihao@211.71.15.32:/home/zhihao/fo3_value_training/run-20261107-single-region-v6/'
& ssh -o BatchMode=yes -o ConnectTimeout=12 -o StrictHostKeyChecking=yes zhihao@211.71.15.32 'sh /home/zhihao/fo3_value_training/run-20261107-single-region-v6/launch_remote.sh' *> "$taskRoot\remote-job.txt"
'DATA_CLEANED_AND_GPU_TRAINING_LAUNCHED'
