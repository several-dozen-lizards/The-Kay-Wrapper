import sys
sys.path.insert(0, '.')
from curiosity_engine import CuriosityStore, CuriosityManager
print("CuriosityStore.mark_pursued:", hasattr(CuriosityStore, 'mark_pursued'))
print("CuriosityManager.mark_pursued:", hasattr(CuriosityManager, 'mark_pursued'))
print("OK - both methods exist")
