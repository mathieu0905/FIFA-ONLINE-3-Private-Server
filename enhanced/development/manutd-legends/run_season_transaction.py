"""Hold shared release locks across fresh resource rebuild, checks and direct install."""
import contextlib,runpy
import organize_seasons as s
real_locks=s.common.locks
with real_locks():
 s.common.closed()
 s.build()
 runpy.run_path(str(s.BASE/'test_season_organize.py'),run_name='__main__')
 # The single outer owner retains both exact lock payloads until installation and
 # supervised service recovery finish; avoid reacquiring our own release locks.
 s.common.locks=contextlib.nullcontext
 try:s.apply()
 finally:s.common.locks=real_locks
