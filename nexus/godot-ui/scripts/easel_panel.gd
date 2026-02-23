## EaselPanel — Panel content for entity painting.
##
## Designed to live inside a DockablePanel via PanelManager.
## Shows persistent canvases, history browser, and live WebSocket updates.
## Entities paint AUTONOMOUSLY during conversations — this is the gallery.
## Paintings persist on disk — the easel is never blank if something exists.
class_name EaselPanel
extends MarginContainer

signal clear_requested(entity: String)

const SERVER_BASE := "http://127.0.0.1:8765"

var _info_label: Label
var _texture_rect: TextureRect
var _entity_select: OptionButton
var _clear_button: Button
var _load_button: Button
var _history_select: OptionButton
var _http_latest: HTTPRequest
var _http_history: HTTPRequest
var _http_load: HTTPRequest

var _current_entity: String = ""
var _iteration: int = 0
var _dimensions: Array = [0, 0]
var _history_files: Array = []
var _loaded_entity: String = ""
var _initialized: bool = false


func _ready() -> void:
	# Margins
	add_theme_constant_override("margin_left", 6)
	add_theme_constant_override("margin_right", 6)
	add_theme_constant_override("margin_top", 4)
	add_theme_constant_override("margin_bottom", 4)
	
	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 5)
	
	# --- Entity + Clear row ---
	var entity_row = HBoxContainer.new()
	entity_row.add_theme_constant_override("separation", 8)
	
	var elbl = Label.new()
	elbl.text = "Entity:"
	elbl.add_theme_font_size_override("font_size", 12)
	elbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	entity_row.add_child(elbl)
	
	_entity_select = OptionButton.new()
	_entity_select.add_item("Reed")
	_entity_select.add_item("Kay")
	_entity_select.selected = 0
	_entity_select.add_theme_font_size_override("font_size", 12)
	_entity_select.item_selected.connect(_on_entity_changed)
	entity_row.add_child(_entity_select)
	
	var spacer1 = Control.new()
	spacer1.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	entity_row.add_child(spacer1)
	
	_clear_button = Button.new()
	_clear_button.text = "Clear"
	_clear_button.add_theme_font_size_override("font_size", 11)
	_clear_button.pressed.connect(_on_clear_pressed)
	entity_row.add_child(_clear_button)
	
	vbox.add_child(entity_row)
	
	# --- History row ---
	var hist_row = HBoxContainer.new()
	hist_row.add_theme_constant_override("separation", 6)
	
	var hlbl = Label.new()
	hlbl.text = "History:"
	hlbl.add_theme_font_size_override("font_size", 11)
	hlbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	hist_row.add_child(hlbl)
	
	_history_select = OptionButton.new()
	_history_select.add_theme_font_size_override("font_size", 11)
	_history_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hist_row.add_child(_history_select)
	
	_load_button = Button.new()
	_load_button.text = "Load"
	_load_button.add_theme_font_size_override("font_size", 11)
	_load_button.pressed.connect(_on_load_pressed)
	hist_row.add_child(_load_button)
	
	vbox.add_child(hist_row)
	
	# --- Info bar ---
	_info_label = Label.new()
	_info_label.text = "No canvas loaded"
	_info_label.add_theme_font_size_override("font_size", 11)
	_info_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.55))
	vbox.add_child(_info_label)
	
	# --- Canvas display ---
	var canvas_bg = PanelContainer.new()
	var bg_style = StyleBoxFlat.new()
	bg_style.bg_color = Color(0.02, 0.02, 0.04)
	bg_style.set_corner_radius_all(4)
	bg_style.content_margin_left = 2
	bg_style.content_margin_right = 2
	bg_style.content_margin_top = 2
	bg_style.content_margin_bottom = 2
	canvas_bg.add_theme_stylebox_override("panel", bg_style)
	canvas_bg.size_flags_vertical = Control.SIZE_EXPAND_FILL
	canvas_bg.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	
	_texture_rect = TextureRect.new()
	_texture_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	_texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_texture_rect.size_flags_vertical = Control.SIZE_EXPAND_FILL
	canvas_bg.add_child(_texture_rect)
	
	vbox.add_child(canvas_bg)
	
	add_child(vbox)
	
	# --- HTTP nodes ---
	_http_latest = HTTPRequest.new()
	_http_latest.request_completed.connect(_on_latest_response)
	add_child(_http_latest)
	
	_http_history = HTTPRequest.new()
	_http_history.request_completed.connect(_on_history_response)
	add_child(_http_history)
	
	_http_load = HTTPRequest.new()
	_http_load.request_completed.connect(_on_load_response)
	add_child(_http_load)


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------

