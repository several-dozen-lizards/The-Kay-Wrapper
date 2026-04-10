## OscillatorPanel - Live oscillator frequency visualization.
## Polls /oscillator/{entity} REST endpoint and renders band power bars,
## coherence, PLV coupling, and body_feels emotion bridge output.
class_name OscillatorPanel
extends VBoxContainer

const API_BASE := "http://localhost:8765"
const POLL_INTERVAL := 4.0

# Band colors (matching EEG convention)
const BAND_COLORS := {
	"delta": Color(0.3, 0.2, 0.6),    # Deep purple
	"theta": Color(0.2, 0.4, 0.8),    # Blue
	"alpha": Color(0.2, 0.7, 0.4),    # Green
	"beta": Color(0.9, 0.7, 0.1),     # Gold
	"gamma": Color(0.9, 0.2, 0.3),    # Red
}
const BAND_ORDER := ["delta", "theta", "alpha", "beta", "gamma"]

# UI nodes
var _entity_toggle: Button
var _body_feels_label: RichTextLabel
var _dominant_label: Label
var _coherence_bar: ProgressBar
var _coherence_label: Label
var _integration_label: Label
var _dwell_label: Label
var _transition_label: Label
var _band_bars: Dictionary = {}  # band_name -> ProgressBar
var _band_labels: Dictionary = {}  # band_name -> Label
var _plv_labels: Dictionary = {}  # pair_name -> Label

# PLV pairs to display
const PLV_PAIRS := ["theta_gamma", "beta_gamma", "theta_alpha"]
const PLV_NAMES := {"theta_gamma": "tg mem", "beta_gamma": "bg emo", "theta_alpha": "ta relax"}

# HTTP + timer
var _http: HTTPRequest
var _timer: Timer
var _current_entity: String = "Kay"

# Smoothed values for animation
var _target_bands: Dictionary = {}
var _current_bands: Dictionary = {}
var _target_coherence: float = 0.5
var _current_coherence: float = 0.5
var _lerp_speed: float = 8.0


func _ready() -> void:
	for b in BAND_ORDER:
		_target_bands[b] = 0.0
		_current_bands[b] = 0.0
	_build_ui()
	_setup_http()
	_setup_timer()
	call_deferred("_poll")


func _process(delta: float) -> void:
	# Smooth lerp band bars toward target values
	for b in BAND_ORDER:
		_current_bands[b] = lerp(_current_bands[b], _target_bands[b], delta * _lerp_speed)
		if b in _band_bars:
			_band_bars[b].value = _current_bands[b] * 100.0
			# Update value label
			if (b + "_val") in _band_labels:
				_band_labels[b + "_val"].text = "%d%%" % int(_current_bands[b] * 100.0)

	# Smooth lerp coherence bar
	_current_coherence = lerp(_current_coherence, _target_coherence, delta * _lerp_speed)
	if _coherence_bar:
		_coherence_bar.value = _current_coherence * 100.0


