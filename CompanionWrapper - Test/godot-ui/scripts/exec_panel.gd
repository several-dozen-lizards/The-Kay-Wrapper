## ExecPanel - Code execution safety admin panel.
## Polls REST API for entity execution status, pending approvals,
## execution log, and file access log. Allows approve/deny/revert.
class_name ExecPanel
extends VBoxContainer

const API_BASE := "http://localhost:8785"
const REFRESH_INTERVAL := 5.0

# UI elements
var _entity_select: OptionButton
var _refresh_btn: Button
var _scroll: ScrollContainer
var _content: VBoxContainer

# Sections
var _status_section: VBoxContainer
var _status_label: RichTextLabel
var _pending_section: VBoxContainer
var _pending_list: VBoxContainer
var _log_section: VBoxContainer
var _log_label: RichTextLabel
var _access_section: VBoxContainer
var _access_label: RichTextLabel

# HTTP nodes
var _status_http: HTTPRequest
var _pending_http: HTTPRequest
var _log_http: HTTPRequest
var _access_http: HTTPRequest

# State
var _auto_timer: Timer
var _last_entity: String = "Kay"
var _action_in_flight: bool = false  # Prevent double-clicks
var _mode_toggle_btn: Button = null  # Persistent — no more rabbit breeding


func _ready() -> void:
	_build_ui()
	_setup_http()
	_setup_timer()
	call_deferred("_fetch_all")


func _setup_http() -> void:
	_status_http = HTTPRequest.new()
	_status_http.request_completed.connect(_on_status_response)
	add_child(_status_http)
	
	_pending_http = HTTPRequest.new()
	_pending_http.request_completed.connect(_on_pending_response)
	add_child(_pending_http)
	
	_log_http = HTTPRequest.new()
	_log_http.request_completed.connect(_on_log_response)
	add_child(_log_http)
	
	_access_http = HTTPRequest.new()
	_access_http.request_completed.connect(_on_access_response)
	add_child(_access_http)


## Create a fresh HTTPRequest for one-shot actions (approve/deny/mode).
## Avoids ERR_BUSY from reusing a single node.
func _make_action_request(url: String) -> void:
	var http = HTTPRequest.new()
	http.request_completed.connect(_on_action_response.bind(http))
	add_child(http)
	var err = http.request(url, [], HTTPClient.METHOD_POST)
	if err != OK:
		push_warning("ExecPanel: action request failed: %s" % err)
		http.queue_free()
		_action_in_flight = false


func _setup_timer() -> void:
	_auto_timer = Timer.new()
	_auto_timer.wait_time = REFRESH_INTERVAL
	_auto_timer.autostart = false
	_auto_timer.timeout.connect(_on_auto_refresh)
	add_child(_auto_timer)


func _build_ui() -> void:
	# Header row
	var header = HBoxContainer.new()
	
	var title = Label.new()
	title.text = "🔒 Code Exec"
	title.add_theme_font_size_override("font_size", 16)
	title.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	header.add_child(title)
	
	var spacer = Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	
	_entity_select = OptionButton.new()
	_entity_select.add_item("Kay")
	_entity_select.add_item("Reed")
	_entity_select.custom_minimum_size.x = 80
	_entity_select.item_selected.connect(_on_entity_changed)
	_apply_input_style(_entity_select)
	header.add_child(_entity_select)
	
	_refresh_btn = Button.new()
	_refresh_btn.text = "🔄"
	_refresh_btn.custom_minimum_size = Vector2(32, 28)
	_refresh_btn.pressed.connect(_on_refresh_pressed)
	_apply_button_style(_refresh_btn)
	header.add_child(_refresh_btn)
	
	add_child(header)
	add_child(HSeparator.new())
	
	# Scrollable content
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	
	_content = VBoxContainer.new()
	_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_content.add_theme_constant_override("separation", 8)
	_scroll.add_child(_content)
	add_child(_scroll)
	
	_build_status_section()
	_build_pending_section()
	_build_log_section()
	_build_access_section()


