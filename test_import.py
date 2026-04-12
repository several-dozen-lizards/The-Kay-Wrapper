import sys, os
sys.path.insert(0, r"D:\Wrappers\Kay")
os.chdir(r"D:\Wrappers\Kay")
try:
    from wrapper_bridge import CompanionWrapper
    print("wrapper_bridge import OK")
except Exception as e:
    print(f"IMPORT ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
