## Sidebar - Dockable icon strip that can be placed on any screen edge.
## Drag the sidebar to a different edge to re-dock it.
## Right-click for dock menu. Click icons to toggle feature panels.
class_name Sidebar
extends Control

signal feature_toggled(feature_id: String, visible: bool)
signal dock_changed(new_dock: int)

enum Dock { RIGHT, LEFT, TOP, BOTTOM }

const THICKNESS := 44
const ICON_SIZE := 28
const BTN_PAD := 6  # padding inside each button

const FEATURES = [
	{"id": "sessions", "icon": "📚", "tip": "Session Browser"},
	{"id": "auto", "icon": "🧠", "tip": "Autonomous Sessions"},
	{"id": "curate", "icon": "📋", "tip": "Memory Curation"},
	{"id": "media", "icon": "📄", "tip": "Media / Documents"},
	{"id": "canvas", "icon": "🎨", "tip": "Canvas"},
	{"id": "gallery", "icon": "🖼", "tip": "Gallery"},
	{"id": "stats", "icon": "📊", "tip": "Stats"},
	{"id": "face", "icon": "😶", "tip": "Face Expression (Ctrl+F)"},
	{"id": "exec", "icon": "🔒", "tip": "Code Execution"},
	{"id": "setup", "icon": "🐍", "tip": "Companion Setup"},
	{"id": "settings", "icon": "⚙", "tip": "Settings"},
]

var _buttons: Dictionary = {}
var _active_feature: String = ""
var _dock: int = Dock.RIGHT
var _dock_menu: PopupMenu
var _bg: Panel
var _container: BoxContainer

# --- Drag state ---
var _dragging: bool = false
var _drag_start: Vector2 = Vector2.ZERO
const DRAG_THRESHOLD := 12.0  # pixels before drag activates


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = true
	_load_dock_preference()
	_build_bg()
	_build_layout()
	_create_dock_menu()


func _build_bg() -> void:
	_bg = Panel.new()
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.05, 0.08, 0.95)
	style.border_color = Color(0.15, 0.15, 0.25)
	_apply_border(style)
	_bg.add_theme_stylebox_override("panel", style)
	add_child(_bg)


func _apply_border(style: StyleBoxFlat) -> void:
	style.border_width_left = 0
	style.border_width_right = 0
	style.border_width_top = 0
	style.border_width_bottom = 0
	match _dock:
		Dock.RIGHT:  style.border_width_left = 1
		Dock.LEFT:   style.border_width_right = 1
		Dock.TOP:    style.border_width_bottom = 1
		Dock.BOTTOM: style.border_width_top = 1


func _build_layout() -> void:
	if _container:
		_container.queue_free()
		_container = null
		_buttons.clear()
	
	var vert = is_vertical()
	
	if vert:
		_container = VBoxContainer.new()
	else:
		_container = HBoxContainer.new()
	
	_container.set_anchors_preset(Control.PRESET_FULL_RECT)
	_container.set_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_KEEP_SIZE, 4)
	_container.add_theme_constant_override("separation", 2)
	_container.mouse_filter = Control.MOUSE_FILTER_PASS
	add_child(_container)
	
	for feat in FEATURES:
		var btn = _make_button(feat, vert)
		_container.add_child(btn)
		_buttons[feat["id"]] = btn
	
	# Spacer pushes settings to end
	var spacer = Control.new()
	spacer.mouse_filter = Control.MOUSE_FILTER_PASS
	if vert:
		spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	else:
		spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_container.add_child(spacer)
	
	var settings_btn = _buttons.get("settings")
	if settings_btn:
		_container.move_child(settings_btn, -1)
	
	# Update background border
	if _bg:
		var style = _bg.get_theme_stylebox("panel") as StyleBoxFlat
		if style:
			_apply_border(style)


func _make_button(feat: Dictionary, vert: bool) -> Button:
	var btn = Button.new()
	btn.text = feat["icon"]
	btn.tooltip_text = feat["tip"]
	btn.toggle_mode = true
	btn.custom_minimum_size = Vector2(ICON_SIZE + BTN_PAD * 2, ICON_SIZE + BTN_PAD * 2)
	btn.add_theme_font_size_override("font_size", 16)
	btn.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	btn.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	btn.mouse_filter = Control.MOUSE_FILTER_STOP
	
	for state_name in ["normal", "hover", "pressed", "focus"]:
		var sb = StyleBoxFlat.new()
		sb.set_corner_radius_all(4)
		sb.content_margin_left = BTN_PAD
		sb.content_margin_right = BTN_PAD
		sb.content_margin_top = BTN_PAD
		sb.content_margin_bottom = BTN_PAD
		match state_name:
			"normal":  sb.bg_color = Color(0.08, 0.08, 0.12)
			"hover":   sb.bg_color = Color(0.12, 0.12, 0.2)
			"pressed":
				sb.bg_color = Color(0.15, 0.2, 0.35)
				sb.border_color = Color(0.3, 0.4, 0.7)
				sb.set_border_width_all(1)
			"focus":   sb.bg_color = Color(0.08, 0.08, 0.12)
		btn.add_theme_stylebox_override(state_name, sb)
	
	btn.toggled.connect(_on_feature_toggled.bind(feat["id"]))
	btn.gui_input.connect(_on_button_input)
	return btn


