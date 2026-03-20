## CuratePanel - Memory curation tools.
## View, edit, and manage entity memory stores.
## Content-type-aware: can handle semantic memories, episodic logs, emotional snapshots.
class_name CuratePanel
extends VBoxContainer

signal curate_action(entity: String, action: String, data: Dictionary)

var _entity_select: OptionButton
var _memory_type_select: OptionButton
var _search_input: LineEdit
var _results_list: RichTextLabel
var _status_label: Label


func _ready() -> void:
	_build_ui()


func _build_ui() -> void:
	var header = Label.new()
	header.text = "📋 Memory Curation"
	header.add_theme_font_size_override("font_size", 15)
	header.add_theme_color_override("font_color", Color(0.7, 0.7, 0.85))
	add_child(header)
	add_child(HSeparator.new())
	
	# Entity selector
	var row1 = HBoxContainer.new()
	row1.add_theme_constant_override("separation", 8)
	
	var e_lbl = Label.new()
	e_lbl.text = "Entity:"
	e_lbl.add_theme_font_size_override("font_size", 11)
	e_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	row1.add_child(e_lbl)
	
	_entity_select = OptionButton.new()
	_entity_select.add_item("Kay")
	_entity_select.add_item("Reed")
	_entity_select.add_theme_font_size_override("font_size", 11)
	row1.add_child(_entity_select)
	
	var t_lbl = Label.new()
	t_lbl.text = "Type:"
	t_lbl.add_theme_font_size_override("font_size", 11)
	t_lbl.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	row1.add_child(t_lbl)
	
	_memory_type_select = OptionButton.new()
	_memory_type_select.add_item("All")
	_memory_type_select.add_item("Semantic")
	_memory_type_select.add_item("Episodic")
	_memory_type_select.add_item("Emotional")
	_memory_type_select.add_theme_font_size_override("font_size", 11)
	row1.add_child(_memory_type_select)
	add_child(row1)
	
	# Search
	var search_row = HBoxContainer.new()
	_search_input = LineEdit.new()
	_search_input.placeholder_text = "Search memories..."
	_search_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_search_input.add_theme_font_size_override("font_size", 11)
	var input_style = StyleBoxFlat.new()
	input_style.bg_color = Color(0.06, 0.06, 0.1)
	input_style.border_color = Color(0.15, 0.15, 0.25)
	input_style.set_border_width_all(1)
	input_style.set_corner_radius_all(3)
	input_style.content_margin_left = 6
	input_style.content_margin_right = 6
	input_style.content_margin_top = 4
	input_style.content_margin_bottom = 4
	_search_input.add_theme_stylebox_override("normal", input_style)
	_search_input.text_submitted.connect(_on_search)
	search_row.add_child(_search_input)
	
	var search_btn = Button.new()
	search_btn.text = "🔍"
	search_btn.add_theme_font_size_override("font_size", 14)
	search_btn.pressed.connect(_on_search.bind(""))
	search_row.add_child(search_btn)
	add_child(search_row)
	
	# Action buttons
	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 4)
	
	var refresh_btn = _make_small_btn("↻ Refresh")
	refresh_btn.pressed.connect(_on_refresh)
	btn_row.add_child(refresh_btn)
	
	var consolidate_btn = _make_small_btn("🔄 Consolidate")
	consolidate_btn.pressed.connect(_on_consolidate)
	btn_row.add_child(consolidate_btn)
	
	var prune_btn = _make_small_btn("✂ Prune")
	prune_btn.pressed.connect(_on_prune)
	btn_row.add_child(prune_btn)
	
	var contra_btn = _make_small_btn("⚠ Contradictions")
	contra_btn.pressed.connect(_on_contradictions)
	btn_row.add_child(contra_btn)
	
	add_child(btn_row)
	
	# Second row — curator actions
	var btn_row2 = HBoxContainer.new()
	btn_row2.add_theme_constant_override("separation", 4)
	
	var pending_btn = _make_small_btn("🗑 Pending")
	pending_btn.pressed.connect(_on_pending)
	btn_row2.add_child(pending_btn)
	
	var approve_all_btn = _make_small_btn("✅ Approve All")
	approve_all_btn.pressed.connect(_on_approve_all)
	btn_row2.add_child(approve_all_btn)
	
	var curator_btn = _make_small_btn("🧹 Curator")
	curator_btn.pressed.connect(_on_curator_status)
	btn_row2.add_child(curator_btn)
	
	var auto_resolve_btn = _make_small_btn("🔄 Auto-resolve")
	auto_resolve_btn.pressed.connect(_on_auto_resolve)
	btn_row2.add_child(auto_resolve_btn)
	
	var curate_now_btn = _make_small_btn("🧠 Curate Now")
	curate_now_btn.pressed.connect(_on_curate_now)
	btn_row2.add_child(curate_now_btn)
	
	var sweep_btn = _make_small_btn("🌊 Full Sweep")
	sweep_btn.pressed.connect(_on_sweep)
	btn_row2.add_child(sweep_btn)
	
	add_child(btn_row2)
	
	# Results display
	_results_list = RichTextLabel.new()
	_results_list.bbcode_enabled = true
	_results_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_results_list.add_theme_color_override("default_color", Color(0.6, 0.6, 0.7))
	_results_list.add_theme_font_size_override("normal_font_size", 11)
	_results_list.selection_enabled = true
	var list_style = StyleBoxFlat.new()
	list_style.bg_color = Color(0.04, 0.04, 0.07)
	list_style.set_corner_radius_all(3)
	_results_list.add_theme_stylebox_override("normal", list_style)
	add_child(_results_list)
	
	# Status
	_status_label = Label.new()
	_status_label.text = "Select entity and memory type to browse"
	_status_label.add_theme_font_size_override("font_size", 10)
	_status_label.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
	add_child(_status_label)


