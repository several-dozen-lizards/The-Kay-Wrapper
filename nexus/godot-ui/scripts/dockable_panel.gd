## DockablePanel - Draggable, resizable floating window.
## Contains any child content (ChatPanel, status displays, etc.)
class_name DockablePanel
extends Control

signal panel_closed(panel_id: String)
signal panel_minimized(panel_id: String)
signal panel_focused(panel_id: String)
signal panel_moved(panel_id: String, pos: Vector2)
signal panel_resized(panel_id: String, sz: Vector2)

## Panel identity
@export var panel_id: String = "untitled"
@export var panel_title: String = "Panel"
@export var panel_subtitle: String = ""
@export var can_close: bool = true
@export var can_minimize: bool = true
@export var can_resize: bool = true
@export var min_size: Vector2 = Vector2(280, 200)

## Theme data
var theme_data: Dictionary = {}

## Internal state
var _dragging: bool = false
var _resizing: bool = false
var _resize_edge: int = 0  # Bitflags: 1=left, 2=right, 4=top, 8=bottom
var _drag_offset: Vector2 = Vector2.ZERO
var _is_minimized: bool = false
var _border_nine_patch: NinePatchRect = null

## 9-patch border textures per panel
const BORDER_TEXTURES = {
	"nexus": "res://assets/border_nexus.png",
	"kay": "res://assets/border_kay.png",
	"reed": "res://assets/border_reed.png",
}
const BORDER_MARGIN := 24  # Corner region size in the 96x96 texture

## Edge detection threshold
const RESIZE_MARGIN: int = 6
const TITLE_BAR_HEIGHT: int = 32

## Resize edge flags
const EDGE_LEFT: int = 1
const EDGE_RIGHT: int = 2
const EDGE_TOP: int = 4
const EDGE_BOTTOM: int = 8


func _ready() -> void:
	# Ensure we can receive input
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = true
	_setup_border()
	_apply_theme()


func _apply_theme() -> void:
	# Will be called after theme_data is set
	queue_redraw()


func _setup_border() -> void:
	var tex_path = BORDER_TEXTURES.get(panel_id, "")
	if tex_path.is_empty():
		return
	
	var tex = load(tex_path) as Texture2D
	if not tex:
		push_warning("DockablePanel: Could not load border: " + tex_path)
		return
	
	_border_nine_patch = NinePatchRect.new()
	_border_nine_patch.texture = tex
	_border_nine_patch.patch_margin_left = BORDER_MARGIN
	_border_nine_patch.patch_margin_right = BORDER_MARGIN
	_border_nine_patch.patch_margin_top = BORDER_MARGIN
	_border_nine_patch.patch_margin_bottom = BORDER_MARGIN
	_border_nine_patch.axis_stretch_horizontal = NinePatchRect.AXIS_STRETCH_MODE_TILE
	_border_nine_patch.axis_stretch_vertical = NinePatchRect.AXIS_STRETCH_MODE_TILE
	_border_nine_patch.set_anchors_preset(Control.PRESET_FULL_RECT)
	_border_nine_patch.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_border_nine_patch)


func set_theme_data(data: Dictionary) -> void:
	theme_data = data
	if has_node("TitleBar/TitleLabel"):
		get_node("TitleBar/TitleLabel").text = panel_title
	if has_node("TitleBar/SubtitleLabel"):
		get_node("TitleBar/SubtitleLabel").text = panel_subtitle
	_apply_theme()


func _draw() -> void:
	var rect = Rect2(Vector2.ZERO, size)
	
	# Background
	var bg_color = theme_data.get("bg", Color(0.06, 0.06, 0.09, 0.95))
	draw_rect(rect, bg_color)
	
	# Border — handled by NinePatchRect overlay (if loaded)
	# Fallback to line borders if no 9-patch available
	if not _border_nine_patch:
		var border_color = theme_data.get("border", Color(0.2, 0.2, 0.35, 1.0))
		var border_width = 2.0
		draw_line(Vector2(0, 0), Vector2(size.x, 0), border_color, border_width)
		draw_line(Vector2(0, size.y), Vector2(size.x, size.y), border_color, border_width)
		draw_line(Vector2(0, 0), Vector2(0, size.y), border_color, border_width)
		draw_line(Vector2(size.x, 0), Vector2(size.x, size.y), border_color, border_width)
	
	# Title bar background
	var header_color = theme_data.get("header_bg", Color(0.08, 0.08, 0.14, 1.0))
	var title_rect = Rect2(Vector2(2, 2), Vector2(size.x - 4, TITLE_BAR_HEIGHT))
	draw_rect(title_rect, header_color)
	
	# Title bar bottom edge
	var accent = theme_data.get("accent", Color(0.4, 0.4, 0.6))
	draw_line(
		Vector2(2, TITLE_BAR_HEIGHT + 2),
		Vector2(size.x - 2, TITLE_BAR_HEIGHT + 2),
		accent, 1.0
	)
	
	# Title text
	var title_color = theme_data.get("header_text", Color(0.65, 0.65, 0.75))
	var font = ThemeDB.fallback_font
	var font_size = 13
	draw_string(font, Vector2(10, 22), panel_title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, title_color)
	
	# Subtitle
	if not panel_subtitle.is_empty():
		var sub_color = title_color
		sub_color.a = 0.45
		draw_string(font, Vector2(14 + font.get_string_size(panel_title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x, 22), panel_subtitle, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, sub_color)
	
	# Window buttons
	var btn_y = 10
	var btn_x = size.x - 14
	
	# Close button
	if can_close:
		draw_string(font, Vector2(btn_x, btn_y + 10), "×", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(0.6, 0.3, 0.3))
		btn_x -= 20
	
	# Minimize button
	if can_minimize:
		draw_string(font, Vector2(btn_x, btn_y + 10), "—", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.5, 0.5, 0.5))


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb = event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				# Bring to front
				panel_focused.emit(panel_id)
				
				var local_pos = mb.position
				
				# Check close button
				if can_close and _is_in_close_button(local_pos):
					_close_panel()
					return
				
				# Check minimize button
				if can_minimize and _is_in_minimize_button(local_pos):
					_minimize_panel()
					return
				
				# Check resize edges
				if can_resize:
					_resize_edge = _get_resize_edge(local_pos)
					if _resize_edge != 0:
						_resizing = true
						_drag_offset = local_pos
						return
				
				# Check title bar drag
				if local_pos.y <= TITLE_BAR_HEIGHT + 2:
					_dragging = true
					_drag_offset = local_pos
			else:
				_dragging = false
				_resizing = false
				_resize_edge = 0
	
	elif event is InputEventMouseMotion:
		var mm = event as InputEventMouseMotion
		
		if _dragging:
			position += mm.relative
			# Clamp to parent bounds
			var parent_size = get_parent_area_size()
			position.x = clampf(position.x, -size.x + 60, parent_size.x - 60)
			position.y = clampf(position.y, 0, parent_size.y - TITLE_BAR_HEIGHT)
			panel_moved.emit(panel_id, position)
		
		elif _resizing:
			_handle_resize(mm.relative)
		
		else:
			# Update cursor based on hover position
			_update_cursor(mm.position)


