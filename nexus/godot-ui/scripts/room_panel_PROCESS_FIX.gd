

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
