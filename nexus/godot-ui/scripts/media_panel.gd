## MediaPanel - Document import and management.
## Upload documents, view imported media, manage file attachments.
class_name MediaPanel
extends VBoxContainer

signal file_import_requested(path: String, entity: String)

var _entity_select: OptionButton
var _file_list: ItemList
var _import_button: Button
var _status_label: Label
var _file_dialog: FileDialog


func _ready() -> void:
	_build_ui()


func _build_ui() -> void:
	var header = Label.new()
	header.text = "📄 Media / Documents"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	add_child(HSeparator.new())
	
	# Entity selector
	var row = HBoxContainer.new()
	var lbl = Label.new()
	lbl.text = "Target:"
	lbl.add_theme_font_size_override("font_size", 11)
	lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	row.add_child(lbl)
	
	_entity_select = OptionButton.new()
	_entity_select.add_item("Kay")
	_entity_select.add_item("Reed")
	_entity_select.add_item("Both")
	_entity_select.add_theme_font_size_override("font_size", 11)
	row.add_child(_entity_select)
	add_child(row)
	
	# Buttons
	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 4)
	
	_import_button = _make_btn("📁 Import File")
	_import_button.pressed.connect(_on_import)
	btn_row.add_child(_import_button)
	
	var refresh_btn = _make_btn("↻ Refresh")
	refresh_btn.pressed.connect(_on_refresh)
	btn_row.add_child(refresh_btn)
	add_child(btn_row)
	
	# File list
	_file_list = ItemList.new()
	_file_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_file_list.custom_minimum_size.y = 200
	_file_list.add_theme_font_size_override("font_size", 11)
	_file_list.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	var list_style = StyleBoxFlat.new()
	list_style.bg_color = Color(0.04, 0.04, 0.07)
	list_style.set_corner_radius_all(3)
	_file_list.add_theme_stylebox_override("panel", list_style)
	add_child(_file_list)
	
	# Status
	_status_label = Label.new()
	_status_label.text = "Import documents to share with entities"
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(_status_label)
	
	# Supported formats info
	var formats = Label.new()
	formats.text = "Supported: .txt .md .json .docx .pdf .csv"
	formats.add_theme_font_size_override("font_size", 9)
	formats.add_theme_color_override("font_color", Color(0.35, 0.35, 0.45))
	add_child(formats)
	
	# File dialog (hidden until needed)
	_file_dialog = FileDialog.new()
	_file_dialog.access = FileDialog.ACCESS_FILESYSTEM
	_file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	_file_dialog.filters = PackedStringArray([
		"*.txt ; Text files",
		"*.md ; Markdown",
		"*.json ; JSON",
		"*.docx ; Word documents",
		"*.pdf ; PDF files",
		"*.csv ; CSV files",
	])
	_file_dialog.file_selected.connect(_on_file_selected)
	add_child(_file_dialog)


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


func _on_import() -> void:
	_file_dialog.popup_centered(Vector2(600, 400))


func _on_file_selected(path: String) -> void:
	var entities = ["Kay", "Reed"]
	match _entity_select.selected:
		0: entities = ["Kay"]
		1: entities = ["Reed"]
	
	for entity in entities:
		file_import_requested.emit(path, entity)
	
	var fname = path.get_file()
	_file_list.add_item("📄 %s → %s" % [fname, ", ".join(PackedStringArray(entities))])
	_status_label.text = "Imported: %s" % fname


func _on_refresh() -> void:
	_status_label.text = "Refreshing file list..."
	# TODO: Hit REST endpoint to list imported documents


func set_status(text: String) -> void:
	_status_label.text = text
