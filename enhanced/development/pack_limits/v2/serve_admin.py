from pathlib import Path
import os,sys
R=Path(__file__).resolve().parent;P=R/'sandbox/server'
sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
import admin
admin.hc=h
server=admin.http.server.ThreadingHTTPServer(('127.0.0.1',18089),admin.Admin)
print('Isolated admin ready at 18089',flush=True)
server.serve_forever()
