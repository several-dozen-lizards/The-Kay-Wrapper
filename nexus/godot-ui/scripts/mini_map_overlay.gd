## MiniMapOverlay - Small room overview showing all three rooms
## with entity dots (Kay=pink, Reed=teal) for quick navigation.
class_name MiniMapOverlay
extends Control

signal room_clicked(room_id: String)

## Room definitions
const ROOMS = {
	"den": {"label": "Den", "color": Color(0.9, 0.5, 0.7, 0.3)},      # Pink tint
	"sanctum": {"label": "Sanctum", "color": Color(0.3, 0.7, 0.8, 0.3)},  # Teal tint
	"commons": {"label": "Commons", "color": Color(0.6, 0.5, 0.8, 0.3)},  # Purple tint
}

## Entity colors
const ENTITY_COLORS = {
	"Kay": Color(0.95, 0.45, 0.65),     # Pink
	"Reed": Color(0.3, 0.8, 0.75),      # Teal
	"Re": Color(0.8, 0.8, 0.8),         # White/gray for human
}

## Room sizes and spacing
const ROOM_RADIUS := 28.0
const ROOM_SPACING := 12.0
const ENTITY_DOT_RADIUS := 5.0

## Current state
var _entity_locations: Dictionary = {}  # entity_name -> room_id
var _current_room: String = "commons"
var _hovered_room: String = ""

## Room positions (computed in _ready)
var _room_positions: Dictionary = {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	custom_minimum_size = Vector2(220, 80)
	_compute_room_positions()


func _compute_room_positions() -> void:
	# Arrange rooms horizontally: Den | Commons | Sanctum
	var center_y := size.y / 2.0
	var total_width := ROOM_RADIUS * 6 + ROOM_SPACING * 2
	var start_x := (size.x - total_width) / 2.0 + ROOM_RADIUS

	_room_positions["den"] = Vector2(start_x, center_y)
	_room_positions["commons"] = Vector2(start_x + ROOM_RADIUS * 2 + ROOM_SPACING, center_y)
	_room_positions["sanctum"] = Vector2(start_x + (ROOM_RADIUS * 2 + ROOM_SPACING) * 2, center_y)


func _draw() -> void:
	_compute_room_positions()

	# Background
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.08, 0.08, 0.12, 0.9))

	# Draw rooms
	for room_id in ["den", "commons", "sanctum"]:
		var pos: Vector2 = _room_positions.get(room_id, Vector2.ZERO)
		var room_def: Dictionary = ROOMS.get(room_id, {})
		var base_color: Color = room_def.get("color", Color(0.5, 0.5, 0.5, 0.3))

		# Highlight current room
		var is_current: bool = (room_id == _current_room)
		var is_hovered: bool = (room_id == _hovered_room)

		# Room circle
		var fill_color := base_color
		if is_current:
			fill_color.a = 0.6
		if is_hovered:
			fill_color = fill_color.lightened(0.2)

		draw_circle(pos, ROOM_RADIUS, fill_color)

		# Border
		var border_color := Color(0.4, 0.4, 0.5)
		if is_current:
			border_color = Color(0.8, 0.8, 0.9)
		_draw_circle_arc(pos, ROOM_RADIUS, 0, TAU, border_color, 2.0)

		# Room label
		var font: Font = ThemeDB.fallback_font
		var label: String = room_def.get("label", room_id.capitalize())
		var label_size := font.get_string_size(label, HORIZONTAL_ALIGNMENT_CENTER, -1, 9)
		draw_string(
			font,
			Vector2(pos.x - label_size.x / 2, pos.y + ROOM_RADIUS + 12),
			label,
			HORIZONTAL_ALIGNMENT_CENTER,
			-1, 9,
			Color(0.7, 0.7, 0.75)
		)

		# Draw entity dots in this room
		_draw_entities_in_room(room_id, pos)


func _draw_entities_in_room(room_id: String, room_pos: Vector2) -> void:
	var entities_here: Array = []
	for ent_name in _entity_locations:
		if _entity_locations[ent_name] == room_id:
			entities_here.append(ent_name)

	if entities_here.is_empty():
		return

	# Position dots around center of room
	var count := entities_here.size()
	for i in range(count):
		var ent_name: String = entities_here[i]
		var angle := (TAU / count) * i - PI / 2  # Start from top
		var dist := ROOM_RADIUS * 0.5 if count > 1 else 0.0
		var dot_pos := room_pos + Vector2(cos(angle), sin(angle)) * dist

		var color: Color = ENTITY_COLORS.get(ent_name, Color(0.7, 0.7, 0.7))
		draw_circle(dot_pos, ENTITY_DOT_RADIUS, color)

		# Add a subtle glow for visibility
		draw_circle(dot_pos, ENTITY_DOT_RADIUS + 2, Color(color.r, color.g, color.b, 0.3))


func _draw_circle_arc(center: Vector2, radius: float, start_angle: float, end_angle: float, color: Color, width: float = 1.0) -> void:
	var segments := 32
	var points := PackedVector2Array()
	for i in range(segments + 1):
		var angle := start_angle + (end_angle - start_angle) * i / segments
		points.append(center + Vector2(cos(angle), sin(angle)) * radius)
	for i in range(points.size() - 1):
		draw_line(points[i], points[i + 1], color, width)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		_hovered_room = _get_room_at_position(mm.position)
		queue_redraw()

	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed:
			var clicked_room := _get_room_at_position(mb.position)
			if not clicked_room.is_empty():
				room_clicked.emit(clicked_room)


func _get_room_at_position(pos: Vector2) -> String:
	for room_id in _room_positions:
		var room_pos: Vector2 = _room_positions[room_id]
		if pos.distance_to(room_pos) <= ROOM_RADIUS:
			return room_id
	return ""


func set_current_room(room_id: String) -> void:
	_current_room = room_id
	queue_redraw()


func set_entity_location(entity_name: String, room_id: String) -> void:
	if room_id.is_empty():
		_entity_locations.erase(entity_name)
	else:
		_entity_locations[entity_name] = room_id
	queue_redraw()


func update_from_registry(registry: Dictionary) -> void:
	# Update entity locations from main.gd's _room_registry
	_entity_locations.clear()
	for room_id in registry:
		var room_data: Dictionary = registry[room_id]
		var entities: Array = room_data.get("entities", [])
		for ent in entities:
			_entity_locations[ent] = room_id
	queue_redraw()


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_compute_room_positions()
		queue_redraw()