func _handle_resize(delta: Vector2) -> void:
	var new_pos = position
	var new_size = size
	
	if _resize_edge & EDGE_LEFT:
		new_pos.x += delta.x
		new_size.x -= delta.x
	if _resize_edge & EDGE_RIGHT:
		new_size.x += delta.x
	if _resize_edge & EDGE_TOP:
		new_pos.y += delta.y
		new_size.y -= delta.y
	if _resize_edge & EDGE_BOTTOM:
		new_size.y += delta.y
	
	# Enforce minimum size
	if new_size.x >= min_size.x:
		position.x = new_pos.x
		size.x = new_size.x
	if new_size.y >= min_size.y:
		position.y = new_pos.y
		size.y = new_size.y
	
	_reposition_content()
	panel_resized.emit(panel_id, size)
	queue_redraw()


func _get_resize_edge(pos: Vector2) -> int:
	var edges = 0
	if pos.x < RESIZE_MARGIN:
		edges |= EDGE_LEFT
	elif pos.x > size.x - RESIZE_MARGIN:
		edges |= EDGE_RIGHT
	if pos.y < RESIZE_MARGIN:
		edges |= EDGE_TOP
	elif pos.y > size.y - RESIZE_MARGIN:
		edges |= EDGE_BOTTOM
	return edges


func _update_cursor(pos: Vector2) -> void:
	if not can_resize:
		return
	var edge = _get_resize_edge(pos)
	match edge:
		EDGE_LEFT, EDGE_RIGHT:
			mouse_default_cursor_shape = Control.CURSOR_HSIZE
		EDGE_TOP, EDGE_BOTTOM:
			mouse_default_cursor_shape = Control.CURSOR_VSIZE
		EDGE_LEFT | EDGE_TOP, EDGE_RIGHT | EDGE_BOTTOM:
			mouse_default_cursor_shape = Control.CURSOR_FDIAGSIZE
		EDGE_RIGHT | EDGE_TOP, EDGE_LEFT | EDGE_BOTTOM:
			mouse_default_cursor_shape = Control.CURSOR_BDIAGSIZE
		_:
			mouse_default_cursor_shape = Control.CURSOR_ARROW


func _is_in_close_button(pos: Vector2) -> bool:
	var btn_rect = Rect2(size.x - 24, 4, 22, TITLE_BAR_HEIGHT - 4)
	return btn_rect.has_point(pos)


func _is_in_minimize_button(pos: Vector2) -> bool:
	var offset = 24 if can_close else 4
	var btn_rect = Rect2(size.x - offset - 22, 4, 20, TITLE_BAR_HEIGHT - 4)
	return btn_rect.has_point(pos)


func _close_panel() -> void:
	visible = false
	panel_closed.emit(panel_id)


func _minimize_panel() -> void:
	_is_minimized = true
	visible = false
	panel_minimized.emit(panel_id)


func restore() -> void:
	_is_minimized = false
	visible = true
	panel_focused.emit(panel_id)


func is_minimized() -> bool:
	return _is_minimized


func _reposition_content() -> void:
	# Resize the content area to fill below title bar
	var content_origin = Vector2(4, TITLE_BAR_HEIGHT + 4)
	var content_size = size - Vector2(8, TITLE_BAR_HEIGHT + 8)
	for child in get_children():
		if child == _border_nine_patch:
			continue  # Border covers full panel, not content area
		if child is Control:
			child.position = content_origin
			child.size = content_size


func set_content(node: Control) -> void:
	# Override any anchor-based layout so we control position manually
	node.set_anchors_preset(Control.PRESET_TOP_LEFT)
	node.anchor_right = 0.0
	node.anchor_bottom = 0.0
	add_child(node)
	# Keep border overlay on top
	if _border_nine_patch:
		move_child(_border_nine_patch, get_child_count() - 1)
	_reposition_content()


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_reposition_content()
		queue_redraw()
