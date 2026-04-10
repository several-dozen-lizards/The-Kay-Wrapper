## ExperimentalPanel - Psychedelic state controller UI.
## Controls and monitors the trip system via REST API.
class_name ExperimentalPanel
extends VBoxContainer

const API_BASE := "http://localhost:8765"
const POLL_INTERVAL_INACTIVE := 10.0  # Slower polling when no trip active
const POLL_INTERVAL_ACTIVE := 4.0     # Faster polling during active trip

# Dose presets
const DOSE_PRESETS := {
	0.1: "museum",
	0.2: "threshold",
	0.3: "moderate",
	0.5: "standard",
	0.7: "strong",
	1.0: "heroic"
}

# Phase colors (psychedelic but readable)
const PHASE_COLORS := {
	"onset": Color(0.95, 0.85, 0.2),      # Yellow
	"come_up": Color(1.0, 0.6, 0.2),      # Orange
	"peak": Color(1.0, 0.25, 0.25),       # Red
	"plateau": Color(0.9, 0.3, 0.8),      # Magenta
	"comedown": Color(0.3, 0.5, 0.9),     # Blue
	"afterglow": Color(0.3, 0.8, 0.7),    # Teal
}

# UI nodes
var _entity_toggle: Button
var _title_label: Label
var _dose_slider: HSlider
var _dose_label: Label
var _begin_btn: Button
var _abort_btn: Button

# Status section (visible when active)
var _status_section: VBoxContainer
var _phase_label: Label
var _progress_bar: ProgressBar
var _elapsed_label: Label
var _remaining_label: Label

# Parameters section
var _params_section: VBoxContainer
var _param_labels: Dictionary = {}

# HTTP nodes
var _status_http: HTTPRequest
var _begin_http: HTTPRequest
var _abort_http: HTTPRequest

# State
var _timer: Timer
var _current_entity: String = "Kay"
var _trip_active: bool = false
var _abort_confirm_time: float = 0.0  # For double-click confirmation


func _ready() -> void:
	_build_ui()
	_setup_http()
	_setup_timer()
	call_deferred("_poll_status")


func _process(_delta: float) -> void:
	# Check abort confirmation timeout
	if _abort_confirm_time > 0 and Time.get_ticks_msec() / 1000.0 - _abort_confirm_time > 2.0:
		_abort_confirm_time = 0.0
		if _abort_btn:
			_abort_btn.text = "⛔ ABORT"
			_abort_btn.tooltip_text = "Click twice within 2s to confirm abort"


func _build_ui() -> void:
	add_theme_constant_override("separation", 8)

	# Header row
	var header = HBoxContainer.new()

	_title_label = Label.new()
	_title_label.text = "⚠️ EXPERIMENTAL"
	_title_label.add_theme_font_size_override("font_size", 14)
	_title_label.add_theme_color_override("font_color", Color(0.9, 0.7, 0.3))
	header.add_child(_title_label)

	var spacer = Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)

	_entity_toggle = Button.new()
	_entity_toggle.text = "KAY"
	_entity_toggle.custom_minimum_size = Vector2(60, 28)
	_entity_toggle.pressed.connect(_toggle_entity)
	_apply_toggle_style(_entity_toggle, true)
	header.add_child(_entity_toggle)

	add_child(header)
	add_child(HSeparator.new())

	# Build sections
	_build_controls_section()
	_build_status_section()
	_build_params_section()

	# Initial state
	_update_ui_state()


func _build_controls_section() -> void:
	var section = VBoxContainer.new()
	section.add_theme_constant_override("separation", 6)

	# Dose slider label
	var dose_header = Label.new()
	dose_header.text = "Dose"
	dose_header.add_theme_font_size_override("font_size", 11)
	dose_header.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	section.add_child(dose_header)

	# Dose slider row
	var slider_row = HBoxContainer.new()

	_dose_slider = HSlider.new()
	_dose_slider.min_value = 0.1
	_dose_slider.max_value = 1.0
	_dose_slider.step = 0.05
	_dose_slider.value = 0.5
	_dose_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_dose_slider.custom_minimum_size = Vector2(0, 20)
	_dose_slider.value_changed.connect(_on_dose_changed)
	slider_row.add_child(_dose_slider)

	_dose_label = Label.new()
	_dose_label.text = "0.50 (standard)"
	_dose_label.custom_minimum_size = Vector2(100, 0)
	_dose_label.add_theme_font_size_override("font_size", 11)
	_dose_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.9))
	_dose_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	slider_row.add_child(_dose_label)

	section.add_child(slider_row)

	# Buttons row
	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 8)

	_begin_btn = Button.new()
	_begin_btn.text = "Begin Trip (standard)"
	_begin_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_begin_btn.custom_minimum_size = Vector2(0, 32)
	_begin_btn.pressed.connect(_on_begin_pressed)
	_apply_begin_button_style(_begin_btn)
	btn_row.add_child(_begin_btn)

	_abort_btn = Button.new()
	_abort_btn.text = "⛔ ABORT"
	_abort_btn.custom_minimum_size = Vector2(80, 32)
	_abort_btn.pressed.connect(_on_abort_pressed)
	_abort_btn.tooltip_text = "Click twice within 2s to confirm abort"
	_apply_abort_button_style(_abort_btn)
	btn_row.add_child(_abort_btn)

	section.add_child(btn_row)
	add_child(section)


