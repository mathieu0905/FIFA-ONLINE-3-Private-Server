"""Publish in a separate process so the 8088 restart cannot kill the transaction."""
import sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from player_database import read,write
from publish_database import apply

path=Path(sys.argv[1]).resolve()
record=read(path)
try:
    record.update(apply(record['candidate'],record['manifest_sha256'],manage_services=True))
except Exception as error:
    record.update(status='apply_failed',error=str(error))
write(path,record)