func _get_selected_entity() -> String:
	if not _entity_select:
		return "Reed"
	match _entity_select.selected:
		0: return "Reed"
		1: return "Kay"
		_: return "Reed"


func fetch_latest_canvas() -> void:
	"""Called externally when the panel becomes visible."""
	_fetch_latest(_get_selected_entity())


func _fetch_latest(entity: String) -> void:
	_loaded_entity = entity
	var url = "%s/canvas/%s/latest" % [SERVER_BASE, entity.to_lower()]
	_http_latest.request(url)
	_info_label.text = "Fetching %s canvas..." % entity


func _fetch_history(entity: String) -> void:
	var url = "%s/canvas/%s/history" % [SERVER_BASE, entity.to_lower()]
	_http_history.request(url)


func _on_latest_response(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		_info_label.text = "Server unavailable"
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or not json.get("has_canvas", false):
		_info_label.text = "%s — no paintings yet" % _loaded_entity
		_texture_rect.texture = null
		_fetch_history(_loaded_entity)
		return
	_display_base64(json["base64"])
	_current_entity = _loaded_entity
	_iteration = json.get("iteration", 0)
	_dimensions = json.get("dimensions", [0, 0])
	_update_info(json.get("filename", ""))
	_fetch_history(_loaded_entity)


func _on_history_response(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json:
		return
	_history_files = json.get("saves", [])
	_history_select.clear()
	if _history_files.is_empty():
		_history_select.add_item("(no history)")
		_load_button.disabled = true
		return
	_load_button.disabled = false
	for save in _history_files:
		_history_select.add_item(save.get("filename", "?"))
	_history_select.selected = _history_files.size() - 1


func _on_load_response(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		_info_label.text = "Load failed"
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or json.has("error"):
		_info_label.text = "Error: %s" % json.get("error", "unknown") if json else "Parse error"
		return
	_info_label.text = "Loaded: %s" % json.get("loaded", "?")


# ---------------------------------------------------------------------------
# Live WebSocket updates
# ---------------------------------------------------------------------------

func on_canvas_updated(entity: String, base64_png: String, dims: Array, iteration: int) -> void:
	var selected = _get_selected_entity()
	if selected.to_lower() != entity.to_lower():
		return
	_current_entity = entity
	_iteration = iteration
	_dimensions = dims
	_display_base64(base64_png)
	_update_info("")
	_fetch_history(entity)


func on_canvas_cleared(entity: String) -> void:
	if _current_entity.to_lower() == entity.to_lower() or _get_selected_entity().to_lower() == entity.to_lower():
		_texture_rect.texture = null
		_info_label.text = "%s canvas cleared" % entity
		_iteration = 0
		_fetch_history(entity)


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

func _display_base64(b64: String) -> void:
	var raw_bytes = Marshalls.base64_to_raw(b64)
	var img = Image.new()
	var err = img.load_png_from_buffer(raw_bytes)
	if err != OK:
		_info_label.text = "Image decode error"
		return
	_texture_rect.texture = ImageTexture.create_from_image(img)


func _update_info(filename: String) -> void:
	var w = _dimensions[0] if _dimensions.size() > 0 else 0
	var h = _dimensions[1] if _dimensions.size() > 1 else 0
	var parts: PackedStringArray = [_current_entity, "%dx%d" % [w, h]]
	if _iteration > 0:
		parts.append("iter %d" % _iteration)
	if filename != "":
		parts.append(filename)
	_info_label.text = " — ".join(parts)


# ---------------------------------------------------------------------------
# User actions
# ---------------------------------------------------------------------------

func _on_entity_changed(_idx: int) -> void:
	_fetch_latest(_get_selected_entity())


func _on_clear_pressed() -> void:
	var entity = _get_selected_entity()
	clear_requested.emit(entity)
	_texture_rect.texture = null
	_info_label.text = "Clearing %s canvas..." % entity


func _on_load_pressed() -> void:
	var idx = _history_select.selected
	if idx < 0 or idx >= _history_files.size():
		return
	var filename = _history_files[idx].get("filename", "")
	if filename == "":
		return
	var entity = _get_selected_entity()
	var url = "%s/canvas/%s/load/%s" % [SERVER_BASE, entity.to_lower(), filename]
	_http_load.request(url, [], HTTPClient.METHOD_POST)
	_info_label.text = "Loading %s..." % filename