func _make_small_btn(text: String) -> Button:
	var btn = Button.new()
	btn.text = text
	btn.add_theme_font_size_override("font_size", 10)
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.1, 0.18)
	style.set_corner_radius_all(3)
	style.content_margin_left = 6
	style.content_margin_right = 6
	style.content_margin_top = 3
	style.content_margin_bottom = 3
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	return btn


func _on_search(_text: String) -> void:
	var query = _search_input.text.strip_edges()
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	_status_label.text = "Searching %s memories..." % entity
	curate_action.emit(entity, "search", {"query": query})


func _on_refresh() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	_status_label.text = "Refreshing..."
	curate_action.emit(entity, "refresh", {})


func _on_consolidate() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "consolidate", {})
	_status_label.text = "Consolidation requested for %s" % entity


func _on_prune() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "prune", {})
	_status_label.text = "Prune requested for %s" % entity


func _on_contradictions() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "contradictions", {})
	_status_label.text = "Loading contradictions for %s..." % entity


func _on_pending() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "pending", {})
	_status_label.text = "Loading pending discards for %s..." % entity


func _on_approve_all() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "approve_all", {})
	_status_label.text = "Approving all discards for %s..." % entity


func _on_curator_status() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "curator_status", {})
	_status_label.text = "Loading curator status for %s..." % entity


func _on_auto_resolve() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "auto_resolve", {})
	_status_label.text = "Auto-resolving transient contradictions for %s..." % entity


func _on_curate_now() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "curate", {})
	_status_label.text = "Running curation cycle for %s (Kay reviews via Sonnet)..." % entity

func _on_sweep() -> void:
	var entity = "Kay" if _entity_select.selected == 0 else "Reed"
	curate_action.emit(entity, "sweep", {})
	_status_label.text = "Running full memory sweep for %s (this may take a few minutes)..." % entity


func display_results(text: String) -> void:
	_results_list.clear()
	_results_list.append_text(text)


func set_status(text: String) -> void:
	_status_label.text = text
