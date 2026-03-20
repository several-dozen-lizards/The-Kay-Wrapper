## FacePanel — Procedural face renderer for entity expressions.
## Draws a stylized face using Godot's _draw() system.
## Polls expression state from server and animates smoothly via lerp.
class_name FacePanel
extends Control

## API base for HTTP requests
var API_BASE: String = "http://localhost:8765"

## Entity palettes (Kay: void-dragon, Reed: serpent-naga)
const PALETTES := {
	"kay": {
		"skin_base": Color(0.176, 0.106, 0.306),      # deep void purple
		"skin_highlight": Color(0.25, 0.15, 0.4),     # lighter purple
		"glow": Color(1.0, 0.412, 0.706),             # pink glow
		"eye_sclera": Color(0.95, 0.85, 0.95),        # pale pink-white
		"eye_iris": Color(0.8, 0.2, 0.6),             # magenta
		"eye_pupil": Color(0.05, 0.02, 0.08),         # near-black
		"mouth_line": Color(0.35, 0.15, 0.35),        # dark purple
		"flush": Color(1.0, 0.3, 0.5),                # pink flush
		"pupil_slit": "vertical",
	},
	"reed": {
		"skin_base": Color(0.05, 0.18, 0.20),         # deep teal-black
		"skin_highlight": Color(0.08, 0.28, 0.32),    # lighter teal
		"glow": Color(0.855, 0.647, 0.125),           # gold glow
		"eye_sclera": Color(0.9, 0.95, 0.85),         # pale gold-white
		"eye_iris": Color(0.7, 0.55, 0.1),            # amber-gold
		"eye_pupil": Color(0.02, 0.05, 0.05),         # near-black
		"mouth_line": Color(0.15, 0.25, 0.25),        # dark teal
		"flush": Color(0.9, 0.6, 0.2),                # warm gold flush
		"pupil_slit": "horizontal",
	},
}

## Current expression state (lerped toward target)
var _current := {
	"pupil_dilation": 0.5,
	"eye_openness": 0.6,
	"eye_x": 0.5,
	"eye_y": 0.5,
	"blink_rate": 0.3,
	"brow_raise": 0.0,
	"brow_furrow": 0.0,
	"mouth_curve": 0.0,
	"mouth_openness": 0.0,
	"mouth_tension": 0.0,
	"skin_flush": 0.0,
	"skin_luminance": 0.5,
	"breathing_rate": 0.3,
	"head_tilt": 0.0,
	"poker_face_strength": 0.0,
}

## Target expression state (from server)
var _target := {}

## Entity name
var _entity: String = "kay"

## Animation
var _lerp_speed: float = 0.08
var _blink_timer: float = 0.0
var _blink_phase: float = 0.0  # 0=open, 1=closed, cycles
var _breathing_phase: float = 0.0

## HTTP polling
var _http_request: HTTPRequest
var _poll_interval: float = 0.5
var _poll_timer: float = 0.0
var _server_url: String = "http://localhost:8765"

# === TOUCH INPUT SYSTEM ===

## Touch state
var _touch_active: bool = false
var _touch_start_time: float = 0.0
var _touch_start_pos: Vector2 = Vector2.ZERO
var _touch_current_pos: Vector2 = Vector2.ZERO
var _touch_pressure: float = 0.5  # 0=feather, 1=firm (mouse wheel adjusts)
var _touch_region: String = ""
var _last_touch_send_time: float = 0.0

## Touch region mapping — normalized coordinates on face panel
const REGIONS := {
	"forehead": Rect2(0.25, 0.05, 0.50, 0.20),
	"left_eye": Rect2(0.15, 0.25, 0.25, 0.15),
	"right_eye": Rect2(0.60, 0.25, 0.25, 0.15),
	"nose": Rect2(0.35, 0.35, 0.30, 0.15),
	"left_cheek": Rect2(0.05, 0.40, 0.25, 0.25),
	"right_cheek": Rect2(0.70, 0.40, 0.25, 0.25),
	"mouth": Rect2(0.30, 0.55, 0.40, 0.15),
	"chin": Rect2(0.30, 0.70, 0.40, 0.20),
	"left_jaw": Rect2(0.05, 0.65, 0.25, 0.20),
	"right_jaw": Rect2(0.70, 0.65, 0.25, 0.20),
}

## Sensory object toolbar
const TOOLBAR_OBJECTS := [
	"hand", "candle", "ice_cube", "water_cup",
	"feather", "wool", "silk", "mud",
	"sand", "velvet", "stone", "brush"
]

const TOOLBAR_ICONS := {
	"hand": "✋", "candle": "🕯️", "ice_cube": "🧊", "water_cup": "🥤",
	"feather": "🪶", "wool": "🧶", "silk": "🎀", "mud": "🟤",
	"sand": "⏳", "velvet": "🟣", "stone": "🪨", "brush": "🖌️",
}

