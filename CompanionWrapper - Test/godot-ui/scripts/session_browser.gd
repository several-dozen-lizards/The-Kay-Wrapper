## SessionBrowser - Browse and load saved conversation sessions.
## Fetches session list from server REST API, displays them,
## and can open in viewer or load into active chat.
class_name SessionBrowser
extends VBoxContainer

signal session_load_requested(filename: String, messages: Array)
signal session_open_requested(filename: String, messages: Array)

const API_BASE := "http://localhost:8785"

var _http: HTTPRequest
var _load_http: HTTPRequest
var _session_list: ItemList
var _status_label: Label
var _open_button: Button
var _load_button: Button
var _save_button: Button
var _refresh_button: Button
var _current_session_label: Label
var _confirm_dialog: ConfirmationDialog
var _pending_load_filename: String = ""
var _pending_load_messages: Array = []
var _action_mode: String = "open"  # "open" or "load"


func _ready() -> void:
	_build_ui()
	# Auto-refresh on show
	visibility_changed.connect(_on_visibility_changed)


func _build_ui() -> void:
	# Header
	var header = Label.new()
	header.text = "📚 Sessions"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	
	var sep = HSeparator.new()
	add_child(sep)
	
	# Current session info
	_current_session_label = Label.new()
	_current_session_label.text = "Current: ..."
	_current_session_label.add_theme_font_size_override("font_size", 10)
	_current_session_label.add_theme_color_override("font_color", Color(0.4, 0.6, 0.4))
	_current_session_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(_current_session_label)
	
	# Button row 1: Refresh and Save
	var btn_row1 = HBoxContainer.new()
	btn_row1.add_theme_constant_override("separation", 4)

	_refresh_button = _make_button("↻ Refresh")
	_refresh_button.pressed.connect(_refresh_sessions)
	btn_row1.add_child(_refresh_button)

	_save_button = _make_button("💾 Save Now")
	_save_button.pressed.connect(_save_current)
	btn_row1.add_child(_save_button)

	add_child(btn_row1)

	# Button row 2: Open and Load
	var btn_row2 = HBoxContainer.new()
	btn_row2.add_theme_constant_override("separation", 4)

	_open_button = _make_button("👁 Open")
	_open_button.tooltip_text = "Open in separate viewer window"
	_open_button.pressed.connect(_open_selected)
	_open_button.disabled = true
	btn_row2.add_child(_open_button)

	_load_button = _make_button("📂 Load")
	_load_button.tooltip_text = "Load into active chat (replaces current)"
	_load_button.pressed.connect(_request_load_selected)
	_load_button.disabled = true
	btn_row2.add_child(_load_button)

	add_child(btn_row2)

	# Confirmation dialog
	_confirm_dialog = ConfirmationDialog.new()
	_confirm_dialog.title = "Load Session?"
	_confirm_dialog.dialog_text = "This will clear the current chat and load the selected session.\n\nContinue?"
	_confirm_dialog.ok_button_text = "Load"
	_confirm_dialog.cancel_button_text = "Cancel"
	_confirm_dialog.confirmed.connect(_on_load_confirmed)
	add_child(_confirm_dialog)
	
	# Session list
	_session_list = ItemList.new()
	_session_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_session_list.custom_minimum_size.y = 200
	_session_list.allow_reselect = true
	_session_list.item_selected.connect(_on_item_selected)
	_session_list.item_activated.connect(_on_item_activated)
	
	var list_style = StyleBoxFlat.new()
	list_style.bg_color = Color(0.04, 0.04, 0.07)
	list_style.border_color = Color(0.12, 0.12, 0.2)
	list_style.set_border_width_all(1)
	list_style.set_corner_radius_all(3)
	_session_list.add_theme_stylebox_override("panel", list_style)
	_session_list.add_theme_color_override("font_color", Color(0.65, 0.65, 0.75))
	_session_list.add_theme_color_override("font_selected_color", Color(0.9, 0.9, 1.0))
	_session_list.add_theme_font_size_override("font_size", 11)
	add_child(_session_list)
	
	# Status
	_status_label = Label.new()
	_status_label.text = "Click Refresh to load sessions"
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(_status_label)
	
	# HTTP clients
	_http = HTTPRequest.new()
	_http.request_completed.connect(_on_list_received)
	add_child(_http)
	
	_load_http = HTTPRequest.new()
	_load_http.request_completed.connect(_on_session_loaded)
	add_child(_load_http)


func _make_button(text: String) -> Button:
	var btn = Button.new()
	btn.text = text
	btn.add_theme_font_size_override("font_size", 11)
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.1, 0.18)
	style.border_color = Color(0.2, 0.2, 0.3)
	style.set_border_width_all(1)
	style.set_corner_radius_all(3)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	return btn


