## SettingsPanel - Global configuration for the Nexus UI.
## LLM provider selection, API keys, UI preferences, entity config.
class_name SettingsPanel
extends VBoxContainer

signal setting_changed(key: String, value: Variant)

const BG_CONFIG_PATH := "user://panel_config.json"
const BG_DIR := "user://backgrounds/"

var _server_url_input: LineEdit
var _kay_port_input: LineEdit
var _reed_port_input: LineEdit
var _theme_select: OptionButton
var _font_size_slider: HSlider
var _font_size_label: Label
var _auto_reconnect_check: CheckBox
var _show_timestamps_check: CheckBox
var _status_label: Label

## Background picker state
var _bg_file_dialog: FileDialog
var _bg_picking_for: String = ""  # "nexus", "kay", or "reed"
var _bg_picking_type: String = "bg"  # "bg" or "accent"
var _bg_labels: Dictionary = {}  # panel_id -> Label showing current bg
var _accent_labels: Dictionary = {}  # panel_id -> Label showing current accent
var _bg_config: Dictionary = {}  # panel_id -> user:// path
var _accent_config: Dictionary = {}  # panel_id -> user:// path


func _ready() -> void:
	_build_ui()


func _build_ui() -> void:
	var header = Label.new()
	header.text = "⚙ Settings"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	add_child(HSeparator.new())
	
	# --- Connection section ---
	_add_section_header("Connection")
	
	_server_url_input = _add_text_field("Nexus Server:", "ws://localhost:8765")
	_kay_port_input = _add_text_field("Kay Room Port:", "8770")
	_reed_port_input = _add_text_field("Reed Room Port:", "8771")
	
	_auto_reconnect_check = CheckBox.new()
	_auto_reconnect_check.text = "Auto-reconnect private rooms"
	_auto_reconnect_check.button_pressed = true
	_auto_reconnect_check.add_theme_font_size_override("font_size", 11)
	_auto_reconnect_check.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	add_child(_auto_reconnect_check)
	
	add_child(HSeparator.new())
	
	# --- Display section ---
	_add_section_header("Display")
	
	_show_timestamps_check = CheckBox.new()
	_show_timestamps_check.text = "Show timestamps"
	_show_timestamps_check.button_pressed = true
	_show_timestamps_check.add_theme_font_size_override("font_size", 11)
	_show_timestamps_check.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	add_child(_show_timestamps_check)
	
	# Font size
	var font_row = HBoxContainer.new()
	var f_lbl = Label.new()
	f_lbl.text = "Font size:"
	f_lbl.add_theme_font_size_override("font_size", 11)
	f_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	font_row.add_child(f_lbl)
	
	_font_size_slider = HSlider.new()
	_font_size_slider.min_value = 10
	_font_size_slider.max_value = 20
	_font_size_slider.step = 1
	_font_size_slider.value = 13
	_font_size_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_font_size_slider.value_changed.connect(_on_font_size_changed)
	font_row.add_child(_font_size_slider)
	
	_font_size_label = Label.new()
	_font_size_label.text = "13"
	_font_size_label.add_theme_font_size_override("font_size", 11)
	_font_size_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	_font_size_label.custom_minimum_size.x = 24
	font_row.add_child(_font_size_label)
	add_child(font_row)
	
	# Theme
	var theme_row = HBoxContainer.new()
	var t_lbl = Label.new()
	t_lbl.text = "Theme:"
	t_lbl.add_theme_font_size_override("font_size", 11)
	t_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	theme_row.add_child(t_lbl)
	
	_theme_select = OptionButton.new()
	_theme_select.add_item("Dark (default)")
	_theme_select.add_item("Void")
	_theme_select.add_item("Midnight")
	_theme_select.add_theme_font_size_override("font_size", 11)
	theme_row.add_child(_theme_select)
	add_child(theme_row)
	
	add_child(HSeparator.new())
	
	# --- Panel Backgrounds section ---
	_add_section_header("Panel Backgrounds")
	_load_bg_config()
	
	for panel_id in ["nexus", "kay", "reed"]:
		# --- Background row ---
		var row = HBoxContainer.new()
		row.add_theme_constant_override("separation", 4)
		
		var lbl = Label.new()
		lbl.text = panel_id.capitalize() + ":"
		lbl.add_theme_font_size_override("font_size", 11)
		lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
		lbl.custom_minimum_size.x = 52
		row.add_child(lbl)
		
		var path_lbl = Label.new()
		if _bg_config.has(panel_id):
			path_lbl.text = _bg_config[panel_id].get_file()
		else:
			path_lbl.text = "(default)"
		path_lbl.add_theme_font_size_override("font_size", 10)
		path_lbl.add_theme_color_override("font_color", Color(0.4, 0.5, 0.5))
		path_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		path_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		row.add_child(path_lbl)
		_bg_labels[panel_id] = path_lbl
		
		var browse_btn = _make_btn("📂")
		browse_btn.tooltip_text = "Choose background for " + panel_id.capitalize()
		browse_btn.pressed.connect(_on_bg_browse.bind(panel_id, "bg"))
		row.add_child(browse_btn)
		
		var clear_btn = _make_btn("✕")
		clear_btn.tooltip_text = "Reset to default"
		clear_btn.pressed.connect(_on_bg_clear.bind(panel_id, "bg"))
		row.add_child(clear_btn)
		
		add_child(row)
		
		# --- Accent row (additive blend, black = transparent) ---
		var acc_row = HBoxContainer.new()
		acc_row.add_theme_constant_override("separation", 4)
		
		var acc_lbl = Label.new()
		acc_lbl.text = "  accent:"
		acc_lbl.add_theme_font_size_override("font_size", 10)
		acc_lbl.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
		acc_lbl.custom_minimum_size.x = 52
		acc_row.add_child(acc_lbl)
		
		var acc_path_lbl = Label.new()
		if _accent_config.has(panel_id):
			acc_path_lbl.text = _accent_config[panel_id].get_file()
		else:
			acc_path_lbl.text = "(none)"
		acc_path_lbl.add_theme_font_size_override("font_size", 10)
		acc_path_lbl.add_theme_color_override("font_color", Color(0.4, 0.45, 0.5))
		acc_path_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		acc_path_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		acc_row.add_child(acc_path_lbl)
		_accent_labels[panel_id] = acc_path_lbl
		
		var acc_browse = _make_btn("✨")
		acc_browse.tooltip_text = "Accent image (black = transparent)"
		acc_browse.pressed.connect(_on_bg_browse.bind(panel_id, "accent"))
		acc_row.add_child(acc_browse)
		
		var acc_clear = _make_btn("✕")
		acc_clear.tooltip_text = "Remove accent"
		acc_clear.pressed.connect(_on_bg_clear.bind(panel_id, "accent"))
		acc_row.add_child(acc_clear)
		
		add_child(acc_row)
	
	# File dialog (added to tree but hidden)
	_bg_file_dialog = FileDialog.new()
	_bg_file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	_bg_file_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_bg_file_dialog.filters = PackedStringArray(["*.png ; PNG Images", "*.jpg ; JPEG Images", "*.jpeg ; JPEG Images", "*.webp ; WebP Images"])
	_bg_file_dialog.title = "Choose Panel Background"
	_bg_file_dialog.size = Vector2i(700, 450)
	_bg_file_dialog.file_selected.connect(_on_bg_file_selected)
	add_child(_bg_file_dialog)
	
	add_child(HSeparator.new())
	
	# --- Actions ---
	_add_section_header("Actions")
	
	var actions_row = HBoxContainer.new()
	actions_row.add_theme_constant_override("separation", 4)
	
	var save_btn = _make_btn("💾 Save Settings")
	save_btn.pressed.connect(_on_save)
	actions_row.add_child(save_btn)
	
	var reset_btn = _make_btn("↻ Reset Layout")
	reset_btn.pressed.connect(_on_reset_layout)
	actions_row.add_child(reset_btn)
	add_child(actions_row)
	
	# Status
	_status_label = Label.new()
	_status_label.text = ""
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.4))
	add_child(_status_label)
	
	# Version info at bottom
	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(spacer)
	
	var version = Label.new()
	version.text = "Nexus v0.1.0 — the crossroads"
	version.add_theme_font_size_override("font_size", 9)
	version.add_theme_color_override("font_color", Color(0.3, 0.3, 0.4))
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(version)