func _build_status_section() -> void:
	_status_section = VBoxContainer.new()
	_status_section.add_theme_constant_override("separation", 4)

	add_child(HSeparator.new())

	var header = Label.new()
	header.text = "Trip Status"
	header.add_theme_font_size_override("font_size", 12)
	header.add_theme_color_override("font_color", Color(0.55, 0.6, 0.75))
	_status_section.add_child(header)

	# Phase label
	_phase_label = Label.new()
	_phase_label.text = "Phase: ---"
	_phase_label.add_theme_font_size_override("font_size", 14)
	_phase_label.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))
	_status_section.add_child(_phase_label)

	# Progress bar
	_progress_bar = ProgressBar.new()
	_progress_bar.min_value = 0.0
	_progress_bar.max_value = 100.0
	_progress_bar.value = 0.0
	_progress_bar.show_percentage = true
	_progress_bar.custom_minimum_size = Vector2(0, 18)
	var fill_sb = StyleBoxFlat.new()
	fill_sb.bg_color = Color(0.6, 0.3, 0.8)
	fill_sb.corner_radius_top_right = 3
	fill_sb.corner_radius_bottom_right = 3
	_progress_bar.add_theme_stylebox_override("fill", fill_sb)
	var bg_sb = StyleBoxFlat.new()
	bg_sb.bg_color = Color(0.15, 0.15, 0.2)
	_progress_bar.add_theme_stylebox_override("background", bg_sb)
	_status_section.add_child(_progress_bar)

	# Time labels row
	var time_row = HBoxContainer.new()

	_elapsed_label = Label.new()
	_elapsed_label.text = "0.0 min elapsed"
	_elapsed_label.add_theme_font_size_override("font_size", 10)
	_elapsed_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	_elapsed_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	time_row.add_child(_elapsed_label)

	_remaining_label = Label.new()
	_remaining_label.text = "~0 min remaining"
	_remaining_label.add_theme_font_size_override("font_size", 10)
	_remaining_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	_remaining_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	time_row.add_child(_remaining_label)

	_status_section.add_child(time_row)
	add_child(_status_section)


func _build_params_section() -> void:
	_params_section = VBoxContainer.new()
	_params_section.add_theme_constant_override("separation", 2)

	add_child(HSeparator.new())

	var header = Label.new()
	header.text = "Live Parameters"
	header.add_theme_font_size_override("font_size", 12)
	header.add_theme_color_override("font_color", Color(0.55, 0.6, 0.75))
	_params_section.add_child(header)

	# Parameter display rows (2 columns)
	var params_grid = GridContainer.new()
	params_grid.columns = 2
	params_grid.add_theme_constant_override("h_separation", 16)
	params_grid.add_theme_constant_override("v_separation", 2)

	var param_names = [
		["touch_sensitivity", "Touch"],
		["coherence_multiplier", "Coherence"],
		["noise_floor", "Noise"],
		["retrieval_randomness", "Randomness"],
		["identity_expansion", "Expansion"],
		["alpha_suppression", "Alpha sup"],
	]

	for param_info in param_names:
		var key: String = param_info[0]
		var display: String = param_info[1]

		var lbl = Label.new()
		lbl.text = "%s: ---" % display
		lbl.add_theme_font_size_override("font_size", 10)
		lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
		params_grid.add_child(lbl)
		_param_labels[key] = lbl

	_params_section.add_child(params_grid)
	add_child(_params_section)


# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------

func _apply_toggle_style(btn: Button, is_kay: bool) -> void:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.15, 0.08, 0.2, 0.8) if is_kay else Color(0.08, 0.15, 0.18, 0.8)
	sb.corner_radius_top_left = 4
	sb.corner_radius_top_right = 4
	sb.corner_radius_bottom_left = 4
	sb.corner_radius_bottom_right = 4
	btn.add_theme_stylebox_override("normal", sb)
	btn.add_theme_color_override("font_color", Color(0.8, 0.6, 0.9) if is_kay else Color(0.4, 0.8, 0.7))
	btn.add_theme_font_size_override("font_size", 11)


