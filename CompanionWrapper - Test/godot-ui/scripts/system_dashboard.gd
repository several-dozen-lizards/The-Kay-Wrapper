## SystemDashboard - Real-time categorized log feeds from Kay, Reed, and Nexus.
## 10-feed grid layout with entity filtering, pause/resume, and export.
class_name SystemDashboard
extends Control

## Feed category definitions
const FEED_CATEGORIES = {
	"oscillator": {
		"title": "Oscillator",
		"tags": ["RESONANCE", "SPATIAL", "OSC", "RESONANCE INJECT", "PHASE"],
		"color": Color(0.6, 0.4, 0.8),
	},
	"vision": {
		"title": "Vision",
		"tags": ["VISUAL", "VISUAL->SOMA", "SACCADE", "ROOM"],
		"color": Color(0.3, 0.7, 0.5),
	},
	"memory": {
		"title": "Memory",
		"tags": ["MEMORY TRIM", "MEMORY 2-TIER", "MEMORY", "MEMORY LAYERS", "RAG", "RAG TRIM", "RECALL TRUNCATION", "RECALL CHECKPOINT", "MEMORY USAGE", "VECTOR_DB", "FOREST", "PURGE", "LAYERS", "VECTOR"],
		"color": Color(0.3, 0.5, 0.8),
	},
	"emotion": {
		"title": "Emotion",
		"tags": ["EMOTION", "EMOTION ENGINE", "EMOTION STORAGE", "EMOTION PATTERNS", "PATTERNS", "VALENCE", "AFFECT"],
		"color": Color(0.8, 0.3, 0.5),
	},
	"stream": {
		"title": "Stream",
		"tags": ["STREAM", "THROTTLE", "INTEROCEPTION", "CONSCIOUSNESS", "CREATIVITY", "TENSION"],
		"color": Color(0.3, 0.6, 0.7),
	},
	"llm": {
		"title": "LLM",
		"tags": ["TEMPERATURE", "LLM", "CACHE", "CACHE MODE", "CACHE SAVINGS", "USAGE", "PERF", "PERF WARNING", "RETRIEVAL", "CONDUCTANCE"],
		"color": Color(0.8, 0.7, 0.3),
	},
	"entity_graph": {
		"title": "Graph",
		"tags": ["ENTITY", "ENTITY GRAPH", "ENTITY OBSERVATION", "OWNERSHIP GROUND_TRUTH", "GRAPH"],
		"color": Color(0.5, 0.7, 0.4),
	},
	"chat_flow": {
		"title": "Chat Flow",
		"tags": ["PACER", "THREAD", "MODE", "WAKE", "PRIVATE", "AUTO", "CURIOSITY"],
		"color": Color(0.85, 0.8, 0.7),
	},
	"nexus": {
		"title": "Nexus",
		"tags": ["CONNECTION", "COMMAND", "SESSION", "HISTORY", "NEXUS", "SERVER"],
		"color": Color(0.65, 0.65, 0.7),
	},
	"system": {
		"title": "System",
		"tags": ["BRIDGE", "STARTUP", "TOOLS", "WEB TOOLS", "SESSION SUMMARY", "CURATOR", "IDENTITY", "RELATIONSHIP", "DOC READER", "SPIRAL", "LLM RETRIEVAL", "ERROR", "WARNING"],
		"color": Color(0.5, 0.5, 0.6),
	},
}

## Feed display order (left-to-right, top-to-bottom in 2-column grid)
const FEED_ORDER = [
	"oscillator", "vision",
	"memory", "emotion",
	"stream", "llm",
	"entity_graph", "chat_flow",
	"nexus", "system"
]

## Entity colors for BBCode
const ENTITY_COLORS = {
	"kay": "#c484c0",   # purple-pink
	"reed": "#4fc2e8",  # teal
	"nexus": "#a0a5b0", # silver-blue
}

## Max lines per feed before trimming
const MAX_LINES = 60
const TRIM_TO = 50

## Feed state
var _feeds: Dictionary = {}  # category_key -> {rtl: RichTextLabel, counter: Label, lines: int}
var _tag_to_category: Dictionary = {}  # tag -> category_key
var _paused: bool = false
var _entity_filter: int = 0  # 0=All, 1=Kay, 2=Reed, 3=Nexus
var _pause_buffer: Array = []

## UI refs
var _entity_dropdown: OptionButton
var _pause_button: Button
var _export_button: Button


func _ready() -> void:
	_build_tag_lookup()
	_build_ui()


func _build_tag_lookup() -> void:
	for category_key in FEED_CATEGORIES:
		var cat = FEED_CATEGORIES[category_key]
		for tag in cat["tags"]:
			_tag_to_category[tag.to_upper()] = category_key


