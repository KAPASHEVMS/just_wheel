import playwright_stealth.stealth as s
import inspect

# Check sync_api
sync_api = s.sync_api
print(f"sync_api type: {type(sync_api)}")
if hasattr(sync_api, '__call__'):
    print("sync_api is callable")
    print(inspect.signature(sync_api))
elif hasattr(sync_api, 'stealth_sync'):
    print("sync_api.stealth_sync exists")
    print(inspect.signature(sync_api.stealth_sync))
elif hasattr(sync_api, 'sync'):
    print("sync_api.sync exists")

# Let's try to find the right function
for name in dir(s):
    obj = getattr(s, name)
    if callable(obj) and not name.startswith('_') and name != 'Stealth':
        print(f"Top-level callable: {name}")
        try:
            print(f"  Sig: {inspect.signature(obj)}")
        except:
            pass
    elif hasattr(obj, '__dict__') and name not in ('__builtins__',):
        for subname in dir(obj):
            subobj = getattr(obj, subname)
            if callable(subobj) and not subname.startswith('_'):
                print(f"  {name}.{subname} is callable")