func _build_status_section() -> void:
	_status_section = _make_section("⚙️ Status")
	_status_label = RichTextLabel.new()
	_status_label.bbcode_enabled = true
	_status_label.fit_content = true
	_status_label.scroll_active = false
	_status_label.add_theme_font_size_override("normal_font_size", 11)
	_status_label.add_theme_color_override("default_color", Color(0.7, 0.7, 0.8))
	_status_label.text = "Loading..."
	_status_section.add_child(_status_label)
	_content.add_child(_status_section)


func _build_pending_section() -> void:
	_pending_section = _make_section("⏳ Pending Approvals")
	_pending_list = VBoxContainer.new()
	_pending_list.add_theme_constant_override("separation", 4)
	_pending_section.add_child(_pending_list)
	_content.add_child(_pending_section)


func _build_log_section() -> void:
	_log_section = _make_section("📋 Execution Log")
	_log_label = RichTextLabel.new()
	_log_label.bbcode_enabled = true
	_log_label.fit_content = true
	_log_label.scroll_active = false
	_log_label.add_theme_font_size_override("normal_font_size", 10)
	_log_label.add_theme_color_override("default_color", Color(0.6, 0.65, 0.7))
	_log_label.text = "—"
	_log_section.add_child(_log_label)
	_content.add_child(_log_section)


func _build_access_section() -> void:
	_access_section = _make_section("🔐 File Access Log")
	_access_label = RichTextLabel.new()
	_access_label.bbcode_enabled = true
	_access_label.fit_content = true
	_access_label.scroll_active = false
	_access_label.add_theme_font_size_override("normal_font_size", 10)
	_access_label.add_theme_color_override("default_color", Color(0.6, 0.65, 0.7))
	_access_label.text = "—"
	_access_section.add_child(_access_label)
	_content.add_child(_access_section)


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------

func _make_section(title: String) -> VBoxContainer:
	var section = VBoxContainer.new()
	section.add_theme_constant_override("separation", 4)
	var lbl = Label.new()
	lbl.text = title
	lbl.add_theme_font_size_override("font_size", 13)
	lbl.add_theme_color_override("font_color", Color(0.55, 0.6, 0.75))
	section.add_child(lbl)
	section.add_child(HSeparator.new())
	return section


func _apply_button_style(btn: Button) -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.12, 0.12, 0.18)
	style.border_color = Color(0.2, 0.2, 0.3)
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.content_margin_left = 6
	style.content_margin_right = 6
	btn.add_theme_stylebox_override("normal", style)
	var hover = style.duplicate()
	hover.bg_color = Color(0.18, 0.18, 0.28)
	btn.add_theme_stylebox_override("hover", hover)


func _apply_input_style(input: Control) -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.12)
	style.border_color = Color(0.2, 0.2, 0.3)
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.content_margin_left = 8
	style.content_margin_right = 8
	if input is LineEdit:
		input.add_theme_stylebox_override("normal", style)
	elif input is OptionButton:
		input.add_theme_stylebox_override("normal", style)


func _apply_approve_style(btn: Button) -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.25, 0.15)
	style.border_color = Color(0.2, 0.45, 0.25)
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.content_margin_left = 8
	style.content_margin_right = 8
	btn.add_theme_stylebox_override("normal", style)
	var hover = style.duplicate()
	hover.bg_color = Color(0.15, 0.35, 0.2)
	btn.add_theme_stylebox_override("hover", hover)
	btn.add_theme_color_override("font_color", Color(0.5, 0.9, 0.5))


func _apply_deny_style(btn: Button) -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.25, 0.1, 0.1)
	style.border_color = Color(0.45, 0.2, 0.2)
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.content_margin_left = 8
	style.content_margin_right = 8
	btn.add_theme_stylebox_override("normal", style)
	var hover = style.duplicate()
	hover.bg_color = Color(0.35, 0.15, 0.15)
	btn.add_theme_stylebox_override("hover", hover)
	btn.add_theme_color_override("font_color", Color(0.9, 0.5, 0.5))


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

