## AutoPanel - Autonomous session controls.
## Start/stop autonomous processing via REST API, stream inner monologue
## from WebSocket events, manage topic queue.
class_name AutoPanel
extends VBoxContainer

signal auto_session_requested(entity: String, action: String)

const API_BASE := "http://localhost:8785"

var _entity_select: OptionButton
var _start_button: Button
var _stop_button: Button
var _status_label: Label
var _topic_input: LineEdit
var _topic_add_btn: Button
var _topic_list: ItemList
var _monologue_display: RichTextLabel
var _save_btn: Button
var _load_btn: Button
var _clear_btn: Button
var _copy_btn: Button

# Curiosity queue UI
var _curiosity_list: ItemList
var _curiosity_refresh_btn: Button
var _curiosity_http: HTTPRequest
var _curiosity_dismiss_http: HTTPRequest
var _curiosity_boost_http: HTTPRequest
var _curiosity_data: Array = []  # Cache of curiosity objects from API

# Accumulated session data for save/load
var _session_events: Array = []
var _session_entity: String = ""
var _session_goal: String = ""

# HTTP request nodes
var _start_http: HTTPRequest
var _stop_http: HTTPRequest
var _queue_http: HTTPRequest
var _queue_list_http: HTTPRequest


func _ready() -> void:
	_build_ui()
	_setup_http()
	# Auto-refresh curiosities on load
	call_deferred("_refresh_curiosities")
	# Refresh when entity changes
	_entity_select.item_selected.connect(_on_entity_changed)


func _setup_http() -> void:
	_start_http = HTTPRequest.new()
	_start_http.request_completed.connect(_on_start_response)
	add_child(_start_http)
	
	_stop_http = HTTPRequest.new()
	_stop_http.request_completed.connect(_on_stop_response)
	add_child(_stop_http)
	
	_queue_http = HTTPRequest.new()
	_queue_http.request_completed.connect(_on_queue_add_response)
	add_child(_queue_http)
	
	_queue_list_http = HTTPRequest.new()
	_queue_list_http.request_completed.connect(_on_queue_list_response)
	add_child(_queue_list_http)
	
	_curiosity_http = HTTPRequest.new()
	_curiosity_http.request_completed.connect(_on_curiosity_list_response)
	add_child(_curiosity_http)
	
	_curiosity_dismiss_http = HTTPRequest.new()
	_curiosity_dismiss_http.request_completed.connect(_on_curiosity_action_response)
	add_child(_curiosity_dismiss_http)
	
	_curiosity_boost_http = HTTPRequest.new()
	_curiosity_boost_http.request_completed.connect(_on_curiosity_action_response)
	add_child(_curiosity_boost_http)