# ---------------------------------------------------------------------------
# Input: drag to re-dock + right-click menu
# ---------------------------------------------------------------------------

func _gui_input(event: InputEvent) -> void:
	_handle_input(event)


func _on_button_input(event: InputEvent) -> void:
	_handle_input(event)


func _handle_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT and mb.pressed:
			_show_dock_menu()
			accept_event()
		elif mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_drag_start = get_global_mouse_position()
				_dragging = false
			else:
				if _dragging:
					_finish_drag()
					accept_event()
				_dragging = false
	
	elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		var pos = get_global_mouse_position()
		if not _dragging and _drag_start.distance_to(pos) > DRAG_THRESHOLD:
			_dragging = true
		if _dragging:
			_update_drag_preview(pos)
			accept_event()


func _finish_drag() -> void:
	var pos = get_global_mouse_position()
	var screen = get_viewport_rect().size
	# Find nearest edge
	var distances = {
		Dock.LEFT:   pos.x,
		Dock.RIGHT:  screen.x - pos.x,
		Dock.TOP:    pos.y,
		Dock.BOTTOM: screen.y - pos.y,
	}
	var nearest = Dock.RIGHT
	var min_dist = INF
	for dock_id in distances:
		if distances[dock_id] < min_dist:
			min_dist = distances[dock_id]
			nearest = dock_id
	
	# Reset visual (remove any preview tint)
	modulate = Color.WHITE
	
	if nearest != _dock:
		set_dock(nearest)


func _update_drag_preview(pos: Vector2) -> void:
	# Subtle visual feedback - tint slightly to show we're dragging
	modulate = Color(0.8, 0.9, 1.0, 0.85)


# ---------------------------------------------------------------------------
# Dock menu
# ---------------------------------------------------------------------------

func _create_dock_menu() -> void:
	_dock_menu = PopupMenu.new()
	_dock_menu.add_item("Dock Right", Dock.RIGHT)
	_dock_menu.add_item("Dock Left", Dock.LEFT)
	_dock_menu.add_item("Dock Top", Dock.TOP)
	_dock_menu.add_item("Dock Bottom", Dock.BOTTOM)
	_dock_menu.id_pressed.connect(_on_dock_selected)
	add_child(_dock_menu)


func _show_dock_menu() -> void:
	for i in range(_dock_menu.item_count):
		_dock_menu.set_item_checked(i, _dock_menu.get_item_id(i) == _dock)
	_dock_menu.position = Vector2i(
		int(get_global_mouse_position().x),
		int(get_global_mouse_position().y)
	)
	_dock_menu.popup()


func _on_dock_selected(id: int) -> void:
	if id != _dock:
		set_dock(id)


# ---------------------------------------------------------------------------
# Feature toggle
# ---------------------------------------------------------------------------

func _on_feature_toggled(pressed: bool, feature_id: String) -> void:
	if _dragging:
		return  # Ignore toggles during drag
	if pressed:
		if _active_feature and _active_feature != feature_id:
			var prev = _buttons.get(_active_feature)
			if prev:
				prev.set_pressed_no_signal(false)
			feature_toggled.emit(_active_feature, false)
		_active_feature = feature_id
		feature_toggled.emit(feature_id, true)
	else:
		if _active_feature == feature_id:
			_active_feature = ""
		feature_toggled.emit(feature_id, false)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

func get_active_feature() -> String:
	return _active_feature


func get_dock() -> int:
	return _dock


func set_dock(new_dock: int) -> void:
	if new_dock == _dock:
		return
	_dock = new_dock
	_save_dock_preference()
	# Rebuild background border
	if _bg:
		var style = _bg.get_theme_stylebox("panel") as StyleBoxFlat
		if style:
			_apply_border(style)
	_build_layout()
	if _active_feature and _buttons.has(_active_feature):
		_buttons[_active_feature].set_pressed_no_signal(true)
	dock_changed.emit(_dock)


func get_thickness() -> int:
	return THICKNESS


func is_vertical() -> bool:
	return _dock == Dock.LEFT or _dock == Dock.RIGHT


func close_all() -> void:
	if _active_feature:
		var btn = _buttons.get(_active_feature)
		if btn:
			btn.set_pressed_no_signal(false)
		feature_toggled.emit(_active_feature, false)
		_active_feature = ""



# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

const CONFIG_PATH := "user://sidebar_config.json"


func _save_dock_preference() -> void:
	var file = FileAccess.open(CONFIG_PATH, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify({"dock": _dock}))
		file.close()


func _load_dock_preference() -> void:
	if not FileAccess.file_exists(CONFIG_PATH):
		return
	var file = FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if not file:
		return
	var json = JSON.new()
	var err = json.parse(file.get_as_text())
	file.close()
	if err == OK and json.data is Dictionary:
		var saved_dock = json.data.get("dock", Dock.RIGHT)
		if saved_dock is float:
			saved_dock = int(saved_dock)
		if saved_dock >= Dock.RIGHT and saved_dock <= Dock.BOTTOM:
			_dock = saved_dock