func _get_entity() -> String:
	return "Kay" if _entity_select.selected == 0 else "Reed"


func _fetch_all() -> void:
	_fetch_status()
	_fetch_pending()
	_fetch_log()
	_fetch_access()


func _fetch_status() -> void:
	var entity = _get_entity().to_lower()
	_status_http.request("%s/exec/%s/status" % [API_BASE, entity])


func _fetch_pending() -> void:
	var entity = _get_entity().to_lower()
	_pending_http.request("%s/exec/%s/pending" % [API_BASE, entity])


func _fetch_log() -> void:
	var entity = _get_entity().to_lower()
	_log_http.request("%s/exec/%s/log?n=15" % [API_BASE, entity])


func _fetch_access() -> void:
	var entity = _get_entity().to_lower()
	_access_http.request("%s/exec/%s/access-log?n=20" % [API_BASE, entity])


# ---------------------------------------------------------------------------
# HTTP Response Handlers
# ---------------------------------------------------------------------------

func _on_status_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		_status_label.text = "[color=#FF6B6B]Server unavailable[/color]"
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data:
		return
	
	var mode: String = data.get("mode", "?")
	var mode_color = "#51CF66" if mode == "autonomous" else "#FFD43B"
	var mode_icon = "🟢" if mode == "autonomous" else "🟡"
	
	var text = "%s Mode: [color=%s][b]%s[/b][/color]\n" % [mode_icon, mode_color, mode]
	
	# Write paths
	var write_paths: Array = data.get("allowed_write_paths", [])
	if write_paths.size() > 0:
		text += "[color=#888899]Extra write paths:[/color]\n"
		for p in write_paths:
			text += "  📁 %s\n" % p
	else:
		text += "[color=#888899]Writes: scratch only[/color]\n"
	
	# Blocked patterns
	var blocked: Array = data.get("blocked_patterns", [])
	if blocked.size() > 0:
		text += "[color=#888899]Blocked patterns: %d[/color]\n" % blocked.size()
	
	# Recent exec summary
	var recent: Array = data.get("recent_executions", [])
	var snap_count: int = data.get("snapshot_count", 0)
	text += "[color=#888899]Recent executions: %d | Snapshots: %d[/color]\n" % [recent.size(), snap_count]
	
	# Pending count
	var pending: Array = data.get("pending_executions", [])
	if pending.size() > 0:
		text += "[color=#FFD43B]⚠ %d pending approval[/color]\n" % pending.size()
	
	# Mode toggle button
	_status_label.text = text.strip_edges()
	
	# Update persistent mode toggle button (create once, update in place)
	var new_mode = "autonomous" if mode == "supervised" else "supervised"
	if not _mode_toggle_btn or not is_instance_valid(_mode_toggle_btn):
		_mode_toggle_btn = Button.new()
		_mode_toggle_btn.custom_minimum_size = Vector2(0, 28)
		_status_section.add_child(_mode_toggle_btn)
	
	_mode_toggle_btn.text = "Switch to %s" % new_mode
	# Clear all old signal connections and rebind with current mode
	for conn in _mode_toggle_btn.pressed.get_connections():
		_mode_toggle_btn.pressed.disconnect(conn["callable"])
	_mode_toggle_btn.pressed.connect(_on_mode_toggle.bind(new_mode))
	if new_mode == "autonomous":
		_apply_approve_style(_mode_toggle_btn)
	else:
		_apply_deny_style(_mode_toggle_btn)