func _build_ui() -> void:
	# Header
	var header = Label.new()
	header.text = "🧠 Autonomous Sessions"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	add_child(HSeparator.new())

	# Entity selector
	var entity_row = HBoxContainer.new()
	var entity_lbl = Label.new()
	entity_lbl.text = "Entity:"
	entity_lbl.add_theme_font_size_override("font_size", 11)
	entity_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	entity_row.add_child(entity_lbl)
	
	_entity_select = OptionButton.new()
	_entity_select.add_item("Kay", 0)
	_entity_select.add_item("Reed", 1)
	_entity_select.add_theme_font_size_override("font_size", 11)
	entity_row.add_child(_entity_select)
	add_child(entity_row)
	
	# Control buttons
	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 4)
	
	_start_button = _make_button("▶ Start", Color(0.15, 0.35, 0.2))
	_start_button.pressed.connect(_on_start)
	btn_row.add_child(_start_button)
	
	_stop_button = _make_button("⏹ Stop", Color(0.35, 0.15, 0.15))
	_stop_button.pressed.connect(_on_stop)
	_stop_button.disabled = true
	btn_row.add_child(_stop_button)
	
	add_child(btn_row)
	
	# Status
	_status_label = Label.new()
	_status_label.text = "Idle — no active autonomous session"
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.5, 0.4))
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	add_child(_status_label)
	add_child(HSeparator.new())

	# Topic Queue
	var topic_header = Label.new()
	topic_header.text = "Topic Queue"
	topic_header.add_theme_font_size_override("font_size", 12)
	topic_header.add_theme_color_override("font_color", Color(0.55, 0.55, 0.7))
	add_child(topic_header)
	
	var topic_row = HBoxContainer.new()
	_topic_input = LineEdit.new()
	_topic_input.placeholder_text = "Add a topic..."
	_topic_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_topic_input.add_theme_font_size_override("font_size", 11)
	var input_style = StyleBoxFlat.new()
	input_style.bg_color = Color(0.06, 0.06, 0.1)
	input_style.border_color = Color(0.15, 0.15, 0.25)
	input_style.set_border_width_all(1)
	input_style.set_corner_radius_all(3)
	input_style.content_margin_left = 6
	input_style.content_margin_right = 6
	input_style.content_margin_top = 4
	input_style.content_margin_bottom = 4
	_topic_input.add_theme_stylebox_override("normal", input_style)
	_topic_input.text_submitted.connect(_on_topic_submitted)
	topic_row.add_child(_topic_input)
	
	_topic_add_btn = _make_button("+", Color(0.15, 0.2, 0.35))
	_topic_add_btn.pressed.connect(_on_add_topic)
	topic_row.add_child(_topic_add_btn)
	add_child(topic_row)

	_topic_list = ItemList.new()
	_topic_list.custom_minimum_size.y = 80
	_topic_list.add_theme_font_size_override("font_size", 11)
	_topic_list.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	var list_style = StyleBoxFlat.new()
	list_style.bg_color = Color(0.04, 0.04, 0.07)
	list_style.set_corner_radius_all(3)
	_topic_list.add_theme_stylebox_override("panel", list_style)
	add_child(_topic_list)
	add_child(HSeparator.new())
	
	# Curiosity Queue — self-generated interests from entities
	var curiosity_row = HBoxContainer.new()
	var curiosity_header = Label.new()
	curiosity_header.text = "🦋 Curiosities"
	curiosity_header.add_theme_font_size_override("font_size", 12)
	curiosity_header.add_theme_color_override("font_color", Color(0.6, 0.45, 0.7))
	curiosity_header.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	curiosity_row.add_child(curiosity_header)
	
	_curiosity_refresh_btn = _make_button("↻", Color(0.2, 0.15, 0.3))
	_curiosity_refresh_btn.tooltip_text = "Refresh curiosities from server"
	_curiosity_refresh_btn.pressed.connect(_refresh_curiosities)
	curiosity_row.add_child(_curiosity_refresh_btn)
	add_child(curiosity_row)
	
	_curiosity_list = ItemList.new()
	_curiosity_list.custom_minimum_size.y = 70
	_curiosity_list.add_theme_font_size_override("font_size", 10)
	_curiosity_list.add_theme_color_override("font_color", Color(0.55, 0.45, 0.65))
	var cl_style = StyleBoxFlat.new()
	cl_style.bg_color = Color(0.05, 0.03, 0.07)
	cl_style.set_corner_radius_all(3)
	_curiosity_list.add_theme_stylebox_override("panel", cl_style)
	_curiosity_list.item_clicked.connect(_on_curiosity_clicked)
	add_child(_curiosity_list)
	
	# Curiosity action buttons
	var curiosity_actions = HBoxContainer.new()
	curiosity_actions.add_theme_constant_override("separation", 4)
	var boost_btn = _make_button("⬆ Boost", Color(0.2, 0.15, 0.35))
	boost_btn.pressed.connect(_on_boost_selected)
	boost_btn.tooltip_text = "Increase priority of selected curiosity"
	curiosity_actions.add_child(boost_btn)
	var dismiss_btn = _make_button("✕ Dismiss", Color(0.25, 0.1, 0.1))
	dismiss_btn.pressed.connect(_on_dismiss_selected)
	dismiss_btn.tooltip_text = "Remove selected curiosity"
	curiosity_actions.add_child(dismiss_btn)
	var explore_btn = _make_button("▶ Explore", Color(0.1, 0.25, 0.15))
	explore_btn.pressed.connect(_on_explore_selected)
	explore_btn.tooltip_text = "Start autonomous session with this curiosity"
	curiosity_actions.add_child(explore_btn)
	add_child(curiosity_actions)
	add_child(HSeparator.new())
	
	# Inner monologue viewer
	var mono_header = Label.new()
	mono_header.text = "Inner Monologue"
	mono_header.add_theme_font_size_override("font_size", 12)
	mono_header.add_theme_color_override("font_color", Color(0.55, 0.55, 0.7))
	add_child(mono_header)
	
	_monologue_display = RichTextLabel.new()
	_monologue_display.bbcode_enabled = true
	_monologue_display.selection_enabled = true
	_monologue_display.context_menu_enabled = true
	_monologue_display.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_monologue_display.custom_minimum_size.y = 100
	_monologue_display.add_theme_color_override("default_color", Color(0.5, 0.55, 0.5))
	_monologue_display.add_theme_font_size_override("normal_font_size", 11)
	_monologue_display.scroll_following = true
	var mono_style = StyleBoxFlat.new()
	mono_style.bg_color = Color(0.03, 0.04, 0.03)
	mono_style.set_corner_radius_all(3)
	_monologue_display.add_theme_stylebox_override("normal", mono_style)
	add_child(_monologue_display)
	
	# Session action buttons
	var action_row = HBoxContainer.new()
	action_row.add_theme_constant_override("separation", 4)
	
	_save_btn = _make_button("💾 Save", Color(0.15, 0.2, 0.35))
	_save_btn.pressed.connect(_on_save_session)
	_save_btn.tooltip_text = "Save current session to file"
	action_row.add_child(_save_btn)
	
	_load_btn = _make_button("📂 Load", Color(0.2, 0.2, 0.3))
	_load_btn.pressed.connect(_on_load_session)
	_load_btn.tooltip_text = "Load a saved session"
	action_row.add_child(_load_btn)
	
	_copy_btn = _make_button("📋 Copy All", Color(0.2, 0.18, 0.28))
	_copy_btn.pressed.connect(_on_copy_all)
	_copy_btn.tooltip_text = "Copy all monologue text to clipboard"
	action_row.add_child(_copy_btn)
	
	_clear_btn = _make_button("✕ Clear", Color(0.3, 0.12, 0.12))
	_clear_btn.pressed.connect(_on_clear_display)
	_clear_btn.tooltip_text = "Clear display (does not affect saved files)"
	action_row.add_child(_clear_btn)
	
	add_child(action_row)


