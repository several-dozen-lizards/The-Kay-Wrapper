## RoomPanel — Renders a circular cosmographic room.
## Entities and objects exist in a circle around a central gol (axis mundi).
## Receives room_update events via WebSocket from the wrapper.
class_name RoomPanel
extends Control

signal room_clicked(position: Vector2)
signal mini_map_room_clicked(room_id: String)

## Room state
var _room_data: Dictionary = {}
var _entity_sprites: Dictionary = {}
var _entity_labels: Dictionary = {}
var _entity_emotes: Dictionary = {}
var _object_sprites: Dictionary = {}
var _object_labels: Dictionary = {}
var _mini_map: MiniMapOverlay

## Colors
const ENTITY_COLORS := {
	"kay": Color(0.176, 0.106, 0.306),   # void purple
	"reed": Color(0, 0.808, 0.820),       # teal
}
const ENTITY_ACCENTS := {
	"kay": Color(1.0, 0.412, 0.706),      # pink glow
	"reed": Color(0.855, 0.647, 0.125),   # gold
}
const OBJECT_COLOR := Color(0.25, 0.22, 0.18, 0.5)
const BG_COLOR := Color(0.06, 0.06, 0.05)
const CIRCLE_COLOR := Color(0.12, 0.11, 0.10)
const GOL_COLOR := Color(0.25, 0.22, 0.15, 0.3)
const RING_COLOR := Color(0.15, 0.14, 0.12, 0.2)
const CARDINAL_COLOR := Color(0.18, 0.16, 0.13, 0.15)

var _lerp_speed: float = 0.12
var _room_radius: float = 300.0
var _room_diameter: float = 600.0


func _ready() -> void:
	# Create mini-map overlay at bottom of panel
	_mini_map = MiniMapOverlay.new()
	_mini_map.name = "MiniMap"
	_mini_map.room_clicked.connect(_on_mini_map_room_clicked)
	add_child(_mini_map)
	_position_mini_map()


func _position_mini_map() -> void:
	if not _mini_map:
		return
	var map_height := 80.0
	_mini_map.position = Vector2(0, size.y - map_height)
	_mini_map.size = Vector2(size.x, map_height)


func _on_mini_map_room_clicked(room_id: String) -> void:
	mini_map_room_clicked.emit(room_id)


func _draw() -> void:
	var panel_size = size
	if panel_size.x < 1 or panel_size.y < 1:
		return
	
	# Background
	draw_rect(Rect2(Vector2.ZERO, panel_size), BG_COLOR)
	
	if _room_data.is_empty():
		# Draw placeholder
		var center = panel_size / 2
		draw_circle(center, 4, GOL_COLOR)
		return
	
	var center = panel_size / 2
	var fit = min(panel_size.x, panel_size.y) * 0.45
	
	# Outer circle (room boundary)
	draw_arc(center, fit, 0, TAU, 64, RING_COLOR, 1.5)
	
	# Inner rings (guides)
	draw_arc(center, fit * 0.4, 0, TAU, 48, RING_COLOR, 0.5)   # inner ring
	draw_arc(center, fit * 0.7, 0, TAU, 48, RING_COLOR, 0.5)   # middle ring
	
	# Cardinal lines (subtle cross)
	var card_len = fit * 1.05
	# N-S
	draw_line(center + Vector2(0, -card_len), center + Vector2(0, card_len), CARDINAL_COLOR, 0.5)
	# E-W
	draw_line(center + Vector2(-card_len, 0), center + Vector2(card_len, 0), CARDINAL_COLOR, 0.5)
	
	# Gol marker (center point)
	draw_circle(center, 6, GOL_COLOR)
	draw_circle(center, 2, Color(0.4, 0.35, 0.25, 0.5))
	
	# Cardinal labels (tiny, at edges)
	# These would need a font — skip for now, use draw_circle markers
	var label_dist = fit * 1.1
	var dot_size = 3.0
	draw_circle(center + Vector2(label_dist, 0), dot_size, Color(0.8, 0.6, 0.2, 0.3))    # E - dawn gold
	draw_circle(center + Vector2(0, -label_dist), dot_size, Color(0.3, 0.6, 0.3, 0.3))    # N - earth green
	draw_circle(center + Vector2(-label_dist, 0), dot_size, Color(0.2, 0.4, 0.8, 0.3))    # W - water blue
	draw_circle(center + Vector2(0, label_dist), dot_size, Color(0.8, 0.3, 0.2, 0.3))     # S - fire red


