import sys, pathlib, importlib, traceback
sys.path.insert(0, str(pathlib.Path.cwd() / 'venv'))
try:
    m = importlib.import_module('app.auth.routes')
    print('IMPORT_OK', m.__file__)
except Exception:
    traceback.print_exc()
    sys.exit(1)