func _on_pending_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data:
		return
	
	# Clear existing pending items
	for child in _pending_list.get_children():
		child.queue_free()
	
	var pending: Array = data.get("pending", [])
	if pending.size() == 0:
		var lbl = Label.new()
		lbl.text = "No pending executions"
		lbl.add_theme_font_size_override("font_size", 11)
		lbl.add_theme_color_override("font_color", Color(0.4, 0.5, 0.4))
		_pending_list.add_child(lbl)
		return
	
	# Approve All button at top
	if pending.size() > 1:
		var all_btn = Button.new()
		all_btn.text = "✅ Approve All (%d)" % pending.size()
		all_btn.custom_minimum_size = Vector2(0, 28)
		_apply_approve_style(all_btn)
		all_btn.pressed.connect(_on_approve_all.bind(all_btn))
		_pending_list.add_child(all_btn)
	
	for item in pending:
		var exec_id: String = item.get("exec_id", "?")
		var desc: String = item.get("description", "")
		var code_preview: String = item.get("code", "")
		var timestamp: String = item.get("timestamp", "")
		
		# Container for this pending item
		var item_box = VBoxContainer.new()
		item_box.add_theme_constant_override("separation", 2)
		
		# Styled background
		var bg = StyleBoxFlat.new()
		bg.bg_color = Color(0.08, 0.08, 0.14, 0.8)
		bg.border_color = Color(0.25, 0.25, 0.4, 0.6)
		bg.set_border_width_all(1)
		bg.set_corner_radius_all(4)
		bg.content_margin_left = 8
		bg.content_margin_right = 8
		bg.content_margin_top = 6
		bg.content_margin_bottom = 6
		
		var panel_cont = PanelContainer.new()
		panel_cont.add_theme_stylebox_override("panel", bg)
		
		var inner = VBoxContainer.new()
		inner.add_theme_constant_override("separation", 4)
		
		# Header: ID + timestamp
		var header_lbl = RichTextLabel.new()
		header_lbl.bbcode_enabled = true
		header_lbl.fit_content = true
		header_lbl.scroll_active = false
		header_lbl.add_theme_font_size_override("normal_font_size", 10)
		var short_id = exec_id.substr(0, 20) if exec_id.length() > 20 else exec_id
		var time_part = timestamp.substr(11, 8) if timestamp.length() > 19 else timestamp
		header_lbl.text = "[color=#B794F6]%s[/color]  [color=#555566]%s[/color]" % [short_id, time_part]
		inner.add_child(header_lbl)
		
		# Description
		if desc:
			var desc_lbl = Label.new()
			desc_lbl.text = desc
			desc_lbl.add_theme_font_size_override("font_size", 11)
			desc_lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
			desc_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
			inner.add_child(desc_lbl)
		
		# Code preview (truncated)
		if code_preview:
			var preview = code_preview.substr(0, 200)
			if code_preview.length() > 200:
				preview += "..."
			var code_lbl = RichTextLabel.new()
			code_lbl.bbcode_enabled = true
			code_lbl.fit_content = true
			code_lbl.scroll_active = false
			code_lbl.add_theme_font_size_override("normal_font_size", 9)
			code_lbl.text = "[color=#6BB6B6][code]%s[/code][/color]" % preview
			inner.add_child(code_lbl)
		
		# Action buttons
		var btn_row = HBoxContainer.new()
		btn_row.add_theme_constant_override("separation", 6)
		
		var approve_btn = Button.new()
		approve_btn.text = "✅ Approve"
		approve_btn.custom_minimum_size = Vector2(0, 26)
		_apply_approve_style(approve_btn)
		approve_btn.pressed.connect(_on_approve.bind(exec_id, approve_btn))
		btn_row.add_child(approve_btn)
		
		var deny_btn = Button.new()
		deny_btn.text = "❌ Deny"
		deny_btn.custom_minimum_size = Vector2(0, 26)
		_apply_deny_style(deny_btn)
		deny_btn.pressed.connect(_on_deny.bind(exec_id, deny_btn))
		btn_row.add_child(deny_btn)
		
		inner.add_child(btn_row)
		panel_cont.add_child(inner)
		_pending_list.add_child(panel_cont)