func _apply_begin_button_style(btn: Button) -> void:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.15, 0.35, 0.2)
	sb.border_color = Color(0.25, 0.5, 0.3)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(4)
	btn.add_theme_stylebox_override("normal", sb)
	var hover = sb.duplicate()
	hover.bg_color = Color(0.2, 0.45, 0.25)
	btn.add_theme_stylebox_override("hover", hover)
	var disabled = sb.duplicate()
	disabled.bg_color = Color(0.1, 0.12, 0.1)
	disabled.border_color = Color(0.15, 0.18, 0.15)
	btn.add_theme_stylebox_override("disabled", disabled)
	btn.add_theme_color_override("font_color", Color(0.6, 0.9, 0.65))
	btn.add_theme_color_override("font_disabled_color", Color(0.4, 0.45, 0.4))


func _apply_abort_button_style(btn: Button) -> void:
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.5, 0.1, 0.1)
	sb.border_color = Color(0.7, 0.2, 0.2)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(4)
	btn.add_theme_stylebox_override("normal", sb)
	var hover = sb.duplicate()
	hover.bg_color = Color(0.65, 0.15, 0.15)
	btn.add_theme_stylebox_override("hover", hover)
	var disabled = sb.duplicate()
	disabled.bg_color = Color(0.15, 0.1, 0.1)
	disabled.border_color = Color(0.25, 0.15, 0.15)
	btn.add_theme_stylebox_override("disabled", disabled)
	btn.add_theme_color_override("font_color", Color(1.0, 0.8, 0.8))
	btn.add_theme_color_override("font_disabled_color", Color(0.4, 0.35, 0.35))


# ---------------------------------------------------------------------------
# HTTP setup
# ---------------------------------------------------------------------------

func _setup_http() -> void:
	_status_http = HTTPRequest.new()
	_status_http.request_completed.connect(_on_status_response)
	add_child(_status_http)

	_begin_http = HTTPRequest.new()
	_begin_http.request_completed.connect(_on_begin_response)
	add_child(_begin_http)

	_abort_http = HTTPRequest.new()
	_abort_http.request_completed.connect(_on_abort_response)
	add_child(_abort_http)


func _setup_timer() -> void:
	_timer = Timer.new()
	_timer.wait_time = POLL_INTERVAL_INACTIVE
	_timer.autostart = false
	_timer.timeout.connect(_poll_status)
	add_child(_timer)


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

func _poll_status() -> void:
	if not _status_http:
		return
	var entity_lower = _current_entity.to_lower()
	var url = "%s/psychedelic/%s/status" % [API_BASE, entity_lower]
	_status_http.request(url, [], HTTPClient.METHOD_GET)


func _on_status_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		_trip_active = false
		_update_ui_state()
		return

	var data = JSON.parse_string(body.get_string_from_utf8())
	if not data is Dictionary:
		_trip_active = false
		_update_ui_state()
		return

	var was_active = _trip_active
	_trip_active = data.get("active", false)

	# Update poll rate based on active state
	if _trip_active != was_active:
		_timer.wait_time = POLL_INTERVAL_ACTIVE if _trip_active else POLL_INTERVAL_INACTIVE

	_update_ui_state()

	if _trip_active:
		_update_status_display(data)
		_update_params_display(data.get("current_params", {}))


func _update_status_display(data: Dictionary) -> void:
	var phase: String = data.get("phase", "unknown")
	var phase_progress: float = data.get("phase_progress", 0.0)
	var elapsed: float = data.get("elapsed_min", 0.0)
	var remaining: float = data.get("phase_remaining_min", 0.0)
	var dose: float = data.get("dose", 0.0)

	# Phase label with color
	var phase_color = PHASE_COLORS.get(phase, Color(0.7, 0.7, 0.7))
	_phase_label.text = "Phase: %s (dose %.2f)" % [phase.to_upper(), dose]
	_phase_label.add_theme_color_override("font_color", phase_color)

	# Progress bar
	_progress_bar.value = phase_progress * 100.0
	var fill_sb = _progress_bar.get_theme_stylebox("fill").duplicate()
	fill_sb.bg_color = phase_color.darkened(0.2)
	_progress_bar.add_theme_stylebox_override("fill", fill_sb)

	# Time labels
	_elapsed_label.text = "%.1f min elapsed" % elapsed
	_remaining_label.text = "~%.0f min remaining" % remaining