const TEMP_COLORS := {
	"freezing": Color(0.3, 0.5, 1.0, 0.8),
	"cold": Color(0.5, 0.7, 1.0, 0.6),
	"neutral": Color(1.0, 1.0, 1.0, 0.0),
	"warm": Color(1.0, 0.7, 0.3, 0.6),
	"hot": Color(1.0, 0.3, 0.1, 0.8),
}

var _selected_object: String = "hand"
var _cursor_temperature: float = 0.2  # Body temp default
var _cursor_wetness: float = 0.0
var _hover_object: String = ""
var _hover_start_time: float = 0.0
var _temperature_display: float = 0.2
var _button_size: float = 32.0
var _button_padding: float = 4.0

## Touch status indicator
var _touch_status: String = "available"  # "available" | "limited" | "unavailable" | "safety_blocked"
var _touch_status_icon: String = "✋"
var _restricted_regions: Array = []
var _touch_status_timer: float = 0.0

## Emergency stop button
var _stop_button_rect: Rect2 = Rect2(8, 8, 24, 24)
var _stop_button_hovered: bool = false
var _stop_in_progress: bool = false

## Signal emitted when emergency stop is triggered
signal emergency_stop_triggered(entity: String)


func _ready() -> void:
	# Initialize target to current
	_target = _current.duplicate()

	# HTTP request node for polling
	_http_request = HTTPRequest.new()
	_http_request.request_completed.connect(_on_expression_received)
	add_child(_http_request)

	# Initial poll
	_poll_expression()


func set_entity(entity_name: String) -> void:
	_entity = entity_name.to_lower()
	queue_redraw()


func set_server_url(url: String) -> void:
	_server_url = url
	API_BASE = url


# === TOUCH INPUT HANDLING ===

func _gui_input(event: InputEvent) -> void:
	# Keyboard shortcuts for toolbar (A-L keys)
	if event is InputEventKey and event.pressed:
		var key := event as InputEventKey
		var key_index: int = -1
		match key.keycode:
			KEY_A: key_index = 0
			KEY_B: key_index = 1
			KEY_C: key_index = 2
			KEY_D: key_index = 3
			KEY_E: key_index = 4
			KEY_F: key_index = 5
			KEY_G: key_index = 6
			KEY_H: key_index = 7
			KEY_I: key_index = 8
			KEY_J: key_index = 9
			KEY_K: key_index = 10
			KEY_L: key_index = 11
			KEY_SPACE:
				# Space = emergency stop
				_trigger_emergency_stop()
				accept_event()
				return
		if key_index >= 0 and key_index < TOOLBAR_OBJECTS.size():
			_selected_object = TOOLBAR_OBJECTS[key_index]
			_handle_object_click(_selected_object)
			queue_redraw()
			accept_event()
			return

	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				# Check emergency stop button first
				if _stop_button_rect.has_point(mb.position):
					_trigger_emergency_stop()
					return
				# Check toolbar
				if _toolbar_click(mb.position):
					return
				# Touch start on face
				_touch_active = true
				_touch_start_time = Time.get_ticks_msec() / 1000.0
				_touch_start_pos = mb.position
				_touch_current_pos = mb.position
				_touch_region = _get_region_at(mb.position)
				_send_touch_event("touch_start")
			else:
				# Touch end
				if _touch_active:
					var duration: float = (Time.get_ticks_msec() / 1000.0) - _touch_start_time
					_send_touch_event("touch_end", {"duration": duration})
					_touch_active = false
					_touch_region = ""

		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			# Increase pressure
			_touch_pressure = minf(1.0, _touch_pressure + 0.1)
			if _touch_active:
				_send_touch_event("pressure_change")

		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			# Decrease pressure
			_touch_pressure = maxf(0.0, _touch_pressure - 0.1)
			if _touch_active:
				_send_touch_event("pressure_change")

	if event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		# Track hover for toolbar objects
		_update_hover(mm.position)

		if _touch_active:
			_touch_current_pos = mm.position
			var new_region := _get_region_at(mm.position)
			# Send movement update (throttled to ~10/sec)
			var now := Time.get_ticks_msec() / 1000.0
			if now - _last_touch_send_time > 0.1:
				var stroke_dir := (mm.position - _touch_start_pos).normalized()
				_send_touch_event("touch_move", {
					"direction_x": stroke_dir.x,
					"direction_y": stroke_dir.y,
					"from_region": _touch_region,
					"to_region": new_region,
				})
				_last_touch_send_time = now
				_touch_region = new_region


