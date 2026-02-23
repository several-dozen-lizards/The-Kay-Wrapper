## CanvasPanel — Persistent easel for entity paintings.
##
## Shows the latest canvas on open (fetched via HTTP), receives live
## updates via WebSocket, and lets you browse/load past iterations.
## Paintings persist on disk — the easel is never blank unless nothing
## has ever been painted.
class_name CanvasPanel
extends VBoxContainer

signal clear_requested(entity: String)

const SERVER_BASE := "http://127.0.0.1:8765"

var _header_label: Label
var _info_label: Label
var _texture_rect: TextureRect
var _entity_select: OptionButton
var _clear_button: Button
var _load_button: Button
var _history_select: OptionButton
var _scroll: ScrollContainer
var _http_latest: HTTPRequest
var _http_history: HTTPRequest
var _http_load: HTTPRequest

var _current_entity: String = ""
var _iteration: int = 0
var _dimensions: Array = [0, 0]
var _history_files: Array = []  # [{filename, ...}, ...]
var _loaded_entity: String = ""  # tracks which entity we last fetched


func _ready() -> void:
	_build_ui()
	# Canvas now handled by EaselWindow — don't auto-fetch here


func _build_ui() -> void:
	# Header
	_header_label = Label.new()
	_header_label.text = "🎨 Easel"
	_header_label.add_theme_font_size_override("font_size", 15)
	_header_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(_header_label)
	add_child(HSeparator.new())

	# Entity selector row
	var entity_row = HBoxContainer.new()
	entity_row.add_theme_constant_override("separation", 6)

	var lbl = Label.new()
	lbl.text = "Entity:"
	lbl.add_theme_font_size_override("font_size", 11)
	lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	entity_row.add_child(lbl)

	_entity_select = OptionButton.new()
	_entity_select.add_item("Reed")
	_entity_select.add_item("Kay")
	_entity_select.selected = 0
	_entity_select.add_theme_font_size_override("font_size", 11)
	_entity_select.item_selected.connect(_on_entity_changed)
	entity_row.add_child(_entity_select)

	var spacer = Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	entity_row.add_child(spacer)

	_clear_button = Button.new()
	_clear_button.text = "Clear"
	_clear_button.add_theme_font_size_override("font_size", 10)
	_clear_button.pressed.connect(_on_clear_pressed)
	entity_row.add_child(_clear_button)

	add_child(entity_row)

	# History row
	var hist_row = HBoxContainer.new()
	hist_row.add_theme_constant_override("separation", 6)

	var hlbl = Label.new()
	hlbl.text = "History:"
	hlbl.add_theme_font_size_override("font_size", 11)
	hlbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	hist_row.add_child(hlbl)

	_history_select = OptionButton.new()
	_history_select.add_theme_font_size_override("font_size", 10)
	_history_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hist_row.add_child(_history_select)

	_load_button = Button.new()
	_load_button.text = "Load"
	_load_button.add_theme_font_size_override("font_size", 10)
	_load_button.pressed.connect(_on_load_pressed)
	hist_row.add_child(_load_button)

	add_child(hist_row)

	# Info bar
	_info_label = Label.new()
	_info_label.text = "Loading..."
	_info_label.add_theme_font_size_override("font_size", 10)
	_info_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.55))
	add_child(_info_label)

	# Canvas display area
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	_texture_rect = TextureRect.new()
	_texture_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	_texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_texture_rect.custom_minimum_size = Vector2(280, 200)

	var bg = PanelContainer.new()
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.03, 0.03, 0.05)
	style.set_corner_radius_all(4)
	style.content_margin_left = 4
	style.content_margin_right = 4
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	bg.add_theme_stylebox_override("panel", style)
	bg.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bg.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bg.add_child(_texture_rect)

	_scroll.add_child(bg)
	add_child(_scroll)

	# HTTP request nodes
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
# HTTP fetching — persistent easel behavior
# ---------------------------------------------------------------------------