func _build_ui() -> void:
	# Entity toggle button
	_entity_toggle = Button.new()
	_entity_toggle.text = "KAY"
	_entity_toggle.pressed.connect(_toggle_entity)
	_entity_toggle.custom_minimum_size = Vector2(0, 28)
	var toggle_sb = StyleBoxFlat.new()
	toggle_sb.bg_color = Color(0.15, 0.08, 0.2, 0.8)
	toggle_sb.corner_radius_top_left = 4
	toggle_sb.corner_radius_top_right = 4
	_entity_toggle.add_theme_stylebox_override("normal", toggle_sb)
	_entity_toggle.add_theme_color_override("font_color", Color(0.8, 0.6, 0.9))
	_entity_toggle.add_theme_font_size_override("font_size", 11)
	add_child(_entity_toggle)

	# body_feels label (prominent, top)
	_body_feels_label = RichTextLabel.new()
	_body_feels_label.bbcode_enabled = true
	_body_feels_label.fit_content = true
	_body_feels_label.custom_minimum_size = Vector2(0, 24)
	_body_feels_label.add_theme_font_size_override("normal_font_size", 12)
	add_child(_body_feels_label)

	# Band power bars
	for b in BAND_ORDER:
		var row = HBoxContainer.new()
		row.custom_minimum_size = Vector2(0, 18)

		var lbl = Label.new()
		lbl.text = b.substr(0, 2).to_upper()
		lbl.custom_minimum_size = Vector2(28, 0)
		lbl.add_theme_font_size_override("font_size", 10)
		lbl.add_theme_color_override("font_color", BAND_COLORS[b].lightened(0.3))
		row.add_child(lbl)
		_band_labels[b] = lbl

		var bar = ProgressBar.new()
		bar.min_value = 0.0
		bar.max_value = 100.0
		bar.value = 0.0
		bar.show_percentage = false
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.custom_minimum_size = Vector2(0, 14)
		# Style the bar fill
		var fill_sb = StyleBoxFlat.new()
		fill_sb.bg_color = BAND_COLORS[b]
		fill_sb.corner_radius_top_right = 2
		fill_sb.corner_radius_bottom_right = 2
		bar.add_theme_stylebox_override("fill", fill_sb)
		var bg_sb = StyleBoxFlat.new()
		bg_sb.bg_color = BAND_COLORS[b].darkened(0.7)
		bar.add_theme_stylebox_override("background", bg_sb)
		row.add_child(bar)
		_band_bars[b] = bar

		var val_lbl = Label.new()
		val_lbl.text = "0%"
		val_lbl.custom_minimum_size = Vector2(34, 0)
		val_lbl.add_theme_font_size_override("font_size", 9)
		val_lbl.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
		val_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		row.add_child(val_lbl)
		_band_labels[b + "_val"] = val_lbl

		add_child(row)

	# Separator
	var sep1 = HSeparator.new()
	sep1.custom_minimum_size = Vector2(0, 8)
	add_child(sep1)

	# Dominant band + dwell time row
	var dom_row = HBoxContainer.new()
	dom_row.custom_minimum_size = Vector2(0, 20)

	_dominant_label = Label.new()
	_dominant_label.text = "DOMINANT: ---"
	_dominant_label.add_theme_font_size_override("font_size", 10)
	_dominant_label.add_theme_color_override("font_color", Color(0.9, 0.85, 0.6))
	_dominant_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dom_row.add_child(_dominant_label)

	_dwell_label = Label.new()
	_dwell_label.text = "0.0s"
	_dwell_label.add_theme_font_size_override("font_size", 9)
	_dwell_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.6))
	_dwell_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_dwell_label.custom_minimum_size = Vector2(40, 0)
	dom_row.add_child(_dwell_label)

	add_child(dom_row)

	# Transition indicator row
	_transition_label = Label.new()
	_transition_label.text = ""
	_transition_label.add_theme_font_size_override("font_size", 9)
	_transition_label.add_theme_color_override("font_color", Color(0.7, 0.5, 0.8))
	_transition_label.custom_minimum_size = Vector2(0, 16)
	add_child(_transition_label)

	# Coherence row
	var coh_row = HBoxContainer.new()
	coh_row.custom_minimum_size = Vector2(0, 20)

	var coh_lbl = Label.new()
	coh_lbl.text = "COH"
	coh_lbl.custom_minimum_size = Vector2(28, 0)
	coh_lbl.add_theme_font_size_override("font_size", 10)
	coh_lbl.add_theme_color_override("font_color", Color(0.6, 0.8, 0.9))
	coh_row.add_child(coh_lbl)

	_coherence_bar = ProgressBar.new()
	_coherence_bar.min_value = 0.0
	_coherence_bar.max_value = 100.0
	_coherence_bar.value = 50.0
	_coherence_bar.show_percentage = false
	_coherence_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_coherence_bar.custom_minimum_size = Vector2(0, 12)
	var coh_fill = StyleBoxFlat.new()
	coh_fill.bg_color = Color(0.4, 0.7, 0.9)
	coh_fill.corner_radius_top_right = 2
	coh_fill.corner_radius_bottom_right = 2
	_coherence_bar.add_theme_stylebox_override("fill", coh_fill)
	var coh_bg = StyleBoxFlat.new()
	coh_bg.bg_color = Color(0.15, 0.2, 0.25)
	_coherence_bar.add_theme_stylebox_override("background", coh_bg)
	coh_row.add_child(_coherence_bar)

	_coherence_label = Label.new()
	_coherence_label.text = "0.50"
	_coherence_label.custom_minimum_size = Vector2(34, 0)
	_coherence_label.add_theme_font_size_override("font_size", 9)
	_coherence_label.add_theme_color_override("font_color", Color(0.6, 0.8, 0.9))
	_coherence_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	coh_row.add_child(_coherence_label)

	add_child(coh_row)

	# Integration index label
	_integration_label = Label.new()
	_integration_label.text = "INT: 0.00"
	_integration_label.add_theme_font_size_override("font_size", 9)
	_integration_label.add_theme_color_override("font_color", Color(0.5, 0.7, 0.6))
	_integration_label.custom_minimum_size = Vector2(0, 16)
	add_child(_integration_label)

	# Separator before PLV
	var sep2 = HSeparator.new()
	sep2.custom_minimum_size = Vector2(0, 6)
	add_child(sep2)

	# PLV coupling header
	var plv_header = Label.new()
	plv_header.text = "PHASE-LOCKING (PLV)"
	plv_header.add_theme_font_size_override("font_size", 9)
	plv_header.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))
	plv_header.custom_minimum_size = Vector2(0, 16)
	add_child(plv_header)

	# PLV coupling labels
	var plv_row = HBoxContainer.new()
	plv_row.custom_minimum_size = Vector2(0, 18)

	for pair in PLV_PAIRS:
		var plv_lbl = Label.new()
		plv_lbl.text = "%s: ---" % PLV_NAMES[pair]
		plv_lbl.add_theme_font_size_override("font_size", 9)
		plv_lbl.add_theme_color_override("font_color", Color(0.6, 0.55, 0.7))
		plv_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		plv_row.add_child(plv_lbl)
		_plv_labels[pair] = plv_lbl

	add_child(plv_row)


