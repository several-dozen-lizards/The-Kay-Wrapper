## Launcher - Persona selection and backend management for JNSQ
##
## Shows all available personas, lets user select which to activate,
## then starts backends and creates chat panels for each.
##
## The launcher reads:
##   - personas/ directory for available personas
##   - last_session.json for previously-open personas (auto-checked)
##
## On launch, it starts a backend process for each selected persona
## and transitions to the tabbed chat UI.
class_name Launcher
extends Control

signal launch_requested(personas: Array[String])
signal create_requested

const PERSONAS_DIR = "personas"
const LAST_SESSION_FILE = "last_session.json"

## UI elements
var _title: Label
var _subtitle: Label
var _persona_list: VBoxContainer
var _scroll: ScrollContainer
var _launch_btn: Button
var _create_btn: Button
var _status_label: Label

## State
var _personas: Array[Dictionary] = []
var _checkboxes: Dictionary = {}  # name -> CheckBox
var _last_session: Dictionary = {}

## Colors
const COLOR_RUNNING = Color(0.3, 0.8, 0.4)
const COLOR_STOPPED = Color(0.5, 0.5, 0.5)
const COLOR_SELECTED = Color(0.4, 0.7, 0.9)


func _ready() -> void:
	_setup_ui()
	_load_personas()
	_load_last_session()
	_update_checkboxes()


func _setup_ui() -> void:
	# Main layout
	var vbox = VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	vbox.add_theme_constant_override("separation", 16)
	add_child(vbox)

	# Padding
	var margin = MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 40)
	margin.add_theme_constant_override("margin_right", 40)
	margin.add_theme_constant_override("margin_top", 40)
	margin.add_theme_constant_override("margin_bottom", 40)
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(margin)

	var content = VBoxContainer.new()
	content.add_theme_constant_override("separation", 20)
	margin.add_child(content)

	# Title
	_title = Label.new()
	_title.text = "JE NE SAIS QUOI"
	_title.add_theme_font_size_override("font_size", 32)
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(_title)

	# Subtitle
	_subtitle = Label.new()
	_subtitle.text = "The indefinable quality."
	_subtitle.add_theme_font_size_override("font_size", 16)
	_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_subtitle.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	content.add_child(_subtitle)

	# Spacer
	var spacer1 = Control.new()
	spacer1.custom_minimum_size = Vector2(0, 20)
	content.add_child(spacer1)

	# Instructions
	var instructions = Label.new()
	instructions.text = "Select companions to activate:"
	instructions.add_theme_font_size_override("font_size", 14)
	content.add_child(instructions)

	# Scrollable persona list
	_scroll = ScrollContainer.new()
	_scroll.custom_minimum_size = Vector2(0, 200)
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(_scroll)

	_persona_list = VBoxContainer.new()
	_persona_list.add_theme_constant_override("separation", 8)
	_persona_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(_persona_list)

	# Spacer
	var spacer2 = Control.new()
	spacer2.custom_minimum_size = Vector2(0, 10)
	content.add_child(spacer2)

	# Button row
	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 16)
	btn_row.alignment = BoxContainer.ALIGNMENT_CENTER
	content.add_child(btn_row)

	# Create New button
	_create_btn = Button.new()
	_create_btn.text = "+ Create New"
	_create_btn.custom_minimum_size = Vector2(140, 40)
	_create_btn.pressed.connect(_on_create_pressed)
	btn_row.add_child(_create_btn)

	# Launch button
	_launch_btn = Button.new()
	_launch_btn.text = "Launch Selected"
	_launch_btn.custom_minimum_size = Vector2(180, 50)
	_launch_btn.pressed.connect(_on_launch_pressed)
	btn_row.add_child(_launch_btn)

	# Status label
	_status_label = Label.new()
	_status_label.text = ""
	_status_label.add_theme_font_size_override("font_size", 12)
	_status_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.5))
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(_status_label)


func _load_personas() -> void:
	"""Load available personas from personas/ directory."""
	_personas.clear()

	# Get wrapper root (parent of godot-ui)
	var wrapper_root = _get_wrapper_root()
	var personas_path = wrapper_root.path_join(PERSONAS_DIR)

	var dir = DirAccess.open(personas_path)
	if dir == null:
		_status_label.text = "No personas/ directory found. Create your first persona!"
		return

	dir.list_dir_begin()
	var folder = dir.get_next()
	while folder != "":
		if dir.current_is_dir() and not folder.begins_with("."):
			var config_path = personas_path.path_join(folder).path_join("config").path_join("persona_config.json")
			if FileAccess.file_exists(config_path):
				var config = _load_persona_config(config_path)
				if config:
					config["folder"] = folder
					_personas.append(config)
		folder = dir.get_next()
	dir.list_dir_end()

	# Sort by name
	_personas.sort_custom(func(a, b): return a.get("name", "") < b.get("name", ""))

	_build_persona_list()


func _load_persona_config(path: String) -> Dictionary:
	"""Load a persona_config.json file."""
	var file = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}

	var content = file.get_as_text()
	file.close()

	var json = JSON.parse_string(content)
	if json == null or not json is Dictionary:
		return {}

	return json