func _add_section_header(text: String) -> void:
	var lbl = Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 12)
	lbl.add_theme_color_override("font_color", Color(0.55, 0.55, 0.7))
	add_child(lbl)


func _add_text_field(label: String, default_val: String) -> LineEdit:
	var row = HBoxContainer.new()
	var lbl = Label.new()
	lbl.text = label
	lbl.add_theme_font_size_override("font_size", 11)
	lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	lbl.custom_minimum_size.x = 100
	row.add_child(lbl)
	
	var input = LineEdit.new()
	input.text = default_val
	input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	input.add_theme_font_size_override("font_size", 11)
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.06, 0.1)
	style.border_color = Color(0.15, 0.15, 0.25)
	style.set_border_width_all(1)
	style.set_corner_radius_all(3)
	style.content_margin_left = 6
	style.content_margin_right = 6
	style.content_margin_top = 3
	style.content_margin_bottom = 3
	input.add_theme_stylebox_override("normal", style)
	row.add_child(input)
	add_child(row)
	return input


func _make_btn(text: String) -> Button:
	var btn = Button.new()
	btn.text = text
	btn.add_theme_font_size_override("font_size", 11)
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.1, 0.18)
	style.set_corner_radius_all(3)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	return btn


func _on_font_size_changed(value: float) -> void:
	_font_size_label.text = str(int(value))
	setting_changed.emit("font_size", int(value))