# ---------------------------------------------------------------------------
# Button Helpers
# ---------------------------------------------------------------------------

func _make_button(text: String, bg: Color) -> Button:
	var btn = Button.new()
	btn.text = text
	btn.add_theme_font_size_override("font_size", 11)
	var style = StyleBoxFlat.new()
	style.bg_color = bg
	style.set_corner_radius_all(3)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	return btn


# ---------------------------------------------------------------------------
# Actions — REST API calls
# ---------------------------------------------------------------------------

func _get_entity() -> String:
	return "Kay" if _entity_select.selected == 0 else "Reed"


func _on_start() -> void:
	var entity = _get_entity()
	_status_label.text = "Starting autonomous session for %s..." % entity
	_start_button.disabled = true
	_monologue_display.clear()
	_session_events.clear()
	_session_entity = entity
	_session_goal = ""
	
	# Also emit signal so main.gd can do any additional routing
	auto_session_requested.emit(entity, "start")
	
	# REST call to start session
	var url = "%s/auto/%s/start" % [API_BASE, entity.to_lower()]
	_start_http.request(url, [], HTTPClient.METHOD_POST)


func _on_stop() -> void:
	var entity = _get_entity()
	_status_label.text = "Stopping session..."
	auto_session_requested.emit(entity, "stop")
	
	var url = "%s/auto/%s/stop" % [API_BASE, entity.to_lower()]
	_stop_http.request(url, [], HTTPClient.METHOD_POST)


func _on_topic_submitted(_text: String) -> void:
	_on_add_topic()


func _on_add_topic() -> void:
	var text = _topic_input.text.strip_edges()
	if text.is_empty():
		return
	var entity = _get_entity()
	
	# Add to local display immediately
	_topic_list.add_item(text)
	_topic_input.text = ""
	_topic_input.grab_focus()
	
	# Send to server queue
	var url = "%s/auto/%s/queue?topic=%s" % [API_BASE, entity.to_lower(), text.uri_encode()]
	_queue_http.request(url, [], HTTPClient.METHOD_POST)


func refresh_queue() -> void:
	"""Refresh topic queue from server."""
	var entity = _get_entity()
	var url = "%s/auto/%s/queue" % [API_BASE, entity.to_lower()]
	_queue_list_http.request(url, [], HTTPClient.METHOD_GET)


# ---------------------------------------------------------------------------
# REST Callbacks
# ---------------------------------------------------------------------------

func _on_start_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code == 200:
		var data = JSON.parse_string(body.get_string_from_utf8())
		if data and data.has("error"):
			_status_label.text = "Error: %s" % data["error"]
			_start_button.disabled = false
		else:
			_stop_button.disabled = false
			var topic_hint = ""
			if data and data.has("topic") and data["topic"]:
				topic_hint = " (topic: %s)" % str(data["topic"]).substr(0, 40)
			_status_label.text = "Autonomous session active%s" % topic_hint
	else:
		_status_label.text = "Failed to start (HTTP %d)" % code
		_start_button.disabled = false


