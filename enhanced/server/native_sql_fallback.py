"""Read-only authoritative SQL fallback for a failed native UI database query."""
from pathlib import Path
import json, sqlite3, threading, time

LANGUAGES=frozenset(('kor','eng','chi','tha','vie','ind'))

class Reader:
    def __init__(self,server,client):
        self.server=Path(server);self.client=Path(client);self.cache={};self.lock=threading.Lock()

    def connect(self,database):
        if database=='fifadb':
            con=sqlite3.connect((self.server/'gamedata/fifadb.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        elif database in LANGUAGES:
            archive=self.client/'data/data_0.big';stat=archive.stat();key=(stat.st_size,stat.st_mtime_ns,database)
            with self.lock:
                if key not in self.cache:
                    # Import only the established read-only decoder; never write a DB/cache file.
                    import sys
                    tools=str(self.server/'tools/re')
                    if tools not in sys.path:sys.path.insert(0,tools)
                    import bigdir,extract_fifadb
                    raw=bigdir.read(archive,f'data/db2/{database}.db.db2')
                    plain=bytes(extract_fifadb.decrypt(raw))
                    self.cache={k:v for k,v in self.cache.items() if k[:2]==key[:2]}
                    self.cache[key]=b'SQLite format 3\0'+plain[16:]
                plain=self.cache[key]
            con=sqlite3.connect(':memory:');con.deserialize(plain)
        else:raise ValueError('Unsupported UI database')
        con.execute('PRAGMA query_only=ON')
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        def authorize(action,one,two,db,source):
            if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_READ and one in tables:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION and (two or '').lower() not in ('load_extension','readfile','writefile'):return sqlite3.SQLITE_OK
            if action==getattr(sqlite3,'SQLITE_RECURSIVE',33):return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        con.set_authorizer(authorize)
        deadline=time.monotonic()+2
        con.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        return con

    def query(self,database,sql):
        if not isinstance(sql,str) or not sql.strip() or len(sql)>1000000:raise ValueError('Invalid UI query')
        con=self.connect(database)
        try:
            cursor=con.execute(sql)
            if cursor.description is None:raise ValueError('Read-only rows required')
            rows=cursor.fetchmany(200001)
            if len(rows)>200000:raise ValueError('UI query result limit exceeded')
            fields=[d[0] for d in cursor.description]
            return [dict(zip(fields,row)) for row in rows]
        finally:con.close()

def install(hc):
    if getattr(hc,'_native_sql_fallback_installed',False):return
    reader=Reader(hc.HERE,hc.GAME);old=hc.route
    def route(path):
        prefix='/static/sql/'
        if not path.startswith(prefix):return old(path)
        database=path[len(prefix):]
        if database not in LANGUAGES and database!='fifadb':return lambda q,b:hc._json(dict(result=False,reason='Unsupported UI database'))
        def endpoint(query,body):
            try:
                request=json.loads(body)
                if not isinstance(request,dict):raise ValueError('Invalid UI SQL payload')
                rows=reader.query(database,request.get('sql'))
                # Use the original serializer: no display translation of stored player names.
                return ('application/json',json.dumps(rows,ensure_ascii=False).encode('utf8'))
            except (sqlite3.Error,ValueError,TypeError,json.JSONDecodeError) as error:
                return hc._json(dict(result=False,reason=str(error)))
        return endpoint
    hc.route=route;hc._native_sql_fallback_reader=reader;hc._native_sql_fallback_installed=True
