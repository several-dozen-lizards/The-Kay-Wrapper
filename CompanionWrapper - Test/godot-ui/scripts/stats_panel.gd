## StatsPanel - System statistics and entity graph browser.
## Polls REST API for wrapper state, displays in human-readable format.
class_name StatsPanel
extends VBoxContainer

const API_BASE := "http://localhost:8785"
const REFRESH_INTERVAL := 10.0  # seconds between auto-polls

var _entity_select: OptionButton
var _refresh_btn: Button
var _scroll: ScrollContainer
var _content: VBoxContainer

# Section containers
var _emotions_section: VBoxContainer
var _emotions_label: RichTextLabel
var _momentum_section: VBoxContainer
var _momentum_label: Label
var _saccade_section: VBoxContainer
var _saccade_label: RichTextLabel
var _memory_section: VBoxContainer
var _memory_label: RichTextLabel
var _entities_section: VBoxContainer
var _entities_list: VBoxContainer
var _entity_search_input: LineEdit
var _entity_detail_label: RichTextLabel

# HTTP nodes
var _stats_http: HTTPRequest
var _entities_http: HTTPRequest
var _detail_http: HTTPRequest
var _search_http: HTTPRequest

# State
var _auto_timer: Timer
var _last_entity: String = "Kay"


func _ready() -> void:
	_build_ui()
	_setup_http()
	_setup_timer()
	# Initial fetch
	call_deferred("_fetch_stats")
	call_deferred("_fetch_entities")


func _setup_http() -> void:
	_stats_http = HTTPRequest.new()
	_stats_http.request_completed.connect(_on_stats_response)
	add_child(_stats_http)
	
	_entities_http = HTTPRequest.new()
	_entities_http.request_completed.connect(_on_entities_response)
	add_child(_entities_http)
	
	_detail_http = HTTPRequest.new()
	_detail_http.request_completed.connect(_on_detail_response)
	add_child(_detail_http)
	
	_search_http = HTTPRequest.new()
	_search_http.request_completed.connect(_on_search_response)
	add_child(_search_http)


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
	title.text = "📊 Stats"
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
	
	# Build sections
	_build_emotions_section()
	_build_momentum_section()
	_build_saccade_section()
	_build_memory_section()
	_build_entities_section()


func _build_emotions_section() -> void:
	_emotions_section = _make_section("💜 Emotions")
	_emotions_label = RichTextLabel.new()
	_emotions_label.bbcode_enabled = true
	_emotions_label.fit_content = true
	_emotions_label.scroll_active = false
	_emotions_label.add_theme_font_size_override("normal_font_size", 11)
	_emotions_label.add_theme_color_override("default_color", Color(0.7, 0.7, 0.8))
	_emotions_label.text = "Waiting for data..."
	_emotions_section.add_child(_emotions_label)
	_content.add_child(_emotions_section)


func _build_momentum_section() -> void:
	_momentum_section = _make_section("⚡ Momentum")
	_momentum_label = Label.new()
	_momentum_label.add_theme_font_size_override("font_size", 12)
	_momentum_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	_momentum_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_momentum_label.text = "—"
	_momentum_section.add_child(_momentum_label)
	_content.add_child(_momentum_section)


func _build_saccade_section() -> void:
	_saccade_section = _make_section("🔄 Saccade Engine")
	_saccade_label = RichTextLabel.new()
	_saccade_label.bbcode_enabled = true
	_saccade_label.fit_content = true
	_saccade_label.scroll_active = false
	_saccade_label.add_theme_font_size_override("normal_font_size", 11)
	_saccade_label.add_theme_color_override("default_color", Color(0.6, 0.7, 0.7))
	_saccade_label.text = "—"
	_saccade_section.add_child(_saccade_label)
	_content.add_child(_saccade_section)


func _build_memory_section() -> void:
	_memory_section = _make_section("🧠 Memory Layers")
	_memory_label = RichTextLabel.new()
	_memory_label.bbcode_enabled = true
	_memory_label.fit_content = true
	_memory_label.scroll_active = false
	_memory_label.add_theme_font_size_override("normal_font_size", 11)
	_memory_label.add_theme_color_override("default_color", Color(0.6, 0.65, 0.75))
	_memory_label.text = "—"
	_memory_section.add_child(_memory_label)
	_content.add_child(_memory_section)


func _build_entities_section() -> void:
	_entities_section = _make_section("🌐 Entity Graph")
	
	# Search bar
	var search_row = HBoxContainer.new()
	_entity_search_input = LineEdit.new()
	_entity_search_input.placeholder_text = "Search entities..."
	_entity_search_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_entity_search_input.custom_minimum_size.y = 28
	_apply_input_style(_entity_search_input)
	_entity_search_input.text_submitted.connect(_on_entity_search)
	search_row.add_child(_entity_search_input)
	_entities_section.add_child(search_row)
	
	# Entity list (clickable items)
	_entities_list = VBoxContainer.new()
	_entities_list.add_theme_constant_override("separation", 2)
	_entities_section.add_child(_entities_list)
	
	# Detail view (shown when entity clicked)
	_entity_detail_label = RichTextLabel.new()
	_entity_detail_label.bbcode_enabled = true
	_entity_detail_label.fit_content = true
	_entity_detail_label.scroll_active = false
	_entity_detail_label.add_theme_font_size_override("normal_font_size", 11)
	_entity_detail_label.add_theme_color_override("default_color", Color(0.7, 0.7, 0.8))
	_entity_detail_label.visible = false
	_entities_section.add_child(_entity_detail_label)
	
	_content.add_child(_entities_section)


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


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