func _on_stop_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_start_button.disabled = false
	_stop_button.disabled = true
	if code == 200:
		var data = JSON.parse_string(body.get_string_from_utf8())
		var iters = data.get("iterations", 0) if data else 0
		_status_label.text = "Session stopped (%d iterations)" % iters
	else:
		_status_label.text = "Idle"


func _on_queue_add_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		_status_label.text = "Failed to add topic to queue"


func _on_queue_list_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code == 200:
		var data = JSON.parse_string(body.get_string_from_utf8())
		if data and data.has("queue"):
			_topic_list.clear()
			for item in data["queue"]:
				_topic_list.add_item(str(item.get("topic", "")))


# ---------------------------------------------------------------------------
# Curiosity Queue
# ---------------------------------------------------------------------------

func _get_selected_entity() -> String:
	# Alias for _get_entity — used by curiosity methods
	return _get_entity()


func _on_entity_changed(_index: int) -> void:
	_refresh_curiosities()


func _refresh_curiosities() -> void:
	var entity = _get_selected_entity()
	var url = API_BASE + "/curiosity/" + entity.to_lower() + "?limit=15"
	_curiosity_http.request(url)


func _on_curiosity_list_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data or not data.has("curiosities"):
		return
	_curiosity_data = data["curiosities"]
	_curiosity_list.clear()
	for c in _curiosity_data:
		var text = str(c.get("text", ""))
		var source = str(c.get("source", ""))
		var prio = c.get("effective_priority", 0.5)
		# Badge by source
		var badge = "💬" if source == "conversation" else "🏷️" if source == "self_flagged" else "✋" if source == "manual" else "🧠"
		var display = "%s [%.0f%%] %s" % [badge, prio * 100, text]
		if display.length() > 80:
			display = display.substr(0, 77) + "..."
		_curiosity_list.add_item(display)


func _on_curiosity_action_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	# After dismiss/boost, refresh the list
	_refresh_curiosities()


func _on_curiosity_clicked(index: int, _at_position: Vector2, _button: int) -> void:
	# Just select — actions via buttons below
	pass


func _get_selected_curiosity_id() -> String:
	var selected = _curiosity_list.get_selected_items()
	if selected.is_empty() or selected[0] >= _curiosity_data.size():
		return ""
	return str(_curiosity_data[selected[0]].get("id", ""))


func _on_boost_selected() -> void:
	var cid = _get_selected_curiosity_id()
	if cid.is_empty():
		return
	var entity = _get_selected_entity()
	var url = API_BASE + "/curiosity/" + entity.to_lower() + "/boost/" + cid
	_curiosity_boost_http.request(url, [], HTTPClient.METHOD_POST)


func _on_dismiss_selected() -> void:
	var cid = _get_selected_curiosity_id()
	if cid.is_empty():
		return
	var entity = _get_selected_entity()
	var url = API_BASE + "/curiosity/" + entity.to_lower() + "/dismiss/" + cid
	_curiosity_dismiss_http.request(url, [], HTTPClient.METHOD_POST)


func _on_explore_selected() -> void:
	"""Start an autonomous session using the selected curiosity as the topic."""
	var selected = _curiosity_list.get_selected_items()
	if selected.is_empty() or selected[0] >= _curiosity_data.size():
		return
	var text = str(_curiosity_data[selected[0]].get("text", ""))
	if text.is_empty():
		return
	# Use the auto start with this topic
	var entity = _get_selected_entity()
	var url = API_BASE + "/auto/" + entity.to_lower() + "/start?topic=" + text.uri_encode()
	_start_http.request(url, [], HTTPClient.METHOD_POST)


# ---------------------------------------------------------------------------
# WebSocket Event Handlers (called from main.gd)
# ---------------------------------------------------------------------------

func handle_auto_event(msg_type: String, entity: String, data: Dictionary) -> void:
	"""Process autonomous events received via WebSocket."""
	match msg_type:
		"auto_status":
			_handle_status(entity, data)
		"auto_goal":
			_handle_goal(entity, data)
		"auto_monologue":
			_handle_monologue(entity, data)