func _process(delta: float) -> void:
	if _room_data.is_empty():
		return
	
	# Update entities
	for entity_id in _entity_sprites:
		var sprite: Control = _entity_sprites[entity_id]
		var edata: Dictionary = _room_data.get("entities", {}).get(entity_id, {})
		if edata.is_empty():
			continue
		
		var target_pos = _state_to_screen(edata)
		sprite.position = sprite.position.lerp(target_pos, _lerp_speed)
		
		if entity_id in _entity_labels:
			var label: Label = _entity_labels[entity_id]
			label.position = Vector2(
				sprite.position.x - label.size.x / 2 + 16,
				sprite.position.y - 20
			)
		
		if entity_id in _entity_emotes:
			var emote_label: Label = _entity_emotes[entity_id]
			if edata.has("emote"):
				emote_label.text = edata["emote"]
				emote_label.visible = true
				emote_label.position = Vector2(
					sprite.position.x - emote_label.size.x / 2 + 16,
					sprite.position.y - 40
				)
			else:
				emote_label.visible = false
	
	# Update objects (position AND size based on current window!)
	for obj_id in _object_sprites:
		var odata: Dictionary = _room_data.get("objects", {}).get(obj_id, {})
		if odata.is_empty():
			continue
		_update_object_visual(obj_id, odata)


func update_room(state: Dictionary) -> void:
	_room_data = state

	var room_meta = state.get("room", {})
	_room_radius = room_meta.get("radius", 300)
	_room_diameter = _room_radius * 2

	for obj_id in state.get("objects", {}):
		var odata: Dictionary = state["objects"][obj_id]
		if obj_id not in _object_sprites:
			_create_object_visual(obj_id, odata)
		_update_object_visual(obj_id, odata)

	for entity_id in state.get("entities", {}):
		var edata: Dictionary = state["entities"][entity_id]
		if entity_id not in _entity_sprites:
			_create_entity_visual(entity_id, edata)

	# Cleanup removed
	for entity_id in _entity_sprites.keys():
		if entity_id not in state.get("entities", {}):
			_remove_entity_visual(entity_id)
	for obj_id in _object_sprites.keys():
		if obj_id not in state.get("objects", {}):
			_remove_object_visual(obj_id)

	# Redraw the circular guides
	queue_redraw()


func switch_room(room_id: String) -> void:
	## Called when an entity moves to a different room.
	## Clears all existing visuals and prepares for new room data.
	print("[ROOM] Switching to room: %s" % room_id)

	# Clear all entity visuals
	for entity_id in _entity_sprites.keys():
		_remove_entity_visual(entity_id)

	# Clear all object visuals
	for obj_id in _object_sprites.keys():
		_remove_object_visual(obj_id)

	# Clear room data — will be repopulated on next update_room call
	_room_data = {}

	# Redraw (will show empty placeholder until new data arrives)
	queue_redraw()


## ====================================================================
## Coordinate mapping — state screen coords to panel space
## ====================================================================

func _state_to_screen(data: Dictionary) -> Vector2:
	## The room engine provides screen_x, screen_y in a (diameter x diameter) space.
	## We scale that to fit our panel.
	var sx = data.get("screen_x", _room_radius)
	var sy = data.get("screen_y", _room_radius)
	
	var panel_size = size
	if panel_size.x < 1 or panel_size.y < 1:
		return Vector2(sx, sy)
	
	var fit = min(panel_size.x, panel_size.y)
	var scale = fit / _room_diameter
	
	var offset_x = (panel_size.x - _room_diameter * scale) / 2
	var offset_y = (panel_size.y - _room_diameter * scale) / 2
	
	return Vector2(sx * scale + offset_x, sy * scale + offset_y)


## ====================================================================
## Entity visuals
## ====================================================================