func _get_selected_entity() -> String:
	var idx = _entity_select.selected if _entity_select else 0
	match idx:
		0: return "Reed"
		1: return "Kay"
		_: return "Reed"


func _fetch_latest(entity: String) -> void:
	"""Fetch the most recent saved canvas from server."""
	_loaded_entity = entity
	var url = "%s/canvas/%s/latest" % [SERVER_BASE, entity.to_lower()]
	_http_latest.request(url)
	_info_label.text = "Fetching %s canvas..." % entity


func _fetch_history(entity: String) -> void:
	"""Fetch list of saved iterations from server."""
	var url = "%s/canvas/%s/history" % [SERVER_BASE, entity.to_lower()]
	_http_history.request(url)


func _on_latest_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		_info_label.text = "Server unavailable — easel empty"
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or not json.get("has_canvas", false):
		_info_label.text = "%s — no paintings yet" % _loaded_entity
		_texture_rect.texture = null
		# Still fetch history in case there are old saves
		_fetch_history(_loaded_entity)
		return

	_display_base64(json["base64"], json.get("dimensions", [0, 0]))
	_current_entity = _loaded_entity
	_iteration = json.get("iteration", 0)
	_dimensions = json.get("dimensions", [0, 0])
	_update_info(json.get("filename", ""))

	# Also populate history
	_fetch_history(_loaded_entity)


func _on_history_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
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
	# Select the latest by default
	_history_select.selected = _history_files.size() - 1


func _on_load_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		_info_label.text = "Load failed"
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or json.has("error"):
		_info_label.text = "Load error: %s" % json.get("error", "unknown")
		return

	# Canvas will arrive via WebSocket broadcast from load endpoint
	_info_label.text = "Loaded: %s" % json.get("loaded", "?")


# ---------------------------------------------------------------------------
# Live WebSocket updates (same as before, but additive to persistent state)
# ---------------------------------------------------------------------------

func on_canvas_updated(entity: String, base64_png: String, dims: Array, iteration: int) -> void:
	var selected = _get_selected_entity()
	if selected.to_lower() != entity.to_lower():
		return

	_current_entity = entity
	_iteration = iteration
	_dimensions = dims

	_display_base64(base64_png, dims)
	_update_info("")
	_color_header(entity)

	# Refresh history list since a new iteration was saved
	_fetch_history(entity)


func on_canvas_cleared(entity: String) -> void:
	if _current_entity == entity or _get_selected_entity().to_lower() == entity.to_lower():
		_texture_rect.texture = null
		_info_label.text = "%s canvas cleared" % entity
		_iteration = 0
		_fetch_history(entity)


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

func _display_base64(b64: String, dims: Array) -> void:
	var raw_bytes = Marshalls.base64_to_raw(b64)
	var img = Image.new()
	var err = img.load_png_from_buffer(raw_bytes)
	if err != OK:
		_info_label.text = "Image decode error"
		return
	var tex = ImageTexture.create_from_image(img)
	_texture_rect.texture = tex


func _update_info(filename: String) -> void:
	var w = _dimensions[0] if _dimensions.size() > 0 else 0
	var h = _dimensions[1] if _dimensions.size() > 1 else 0
	var parts = [_current_entity, "%dx%d" % [w, h]]
	if _iteration > 0:
		parts.append("iter %d" % _iteration)
	if filename != "":
		parts.append(filename)
	_info_label.text = " — ".join(parts)
	_color_header(_current_entity)


func _color_header(entity: String) -> void:
	match entity.to_lower():
		"kay":
			_header_label.add_theme_color_override("font_color", Color(0.77, 0.52, 0.75))
		"reed":
			_header_label.add_theme_color_override("font_color", Color(0.31, 0.76, 0.91))
		_:
			_header_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))


func _on_entity_changed(_idx: int) -> void:
	var entity = _get_selected_entity()
	_fetch_latest(entity)


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