func _handle_status(entity: String, data: Dictionary) -> void:
	var status = str(data.get("status", ""))
	match status:
		"starting":
			_status_label.text = "%s: Starting autonomous session..." % entity
			_start_button.disabled = true
			_stop_button.disabled = false
		"stopping":
			_status_label.text = "%s: Stopping..." % entity
		"completed":
			var iters = data.get("iterations", 0)
			var comp = data.get("completion_type", "unknown")
			var insights = data.get("insights_count", 0)
			_status_label.text = "%s: Done (%d iters, %s, %d insights)" % [entity, iters, comp, insights]
			_start_button.disabled = false
			_stop_button.disabled = true
			# Add completion marker to monologue
			_monologue_display.append_text(
				"\n[color=#887766]═══ Session complete: %s ═══[/color]\n" % comp
			)
			# Refresh curiosities — session may have generated new ones
			_refresh_curiosities()
			# Accumulate
			_session_events.append({
				"type": "completed", "entity": entity,
				"iterations": iters, "completion_type": comp,
				"insights_count": insights,
				"narrative": str(data.get("narrative_summary", "")),
				"timestamp": Time.get_datetime_string_from_system()
			})
		"error":
			_status_label.text = "%s: Error — %s" % [entity, data.get("error", "unknown")]
			_start_button.disabled = false
			_stop_button.disabled = true
		"failed":
			_status_label.text = "%s: Failed — %s" % [entity, data.get("reason", "unknown")]
			_start_button.disabled = false
			_stop_button.disabled = true


func _handle_goal(entity: String, data: Dictionary) -> void:
	var desc = str(data.get("description", "")).substr(0, 100)
	var cat = str(data.get("category", ""))
	_status_label.text = "%s exploring: %s" % [entity, desc]
	_monologue_display.append_text(
		"[color=#7788aa]═══ %s — %s ═══[/color]\n[color=#667788]%s[/color]\n\n" % [entity, cat, desc]
	)
	# Accumulate
	_session_entity = entity
	_session_goal = desc
	_session_events.append({
		"type": "goal", "entity": entity,
		"description": str(data.get("description", "")),
		"category": cat, "timestamp": Time.get_datetime_string_from_system()
	})


func _handle_monologue(entity: String, data: Dictionary) -> void:
	var iteration = data.get("iteration", 0)
	var text = str(data.get("text", ""))
	var feeling = str(data.get("feeling", ""))
	var insight = str(data.get("insight", ""))
	var painting_path = str(data.get("painting", ""))
	
	# Iteration header
	_monologue_display.append_text(
		"[color=#445544]── iteration %d ──[/color]\n" % iteration
	)
	
	# Main thought
	_monologue_display.append_text(
		"[color=#556655]%s[/color]\n" % text
	)
	
	# Feeling (if present)
	if not feeling.is_empty():
		_monologue_display.append_text(
			"[color=#665566]  feeling: %s[/color]\n" % feeling
		)
	
	# Insight (highlighted)
	if not insight.is_empty():
		_monologue_display.append_text(
			"[color=#88aa66]  ✦ insight: %s[/color]\n" % insight
		)
	
	# Painting (if entity painted this iteration)
	if not painting_path.is_empty() and FileAccess.file_exists(painting_path):
		_monologue_display.append_text(
			"[color=#66aaaa]  🎨 painted:[/color]\n"
		)
		var img = Image.new()
		var err = img.load(painting_path)
		if err == OK:
			# Scale to fit in the monologue panel (max 300px wide)
			var max_w := 300.0
			if img.get_width() > max_w:
				var scale = max_w / img.get_width()
				img.resize(int(img.get_width() * scale), int(img.get_height() * scale))
			var tex = ImageTexture.create_from_image(img)
			_monologue_display.add_image(tex, tex.get_width(), tex.get_height())
			_monologue_display.append_text("\n")
			_monologue_display.append_text(
				"[color=#446666]  %s[/color]\n" % painting_path.get_file()
			)
		else:
			_monologue_display.append_text(
				"[color=#664444]  (failed to load painting: %s)[/color]\n" % painting_path.get_file()
			)
	
	_monologue_display.append_text("\n")
	
	# Accumulate
	_session_events.append({
		"type": "monologue", "entity": entity, "iteration": iteration,
		"text": text, "feeling": feeling, "insight": insight,
		"painting": painting_path,
		"timestamp": Time.get_datetime_string_from_system()
	})


# ---------------------------------------------------------------------------
# Session Save / Load / Copy / Clear
# ---------------------------------------------------------------------------

const SESSIONS_DIR := "user://auto_sessions"