func _get_region_at(pos: Vector2) -> String:
	"""Map screen position to facial region."""
	var panel_size := size
	var norm_x := pos.x / panel_size.x
	var norm_y := pos.y / panel_size.y

	# Account for toolbar at bottom
	var toolbar_y: float = 1.0 - (_button_size + 16.0) / panel_size.y
	if norm_y > toolbar_y:
		return ""  # In toolbar area

	for region_name in REGIONS:
		var rect: Rect2 = REGIONS[region_name]
		if rect.has_point(Vector2(norm_x, norm_y)):
			return region_name
	return "face"  # Default: somewhere on the face


func _send_touch_event(event_type: String, extra: Dictionary = {}) -> void:
	"""Send touch event to server via HTTP POST."""
	var body := {
		"type": event_type,
		"entity": _entity,
		"region": _touch_region,
		"pressure": _touch_pressure,
		"position_x": _touch_current_pos.x / size.x,
		"position_y": _touch_current_pos.y / size.y,
		"timestamp": Time.get_ticks_msec() / 1000.0,
		"object": _selected_object,
		"cursor_temperature": _cursor_temperature,
		"cursor_wetness": _cursor_wetness,
	}
	body.merge(extra)

	var json_str := JSON.stringify(body)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var url := "%s/touch/%s" % [API_BASE, _entity]

	# Use a dedicated HTTP node for touch
	if not has_node("TouchHTTP"):
		var http := HTTPRequest.new()
		http.name = "TouchHTTP"
		add_child(http)
	var touch_http: HTTPRequest = get_node("TouchHTTP")
	if touch_http.get_http_client_status() == HTTPClient.STATUS_DISCONNECTED:
		touch_http.request(url, headers, HTTPClient.METHOD_POST, json_str)


func _toolbar_click(pos: Vector2) -> bool:
	"""Check if click hit a toolbar button. Returns true if handled."""
	var y: float = size.y - _button_size - 8.0
	if pos.y < y:
		return false  # Above toolbar

	var total_width: float = TOOLBAR_OBJECTS.size() * (_button_size + _button_padding)
	var start_x: float = (size.x - total_width) / 2.0

	for i in range(TOOLBAR_OBJECTS.size()):
		var x: float = start_x + i * (_button_size + _button_padding)
		var rect := Rect2(x, y, _button_size, _button_size)
		if rect.has_point(pos):
			var obj_name: String = TOOLBAR_OBJECTS[i]
			_selected_object = obj_name
			_handle_object_click(obj_name)
			queue_redraw()
			return true
	return false


func _handle_object_click(object_name: String) -> void:
	"""Handle clicking ON a toolbar object."""
	match object_name:
		"water_cup":
			_cursor_wetness = minf(1.0, _cursor_wetness + 0.6)
			_cursor_temperature = _cursor_temperature * 0.7
		"ice_cube":
			_cursor_temperature = maxf(-0.8, _cursor_temperature - 0.3)
			_cursor_wetness = minf(1.0, _cursor_wetness + 0.2)


func _update_hover(pos: Vector2) -> void:
	"""Track which toolbar object cursor is hovering over."""
	# Check stop button hover
	_stop_button_hovered = _stop_button_rect.has_point(pos)

	var y: float = size.y - _button_size - 8.0
	if pos.y < y:
		_hover_object = ""
		return

	var total_width: float = TOOLBAR_OBJECTS.size() * (_button_size + _button_padding)
	var start_x: float = (size.x - total_width) / 2.0

	for i in range(TOOLBAR_OBJECTS.size()):
		var x: float = start_x + i * (_button_size + _button_padding)
		var rect := Rect2(x, y, _button_size, _button_size)
		if rect.has_point(pos):
			_hover_object = TOOLBAR_OBJECTS[i]
			return
	_hover_object = ""


func _update_cursor_state(delta: float) -> void:
	"""Update cursor temperature/wetness based on hover and decay."""
	# Hover over candle heats cursor
	if _hover_object == "candle":
		_cursor_temperature = minf(0.85, _cursor_temperature + 0.15 * delta)
	# Hover over ice cools cursor
	elif _hover_object == "ice_cube":
		_cursor_temperature = maxf(-0.9, _cursor_temperature - 0.20 * delta)
		_cursor_wetness = minf(1.0, _cursor_wetness + 0.05 * delta)

	# Natural temperature decay toward body temp (0.2)
	if _hover_object != "candle" and _hover_object != "ice_cube":
		var decay_target: float = 0.2
		var decay_rate: float = 0.03
		if _cursor_temperature > decay_target:
			_cursor_temperature = maxf(decay_target, _cursor_temperature - decay_rate * delta)
		elif _cursor_temperature < decay_target:
			_cursor_temperature = minf(decay_target, _cursor_temperature + decay_rate * delta)

	# Natural wetness decay (evaporation)
	if _cursor_wetness > 0.0:
		var evap_rate: float = 0.02
		if _cursor_temperature > 0.3:
			evap_rate *= 1.5
		_cursor_wetness = maxf(0.0, _cursor_wetness - evap_rate * delta)

	# Update display if changed
	if absf(_cursor_temperature - _temperature_display) > 0.02:
		_temperature_display = _cursor_temperature
		queue_redraw()