func _setup_http() -> void:
	_http = HTTPRequest.new()
	_http.name = "OscillatorHTTP"
	add_child(_http)
	_http.request_completed.connect(_on_response)


func _setup_timer() -> void:
	_timer = Timer.new()
	_timer.name = "PollTimer"
	_timer.wait_time = POLL_INTERVAL
	_timer.one_shot = false
	_timer.autostart = true
	add_child(_timer)
	_timer.timeout.connect(_poll)


func _poll() -> void:
	if not _http:
		return
	var entity_lower = _current_entity.to_lower()
	var url = "%s/oscillator/%s" % [API_BASE, entity_lower]
	var err = _http.request(url)
	if err != OK:
		print("[OSC PANEL] HTTP request failed: ", err)


func _on_response(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		# Silently fail — endpoint may not be running
		_body_feels_label.text = "[color=#666]offline[/color]"
		return

	var json_str = body.get_string_from_utf8()
	var json = JSON.parse_string(json_str)
	if not json is Dictionary:
		return

	# Update band power targets (smooth animation)
	var band_power = json.get("band_power", {})
	for b in BAND_ORDER:
		if band_power.has(b):
			_target_bands[b] = float(band_power[b])

	# Update dominant band
	var dominant = json.get("dominant_band", "---")
	if dominant and _dominant_label:
		var dom_upper = dominant.to_upper()
		var dom_color = BAND_COLORS.get(dominant, Color(0.7, 0.7, 0.7))
		_dominant_label.add_theme_color_override("font_color", dom_color.lightened(0.2))
		_dominant_label.text = "DOMINANT: %s" % dom_upper

	# Update dwell time
	var dwell = json.get("dwell_time", 0.0)
	if _dwell_label:
		_dwell_label.text = "%.1fs" % dwell

	# Update transition indicator
	var in_transition = json.get("in_transition", false)
	if _transition_label:
		if in_transition:
			var from_band = json.get("transition_from", "")
			var to_band = json.get("transition_to", "")
			var progress = json.get("transition_progress", 0.0)
			_transition_label.text = "%s -> %s (%.0f%%)" % [from_band.to_upper(), to_band.to_upper(), progress * 100]
			_transition_label.add_theme_color_override("font_color", Color(0.9, 0.6, 0.3))
		else:
			_transition_label.text = ""

	# Update coherence (smooth animation)
	var global_coh = json.get("global_coherence", json.get("coherence", 0.5))
	_target_coherence = float(global_coh)
	if _coherence_label:
		_coherence_label.text = "%.2f" % global_coh

	# Update integration index
	var integration = json.get("integration_index", 0.0)
	if _integration_label:
		_integration_label.text = "INT: %.2f" % integration

	# Update PLV coupling values
	var plv_data = json.get("cross_band_plv", {})
	for pair in PLV_PAIRS:
		if pair in _plv_labels:
			var val = plv_data.get(pair, 0.0)
			_plv_labels[pair].text = "%s: %.2f" % [PLV_NAMES[pair], val]
			# Color intensity based on coupling strength
			var intensity = clamp(val, 0.0, 1.0)
			var plv_color = Color(0.5 + intensity * 0.4, 0.4 + intensity * 0.2, 0.6 + intensity * 0.3)
			_plv_labels[pair].add_theme_color_override("font_color", plv_color)

	# Update body_feels (emotion bridge output)
	var body_feels = json.get("body_feels", "")
	if _body_feels_label:
		if body_feels and not str(body_feels).is_empty():
			_body_feels_label.text = "[color=#9a8fc2]%s[/color]" % str(body_feels)
		else:
			_body_feels_label.text = "[color=#666]---[/color]"


func _toggle_entity() -> void:
	if _current_entity == "Kay":
		_current_entity = "Reed"
		_entity_toggle.text = "REED"
		_entity_toggle.add_theme_color_override("font_color", Color(0.4, 0.8, 0.7))
	else:
		_current_entity = "Kay"
		_entity_toggle.text = "KAY"
		_entity_toggle.add_theme_color_override("font_color", Color(0.8, 0.6, 0.9))

	# Re-poll immediately for instant feedback
	_poll()
