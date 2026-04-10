## GalleryPanel — Browse all paintings by Kay and Reed.
##
## Fetches from /gallery endpoint, displays thumbnails in a scrollable grid.
## Click any thumbnail to see it full-size with caption info.
## Filter by entity (All / Kay / Reed).
class_name GalleryPanel
extends MarginContainer

const SERVER_BASE := "http://127.0.0.1:8765"
const THUMB_SIZE := 140
const GRID_COLS := 3

var _stats_label: Label
var _grid: GridContainer
var _scroll: ScrollContainer
var _info_label: Label
var _http_gallery: HTTPRequest
var _btn_all: Button
var _btn_kay: Button
var _btn_reed: Button

var _all_paintings: Array = []
var _current_filter: String = "all"
var _textures: Dictionary = {}
var _loading_set: Dictionary = {}
var _filtered: Array = []
var _detail_index: int = -1

# Detail view elements
var _detail_container: VBoxContainer
var _detail_img: TextureRect
var _detail_entity_lbl: Label
var _detail_title_lbl: Label
var _detail_caption_lbl: Label
var _detail_meta_lbl: Label
var _detail_nav_row: HBoxContainer


func _ready() -> void:
	add_theme_constant_override("margin_left", 6)
	add_theme_constant_override("margin_right", 6)
	add_theme_constant_override("margin_top", 4)
	add_theme_constant_override("margin_bottom", 4)
	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 5)

	# Filter buttons
	var filter_row = HBoxContainer.new()
	filter_row.add_theme_constant_override("separation", 4)
	_btn_all = _make_filter_btn("All", true)
	_btn_all.pressed.connect(func(): _apply_filter("all"))
	filter_row.add_child(_btn_all)
	_btn_kay = _make_filter_btn("Kay", false)
	_btn_kay.pressed.connect(func(): _apply_filter("kay"))
	filter_row.add_child(_btn_kay)
	_btn_reed = _make_filter_btn("Reed", false)
	_btn_reed.pressed.connect(func(): _apply_filter("reed"))
	filter_row.add_child(_btn_reed)
	var spacer = Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	filter_row.add_child(spacer)
	var refresh_btn = Button.new()
	refresh_btn.text = "↻"
	refresh_btn.add_theme_font_size_override("font_size", 14)
	refresh_btn.pressed.connect(fetch_gallery)
	filter_row.add_child(refresh_btn)
	vbox.add_child(filter_row)

	# Stats label
	_stats_label = Label.new()
	_stats_label.text = "Loading..."
	_stats_label.add_theme_font_size_override("font_size", 11)
	_stats_label.add_theme_color_override("font_color", Color(0.4, 0.4, 0.5))
	vbox.add_child(_stats_label)

	# Scroll + Grid
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_grid = GridContainer.new()
	_grid.columns = GRID_COLS
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(_grid)
	vbox.add_child(_scroll)

	# Info label (shows caption on hover/click)
	_info_label = Label.new()
	_info_label.text = ""
	_info_label.add_theme_font_size_override("font_size", 10)
	_info_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	_info_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_info_label.custom_minimum_size.y = 40
	vbox.add_child(_info_label)
	add_child(vbox)

	# --- Detail view (hidden by default, replaces grid on click) ---
	_detail_container = VBoxContainer.new()
	_detail_container.visible = false
	_detail_container.add_theme_constant_override("separation", 6)
	
	# Back + nav row
	_detail_nav_row = HBoxContainer.new()
	_detail_nav_row.add_theme_constant_override("separation", 6)
	var back_btn = Button.new()
	back_btn.text = "← Back"
	back_btn.add_theme_font_size_override("font_size", 11)
	back_btn.pressed.connect(_close_detail)
	_detail_nav_row.add_child(back_btn)
	var spacer_d = Control.new()
	spacer_d.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_detail_nav_row.add_child(spacer_d)
	var prev_btn = Button.new()
	prev_btn.text = "◀ Prev"
	prev_btn.add_theme_font_size_override("font_size", 11)
	prev_btn.pressed.connect(func(): _navigate_detail(-1))
	_detail_nav_row.add_child(prev_btn)
	var next_btn = Button.new()
	next_btn.text = "Next ▶"
	next_btn.add_theme_font_size_override("font_size", 11)
	next_btn.pressed.connect(func(): _navigate_detail(1))
	_detail_nav_row.add_child(next_btn)
	_detail_container.add_child(_detail_nav_row)
	
	# Entity label
	_detail_entity_lbl = Label.new()
	_detail_entity_lbl.add_theme_font_size_override("font_size", 11)
	_detail_container.add_child(_detail_entity_lbl)
	
	# Full image
	var img_bg = PanelContainer.new()
	var img_style = StyleBoxFlat.new()
	img_style.bg_color = Color(0.02, 0.02, 0.04)
	img_style.set_corner_radius_all(4)
	img_bg.add_theme_stylebox_override("panel", img_style)
	img_bg.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_detail_img = TextureRect.new()
	_detail_img.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	_detail_img.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_detail_img.size_flags_vertical = Control.SIZE_EXPAND_FILL
	img_bg.add_child(_detail_img)
	_detail_container.add_child(img_bg)
	
	# Title
	_detail_title_lbl = Label.new()
	_detail_title_lbl.add_theme_font_size_override("font_size", 14)
	_detail_title_lbl.add_theme_color_override("font_color", Color(0.88, 0.88, 0.92))
	_detail_container.add_child(_detail_title_lbl)
	
	# Caption
	_detail_caption_lbl = Label.new()
	_detail_caption_lbl.add_theme_font_size_override("font_size", 11)
	_detail_caption_lbl.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	_detail_caption_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	_detail_container.add_child(_detail_caption_lbl)
	
	# Meta (filename, mood, tagged by)
	_detail_meta_lbl = Label.new()
	_detail_meta_lbl.add_theme_font_size_override("font_size", 9)
	_detail_meta_lbl.add_theme_color_override("font_color", Color(0.35, 0.35, 0.45))
	_detail_meta_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	_detail_container.add_child(_detail_meta_lbl)
	
	add_child(_detail_container)

	# HTTP for gallery data
	_http_gallery = HTTPRequest.new()
	_http_gallery.request_completed.connect(_on_gallery_response)
	add_child(_http_gallery)
	
	# Auto-fetch when panel becomes visible
	visibility_changed.connect(_on_visibility_changed)