func _on_save() -> void:
	_status_label.text = "Settings saved"
	setting_changed.emit("save", true)


func _on_reset_layout() -> void:
	setting_changed.emit("reset_layout", true)
	_status_label.text = "Layout reset"


## ========================================================================
## Panel Background Management
## ========================================================================

func _load_bg_config() -> void:
	if not FileAccess.file_exists(BG_CONFIG_PATH):
		return
	var file = FileAccess.open(BG_CONFIG_PATH, FileAccess.READ)
	if not file:
		return
	var json = JSON.new()
	var err = json.parse(file.get_as_text())
	file.close()
	if err == OK and json.data is Dictionary:
		var bgs = json.data.get("backgrounds", {})
		if bgs is Dictionary:
			_bg_config = bgs
		var accents = json.data.get("accents", {})
		if accents is Dictionary:
			_accent_config = accents


func _save_bg_config() -> void:
	var file = FileAccess.open(BG_CONFIG_PATH, FileAccess.WRITE)
	if not file:
		push_warning("SettingsPanel: Could not save bg config")
		return
	file.store_string(JSON.stringify({
		"backgrounds": _bg_config,
		"accents": _accent_config,
	}))
	file.close()


func _on_bg_browse(panel_id: String, img_type: String = "bg") -> void:
	_bg_picking_for = panel_id
	_bg_picking_type = img_type
	var type_label = "Background" if img_type == "bg" else "Accent"
	_bg_file_dialog.title = "%s for %s" % [type_label, panel_id.capitalize()]
	_bg_file_dialog.popup_centered()


func _on_bg_file_selected(path: String) -> void:
	if _bg_picking_for.is_empty():
		return
	# Ensure backgrounds directory exists
	DirAccess.make_dir_recursive_absolute(BG_DIR)
	
	# Copy file to user:// so it persists
	var prefix = _bg_picking_for + ("_accent" if _bg_picking_type == "accent" else "_bg")
	var filename = prefix + "." + path.get_extension()
	var dest = BG_DIR + filename
	
	# Read source file and write to user://
	var src_file = FileAccess.open(path, FileAccess.READ)
	if not src_file:
		_status_label.text = "Error: Could not read " + path.get_file()
		return
	var data = src_file.get_buffer(src_file.get_length())
	src_file.close()
	
	var dst_file = FileAccess.open(dest, FileAccess.WRITE)
	if not dst_file:
		_status_label.text = "Error: Could not write to user dir"
		return
	dst_file.store_buffer(data)
	dst_file.close()
	
	# Update correct config
	if _bg_picking_type == "accent":
		_accent_config[_bg_picking_for] = dest
		if _accent_labels.has(_bg_picking_for):
			_accent_labels[_bg_picking_for].text = path.get_file()
	else:
		_bg_config[_bg_picking_for] = dest
		if _bg_labels.has(_bg_picking_for):
			_bg_labels[_bg_picking_for].text = path.get_file()
	
	_save_bg_config()
	
	var type_label = "accent" if _bg_picking_type == "accent" else "background"
	_status_label.text = "%s %s updated" % [_bg_picking_for.capitalize(), type_label]
	
	# Notify main to reload (same signal — reload_background handles both)
	setting_changed.emit("panel_bg_" + _bg_picking_for, dest)
	_bg_picking_for = ""
	_bg_picking_type = "bg"


func _on_bg_clear(panel_id: String, img_type: String = "bg") -> void:
	if img_type == "accent":
		_accent_config.erase(panel_id)
		if _accent_labels.has(panel_id):
			_accent_labels[panel_id].text = "(none)"
	else:
		_bg_config.erase(panel_id)
		if _bg_labels.has(panel_id):
			_bg_labels[panel_id].text = "(default)"
	_save_bg_config()
	var type_label = "accent" if img_type == "accent" else "background"
	_status_label.text = "%s %s cleared" % [panel_id.capitalize(), type_label]
	setting_changed.emit("panel_bg_" + panel_id, "")


## Returns the user-selected background path for a panel, or empty string for default
static func get_panel_bg(panel_id: String) -> String:
	return _get_config_value("backgrounds", panel_id)


## Returns the user-selected accent path for a panel, or empty string for none
static func get_panel_accent(panel_id: String) -> String:
	return _get_config_value("accents", panel_id)


static func _get_config_value(section: String, panel_id: String) -> String:
	if not FileAccess.file_exists(BG_CONFIG_PATH):
		return ""
	var file = FileAccess.open(BG_CONFIG_PATH, FileAccess.READ)
	if not file:
		return ""
	var json = JSON.new()
	var err = json.parse(file.get_as_text())
	file.close()
	if err == OK and json.data is Dictionary:
		var data = json.data.get(section, {})
		if data is Dictionary and data.has(panel_id):
			return data[panel_id]
	return ""
