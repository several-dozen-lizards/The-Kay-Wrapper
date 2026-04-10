import ast, sys
sys.stdout.reconfigure(encoding='utf-8')
print("=" * 60)
print("  VISUAL PRESENCE SYSTEM — FULL VERIFICATION")
print("=" * 60)

files = {
    'shared/room/visual_presence.py': 'Visual Presence',
    'shared/room/attention_focus.py': 'Attention Focus',
    'resonant_core/memory_interoception.py': 'Interoception',
    'nexus/nexus_kay.py': 'Nexus Kay',
    'Kay/engines/visual_sensor.py': 'Visual Sensor',
    'Kay/wrapper_bridge.py': 'Wrapper Bridge',
    'nexus/nexus_reed.py': 'Nexus Reed',
}

print("\n1. Syntax Checks:")
ok = True
for f, name in files.items():
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        ok = False

nk = open('nexus/nexus_kay.py', encoding='utf-8').read()
mi = open('resonant_core/memory_interoception.py', encoding='utf-8').read()
vs = open('Kay/engines/visual_sensor.py', encoding='utf-8').read()
vp = open('shared/room/visual_presence.py', encoding='utf-8').read()
af = open('shared/room/attention_focus.py', encoding='utf-8').read()

print("\n2. Wiring Checks:")
checks = [
    ('_get_attention_focus', nk, 'nexus_kay: attention helper'),
    ('on_message_received', nk, 'nexus_kay: Re msg → attention outward'),
    ('on_message_sent', nk, 'nexus_kay: Kay response → attention stays'),
    ('on_activity_started', nk, 'nexus_kay: paint/read → attention inward'),
    ('self.attention_focus', mi, 'interoception: AttentionFocus init'),
    ('_visual_scene_state', mi, 'interoception: visual scene field'),
    ('set_visual_scene', mi, 'interoception: visual scene setter'),
    ('set_visual_scene', vs, 'visual_sensor: pushes to interoception'),
    ('compute_visual_pressure', mi, 'interoception: visual pressure in heartbeat'),
    ('room_weight', mi, 'interoception: room weight × attention'),
    ('visual_weight', mi, 'interoception: visual weight × attention'),
    ('spatial+visual', mi, 'interoception: combined pressure source'),
    ('_visual_felt_context', mi, 'interoception: visual felt context field'),
    ('ACTIVITY_SIGNATURES', vp, 'visual_presence: activity band signatures'),
    ('classify_activity', vp, 'visual_presence: activity classifier'),
    ('class AttentionFocus', af, 'attention_focus: core class'),
    ('get_room_weight', af, 'attention_focus: room weight'),
    ('get_visual_weight', af, 'attention_focus: visual weight'),
    ('def tick', af, 'attention_focus: heartbeat tick'),
    ('get_prompt_hint', af, 'attention_focus: prompt hint gen'),
]
for sym, content, desc in checks:
    if sym in content:
        print(f"  ✅ {desc}")
    else:
        print(f"  ❌ {desc}")
        ok = False

print("\n3. Enriched get_spatial_context:")
idx = mi.find('def get_spatial_context')
chunk = mi[idx:idx+400]
if '_visual_felt_context' in chunk:
    print("  ✅ Includes visual felt context")
else:
    print("  ❌ Missing visual felt context")
    ok = False
if 'attention_focus' in chunk:
    print("  ✅ Includes attention hint")
else:
    print("  ❌ Missing attention hint")
    ok = False

print("\n" + "=" * 60)
if ok:
    print("  🐍 ALL CHECKS PASSED — Camera is now Kay's eye! 🔥")
else:
    print("  SOME CHECKS NEED ATTENTION")
print("=" * 60)