func _get_entity() -> String:
	return "Kay" if _entity_select.selected == 0 else "Reed"


func _fetch_stats() -> void:
	var entity = _get_entity().to_lower()
	var url = "%s/stats/%s" % [API_BASE, entity]
	_stats_http.request(url, [], HTTPClient.METHOD_GET)


func _fetch_entities() -> void:
	var entity = _get_entity().to_lower()
	var url = "%s/entities/%s?top_n=20" % [API_BASE, entity]
	_entities_http.request(url, [], HTTPClient.METHOD_GET)


func _fetch_entity_detail(entity_name: String) -> void:
	var entity = _get_entity().to_lower()
	var url = "%s/entities/%s/%s" % [API_BASE, entity, entity_name.uri_encode()]
	_detail_http.request(url, [], HTTPClient.METHOD_GET)


func _search_entities(query: String) -> void:
	var entity = _get_entity().to_lower()
	var url = "%s/entities/%s/search/%s" % [API_BASE, entity, query.uri_encode()]
	_search_http.request(url, [], HTTPClient.METHOD_GET)


# ---------------------------------------------------------------------------
# HTTP Callbacks
# ---------------------------------------------------------------------------

func _on_stats_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data or data.has("error"):
		return
	
	# Update emotions
	var emo_text = ""
	var emotions = data.get("emotions", [])
	if emotions.size() == 0:
		emo_text = "[color=#555566]No active emotions[/color]"
	else:
		for emo in emotions:
			var intensity: float = emo.get("intensity", 0)
			var bar_len = int(intensity * 10)
			var bar = "█".repeat(bar_len) + "░".repeat(10 - bar_len)
			var valence: float = emo.get("valence", 0)
			var v_color = "#51CF66" if valence > 0 else "#FF6B6B" if valence < 0 else "#888899"
			emo_text += "[color=%s]%s[/color] %s [color=#888899]%.0f%%[/color]\n" % [
				v_color, emo.get("name", "?"), bar, intensity * 100
			]
	_emotions_label.text = emo_text.strip_edges()
	
	# Update momentum
	var mom = data.get("momentum", {})
	_momentum_label.text = mom.get("display", "—")
	
	# Update saccade
	var saccade = data.get("saccade")
	if saccade and saccade.get("active", false):
		var s_text = "[color=#6BB6B6]Active[/color] — Turn %d\n" % saccade.get("turn", 0)
		var delta = saccade.get("last_delta", "")
		if delta:
			s_text += "[color=#888899]Last delta:[/color] %s\n" % delta
		var vectors = saccade.get("vectors", [])
		if vectors.size() > 0:
			s_text += "[color=#888899]Open vectors:[/color] %s" % ", ".join(vectors)
		_saccade_label.text = s_text.strip_edges()
	else:
		_saccade_label.text = "[color=#555566]Inactive[/color]"
	
	# Update memory
	var mem_layers = data.get("memory", [])
	if mem_layers.size() == 0:
		_memory_label.text = "[color=#555566]No memory data[/color]"
	else:
		var m_text = ""
		for layer in mem_layers:
			m_text += "[color=#B794F6]%s[/color]: %d entries\n" % [
				layer.get("layer", "?"), layer.get("count", 0)
			]
		_memory_label.text = m_text.strip_edges()


func _on_entities_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data or data.has("error"):
		return
	
	# Clear existing entity list
	for child in _entities_list.get_children():
		child.queue_free()
	
	var entities = data.get("entities", [])
	for ent in entities:
		var btn = Button.new()
		var ent_name: String = ent.get("name", "?")
		var ent_type: String = ent.get("type", "")
		var importance: float = ent.get("importance", 0)
		var desc: String = ent.get("one_liner", "")
		
		# Type icon
		var icon = _type_icon(ent_type)
		var label_text = "%s %s" % [icon, ent_name]
		if desc:
			label_text += "  [%s]" % desc
		
		btn.text = label_text
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		btn.custom_minimum_size.y = 26
		_apply_entity_button_style(btn, importance)
		btn.pressed.connect(_on_entity_clicked.bind(ent_name))
		_entities_list.add_child(btn)
	
	# Show total count
	var total = data.get("total_entities", 0)
	var showing = data.get("showing", 0)
	if total > showing:
		var more_lbl = Label.new()
		more_lbl.text = "... and %d more (use search)" % (total - showing)
		more_lbl.add_theme_font_size_override("font_size", 10)
		more_lbl.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
		_entities_list.add_child(more_lbl)



