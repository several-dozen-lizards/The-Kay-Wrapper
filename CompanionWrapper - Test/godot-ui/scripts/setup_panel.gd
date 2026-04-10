## SetupPanel - Companion persona setup and configuration.
## Create and manage companion personas from within the UI.
class_name SetupPanel
extends VBoxContainer

var _persona_name_label: Label
var _persona_id_label: Label
var _persona_pronouns_label: Label
var _status_label: Label
var _system_prompt_edit: TextEdit
var _original_system_prompt: String = ""
var _persona_config: Dictionary = {}
var _persona_folder: String = ""

## File dialog for document import
var _folder_dialog: FileDialog


func _ready() -> void:
	_find_persona_folder()
	_build_ui()
	_load_persona_config()
	_load_system_prompt()


func _find_persona_folder() -> void:
	## Find the persona folder relative to the Godot project/executable
	var paths = [
		OS.get_executable_path().get_base_dir().path_join("../persona"),
		ProjectSettings.globalize_path("res://").path_join("../persona"),
		ProjectSettings.globalize_path("res://").path_join("../../persona"),
	]
	for p in paths:
		var check_file = p.path_join("persona_config.json")
		if FileAccess.file_exists(check_file):
			_persona_folder = p
			return
	# Fallback to first path even if not found
	_persona_folder = paths[0]