func _build_ui() -> void:
	# Main layout
	var vbox = VBoxContainer.new()
	vbox.set_anchors_preset(PRESET_FULL_RECT)
	vbox.add_theme_constant_override("separation", 4)
	add_child(vbox)

	# --- Toolbar ---
	var toolbar = HBoxContainer.new()
	toolbar.custom_minimum_size.y = 28
	toolbar.add_theme_constant_override("separation", 8)
	vbox.add_child(toolbar)

	var title = Label.new()
	title.text = "System Dashboard"
	title.add_theme_color_override("font_color", Color(0.7, 0.75, 0.8))
	toolbar.add_child(title)

	toolbar.add_child(_create_spacer())

	# Entity filter dropdown
	_entity_dropdown = OptionButton.new()
	_entity_dropdown.add_item("All", 0)
	_entity_dropdown.add_item("Kay", 1)
	_entity_dropdown.add_item("Reed", 2)
	_entity_dropdown.add_item("Nexus", 3)
	_entity_dropdown.selected = 0
	_entity_dropdown.item_selected.connect(_on_filter_changed)
	_entity_dropdown.add_theme_color_override("font_color", Color(0.7, 0.7, 0.75))
	toolbar.add_child(_entity_dropdown)

	# Pause/Resume button
	_pause_button = Button.new()
	_pause_button.text = "Pause"
	_pause_button.flat = true
	_pause_button.toggle_mode = true
	_pause_button.add_theme_color_override("font_color", Color(0.6, 0.6, 0.65))
	_pause_button.toggled.connect(_on_pause_toggled)
	toolbar.add_child(_pause_button)

	# Export button
	_export_button = Button.new()
	_export_button.text = "Export"
	_export_button.flat = true
	_export_button.add_theme_color_override("font_color", Color(0.6, 0.6, 0.65))
	_export_button.pressed.connect(_on_export_pressed)
	toolbar.add_child(_export_button)

	# --- Feed grid inside scroll container ---
	var scroll = ScrollContainer.new()
	scroll.size_flags_vertical = SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	vbox.add_child(scroll)

	var grid = GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = SIZE_EXPAND_FILL
	grid.size_flags_vertical = SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 4)
	grid.add_theme_constant_override("v_separation", 4)
	scroll.add_child(grid)

	# Create feed boxes in order
	for category_key in FEED_ORDER:
		var feed_box = _create_feed_box(category_key)
		grid.add_child(feed_box)


func _create_spacer() -> Control:
	var spacer = Control.new()
	spacer.size_flags_horizontal = SIZE_EXPAND_FILL
	return spacer


func _create_feed_box(category_key: String) -> PanelContainer:
	var cat = FEED_CATEGORIES[category_key]
	var cat_color: Color = cat["color"]

	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(280, 160)
	panel.size_flags_horizontal = SIZE_EXPAND_FILL

	# Dark background style
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.1, 0.95)
	style.border_color = Color(0.15, 0.15, 0.2)
	style.set_border_width_all(1)
	style.border_width_top = 3
	style.border_color = cat_color
	style.corner_radius_top_left = 3
	style.corner_radius_top_right = 3
	panel.add_theme_stylebox_override("panel", style)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	panel.add_child(vbox)

	# Header with title and line counter
	var header = HBoxContainer.new()
	header.custom_minimum_size.y = 20
	vbox.add_child(header)

	var title_label = Label.new()
	title_label.text = cat["title"]
	title_label.add_theme_color_override("font_color", cat_color)
	title_label.add_theme_font_size_override("font_size", 13)
	header.add_child(title_label)

	header.add_child(_create_spacer())

	var counter = Label.new()
	counter.text = "0"
	counter.add_theme_color_override("font_color", Color(0.4, 0.4, 0.45))
	counter.add_theme_font_size_override("font_size", 10)
	header.add_child(counter)

	# Separator
	var sep = HSeparator.new()
	sep.add_theme_color_override("separation", Color(0.2, 0.2, 0.25))
	vbox.add_child(sep)

	# RichTextLabel for log content
	var rtl = RichTextLabel.new()
	rtl.bbcode_enabled = true
	rtl.scroll_following = true
	rtl.size_flags_horizontal = SIZE_EXPAND_FILL
	rtl.size_flags_vertical = SIZE_EXPAND_FILL
	rtl.fit_content = false
	rtl.add_theme_color_override("default_color", Color(0.7, 0.7, 0.75))
	rtl.add_theme_font_size_override("normal_font_size", 11)
	vbox.add_child(rtl)

	# Store refs
	_feeds[category_key] = {
		"rtl": rtl,
		"counter": counter,
		"lines": 0
	}

	return panel


