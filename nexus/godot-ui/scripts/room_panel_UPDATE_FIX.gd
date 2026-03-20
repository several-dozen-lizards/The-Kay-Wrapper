
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