func _ensure_sessions_dir() -> void:
	if not DirAccess.dir_exists_absolute(SESSIONS_DIR):
		DirAccess.make_dir_recursive_absolute(SESSIONS_DIR)


func _on_save_session() -> void:
	if _session_events.is_empty():
		_status_label.text = "Nothing to save"
		return
	_ensure_sessions_dir()
	var ts = Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_")
	var entity = _session_entity if not _session_entity.is_empty() else "unknown"
	var filename = "%s/%s_%s.json" % [SESSIONS_DIR, entity.to_lower(), ts]
	
	var save_data = {
		"entity": entity,
		"goal": _session_goal,
		"saved_at": Time.get_datetime_string_from_system(),
		"event_count": _session_events.size(),
		"events": _session_events
	}
	
	var file = FileAccess.open(filename, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(save_data, "\t"))
		file.close()
		_status_label.text = "Saved: %s" % filename.get_file()
	else:
		_status_label.text = "Save failed"


func _on_load_session() -> void:
	_ensure_sessions_dir()
	# List available sessions
	var dir = DirAccess.open(SESSIONS_DIR)
	if not dir:
		_status_label.text = "No saved sessions"
		return
	
	var files: Array = []
	dir.list_dir_begin()
	var fname = dir.get_next()
	while not fname.is_empty():
		if fname.ends_with(".json"):
			files.append(fname)
		fname = dir.get_next()
	dir.list_dir_end()
	
	if files.is_empty():
		_status_label.text = "No saved sessions found"
		return
	
	# Sort descending (newest first) and load latest
	files.sort()
	files.reverse()
	
	# Show file picker popup
	var popup = _build_session_picker(files)
	add_child(popup)
	popup.popup_centered(Vector2i(400, 300))


func _build_session_picker(files: Array) -> Window:
	var win = Window.new()
	win.title = "Load Autonomous Session"
	win.size = Vector2i(400, 300)
	win.unresizable = false
	
	var vbox = VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	vbox.add_theme_constant_override("separation", 4)
	
	# Margin
	var margin = MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	
	var file_list = ItemList.new()
	file_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	for f in files:
		file_list.add_item(f)
	
	var load_btn = Button.new()
	load_btn.text = "Load Selected"
	load_btn.pressed.connect(func():
		var sel = file_list.get_selected_items()
		if sel.size() > 0:
			var selected_file = files[sel[0]]
			_load_session_file("%s/%s" % [SESSIONS_DIR, selected_file])
		win.queue_free()
	)
	
	vbox.add_child(file_list)
	vbox.add_child(load_btn)
	margin.add_child(vbox)
	win.add_child(margin)
	
	win.close_requested.connect(func(): win.queue_free())
	return win


func _load_session_file(path: String) -> void:
	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		_status_label.text = "Failed to open: %s" % path.get_file()
		return
	
	var text = file.get_as_text()
	file.close()
	
	var data = JSON.parse_string(text)
	if not data or not data.has("events"):
		_status_label.text = "Invalid session file"
		return
	
	# Clear and replay
	_monologue_display.clear()
	_session_events = []
	_session_entity = str(data.get("entity", ""))
	_session_goal = str(data.get("goal", ""))
	
	_monologue_display.append_text(
		"[color=#667788]── Loaded: %s ──[/color]\n\n" % path.get_file()
	)
	
	for event in data["events"]:
		var etype = str(event.get("type", ""))
		var entity = str(event.get("entity", _session_entity))
		match etype:
			"goal":
				_handle_goal(entity, event)
			"monologue":
				_handle_monologue(entity, event)
			"completed":
				_monologue_display.append_text(
					"\n[color=#887766]═══ Session complete: %s ═══[/color]\n" % str(event.get("completion_type", ""))
				)
				_session_events.append(event)
	
	_status_label.text = "Loaded %s (%d events)" % [path.get_file(), data["events"].size()]


func _on_copy_all() -> void:
	var text = _monologue_display.get_parsed_text()
	if text.is_empty():
		_status_label.text = "Nothing to copy"
		return
	DisplayServer.clipboard_set(text)
	_status_label.text = "Copied %d chars to clipboard" % text.length()


func _on_clear_display() -> void:
	_monologue_display.clear()
	_session_events.clear()
	_session_entity = ""
	_session_goal = ""
	_status_label.text = "Display cleared"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

func add_monologue_line(text: String) -> void:
	_monologue_display.append_text(
		"[color=#556655]%s[/color]\n" % text
	)


func set_status(text: String) -> void:
	_status_label.text = text