func _on_filter_changed(index: int) -> void:
	_entity_filter = index


func _on_pause_toggled(pressed: bool) -> void:
	_paused = pressed
	_pause_button.text = "Resume" if pressed else "Pause"
	if not pressed and not _pause_buffer.is_empty():
		# Flush buffered logs
		for entry in _pause_buffer:
			_process_log(entry[0], entry[1], entry[2], entry[3])
		_pause_buffer.clear()


func _on_export_pressed() -> void:
	# Export all feed content to clipboard
	var output = PackedStringArray()
	output.append("=== System Dashboard Export ===\n")
	for category_key in FEED_ORDER:
		if _feeds.has(category_key):
			var cat = FEED_CATEGORIES[category_key]
			var rtl: RichTextLabel = _feeds[category_key]["rtl"]
			output.append("\n--- %s ---\n" % cat["title"])
			output.append(rtl.get_parsed_text())
	DisplayServer.clipboard_set("\n".join(output))
	# Visual feedback
	var original = _export_button.text
	_export_button.text = "Copied!"
	_export_button.add_theme_color_override("font_color", Color(0.5, 0.8, 0.5))
	await get_tree().create_timer(1.5).timeout
	_export_button.text = original
	_export_button.add_theme_color_override("font_color", Color(0.6, 0.6, 0.65))


## Public API - called by main.gd when log signals fire
func add_log(entity: String, tag: String, message: String, ts: float) -> void:
	# Filter by entity
	var entity_lower = entity.to_lower()
	match _entity_filter:
		1:  # Kay only
			if entity_lower != "kay":
				return
		2:  # Reed only
			if entity_lower != "reed":
				return
		3:  # Nexus only
			if entity_lower != "nexus":
				return

	# Buffer if paused
	if _paused:
		_pause_buffer.append([entity, tag, message, ts])
		if _pause_buffer.size() > 500:
			_pause_buffer = _pause_buffer.slice(-400)
		return

	_process_log(entity, tag, message, ts)


func _process_log(entity: String, tag: String, message: String, ts: float) -> void:
	var tag_upper = tag.to_upper()

	# Route to category
	var category_key = _tag_to_category.get(tag_upper, "system")
	if not _feeds.has(category_key):
		category_key = "system"

	var feed = _feeds[category_key]
	var rtl: RichTextLabel = feed["rtl"]
	var counter: Label = feed["counter"]

	# Format timestamp
	var time_str = _format_time(ts)

	# Entity color
	var entity_lower = entity.to_lower()
	var entity_color = ENTITY_COLORS.get(entity_lower, "#a0a0a0")

	# Category color
	var cat_color = FEED_CATEGORIES[category_key]["color"]
	var cat_hex = "#%02x%02x%02x" % [int(cat_color.r * 255), int(cat_color.g * 255), int(cat_color.b * 255)]

	# Build BBCode line
	var line = "[color=#404045]%s[/color] " % time_str
	line += "[color=%s][%s][/color] " % [entity_color, entity.to_upper()]
	line += "[color=%s][%s][/color] " % [cat_hex, tag_upper]
	line += "%s\n" % _escape_bbcode(message)

	rtl.append_text(line)
	feed["lines"] += 1
	counter.text = str(feed["lines"])

	# Trim if over limit
	if feed["lines"] > MAX_LINES:
		_trim_feed(feed)


func _format_time(ts: float) -> String:
	if ts <= 0:
		return "--:--:--"
	var dt = Time.get_datetime_dict_from_unix_time(int(ts))
	return "%02d:%02d:%02d" % [dt.hour, dt.minute, dt.second]


func _escape_bbcode(text: String) -> String:
	return text.replace("[", "[lb]").replace("]", "[rb]")


func _trim_feed(feed: Dictionary) -> void:
	var rtl: RichTextLabel = feed["rtl"]
	var text = rtl.get_parsed_text()
	var lines = text.split("\n")
	if lines.size() > MAX_LINES:
		rtl.clear()
		var keep = lines.slice(-TRIM_TO)
		for line in keep:
			if not line.is_empty():
				rtl.append_text(line + "\n")
		feed["lines"] = keep.size()
		feed["counter"].text = str(feed["lines"])


## Legacy handler for old logs_received format (backward compat)
func handle_logs(entries: Array) -> void:
	for entry in entries:
		if entry is Dictionary:
			add_log(
				entry.get("entity", ""),
				entry.get("tag", "SYSTEM"),
				entry.get("message", ""),
				entry.get("ts", 0.0)
			)