func _create_entity_visual(entity_id: String, data: Dictionary) -> void:
	var sprite_path = "res://sprites/entities/" + entity_id + ".png"
	var visual: Control
	
	if ResourceLoader.exists(sprite_path):
		var tex_rect = TextureRect.new()
		tex_rect.texture = load(sprite_path)
		tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tex_rect.custom_minimum_size = Vector2(32, 48)
		visual = tex_rect
	else:
		var base_color = ENTITY_COLORS.get(entity_id, Color.WHITE)
		var accent = ENTITY_ACCENTS.get(entity_id, Color.WHITE)
		
		var container = Control.new()
		container.custom_minimum_size = Vector2(32, 48)
		container.size = Vector2(32, 48)
		
		var glow = ColorRect.new()
		glow.color = accent
		glow.color.a = 0.6
		glow.position = Vector2(-2, -2)
		glow.size = Vector2(36, 52)
		container.add_child(glow)
		
		var body = ColorRect.new()
		body.color = base_color
		body.size = Vector2(32, 48)
		container.add_child(body)
		
		var left_eye = ColorRect.new()
		left_eye.color = Color.WHITE
		left_eye.size = Vector2(4, 4)
		left_eye.position = Vector2(8, 14)
		container.add_child(left_eye)
		
		var right_eye = ColorRect.new()
		right_eye.color = Color.WHITE
		right_eye.size = Vector2(4, 4)
		right_eye.position = Vector2(20, 14)
		container.add_child(right_eye)
		
		visual = container
	
	var start_pos = _state_to_screen(data)
	visual.position = start_pos
	visual.z_index = 10
	add_child(visual)
	_entity_sprites[entity_id] = visual
	
	var label = Label.new()
	label.text = data.get("display_name", entity_id)
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color",
		ENTITY_ACCENTS.get(entity_id, Color.WHITE))
	label.z_index = 11
	add_child(label)
	_entity_labels[entity_id] = label
	
	var emote_label = Label.new()
	emote_label.visible = false
	emote_label.add_theme_font_size_override("font_size", 10)
	emote_label.add_theme_color_override("font_color", Color(1, 1, 0.7))
	emote_label.z_index = 12
	add_child(emote_label)
	_entity_emotes[entity_id] = emote_label


func _remove_entity_visual(entity_id: String) -> void:
	if entity_id in _entity_sprites:
		_entity_sprites[entity_id].queue_free()
		_entity_sprites.erase(entity_id)
	if entity_id in _entity_labels:
		_entity_labels[entity_id].queue_free()
		_entity_labels.erase(entity_id)
	if entity_id in _entity_emotes:
		_entity_emotes[entity_id].queue_free()
		_entity_emotes.erase(entity_id)


## ====================================================================
## Object visuals
## ====================================================================

func _create_object_visual(obj_id: String, data: Dictionary) -> void:
	var sprite_path = "res://sprites/objects/" + obj_id + ".png"
	var visual: Control
	
	# Calculate scaled size (proportional to window!)
	var panel_size = size
	var fit = min(panel_size.x, panel_size.y)
	var scale = fit / _room_diameter
	var s = data.get("size", 32) * 2 * scale  # Scale with window!
	
	if ResourceLoader.exists(sprite_path):
		var tex_rect = TextureRect.new()
		tex_rect.texture = load(sprite_path)
		tex_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex_rect.stretch_mode = TextureRect.STRETCH_SCALE
		tex_rect.custom_minimum_size = Vector2(s, s)
		tex_rect.size = Vector2(s, s)  # Scale sprite to window size!
		visual = tex_rect
	else:
		# Circular fallback for objects in a circular room
		var rect = ColorRect.new()
		rect.color = OBJECT_COLOR
		rect.size = Vector2(s, s)
		visual = rect
	
	visual.z_index = 1
	add_child(visual)
	_object_sprites[obj_id] = visual
	
	var label = Label.new()
	label.text = data.get("display_name", obj_id)
	label.add_theme_font_size_override("font_size", 9)
	label.add_theme_color_override("font_color", Color(0.5, 0.48, 0.4))
	label.z_index = 2
	add_child(label)
	_object_labels[obj_id] = label


func _update_object_visual(obj_id: String, data: Dictionary) -> void:
	if obj_id not in _object_sprites:
		return
	
	var visual = _object_sprites[obj_id]
	
	# Recalculate scaled size (proportional to current window!)
	var panel_size = size
	var fit = min(panel_size.x, panel_size.y)
	var scale = fit / _room_diameter
	var s = data.get("size", 32) * 2 * scale  # Scale with window!
	
	# Update size
	visual.custom_minimum_size = Vector2(s, s)
	visual.size = Vector2(s, s)
	
	# Update position
	var screen_pos = _state_to_screen(data)
	visual.position = screen_pos - Vector2(s, s) / 2
	
	# Update label position
	if obj_id in _object_labels:
		var label = _object_labels[obj_id]
		label.position = Vector2(
			screen_pos.x - label.size.x / 2,
			screen_pos.y - s / 2 - 14
		)


func _remove_object_visual(obj_id: String) -> void:
	if obj_id in _object_sprites:
		_object_sprites[obj_id].queue_free()
		_object_sprites.erase(obj_id)
	if obj_id in _object_labels:
		_object_labels[obj_id].queue_free()
		_object_labels.erase(obj_id)


## ====================================================================
## Mini-map integration
## ====================================================================

func update_mini_map(registry: Dictionary) -> void:
	## Update mini-map from main.gd's room registry
	if _mini_map:
		_mini_map.update_from_registry(registry)


func set_mini_map_current_room(room_id: String) -> void:
	if _mini_map:
		_mini_map.set_current_room(room_id)


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_position_mini_map()