func _build_ui() -> void:
	var header = Label.new()
	header.text = "Companion Setup"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	add_child(HSeparator.new())

	# --- Current Companion Section ---
	_add_section_header("Current Companion")

	# Name row
	var name_row = HBoxContainer.new()
	var name_lbl = Label.new()
	name_lbl.text = "Name:"
	name_lbl.add_theme_font_size_override("font_size", 11)
	name_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	name_lbl.custom_minimum_size.x = 70
	name_row.add_child(name_lbl)

	_persona_name_label = Label.new()
	_persona_name_label.text = "(loading...)"
	_persona_name_label.add_theme_font_size_override("font_size", 11)
	_persona_name_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	name_row.add_child(_persona_name_label)
	add_child(name_row)

	# Entity ID row
	var id_row = HBoxContainer.new()
	var id_lbl = Label.new()
	id_lbl.text = "Entity ID:"
	id_lbl.add_theme_font_size_override("font_size", 11)
	id_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	id_lbl.custom_minimum_size.x = 70
	id_row.add_child(id_lbl)

	_persona_id_label = Label.new()
	_persona_id_label.text = "(loading...)"
	_persona_id_label.add_theme_font_size_override("font_size", 11)
	_persona_id_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	id_row.add_child(_persona_id_label)
	add_child(id_row)

	# Pronouns row
	var pronouns_row = HBoxContainer.new()
	var pronouns_lbl = Label.new()
	pronouns_lbl.text = "Pronouns:"
	pronouns_lbl.add_theme_font_size_override("font_size", 11)
	pronouns_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	pronouns_lbl.custom_minimum_size.x = 70
	pronouns_row.add_child(pronouns_lbl)

	_persona_pronouns_label = Label.new()
	_persona_pronouns_label.text = "(loading...)"
	_persona_pronouns_label.add_theme_font_size_override("font_size", 11)
	_persona_pronouns_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	pronouns_row.add_child(_persona_pronouns_label)
	add_child(pronouns_row)

	# Action buttons row
	var action_row = HBoxContainer.new()
	action_row.add_theme_constant_override("separation", 4)

	var reload_btn = _make_btn("Reload Persona")
	reload_btn.pressed.connect(_on_reload_persona)
	action_row.add_child(reload_btn)

	var open_folder_btn = _make_btn("Open Folder")
	open_folder_btn.pressed.connect(_on_open_folder)
	action_row.add_child(open_folder_btn)
	add_child(action_row)

	add_child(HSeparator.new())

	# --- Setup Wizard Section ---
	_add_section_header("Setup Wizard")

	var wizard_desc = Label.new()
	wizard_desc.text = "Creates or reconfigures your companion's personality"
	wizard_desc.add_theme_font_size_override("font_size", 10)
	wizard_desc.add_theme_color_override("font_color", Color(0.45, 0.45, 0.55))
	wizard_desc.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(wizard_desc)

	var wizard_row = HBoxContainer.new()
	wizard_row.add_theme_constant_override("separation", 4)

	var wizard_btn = _make_btn("Run Setup Wizard")
	wizard_btn.pressed.connect(_on_run_wizard)
	wizard_row.add_child(wizard_btn)
	add_child(wizard_row)

	add_child(HSeparator.new())

	# --- Document Import Section ---
	_add_section_header("Document Import")

	var import_desc = Label.new()
	import_desc.text = "Analyze documents to generate a persona"
	import_desc.add_theme_font_size_override("font_size", 10)
	import_desc.add_theme_color_override("font_color", Color(0.45, 0.45, 0.55))
	import_desc.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(import_desc)

	var import_row = HBoxContainer.new()
	import_row.add_theme_constant_override("separation", 4)

	var import_btn = _make_btn("Import from Documents")
	import_btn.pressed.connect(_on_import_documents)
	import_row.add_child(import_btn)
	add_child(import_row)

	# Create folder dialog
	_folder_dialog = FileDialog.new()
	_folder_dialog.file_mode = FileDialog.FILE_MODE_OPEN_DIR
	_folder_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_folder_dialog.title = "Select Document Folder"
	_folder_dialog.size = Vector2i(700, 450)
	_folder_dialog.dir_selected.connect(_on_folder_selected)
	add_child(_folder_dialog)

	add_child(HSeparator.new())

	# --- System Prompt Editor Section ---
	_add_section_header("System Prompt")

	var prompt_desc = Label.new()
	prompt_desc.text = "Edit the companion's personality and behavior"
	prompt_desc.add_theme_font_size_override("font_size", 10)
	prompt_desc.add_theme_color_override("font_color", Color(0.45, 0.45, 0.55))
	prompt_desc.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(prompt_desc)

	# Text editor
	_system_prompt_edit = TextEdit.new()
	_system_prompt_edit.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_system_prompt_edit.add_theme_font_size_override("font_size", 11)
	_system_prompt_edit.add_theme_color_override("font_color", Color(0.75, 0.75, 0.8))
	var edit_style = StyleBoxFlat.new()
	edit_style.bg_color = Color(0.04, 0.04, 0.07)
	edit_style.set_corner_radius_all(3)
	edit_style.content_margin_left = 6
	edit_style.content_margin_right = 6
	edit_style.content_margin_top = 4
	edit_style.content_margin_bottom = 4
	_system_prompt_edit.add_theme_stylebox_override("normal", edit_style)
	_system_prompt_edit.add_theme_stylebox_override("focus", edit_style)
	add_child(_system_prompt_edit)

	# Save/Revert buttons
	var prompt_btn_row = HBoxContainer.new()
	prompt_btn_row.add_theme_constant_override("separation", 4)

	var save_btn = _make_btn("Save")
	save_btn.pressed.connect(_on_save_system_prompt)
	prompt_btn_row.add_child(save_btn)

	var revert_btn = _make_btn("Revert")
	revert_btn.pressed.connect(_on_revert_system_prompt)
	prompt_btn_row.add_child(revert_btn)
	add_child(prompt_btn_row)

	# Status
	_status_label = Label.new()
	_status_label.text = ""
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.4))
	add_child(_status_label)


func _add_section_header(text: String) -> void:
	var lbl = Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 12)
	lbl.add_theme_color_override("font_color", Color(0.55, 0.55, 0.7))
	add_child(lbl)


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


## ========================================================================
## Persona config loading
## ========================================================================

func _load_persona_config() -> void:
	var config_path = _persona_folder.path_join("persona_config.json")
	if not FileAccess.file_exists(config_path):
		_persona_name_label.text = "(not found)"
		_persona_id_label.text = "-"
		_persona_pronouns_label.text = "-"
		_status_label.text = "No persona config found at: " + config_path
		return

	var file = FileAccess.open(config_path, FileAccess.READ)
	if not file:
		_status_label.text = "Error reading persona config"
		return

	var json = JSON.new()
	var err = json.parse(file.get_as_text())
	file.close()

	if err != OK:
		_status_label.text = "Error parsing persona config JSON"
		return

	_persona_config = json.data if json.data is Dictionary else {}
	_update_persona_display()


