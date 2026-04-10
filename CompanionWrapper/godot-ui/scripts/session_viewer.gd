## SessionViewer - Read-only window for viewing saved sessions.
## Opens in a separate window without affecting the active chat.
## Shows both messages and terminal logs in tabs.
class_name SessionViewer
extends Window

const API_BASE := "http://localhost:8765"

var _tab_container: TabContainer
var _messages_scroll: ScrollContainer
var _messages_content: VBoxContainer
var _logs_scroll: ScrollContainer
var _logs_content: VBoxContainer
var _title_label: Label
var _close_button: Button
var _http: HTTPRequest
var _message_count: int = 0
var _current_filename: String = ""


func _init() -> void:
	title = "Session Viewer"
	size = Vector2i(700, 750)
	min_size = Vector2i(450, 400)
	transient = false
	unresizable = false


func _ready() -> void:
	_build_ui()
	close_requested.connect(_on_close_requested)


func _build_ui() -> void:
	var main_container = VBoxContainer.new()
	main_container.set_anchors_preset(Control.PRESET_FULL_RECT)
	main_container.offset_left = 8
	main_container.offset_top = 8
	main_container.offset_right = -8
	main_container.offset_bottom = -8
	add_child(main_container)

	# Header with title and close button
	var header = HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)

	_title_label = Label.new()
	_title_label.text = "Session"
	_title_label.add_theme_font_size_override("font_size", 14)
	_title_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.95))
	_title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_title_label)

	_close_button = Button.new()
	_close_button.text = "Close"
	_close_button.add_theme_font_size_override("font_size", 11)
	_close_button.pressed.connect(_on_close_requested)
	var close_style = StyleBoxFlat.new()
	close_style.bg_color = Color(0.15, 0.1, 0.1)
	close_style.set_corner_radius_all(3)
	close_style.content_margin_left = 10
	close_style.content_margin_right = 10
	close_style.content_margin_top = 4
	close_style.content_margin_bottom = 4
	_close_button.add_theme_stylebox_override("normal", close_style)
	header.add_child(_close_button)

	main_container.add_child(header)

	# Tab container
	_tab_container = TabContainer.new()
	_tab_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_tab_container.add_theme_font_size_override("font_size", 12)

	# Messages tab
	var messages_panel = PanelContainer.new()
	messages_panel.name = "Messages"
	var msg_style = StyleBoxFlat.new()
	msg_style.bg_color = Color(0.03, 0.03, 0.05)
	messages_panel.add_theme_stylebox_override("panel", msg_style)

	_messages_scroll = ScrollContainer.new()
	_messages_scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	_messages_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED

	_messages_content = VBoxContainer.new()
	_messages_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_messages_content.add_theme_constant_override("separation", 6)
	_messages_scroll.add_child(_messages_content)
	messages_panel.add_child(_messages_scroll)
	_tab_container.add_child(messages_panel)

	# Logs tab
	var logs_panel = PanelContainer.new()
	logs_panel.name = "Logs"
	var logs_style = StyleBoxFlat.new()
	logs_style.bg_color = Color(0.02, 0.02, 0.03)
	logs_panel.add_theme_stylebox_override("panel", logs_style)

	_logs_scroll = ScrollContainer.new()
	_logs_scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	_logs_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED

	_logs_content = VBoxContainer.new()
	_logs_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_logs_content.add_theme_constant_override("separation", 2)
	_logs_scroll.add_child(_logs_content)
	logs_panel.add_child(_logs_scroll)
	_tab_container.add_child(logs_panel)

	main_container.add_child(_tab_container)

	# HTTP client for logs
	_http = HTTPRequest.new()
	_http.request_completed.connect(_on_logs_received)
	add_child(_http)


func load_session(filename: String, messages: Array) -> void:
	"""Load messages into the viewer and fetch logs."""
	_current_filename = filename

	# Clear existing messages
	for child in _messages_content.get_children():
		child.queue_free()

	_message_count = messages.size()
	title = "Session: %s" % filename
	_title_label.text = "%s (%d messages)" % [filename, _message_count]

	# Add header
	var header_msg = _create_system_label("=== Session: %s ===" % filename)
	_messages_content.add_child(header_msg)

	# Add messages
	for msg in messages:
		if msg is Dictionary:
			var sender: String = msg.get("sender", "?")
			var content: String = msg.get("content", "")
			var msg_type: String = msg.get("type", msg.get("msg_type", "chat"))
			var timestamp: String = msg.get("timestamp", "")

			if msg_type == "system":
				_messages_content.add_child(_create_system_label(content))
			else:
				_messages_content.add_child(_create_message_label(sender, content, msg_type, timestamp))

	# Add footer
	var footer = _create_system_label("=== End of session (%d messages) ===" % _message_count)
	_messages_content.add_child(footer)

	# Scroll to top
	await get_tree().process_frame
	_messages_scroll.scroll_vertical = 0

	# Fetch logs for this session
	_fetch_logs(filename)