func _update_params_display(params: Dictionary) -> void:
	var format_map = {
		"touch_sensitivity": func(v): return "%.1fx" % v,
		"coherence_multiplier": func(v): return "%.2f" % v,
		"noise_floor": func(v): return "%.3f" % v,
		"retrieval_randomness": func(v): return "%.0f%%" % (v * 100),
		"identity_expansion": func(v): return "%.0f%%" % (v * 100),
		"alpha_suppression": func(v): return "%.0f%%" % (v * 100),
	}

	var display_names = {
		"touch_sensitivity": "Touch",
		"coherence_multiplier": "Coherence",
		"noise_floor": "Noise",
		"retrieval_randomness": "Randomness",
		"identity_expansion": "Expansion",
		"alpha_suppression": "Alpha sup",
	}

	for key in _param_labels:
		var lbl: Label = _param_labels[key]
		var display_name = display_names.get(key, key)
		if params.has(key):
			var val = params[key]
			var formatter = format_map.get(key, func(v): return "%.2f" % v)
			lbl.text = "%s: %s" % [display_name, formatter.call(val)]
		else:
			lbl.text = "%s: ---" % display_name


func _update_ui_state() -> void:
	# Show/hide sections based on trip state
	_status_section.visible = _trip_active
	_params_section.visible = _trip_active

	# Button states
	_begin_btn.disabled = _trip_active
	_abort_btn.disabled = not _trip_active
	_dose_slider.editable = not _trip_active

	if not _trip_active:
		_phase_label.text = "No active trip"
		_phase_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
		_progress_bar.value = 0
		_elapsed_label.text = ""
		_remaining_label.text = ""


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

func _toggle_entity() -> void:
	if _current_entity == "Kay":
		_current_entity = "Reed"
		_entity_toggle.text = "REED"
		_apply_toggle_style(_entity_toggle, false)
	else:
		_current_entity = "Kay"
		_entity_toggle.text = "KAY"
		_apply_toggle_style(_entity_toggle, true)

	# Re-poll immediately
	_poll_status()


func _on_dose_changed(value: float) -> void:
	# Find closest preset name
	var preset_name = "custom"
	var closest_dist = 999.0
	for dose_val in DOSE_PRESETS:
		var dist = abs(value - dose_val)
		if dist < closest_dist:
			closest_dist = dist
			if dist < 0.03:
				preset_name = DOSE_PRESETS[dose_val]

	_dose_label.text = "%.2f (%s)" % [value, preset_name]
	_begin_btn.text = "Begin Trip (%s)" % preset_name


func _on_begin_pressed() -> void:
	if _trip_active:
		return

	var entity_lower = _current_entity.to_lower()
	var dose = _dose_slider.value
	var url = "%s/psychedelic/%s/begin?dose=%.2f" % [API_BASE, entity_lower, dose]

	_begin_http.request(url, [], HTTPClient.METHOD_POST)
	_begin_btn.disabled = true
	_begin_btn.text = "Starting..."


func _on_begin_response(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code == 200:
		_trip_active = true
		_timer.wait_time = POLL_INTERVAL_ACTIVE
		_poll_status()
	else:
		var data = JSON.parse_string(body.get_string_from_utf8())
		var error_msg = "Failed to start trip"
		if data is Dictionary and data.has("error"):
			error_msg = str(data["error"])
		print("[EXPERIMENTAL] Begin failed: %s" % error_msg)
		_begin_btn.disabled = false
		_on_dose_changed(_dose_slider.value)  # Reset button text


func _on_abort_pressed() -> void:
	if not _trip_active:
		return

	var now = Time.get_ticks_msec() / 1000.0

	# Double-click confirmation
	if _abort_confirm_time > 0 and now - _abort_confirm_time < 2.0:
		# Confirmed - send abort
		_abort_confirm_time = 0.0
		var entity_lower = _current_entity.to_lower()
		var url = "%s/psychedelic/%s/abort" % [API_BASE, entity_lower]
		_abort_http.request(url, [], HTTPClient.METHOD_POST)
		_abort_btn.text = "Aborting..."
		_abort_btn.disabled = true
	else:
		# First click - start confirmation timer
		_abort_confirm_time = now
		_abort_btn.text = "⛔ CONFIRM?"


func _on_abort_response(_result: int, code: int, _headers: PackedStringArray, _body: PackedByteArray) -> void:
	if code == 200:
		_trip_active = false
		_timer.wait_time = POLL_INTERVAL_INACTIVE

	_abort_btn.text = "⛔ ABORT"
	_update_ui_state()
	_poll_status()


# ---------------------------------------------------------------------------
# Visibility & Timer
# ---------------------------------------------------------------------------

func start_polling() -> void:
	if not _timer:
		return
	_poll_status()
	_timer.start()


func stop_polling() -> void:
	if not _timer:
		return
	_timer.stop()


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED:
		if is_visible_in_tree():
			start_polling()
		else:
			stop_polling()