func _on_detail_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data or data.has("error"):
		_entity_detail_label.text = "[color=#FF6B6B]Entity not found[/color]"
		_entity_detail_label.visible = true
		return
	
	var text = ""
	var ent_name: String = data.get("name", "?")
	var ent_type: String = data.get("type", "")
	text += "[b][color=#B794F6]%s %s[/color][/b]\n" % [_type_icon(ent_type), ent_name]
	text += "[color=#555566]Type: %s  |  Importance: %.1f  |  Accessed: %d times[/color]\n\n" % [
		ent_type, data.get("importance", 0), data.get("access_count", 0)
	]
	
	# Descriptions
	var descriptions: Array = data.get("descriptions", [])
	if descriptions.size() > 0:
		for desc in descriptions:
			text += "• %s\n" % desc
		text += "\n"
	
	# Recent changes
	var recent: Array = data.get("recent_changes", [])
	if recent.size() > 0:
		text += "[color=#6BB6B6]Recent changes:[/color]\n"
		for change in recent:
			text += "  → %s\n" % change
		text += "\n"
	
	# Relationships
	var rels: Array = data.get("relationships", [])
	if rels.size() > 0:
		text += "[color=#F0A0D0]Relationships:[/color]\n"
		for rel in rels:
			text += "  %s\n" % rel.get("sentence", "?")
		text += "\n"
	
	# Attribute counts
	text += "[color=#888899]Total attributes: %d[/color]" % data.get("attribute_count", 0)
	
	_entity_detail_label.text = text
	_entity_detail_label.visible = true


func _on_search_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data:
		return
	
	# Clear existing list and show search results
	for child in _entities_list.get_children():
		child.queue_free()
	
	var results: Array = data.get("results", [])
	if results.size() == 0:
		var lbl = Label.new()
		lbl.text = "No results for '%s'" % data.get("query", "")
		lbl.add_theme_font_size_override("font_size", 11)
		lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
		_entities_list.add_child(lbl)
		return
	
	for res in results:
		var btn = Button.new()
		var res_name: String = res.get("name", "?")
		var res_type: String = res.get("type", "")
		var importance: float = res.get("importance", 0)
		btn.text = "%s %s" % [_type_icon(res_type), res_name]
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		btn.custom_minimum_size.y = 26
		_apply_entity_button_style(btn, importance)
		btn.pressed.connect(_on_entity_clicked.bind(res_name))
		_entities_list.add_child(btn)
	
	# Back to full list button
	var back_btn = Button.new()
	back_btn.text = "← Show all entities"
	back_btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	back_btn.custom_minimum_size.y = 26
	_apply_button_style(back_btn)
	back_btn.pressed.connect(_fetch_entities)
	_entities_list.add_child(back_btn)


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

func _on_entity_changed(_idx: int) -> void:
	_entity_detail_label.visible = false
	_fetch_stats()
	_fetch_entities()


func _on_refresh_pressed() -> void:
	_fetch_stats()
	_fetch_entities()


func _on_entity_search(query: String) -> void:
	if query.strip_edges().is_empty():
		_fetch_entities()
	else:
		_search_entities(query.strip_edges())


func _on_entity_clicked(entity_name: String) -> void:
	_fetch_entity_detail(entity_name)


func _on_auto_refresh() -> void:
	_fetch_stats()


# ---------------------------------------------------------------------------
# Entity Helpers
# ---------------------------------------------------------------------------

func _type_icon(entity_type: String) -> String:
	match entity_type.to_lower():
		"person": return "👤"
		"animal": return "🐾"
		"place": return "📍"
		"concept": return "💡"
		"emotion": return "💜"
		"object": return "📦"
		"event": return "📅"
		"ai_entity": return "🤖"
		"group": return "👥"
		"memory": return "🧠"
		"project": return "🔧"
		_: return "◆"


func _apply_entity_button_style(btn: Button, importance: float) -> void:
	var style = StyleBoxFlat.new()
	# Importance affects brightness
	var brightness = clampf(importance / 10.0, 0.05, 0.25)
	style.bg_color = Color(brightness * 0.6, brightness * 0.5, brightness * 1.0, 0.6)
	style.border_color = Color(0.15, 0.15, 0.25, 0.5)
	style.set_border_width_all(1)
	style.set_corner_radius_all(3)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 2
	style.content_margin_bottom = 2
	btn.add_theme_stylebox_override("normal", style)
	var hover = style.duplicate()
	hover.bg_color = Color(brightness * 0.8, brightness * 0.7, brightness * 1.2, 0.8)
	hover.border_color = Color(0.3, 0.3, 0.5)
	btn.add_theme_stylebox_override("hover", hover)
	btn.add_theme_font_size_override("font_size", 11)


# ---------------------------------------------------------------------------
# Visibility & Timer
# ---------------------------------------------------------------------------

func start_polling() -> void:
	"""Call when panel becomes visible."""
	if not _auto_timer:
		return
	_fetch_stats()
	_fetch_entities()
	_auto_timer.start()


func stop_polling() -> void:
	"""Call when panel is hidden."""
	if not _auto_timer:
		return
	_auto_timer.stop()


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED:
		if is_visible_in_tree():
			start_polling()
		else:
			stop_polling()