func _fetch_logs(filename: String) -> void:
	"""Fetch terminal logs for the session."""
	# Clear existing logs
	for child in _logs_content.get_children():
		child.queue_free()

	# Add loading indicator
	var loading = _create_log_label("[Fetching logs...]", "INFO")
	_logs_content.add_child(loading)

	# Request logs from server
	var url = "%s/sessions/%s/logs?lines=500" % [API_BASE, filename.uri_encode()]
	_http.request(url)


func _on_logs_received(result: int, code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	# Clear loading indicator
	for child in _logs_content.get_children():
		child.queue_free()

	if code != 200:
		var error_lbl = _create_log_label("[Failed to fetch logs: HTTP %d]" % code, "ERROR")
		_logs_content.add_child(error_lbl)
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json or not json is Dictionary:
		var error_lbl = _create_log_label("[Invalid log response]", "ERROR")
		_logs_content.add_child(error_lbl)
		return

	if not json.get("exists", false):
		var no_logs = _create_log_label("[No log file found for this session]", "INFO")
		_logs_content.add_child(no_logs)
		return

	var lines: Array = json.get("lines", [])
	var total: int = json.get("total_lines", lines.size())

	# Header
	var header = _create_log_label("=== Terminal Logs (%d lines) ===" % total, "INFO")
	_logs_content.add_child(header)

	# Add log lines
	for line in lines:
		var line_str: String = str(line).strip_edges()
		if line_str.is_empty():
			continue

		# Detect log level from line content
		var level = "DEBUG"
		if "[ERROR]" in line_str or "Error" in line_str:
			level = "ERROR"
		elif "[WARNING]" in line_str or "Warning" in line_str:
			level = "WARNING"
		elif "[INFO]" in line_str:
			level = "INFO"

		_logs_content.add_child(_create_log_label(line_str, level))

	# Scroll to bottom (most recent logs)
	await get_tree().process_frame
	_logs_scroll.scroll_vertical = _logs_scroll.get_v_scroll_bar().max_value


func _create_system_label(text: String) -> Label:
	var lbl = Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 10)
	lbl.add_theme_color_override("font_color", Color(0.4, 0.5, 0.4))
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return lbl


func _create_log_label(text: String, level: String) -> Label:
	var lbl = Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 10)
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	# Color by log level
	match level:
		"ERROR":
			lbl.add_theme_color_override("font_color", Color(0.9, 0.4, 0.4))
		"WARNING":
			lbl.add_theme_color_override("font_color", Color(0.9, 0.7, 0.3))
		"INFO":
			lbl.add_theme_color_override("font_color", Color(0.5, 0.7, 0.5))
		_:
			lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))

	return lbl


func _create_message_label(sender: String, content: String, msg_type: String, timestamp: String) -> RichTextLabel:
	var rtl = RichTextLabel.new()
	rtl.bbcode_enabled = true
	rtl.fit_content = true
	rtl.scroll_active = false
	rtl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rtl.add_theme_font_size_override("normal_font_size", 12)

	# Color based on sender
	var name_color := Color(0.6, 0.7, 0.8)  # Default
	if sender == "Kay":
		name_color = Color(0.5, 0.7, 0.9)
	elif sender == "Reed":
		name_color = Color(0.6, 0.5, 0.8)
	elif sender == "Re":
		name_color = Color(0.8, 0.8, 0.6)

	# Format message
	var time_str = ""
	if not timestamp.is_empty():
		# Extract just the time part if full ISO timestamp
		if timestamp.length() > 16:
			time_str = "[color=#555555][%s][/color] " % timestamp.substr(11, 5)

	var prefix = ""
	if msg_type == "emote":
		prefix = "[i]*"
		var suffix = "*[/i]"
		rtl.text = "%s%s[color=#%s]%s[/color] %s%s" % [
			time_str, prefix, name_color.to_html(false), sender, content, suffix
		]
	elif msg_type == "thought":
		rtl.text = "%s[color=#666666](%s thinks: %s)[/color]" % [time_str, sender, content]
	else:
		rtl.text = "%s[color=#%s][b]%s:[/b][/color] %s" % [
			time_str, name_color.to_html(false), sender, content
		]

	return rtl


func _on_close_requested() -> void:
	hide()
	queue_free()