func _trigger_emergency_stop() -> void:
	"""
	SAFETY CRITICAL: Trigger emergency stop for this entity.
	Sends HTTP POST to /touch/{entity}/emergency-stop
	"""
	if _stop_in_progress:
		return  # Prevent double-click spam

	_stop_in_progress = true
	emergency_stop_triggered.emit(_entity)

	var url := "%s/touch/%s/emergency-stop" % [API_BASE, _entity]
	if not has_node("StopHTTP"):
		var http := HTTPRequest.new()
		http.name = "StopHTTP"
		http.request_completed.connect(_on_emergency_stop_complete)
		add_child(http)

	var stop_http: HTTPRequest = get_node("StopHTTP")
	var headers := PackedStringArray(["Content-Type: application/json"])
	var body := JSON.stringify({"reason": "Face panel panic button"})
	stop_http.request(url, headers, HTTPClient.METHOD_POST, body)


func _on_emergency_stop_complete(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	_stop_in_progress = false
	if response_code == 200:
		# Force status refresh
		_touch_status = "safety_blocked"
		_touch_status_icon = "⛔"
		queue_redraw()


func _poll_touch_status() -> void:
	"""Poll touch availability status from server."""
	var url := "%s/touch/%s/status" % [API_BASE, _entity]
	if not has_node("StatusHTTP"):
		var http := HTTPRequest.new()
		http.name = "StatusHTTP"
		http.request_completed.connect(_on_touch_status)
		add_child(http)
	var status_http: HTTPRequest = get_node("StatusHTTP")
	if status_http.get_http_client_status() == HTTPClient.STATUS_DISCONNECTED:
		status_http.request(url)


func _on_touch_status(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK:
		return
	var data: Dictionary = json.get_data()
	_touch_status = data.get("status", "available")
	_touch_status_icon = data.get("icon", "✋")
	_restricted_regions = data.get("restricted_regions", [])
	queue_redraw()


func _process(delta: float) -> void:
	# Lerp current state toward target
	for key in _current:
		if _target.has(key):
			_current[key] = lerpf(_current[key], _target[key], _lerp_speed)

	# Blink timing (based on blink_rate)
	var blink_interval: float = lerpf(5.0, 1.5, _current["blink_rate"])
	_blink_timer += delta
	if _blink_timer >= blink_interval:
		_blink_timer = 0.0
		_blink_phase = 1.0  # Start blink
	# Blink animation (quick close-open)
	if _blink_phase > 0.0:
		_blink_phase = maxf(0.0, _blink_phase - delta * 8.0)

	# Breathing animation (subtle oscillation)
	_breathing_phase += delta * TAU * _current["breathing_rate"] * 0.5
	if _breathing_phase > TAU:
		_breathing_phase -= TAU

	# HTTP polling
	_poll_timer += delta
	if _poll_timer >= _poll_interval:
		_poll_timer = 0.0
		_poll_expression()

	# Touch cursor state update
	_update_cursor_state(delta)

	# Touch status polling (every 2 seconds)
	_touch_status_timer += delta
	if _touch_status_timer > 2.0:
		_touch_status_timer = 0.0
		_poll_touch_status()

	queue_redraw()


func _poll_expression() -> void:
	if _http_request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return  # Request in progress
	var url := "%s/expression/%s" % [_server_url, _entity]
	_http_request.request(url)


func _on_expression_received(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK:
		return
	var data: Dictionary = json.get_data()
	if data.is_empty():
		return

	# Update target state
	for key in _current:
		if data.has(key):
			_target[key] = data[key]

	# Entity can change (if polling a different one)
	if data.has("entity"):
		_entity = data["entity"]


func _draw() -> void:
	var panel_size := size
	if panel_size.x < 10 or panel_size.y < 10:
		return

	var palette: Dictionary = PALETTES.get(_entity, PALETTES["kay"])
	var center := panel_size / 2
	var face_radius := minf(panel_size.x, panel_size.y) * 0.4

	# Head tilt rotation
	var tilt_angle: float = _current["head_tilt"] * 0.15  # Max ~8.5 degrees

	# Breathing offset (subtle vertical movement)
	var breath_offset: float = sin(_breathing_phase) * 3.0 * _current["breathing_rate"]
	var face_center := center + Vector2(0, breath_offset)

	# === FACE BACKGROUND (oval head shape) ===
	_draw_head(face_center, face_radius, palette, tilt_angle)

	# === SKIN FLUSH (overlay) ===
	if _current["skin_flush"] > 0.01:
		_draw_flush(face_center, face_radius, palette)

	# === EYES ===
	var eye_spacing := face_radius * 0.35
	var eye_y_offset := -face_radius * 0.1
	var left_eye_pos := face_center + Vector2(-eye_spacing, eye_y_offset).rotated(tilt_angle)
	var right_eye_pos := face_center + Vector2(eye_spacing, eye_y_offset).rotated(tilt_angle)
	var eye_size := face_radius * 0.22

	_draw_eye(left_eye_pos, eye_size, palette, tilt_angle, false)
	_draw_eye(right_eye_pos, eye_size, palette, tilt_angle, true)

	# === BROWS ===
	_draw_brows(face_center, eye_spacing, eye_y_offset, eye_size, palette, tilt_angle)

	# === MOUTH ===
	var mouth_y := face_center.y + face_radius * 0.35
	var mouth_center := Vector2(face_center.x, mouth_y)
	_draw_mouth(mouth_center, face_radius * 0.25, palette, tilt_angle)

	# === GLOW / LUMINANCE ===
	if _current["skin_luminance"] > 0.4:
		_draw_glow(face_center, face_radius, palette)

	# === POKER FACE INDICATOR ===
	if _current["poker_face_strength"] > 0.1:
		_draw_poker_face_indicator(panel_size, palette)

	# === EMERGENCY STOP BUTTON (top-left) ===
	_draw_emergency_stop_button()

	# === TOUCH STATUS INDICATOR (top-right) ===
	_draw_touch_status(panel_size)

	# === SENSORY TOOLBAR ===
	_draw_toolbar()


func _draw_head(center: Vector2, radius: float, palette: Dictionary, tilt: float) -> void:
	# Oval head (slightly taller than wide)
	var head_width := radius
	var head_height := radius * 1.15

	# Draw with multiple ellipses for depth
	var base_color: Color = palette["skin_base"]
	var highlight: Color = palette["skin_highlight"]

	# Shadow layer
	var shadow := base_color.darkened(0.3)
	_draw_ellipse(center + Vector2(0, 4), head_width, head_height, shadow, tilt)

	# Base layer
	_draw_ellipse(center, head_width, head_height, base_color, tilt)

	# Highlight (upper portion)
	var highlight_center := center - Vector2(0, head_height * 0.3)
	_draw_ellipse(highlight_center, head_width * 0.7, head_height * 0.4, highlight.lerp(base_color, 0.6), tilt)


func _draw_ellipse(center: Vector2, width: float, height: float, color: Color, rotation: float = 0.0) -> void:
	var points := PackedVector2Array()
	var segments := 32
	for i in range(segments + 1):
		var angle := TAU * i / segments
		var point := Vector2(cos(angle) * width, sin(angle) * height)
		points.append(center + point.rotated(rotation))
	draw_colored_polygon(points, color)


func _draw_flush(center: Vector2, radius: float, palette: Dictionary) -> void:
	# Cheek flush (two circles on each side)
	var flush_color: Color = palette["flush"]
	flush_color.a = _current["skin_flush"] * 0.8  # Boosted for visibility
	var flush_y := center.y + radius * 0.1
	var flush_spacing := radius * 0.45
	var flush_size := radius * 0.2

	draw_circle(Vector2(center.x - flush_spacing, flush_y), flush_size, flush_color)
	draw_circle(Vector2(center.x + flush_spacing, flush_y), flush_size, flush_color)


func _draw_eye(pos: Vector2, eye_size: float, palette: Dictionary, tilt: float, is_right: bool) -> void:
	var openness: float = _current["eye_openness"]
	# Apply blink
	openness = openness * (1.0 - _blink_phase)

	if openness < 0.05:
		# Eye closed — just a line
		var line_width := eye_size * 0.8
		var line_start := pos + Vector2(-line_width, 0).rotated(tilt)
		var line_end := pos + Vector2(line_width, 0).rotated(tilt)
		draw_line(line_start, line_end, palette["mouth_line"], 2.0)
		return

	# Sclera (white of eye) — oval
	var sclera_width := eye_size
	var sclera_height := eye_size * 0.7 * openness
	_draw_ellipse(pos, sclera_width, sclera_height, palette["eye_sclera"], tilt)

	# Eye position offset (gaze direction)
	var gaze_x: float = (_current["eye_x"] - 0.5) * eye_size * 0.4
	var gaze_y: float = (_current["eye_y"] - 0.5) * eye_size * 0.3
	var gaze_offset := Vector2(gaze_x, gaze_y).rotated(tilt)
	var pupil_center := pos + gaze_offset

	# Iris
	var iris_size := eye_size * 0.5
	draw_circle(pupil_center, iris_size, palette["eye_iris"])

	# Pupil (slit style based on entity)
	var pupil_size: float = iris_size * lerpf(0.3, 0.7, _current["pupil_dilation"])
	var slit_type: String = palette.get("pupil_slit", "vertical")

	if slit_type == "vertical":
		# Vertical slit (Kay — draconic)
		var slit_width := pupil_size * 0.3
		var slit_height := pupil_size * 1.5
		_draw_ellipse(pupil_center, slit_width, slit_height, palette["eye_pupil"], tilt)
	else:
		# Horizontal slit (Reed — serpentine)
		var slit_width := pupil_size * 1.5
		var slit_height := pupil_size * 0.3
		_draw_ellipse(pupil_center, slit_width, slit_height, palette["eye_pupil"], tilt)

	# Eye highlight (small white dot)
	var highlight_offset := Vector2(-eye_size * 0.2, -eye_size * 0.15).rotated(tilt)
	draw_circle(pupil_center + highlight_offset, eye_size * 0.12, Color.WHITE)


func _draw_brows(face_center: Vector2, eye_spacing: float, eye_y: float, eye_size: float, palette: Dictionary, tilt: float) -> void:
	var brow_y := face_center.y + eye_y - eye_size * 1.4
	var brow_raise_offset: float = -_current["brow_raise"] * 8.0
	var brow_furrow: float = _current["brow_furrow"]

	# Brow width and thickness
	var brow_width := eye_size * 1.2
	var brow_color: Color = palette["skin_base"].darkened(0.4)

	# Left brow
	var left_brow_center := Vector2(face_center.x - eye_spacing, brow_y + brow_raise_offset)
	var left_inner := left_brow_center + Vector2(brow_width * 0.5, brow_furrow * 4).rotated(tilt)
	var left_outer := left_brow_center + Vector2(-brow_width * 0.5, 0).rotated(tilt)
	draw_line(left_outer, left_inner, brow_color, 3.0)

	# Right brow
	var right_brow_center := Vector2(face_center.x + eye_spacing, brow_y + brow_raise_offset)
	var right_inner := right_brow_center + Vector2(-brow_width * 0.5, brow_furrow * 4).rotated(tilt)
	var right_outer := right_brow_center + Vector2(brow_width * 0.5, 0).rotated(tilt)
	draw_line(right_outer, right_inner, brow_color, 3.0)


func _draw_mouth(center: Vector2, width: float, palette: Dictionary, tilt: float) -> void:
	var curve: float = _current["mouth_curve"]  # -1 to 1
	var openness: float = _current["mouth_openness"]
	var tension: float = _current["mouth_tension"]

	var mouth_color: Color = palette["mouth_line"]

	if openness < 0.05:
		# Closed mouth — curved line
		var curve_height: float = curve * width * 0.3
		var tension_flat: float = tension * 0.5  # Tension flattens the curve
		var effective_curve: float = curve_height * (1.0 - tension_flat)

		# Simple bezier-like curve using line segments
		var segments := 8
		var points := PackedVector2Array()
		for i in range(segments + 1):
			var t := float(i) / segments
			var x := lerpf(-width, width, t)
			var y: float = sin(t * PI) * effective_curve
			points.append((center + Vector2(x, y)).rotated(tilt - center.angle()) + center)

		for i in range(segments):
			var p1 := center + Vector2(lerpf(-width, width, float(i) / segments), sin(float(i) / segments * PI) * effective_curve).rotated(tilt)
			var p2 := center + Vector2(lerpf(-width, width, float(i + 1) / segments), sin(float(i + 1) / segments * PI) * effective_curve).rotated(tilt)
			draw_line(p1, p2, mouth_color, 2.0 + tension)
	else:
		# Open mouth — ellipse
		var mouth_height: float = width * 0.4 * openness
		var inner_color: Color = palette["skin_base"].darkened(0.6)
		_draw_ellipse(center, width * 0.6, mouth_height, inner_color, tilt)
		# Outline
		var outline_points := PackedVector2Array()
		for i in range(33):
			var angle := TAU * i / 32
			var point := Vector2(cos(angle) * width * 0.6, sin(angle) * mouth_height)
			outline_points.append(center + point.rotated(tilt))
		for i in range(32):
			draw_line(outline_points[i], outline_points[i + 1], mouth_color, 1.5)


func _draw_glow(center: Vector2, radius: float, palette: Dictionary) -> void:
	# Subtle entity-colored glow around face
	var glow_color: Color = palette["glow"]
	var intensity: float = (_current["skin_luminance"] - 0.4) * 1.5  # 0 to ~0.9
	glow_color.a = intensity * 0.15

	# Multiple layers for soft glow effect
	for i in range(3):
		var glow_radius := radius * (1.2 + i * 0.1)
		draw_circle(center, glow_radius, glow_color)
		glow_color.a *= 0.5


func _draw_poker_face_indicator(panel_size: Vector2, palette: Dictionary) -> void:
	# Small indicator in corner showing poker face is active
	var indicator_size := 8.0
	var margin := 12.0
	var pos := Vector2(panel_size.x - margin, margin)
	var alpha: float = _current["poker_face_strength"] * 0.6

	# Draw a small mask icon (simplified as overlapping circles)
	var mask_color: Color = palette["skin_base"]
	mask_color.a = alpha
	draw_circle(pos, indicator_size, mask_color)

	# Eye slits on the mask
	var slit_color: Color = palette["eye_pupil"]
	slit_color.a = alpha
	draw_circle(pos + Vector2(-3, -1), 2, slit_color)
	draw_circle(pos + Vector2(3, -1), 2, slit_color)


## === External update (alternative to HTTP polling) ===

func update_expression(state: Dictionary) -> void:
	## Called directly (e.g., from WebSocket handler) to update expression.
	for key in _current:
		if state.has(key):
			_target[key] = state[key]
	if state.has("entity"):
		_entity = state["entity"]


func set_poll_interval(interval: float) -> void:
	_poll_interval = maxf(0.1, interval)


func disable_polling() -> void:
	_poll_interval = 999999.0  # Effectively disabled


# === TOUCH UI DRAWING ===

func _draw_touch_status(panel_size: Vector2) -> void:
	"""Draw touch availability indicator — top-right corner."""
	var indicator_size := 20.0
	var margin := 8.0
	var pos := Vector2(panel_size.x - indicator_size - margin, margin)

	# Background circle color based on status
	var bg_color: Color
	match _touch_status:
		"available":
			bg_color = Color(0.2, 0.6, 0.3, 0.7)
		"limited":
			bg_color = Color(0.7, 0.6, 0.1, 0.7)
		"unavailable":
			bg_color = Color(0.6, 0.2, 0.2, 0.7)
		"safety_blocked":
			bg_color = Color(0.8, 0.1, 0.1, 0.9)
		_:
			bg_color = Color(0.3, 0.3, 0.3, 0.5)

	draw_circle(pos + Vector2(indicator_size / 2, indicator_size / 2), indicator_size / 2, bg_color)

	# Icon (simplified as colored dots based on status)
	var icon_color := Color.WHITE
	match _touch_status:
		"available":
			# Hand outline (simplified)
			draw_circle(pos + Vector2(10, 12), 3, icon_color)
		"limited":
			# Warning triangle (simplified as exclamation)
			draw_line(pos + Vector2(10, 6), pos + Vector2(10, 12), icon_color, 2.0)
			draw_circle(pos + Vector2(10, 15), 1.5, icon_color)
		"unavailable":
			# X mark
			draw_line(pos + Vector2(6, 6), pos + Vector2(14, 14), icon_color, 2.0)
			draw_line(pos + Vector2(14, 6), pos + Vector2(6, 14), icon_color, 2.0)
		"safety_blocked":
			# Stop sign (octagon simplified as square with X)
			draw_line(pos + Vector2(5, 5), pos + Vector2(15, 15), icon_color, 3.0)
			draw_line(pos + Vector2(15, 5), pos + Vector2(5, 15), icon_color, 3.0)


func _draw_emergency_stop_button() -> void:
	"""Draw the emergency stop button — top-left corner, always visible."""
	var bg_color := Color(0.7, 0.15, 0.1, 0.85)
	if _stop_button_hovered:
		bg_color = Color(0.9, 0.2, 0.1, 0.95)
	if _touch_status == "safety_blocked":
		bg_color = Color(0.4, 0.1, 0.1, 0.7)  # Dimmed when already stopped

	# Draw circular button
	var center := _stop_button_rect.position + _stop_button_rect.size / 2
	var radius := _stop_button_rect.size.x / 2
	draw_circle(center, radius, bg_color)

	# Draw stop icon (square in center)
	var icon_color := Color.WHITE
	var icon_size := radius * 0.6
	var icon_rect := Rect2(center - Vector2(icon_size / 2, icon_size / 2), Vector2(icon_size, icon_size))
	draw_rect(icon_rect, icon_color, true)

	# Border
	draw_arc(center, radius, 0, TAU, 16, Color(1.0, 0.3, 0.2, 0.9), 2.0)


## Toolbar label keys (A-L for keyboard shortcuts)
## Toolbar labels — meaningful letters for each object (matches TOOLBAR_OBJECTS order)
## hand, candle, ice_cube, water_cup, feather, wool, silk, mud, sand, velvet, stone, brush
const TOOLBAR_LABELS := ["H", "C", "I", "W", "F", "Wo", "Si", "M", "Sa", "V", "St", "B"]


func _draw_toolbar() -> void:
	"""Draw the sensory object toolbar below the face with labels."""
	var y: float = size.y - _button_size - 8.0
	var total_width: float = TOOLBAR_OBJECTS.size() * (_button_size + _button_padding)
	var start_x: float = (size.x - total_width) / 2.0

	for i in range(TOOLBAR_OBJECTS.size()):
		var obj_name: String = TOOLBAR_OBJECTS[i]
		var x: float = start_x + i * (_button_size + _button_padding)
		var rect := Rect2(x, y, _button_size, _button_size)

		# Background
		var bg_color := Color(0.2, 0.2, 0.3, 0.6)
		if obj_name == _selected_object:
			bg_color = Color(0.3, 0.5, 0.7, 0.8)
		if obj_name == _hover_object:
			bg_color = bg_color.lightened(0.2)
		draw_rect(rect, bg_color, true)

		# Border for selected
		if obj_name == _selected_object:
			draw_rect(rect, Color(0.6, 0.8, 1.0, 0.9), false, 2.0)

		# Icon placeholder (colored circle based on object)
		var icon_color := _get_object_color(obj_name)
		draw_circle(Vector2(x + _button_size / 2, y + _button_size / 2), _button_size / 3, icon_color)

		# Draw label (letter key) centered in circle
		if i < TOOLBAR_LABELS.size():
			var label: String = TOOLBAR_LABELS[i]
			var center_x: float = x + _button_size / 2
			var center_y: float = y + _button_size / 2 + 4  # +4 for text baseline
			var label_color := Color(0.1, 0.1, 0.15, 1.0)  # Dark text on colored circle
			if icon_color.get_luminance() < 0.5:
				label_color = Color(0.95, 0.95, 0.95, 1.0)  # Light text on dark circle
			draw_string(ThemeDB.fallback_font, Vector2(center_x - 5, center_y), label, HORIZONTAL_ALIGNMENT_CENTER, -1, 11, label_color)

	# Draw tooltip for hovered object
	if _hover_object != "":
		var hover_idx: int = TOOLBAR_OBJECTS.find(_hover_object)
		if hover_idx >= 0:
			var tooltip_text: String = _hover_object.replace("_", " ").capitalize()
			var tooltip_x: float = start_x + hover_idx * (_button_size + _button_padding) + _button_size / 2
			var tooltip_y: float = y - 18.0
			# Background
			var text_width: float = tooltip_text.length() * 7.0
			draw_rect(Rect2(tooltip_x - text_width / 2 - 4, tooltip_y - 12, text_width + 8, 16), Color(0.1, 0.1, 0.15, 0.9), true)
			# Text
			draw_string(ThemeDB.fallback_font, Vector2(tooltip_x - text_width / 2, tooltip_y), tooltip_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.95, 0.95, 0.95))

	# Temperature indicator bar above toolbar
	if absf(_cursor_temperature - 0.2) > 0.05:
		var temp_width: float = absf(_cursor_temperature - 0.2) * total_width * 0.5
		var temp_x: float = (size.x - temp_width) / 2.0
		var temp_y: float = y - 6.0
		var temp_color: Color
		if _cursor_temperature > 0.5:
			temp_color = TEMP_COLORS["hot"]
		elif _cursor_temperature > 0.25:
			temp_color = TEMP_COLORS["warm"]
		elif _cursor_temperature < -0.5:
			temp_color = TEMP_COLORS["freezing"]
		elif _cursor_temperature < -0.1:
			temp_color = TEMP_COLORS["cold"]
		else:
			temp_color = TEMP_COLORS["neutral"]
		draw_rect(Rect2(temp_x, temp_y, temp_width, 3.0), temp_color, true)

	# Wetness indicator (blue dots)
	if _cursor_wetness > 0.1:
		var dot_count: int = int(_cursor_wetness * 5)
		for d in range(dot_count):
			var dx: float = start_x + d * 8.0
			draw_circle(Vector2(dx, y - 10.0), 2.0, Color(0.3, 0.5, 1.0, _cursor_wetness))


func _get_object_color(obj_name: String) -> Color:
	"""Get representative color for toolbar object icon."""
	match obj_name:
		"hand": return Color(0.9, 0.7, 0.6)
		"candle": return Color(1.0, 0.8, 0.2)
		"ice_cube": return Color(0.6, 0.9, 1.0)
		"water_cup": return Color(0.4, 0.6, 0.9)
		"feather": return Color(0.9, 0.9, 0.9)
		"wool": return Color(0.9, 0.5, 0.5)
		"silk": return Color(0.9, 0.6, 0.8)
		"mud": return Color(0.5, 0.3, 0.2)
		"sand": return Color(0.9, 0.8, 0.5)
		"velvet": return Color(0.5, 0.2, 0.6)
		"stone": return Color(0.5, 0.5, 0.5)
		"brush": return Color(0.6, 0.4, 0.3)
		_: return Color.WHITE