func _on_log_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data:
		return
	
	var entries: Array = data.get("entries", [])
	if entries.size() == 0:
		_log_label.text = "[color=#555566]No executions yet[/color]"
		return
	
	var text = ""
	for entry in entries:
		var action: String = entry.get("action", "?")
		var success = entry.get("success", false)
		var timestamp: String = entry.get("timestamp", "")
		var time_part = timestamp.substr(11, 8) if timestamp.length() > 19 else timestamp
		var desc: String = entry.get("description", "")
		var exec_time = entry.get("execution_time", 0)
		var files: Array = entry.get("files_created", [])
		
		var icon = "✓" if success else "✗" if action == "executed" else "⏳" if action == "queued" else "⊘"
		var color = "#51CF66" if success else "#FF6B6B" if action == "executed" else "#FFD43B" if action == "queued" else "#888899"
		
		text += "[color=%s]%s[/color] [color=#555566]%s[/color]" % [color, icon, time_part]
		if desc:
			text += " %s" % desc.substr(0, 40)
		if exec_time > 0:
			text += " [color=#555566](%.1fs)[/color]" % exec_time
		if files.size() > 0:
			text += " [color=#6BB6B6]→ %s[/color]" % ", ".join(files)
		text += "\n"
	
	_log_label.text = text.strip_edges()


func _on_access_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data:
		return
	
	var entries: Array = data.get("entries", [])
	if entries.size() == 0:
		_access_label.text = "[color=#555566]No file access yet[/color]"
		return
	
	var text = ""
	for entry in entries:
		var allowed = entry.get("allowed", false)
		var action: String = entry.get("action", "?")
		var path: String = entry.get("path", "?")
		var timestamp: String = entry.get("timestamp", "")
		var time_part = timestamp.substr(11, 8) if timestamp.length() > 19 else timestamp
		
		# Shorten path for display
		var short_path = path
		if short_path.length() > 50:
			short_path = "..." + short_path.substr(short_path.length() - 47)
		
		if allowed:
			text += "[color=#51CF66]✓[/color] [color=#555566]%s[/color] %s\n" % [time_part, short_path]
		else:
			text += "[color=#FF6B6B]✗ BLOCKED[/color] [color=#555566]%s[/color] %s\n" % [time_part, short_path]
	
	_access_label.text = text.strip_edges()


func _on_action_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray, http: HTTPRequest) -> void:
	# Free the one-shot HTTP node
	http.queue_free()
	_action_in_flight = false
	# After any action, refresh immediately
	_fetch_all()


# ---------------------------------------------------------------------------
# Action Handlers
# ---------------------------------------------------------------------------

func _on_approve(exec_id: String, btn: Button) -> void:
	if _action_in_flight:
		return
	_action_in_flight = true
	btn.text = "⏳ Approving..."
	btn.disabled = true
	var entity = _get_entity().to_lower()
	_make_action_request("%s/exec/%s/approve/%s" % [API_BASE, entity, exec_id])


func _on_deny(exec_id: String, btn: Button) -> void:
	if _action_in_flight:
		return
	_action_in_flight = true
	btn.text = "⏳ Denying..."
	btn.disabled = true
	var entity = _get_entity().to_lower()
	_make_action_request("%s/exec/%s/deny/%s" % [API_BASE, entity, exec_id])


func _on_approve_all(btn: Button) -> void:
	if _action_in_flight:
		return
	_action_in_flight = true
	btn.text = "⏳ Approving all..."
	btn.disabled = true
	var entity = _get_entity().to_lower()
	_make_action_request("%s/exec/%s/approve-all" % [API_BASE, entity])


func _on_mode_toggle(new_mode: String) -> void:
	if _action_in_flight:
		return
	_action_in_flight = true
	var entity = _get_entity().to_lower()
	_make_action_request("%s/exec/%s/mode/%s" % [API_BASE, entity, new_mode])


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

func _on_entity_changed(_idx: int) -> void:
	_fetch_all()


func _on_refresh_pressed() -> void:
	_fetch_all()


func _on_auto_refresh() -> void:
	_fetch_all()


# ---------------------------------------------------------------------------
# Visibility & Timer
# ---------------------------------------------------------------------------

func start_polling() -> void:
	if not _auto_timer:
		return
	_fetch_all()
	_auto_timer.start()


func stop_polling() -> void:
	if not _auto_timer:
		return
	_auto_timer.stop()


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED:
		if is_visible_in_tree():
			start_polling()
		else:
			stop_polling()