func _load_last_session() -> void:
	"""Load last_session.json to know which personas were previously open."""
	var wrapper_root = _get_wrapper_root()
	var session_path = wrapper_root.path_join(LAST_SESSION_FILE)

	if not FileAccess.file_exists(session_path):
		return

	var file = FileAccess.open(session_path, FileAccess.READ)
	if file == null:
		return

	var content = file.get_as_text()
	file.close()

	var json = JSON.parse_string(content)
	if json != null and json is Dictionary:
		_last_session = json


func _save_last_session(selected: Array[String]) -> void:
	"""Save which personas were launched to last_session.json."""
	var wrapper_root = _get_wrapper_root()
	var session_path = wrapper_root.path_join(LAST_SESSION_FILE)

	_last_session["last_open"] = selected
	_last_session["last_closed"] = Time.get_datetime_string_from_system(true)

	var file = FileAccess.open(session_path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(_last_session, "  "))
		file.close()


func _build_persona_list() -> void:
	"""Build the persona checkbox list."""
	# Clear existing
	for child in _persona_list.get_children():
		child.queue_free()
	_checkboxes.clear()

	if _personas.is_empty():
		var empty_label = Label.new()
		empty_label.text = "No personas found. Click '+ Create New' to get started."
		empty_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		_persona_list.add_child(empty_label)
		return

	for persona in _personas:
		var row = _create_persona_row(persona)
		_persona_list.add_child(row)


func _create_persona_row(persona: Dictionary) -> Control:
	"""Create a row for a single persona."""
	var folder = persona.get("folder", "unknown")
	var display_name = persona.get("name", folder)
	var description = persona.get("description", "")
	var theme_color = Color.from_string(persona.get("room", {}).get("color", "#808080"), Color(0.5, 0.5, 0.5))

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 12)

	# Checkbox
	var checkbox = CheckBox.new()
	checkbox.text = ""
	_checkboxes[folder] = checkbox
	hbox.add_child(checkbox)

	# Color indicator
	var color_rect = ColorRect.new()
	color_rect.color = theme_color
	color_rect.custom_minimum_size = Vector2(4, 40)
	hbox.add_child(color_rect)

	# Name and description
	var text_vbox = VBoxContainer.new()
	text_vbox.add_theme_constant_override("separation", 2)
	text_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(text_vbox)

	var name_label = Label.new()
	name_label.text = display_name
	name_label.add_theme_font_size_override("font_size", 16)
	text_vbox.add_child(name_label)

	if description:
		var desc_label = Label.new()
		desc_label.text = description
		desc_label.add_theme_font_size_override("font_size", 12)
		desc_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		text_vbox.add_child(desc_label)

	# Status indicator
	var status = _get_persona_status(folder)
	var status_label = Label.new()
	status_label.text = status.text
	status_label.add_theme_color_override("font_color", status.color)
	status_label.add_theme_font_size_override("font_size", 12)
	hbox.add_child(status_label)

	return hbox


func _get_persona_status(folder: String) -> Dictionary:
	"""Get status text and color for a persona."""
	# Check if it was open last session
	var last_open: Array = _last_session.get("last_open", [])
	if folder in last_open:
		return {"text": "Last session", "color": COLOR_SELECTED}

	# Check if currently running (would need to read running_backends.json)
	# For now, just show "Saved"
	return {"text": "Saved", "color": COLOR_STOPPED}


func _update_checkboxes() -> void:
	"""Pre-check personas that were open last session."""
	var last_open: Array = _last_session.get("last_open", [])
	for folder in _checkboxes:
		var checkbox = _checkboxes[folder] as CheckBox
		checkbox.button_pressed = folder in last_open


func _get_selected_personas() -> Array[String]:
	"""Get list of selected persona folder names."""
	var selected: Array[String] = []
	for folder in _checkboxes:
		var checkbox = _checkboxes[folder] as CheckBox
		if checkbox.button_pressed:
			selected.append(folder)
	return selected


func _on_launch_pressed() -> void:
	var selected = _get_selected_personas()
	if selected.is_empty():
		_status_label.text = "Select at least one companion to launch."
		return

	_status_label.text = "Launching %d companion(s)..." % selected.size()
	_launch_btn.disabled = true

	# Save session state
	_save_last_session(selected)

	# Emit signal for main.gd to handle
	launch_requested.emit(selected)


func _on_create_pressed() -> void:
	_status_label.text = "Opening persona creator..."
	create_requested.emit()


func _get_wrapper_root() -> String:
	"""Get the wrapper root directory (parent of godot-ui)."""
	# In editor: res:// is the godot-ui folder
	# Exported: executable is in godot-ui folder
	var exe_path = OS.get_executable_path()
	if exe_path.is_empty() or exe_path.contains("godot"):
		# Running in editor - use project path's parent
		return ProjectSettings.globalize_path("res://").get_base_dir()
	else:
		# Exported - executable's parent directory
		return exe_path.get_base_dir().get_base_dir()


func get_persona_config(folder: String) -> Dictionary:
	"""Get config for a specific persona."""
	for persona in _personas:
		if persona.get("folder") == folder:
			return persona
	return {}


func refresh_personas() -> void:
	"""Reload the persona list."""
	_load_personas()
	_update_checkboxes()