func _update_persona_display() -> void:
	_persona_name_label.text = str(_persona_config.get("name", "(unknown)"))
	_persona_id_label.text = str(_persona_config.get("entity_id", "-"))

	var pronouns = _persona_config.get("pronouns", {})
	if pronouns is Dictionary:
		var subj = str(pronouns.get("subject", "they"))
		var obj = str(pronouns.get("object", "them"))
		var poss = str(pronouns.get("possessive", "their"))
		_persona_pronouns_label.text = "%s/%s/%s" % [subj, obj, poss]
	else:
		_persona_pronouns_label.text = "-"


## ========================================================================
## System prompt loading/saving
## ========================================================================

func _load_system_prompt() -> void:
	var prompt_path = _persona_folder.path_join("system_prompt.md")
	if not FileAccess.file_exists(prompt_path):
		_system_prompt_edit.text = "# System prompt not found\n\nRun the setup wizard to create one."
		_original_system_prompt = _system_prompt_edit.text
		return

	var file = FileAccess.open(prompt_path, FileAccess.READ)
	if not file:
		_status_label.text = "Error reading system prompt"
		return

	_system_prompt_edit.text = file.get_as_text()
	_original_system_prompt = _system_prompt_edit.text
	file.close()


func _on_save_system_prompt() -> void:
	var prompt_path = _persona_folder.path_join("system_prompt.md")
	var file = FileAccess.open(prompt_path, FileAccess.WRITE)
	if not file:
		_status_label.text = "Error: Could not write to system prompt file"
		return

	file.store_string(_system_prompt_edit.text)
	file.close()
	_original_system_prompt = _system_prompt_edit.text
	_status_label.text = "System prompt saved"


func _on_revert_system_prompt() -> void:
	_system_prompt_edit.text = _original_system_prompt
	_status_label.text = "Reverted to last saved version"


## ========================================================================
## Action handlers
## ========================================================================

func _on_reload_persona() -> void:
	_load_persona_config()
	_load_system_prompt()
	_status_label.text = "Persona reloaded"


func _on_open_folder() -> void:
	if _persona_folder.is_empty():
		_status_label.text = "Persona folder not found"
		return
	OS.shell_open(_persona_folder)


func _on_run_wizard() -> void:
	_status_label.text = "Starting setup wizard..."
	var wrapper_root = _persona_folder.get_base_dir()
	var wizard_path = wrapper_root.path_join("setup_wizard.py")

	if OS.get_name() == "Windows":
		# Open a new cmd window and run the wizard
		var args = ["/c", "start", "cmd", "/k", "cd", "/d", wrapper_root, "&&", "python", "setup_wizard.py"]
		OS.create_process("cmd", args)
	else:
		# Linux/Mac - try different terminal emulators
		var terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]
		for term in terminals:
			var result = OS.create_process(term, ["-e", "bash", "-c", "cd '%s' && python3 setup_wizard.py; read" % wrapper_root])
			if result != -1:
				break
	_status_label.text = "Setup wizard launched in new terminal"


func _on_import_documents() -> void:
	_folder_dialog.popup_centered()


func _on_folder_selected(folder_path: String) -> void:
	_status_label.text = "Importing from: " + folder_path.get_file() + "..."
	var wrapper_root = _persona_folder.get_base_dir()

	if OS.get_name() == "Windows":
		var args = ["/c", "start", "cmd", "/k", "cd", "/d", wrapper_root, "&&", "python", "setup_wizard.py", "--import", folder_path]
		OS.create_process("cmd", args)
	else:
		var terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]
		for term in terminals:
			var result = OS.create_process(term, ["-e", "bash", "-c", "cd '%s' && python3 setup_wizard.py --import '%s'; read" % [wrapper_root, folder_path]])
			if result != -1:
				break
	_status_label.text = "Document import launched in new terminal"


## ========================================================================
## Public API - get companion name for other panels
## ========================================================================

func get_companion_name() -> String:
	if _persona_config.has("name"):
		return str(_persona_config["name"])
	return "Companion"


func get_entity_id() -> String:
	if _persona_config.has("entity_id"):
		return str(_persona_config["entity_id"])
	return "companion"