func _on_visibility_changed() -> void:
	if visible:
		_refresh_sessions()


func _refresh_sessions() -> void:
	_status_label.text = "Loading..."
	_session_list.clear()
	var err = _http.request(API_BASE + "/sessions")
	if err != OK:
		_status_label.text = "Request failed (server running?)"


func _save_current() -> void:
	_status_label.text = "Saving..."
	var save_http = HTTPRequest.new()
	save_http.request_completed.connect(_on_save_done.bind(save_http))
	add_child(save_http)
	save_http.request(API_BASE + "/save", [], HTTPClient.METHOD_POST)


func _on_save_done(result: int, code: int, headers: PackedStringArray, 
		body: PackedByteArray, http_node: HTTPRequest) -> void:
	http_node.queue_free()
	if code == 200:
		_status_label.text = "Session saved!"
		_refresh_sessions()
	else:
		_status_label.text = "Save failed (code %d)" % code


func _on_list_received(result: int, code: int, headers: PackedStringArray,
		body: PackedByteArray) -> void:
	if code != 200:
		_status_label.text = "Failed to load (code %d)" % code
		return
	
	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or not json is Dictionary:
		_status_label.text = "Invalid response"
		return
	
	# Update current session info
	var current = json.get("current_session", "?")
	var msg_count = json.get("message_count", 0)
	_current_session_label.text = "Current: %s (%d msgs)" % [current, msg_count]
	
	# Populate list
	_session_list.clear()
	var files: Array = json.get("saved_files", [])
	for f in files:
		var name: String = f.get("name", "?")
		var size_bytes: int = f.get("size", 0)
		var size_str = _format_size(size_bytes)
		var modified: String = f.get("modified", "")
		var date_str = modified.substr(0, 10) if modified.length() >= 10 else "?"
		
		var display = "%s  (%s, %s)" % [name, size_str, date_str]
		_session_list.add_item(display)
		_session_list.set_item_metadata(_session_list.item_count - 1, name)
	
	_status_label.text = "%d session files" % files.size()
	_open_button.disabled = true
	_load_button.disabled = true


func _on_item_selected(index: int) -> void:
	_open_button.disabled = false
	_load_button.disabled = false


func _on_item_activated(index: int) -> void:
	# Double-click = open in viewer (non-destructive)
	_open_selected()


func _open_selected() -> void:
	"""Open selected session in a separate viewer window."""
	var idx = _session_list.get_selected_items()
	if idx.is_empty():
		return
	var filename: String = _session_list.get_item_metadata(idx[0])
	_action_mode = "open"
	_status_label.text = "Opening %s..." % filename
	var err = _load_http.request(API_BASE + "/sessions/" + filename.uri_encode())
	if err != OK:
		_status_label.text = "Open request failed"


func _request_load_selected() -> void:
	"""Show confirmation dialog before loading into active chat."""
	var idx = _session_list.get_selected_items()
	if idx.is_empty():
		return
	var filename: String = _session_list.get_item_metadata(idx[0])
	_pending_load_filename = filename
	_confirm_dialog.dialog_text = "This will clear the current Nexus chat and load:\n\n%s\n\nContinue?" % filename
	_confirm_dialog.popup_centered()


func _on_load_confirmed() -> void:
	"""User confirmed load - fetch and load the session."""
	if _pending_load_filename.is_empty():
		return
	_action_mode = "load"
	_status_label.text = "Loading %s..." % _pending_load_filename
	var err = _load_http.request(API_BASE + "/sessions/" + _pending_load_filename.uri_encode())
	if err != OK:
		_status_label.text = "Load request failed"


func _on_session_loaded(result: int, code: int, headers: PackedStringArray,
		body: PackedByteArray) -> void:
	if code != 200:
		_status_label.text = "Load failed (code %d)" % code
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or not json is Dictionary:
		_status_label.text = "Invalid session data"
		return

	var messages: Array = json.get("messages", [])
	var filename: String = json.get("filename", "?")

	if _action_mode == "open":
		_status_label.text = "Opened %s (%d messages)" % [filename, messages.size()]
		session_open_requested.emit(filename, messages)
	else:  # load
		_status_label.text = "Loaded %s (%d messages)" % [filename, messages.size()]
		session_load_requested.emit(filename, messages)
		_pending_load_filename = ""
		_pending_load_messages = []


func _format_size(bytes: int) -> String:
	if bytes < 1024:
		return "%d B" % bytes
	elif bytes < 1024 * 1024:
		return "%.1f KB" % (bytes / 1024.0)
	else:
		return "%.1f MB" % (bytes / (1024.0 * 1024.0))