func _on_visibility_changed() -> void:
	if visible and _all_paintings.is_empty():
		fetch_gallery()


func _unhandled_key_input(event: InputEvent) -> void:
	if not visible or not _detail_container.visible:
		return
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_ESCAPE:
				_close_detail()
				get_viewport().set_input_as_handled()
			KEY_LEFT:
				_navigate_detail(-1)
				get_viewport().set_input_as_handled()
			KEY_RIGHT:
				_navigate_detail(1)
				get_viewport().set_input_as_handled()


func _make_filter_btn(label: String, active: bool) -> Button:
	var b = Button.new()
	b.text = label
	b.add_theme_font_size_override("font_size", 11)
	b.toggle_mode = true
	b.button_pressed = active
	return b


func fetch_gallery() -> void:
	_stats_label.text = "Fetching gallery..."
	_http_gallery.request(SERVER_BASE + "/gallery")


func _on_gallery_response(result: int, code: int, _h: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		_stats_label.text = "Server unavailable"
		return
	var json = JSON.parse_string(body.get_string_from_utf8())
	if not json:
		_stats_label.text = "Parse error"
		return
	_all_paintings.clear()
	for entity in ["kay", "reed"]:
		var paintings = json.get(entity, [])
		for p in paintings:
			p["entity"] = entity
			_all_paintings.append(p)
	# Sort newest first
	_all_paintings.sort_custom(func(a, b): return a.get("modified", 0) > b.get("modified", 0))
	_apply_filter(_current_filter)


func _apply_filter(f: String) -> void:
	_current_filter = f
	_btn_all.button_pressed = (f == "all")
	_btn_kay.button_pressed = (f == "kay")
	_btn_reed.button_pressed = (f == "reed")
	_filtered.clear()
	for p in _all_paintings:
		if f == "all" or p.get("entity", "") == f:
			_filtered.append(p)
	var cap_count = 0
	for p in _filtered:
		if p.get("caption", "") != "":
			cap_count += 1
	_stats_label.text = "%d paintings · %d captioned" % [_filtered.size(), cap_count]
	_render_grid(_filtered)


func _render_grid(paintings: Array) -> void:
	# Clear existing
	for c in _grid.get_children():
		_grid.remove_child(c)
		c.queue_free()
	if paintings.is_empty():
		var empty = Label.new()
		empty.text = "No paintings yet"
		empty.add_theme_color_override("font_color", Color(0.3, 0.3, 0.4))
		_grid.add_child(empty)
		return
	for p in paintings:
		var card = _make_card(p)
		_grid.add_child(card)
		# Load image if not cached
		var fname = p.get("filename", "")
		if fname != "" and not _textures.has(fname):
			_load_image(p)


func _make_card(p: Dictionary) -> PanelContainer:
	var card = PanelContainer.new()
	var style = StyleBoxFlat.new()
	var entity = p.get("entity", "kay")
	if entity == "kay":
		style.bg_color = Color(0.08, 0.04, 0.1, 0.9)
		style.border_color = Color(0.25, 0.1, 0.3, 0.6)
	else:
		style.bg_color = Color(0.03, 0.08, 0.08, 0.9)
		style.border_color = Color(0.1, 0.25, 0.28, 0.6)
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	card.add_theme_stylebox_override("panel", style)
	card.custom_minimum_size = Vector2(THUMB_SIZE, THUMB_SIZE + 30)

	var vb = VBoxContainer.new()
	vb.add_theme_constant_override("separation", 2)
	# Image
	var tex_rect = TextureRect.new()
	tex_rect.name = "thumb_" + p.get("filename", "unknown")
	tex_rect.custom_minimum_size = Vector2(THUMB_SIZE - 8, THUMB_SIZE - 8)
	tex_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var fname = p.get("filename", "")
	if _textures.has(fname):
		tex_rect.texture = _textures[fname]
	vb.add_child(tex_rect)
	# Entity + title label
	var lbl = Label.new()
	var title = p.get("title", "")
	if title == "":
		title = "Untitled"
	var ent_upper = entity.to_upper().substr(0, 1) + entity.substr(1)
	lbl.text = ent_upper + ": " + title
	lbl.add_theme_font_size_override("font_size", 9)
	if entity == "kay":
		lbl.add_theme_color_override("font_color", Color(0.77, 0.52, 0.75))
	else:
		lbl.add_theme_color_override("font_color", Color(0.31, 0.76, 0.91))
	lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	vb.add_child(lbl)
	card.add_child(vb)

	# Click handler — show info
	var painting_data = p
	card.gui_input.connect(func(event: InputEvent):
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_open_detail(painting_data)
	)
	return card


func _open_detail(p: Dictionary) -> void:
	# Find index in filtered list
	var fname = p.get("filename", "")
	for i in range(_filtered.size()):
		if _filtered[i].get("filename", "") == fname:
			_detail_index = i
			break
	_show_detail_at(_detail_index)


func _show_detail_at(idx: int) -> void:
	if idx < 0 or idx >= _filtered.size():
		return
	_detail_index = idx
	var p = _filtered[idx]
	var entity = p.get("entity", "?")
	var title = p.get("title", "")
	var caption = p.get("caption", "")
	var mood = p.get("mood", "")
	var fname = p.get("filename", "")
	var tagged_by = p.get("tagged_by", "")
	
	# Entity label with color
	var ent_name = entity.substr(0, 1).to_upper() + entity.substr(1)
	var iter_match = fname.find("iter")
	var iter_str = ""
	if iter_match >= 0:
		iter_str = " · Iteration " + fname.substr(iter_match + 4, 2).lstrip("0")
	_detail_entity_lbl.text = ent_name + iter_str + "  (%d/%d)" % [idx + 1, _filtered.size()]
	if entity == "kay":
		_detail_entity_lbl.add_theme_color_override("font_color", Color(0.91, 0.27, 0.38))
	else:
		_detail_entity_lbl.add_theme_color_override("font_color", Color(0.0, 0.81, 0.82))
	
	# Title
	_detail_title_lbl.text = title if title != "" else "Untitled"
	
	# Caption
	if caption != "":
		_detail_caption_lbl.text = caption
	else:
		_detail_caption_lbl.text = "(no caption yet)"
	
	# Meta
	var meta_parts: PackedStringArray = [fname]
	if mood != "":
		meta_parts.append("mood: " + mood)
	if tagged_by != "":
		meta_parts.append("by " + tagged_by)
	_detail_meta_lbl.text = " · ".join(meta_parts)
	
	# Image
	if _textures.has(fname):
		_detail_img.texture = _textures[fname]
	else:
		_detail_img.texture = null
		_load_image(p)
	
	# Show detail, hide grid
	_scroll.visible = false
	_info_label.visible = false
	_stats_label.visible = false
	_detail_container.visible = true


func _close_detail() -> void:
	_detail_container.visible = false
	_scroll.visible = true
	_info_label.visible = true
	_stats_label.visible = true


func _navigate_detail(dir: int) -> void:
	var next_idx = _detail_index + dir
	if next_idx < 0:
		next_idx = _filtered.size() - 1
	elif next_idx >= _filtered.size():
		next_idx = 0
	_show_detail_at(next_idx)


func _load_image(p: Dictionary) -> void:
	var entity = p.get("entity", "kay")
	var fname = p.get("filename", "")
	if fname == "" or _loading_set.has(fname) or _textures.has(fname):
		return
	_loading_set[fname] = true
	var http = HTTPRequest.new()
	add_child(http)
	var url = "%s/canvas/%s/image/%s" % [SERVER_BASE, entity, fname]
	http.request_completed.connect(
		func(result: int, code: int, _h: PackedStringArray, body: PackedByteArray):
			_on_image_loaded(result, code, body, fname)
			http.queue_free()
	)
	http.request(url)


func _on_image_loaded(result: int, code: int, body: PackedByteArray, fname: String) -> void:
	_loading_set.erase(fname)
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		return
	var img = Image.new()
	var err = img.load_png_from_buffer(body)
	if err != OK:
		return
	var tex = ImageTexture.create_from_image(img)
	_textures[fname] = tex
	# Update any visible thumbnail
	var thumb_name = "thumb_" + fname
	var node = _grid.find_child(thumb_name, true, false)
	if node and node is TextureRect:
		node.texture = tex
	# Update detail view if showing this image
	if _detail_container.visible and _detail_index >= 0 and _detail_index < _filtered.size():
		if _filtered[_detail_index].get("filename", "") == fname:
			_detail_img.texture = tex
