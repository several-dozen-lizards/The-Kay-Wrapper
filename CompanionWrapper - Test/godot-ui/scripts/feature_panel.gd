## FeaturePanel - Slide-out content area for sidebar features.
## Contains sub-panels for Sessions, Auto, Curate, Media, Settings etc.
## Appears between the chat panels and the sidebar icon strip.
class_name FeaturePanel
extends PanelContainer

const PANEL_WIDTH := 320

var _current_feature: String = ""
var _panels: Dictionary = {}  # feature_id -> Control

## Sub-panel references
var session_browser: SessionBrowser
var auto_panel: AutoPanel
var curate_panel: CuratePanel
var media_panel: MediaPanel
var canvas_panel: CanvasPanel
var stats_panel: StatsPanel
var exec_panel: ExecPanel
var settings_panel: SettingsPanel
var setup_panel: SetupPanel


func _ready() -> void:
	custom_minimum_size.x = PANEL_WIDTH
	size.x = PANEL_WIDTH
	visible = false
	_apply_style()
	_create_sub_panels()


func _apply_style() -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.06, 0.1, 0.97)
	style.border_color = Color(0.15, 0.15, 0.25)
	style.border_width_left = 1
	style.border_width_right = 1
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	style.content_margin_left = 8
	style.content_margin_right = 8
	add_theme_stylebox_override("panel", style)


func _create_sub_panels() -> void:
	session_browser = SessionBrowser.new()
	_register("sessions", session_browser)
	
	auto_panel = AutoPanel.new()
	_register("auto", auto_panel)
	
	curate_panel = CuratePanel.new()
	_register("curate", curate_panel)
	
	media_panel = MediaPanel.new()
	_register("media", media_panel)
	
	canvas_panel = CanvasPanel.new()
	_register("canvas", canvas_panel)
	
	# Gallery and Stats are placeholders for now
	var gallery_placeholder = _make_placeholder("🖼 Gallery", "Image gallery — coming soon")
	_register("gallery", gallery_placeholder)
	
	stats_panel = StatsPanel.new()
	_register("stats", stats_panel)
	
	exec_panel = ExecPanel.new()
	_register("exec", exec_panel)

	setup_panel = SetupPanel.new()
	_register("setup", setup_panel)

	settings_panel = SettingsPanel.new()
	_register("settings", settings_panel)


func _register(feature_id: String, panel: Control) -> void:
	panel.visible = false
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(panel)
	_panels[feature_id] = panel


func show_feature(feature_id: String) -> void:
	if _current_feature == feature_id:
		# Toggle off — clicking same feature again closes it
		hide_feature(feature_id)
		return
	# Hide previous
	if _current_feature and _panels.has(_current_feature):
		_panels[_current_feature].visible = false
	# Show new
	_current_feature = feature_id
	if _panels.has(feature_id):
		_panels[feature_id].visible = true
		visible = true
	else:
		visible = false


func hide_feature(feature_id: String) -> void:
	if _panels.has(feature_id):
		_panels[feature_id].visible = false
	if _current_feature == feature_id:
		_current_feature = ""
		visible = false


func hide_all() -> void:
	for panel in _panels.values():
		panel.visible = false
	_current_feature = ""
	visible = false


func _make_placeholder(title: String, desc: String) -> VBoxContainer:
	var vbox = VBoxContainer.new()
	var lbl = Label.new()
	lbl.text = title
	lbl.add_theme_font_size_override("font_size", 16)
	lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.8))
	vbox.add_child(lbl)
	var sep = HSeparator.new()
	vbox.add_child(sep)
	var desc_lbl = Label.new()
	desc_lbl.text = desc
	desc_lbl.add_theme_font_size_override("font_size", 12)
	desc_lbl.add_theme_color_override("font_color", Color(0.45, 0.45, 0.55))
	desc_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	vbox.add_child(desc_lbl)
	return vbox
