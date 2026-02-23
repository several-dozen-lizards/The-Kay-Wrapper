## ChatPanel - Chat display + input component.
## Can work standalone or embedded inside a DockablePanel.
class_name ChatPanel
extends PanelContainer

signal message_submitted(text: String)

## Speaker colors - BBCode color tags
const COLORS = {
	"Re": "#4EC9B0",
	"Kay": "#C586C0",
	"Reed": "#4FC1E9",
	"System": "#808080",
	"default": "#D4D4D4",
}

## Panel theme presets
const THEMES = {
	"nexus": {
		"bg": Color(0.06, 0.06, 0.09, 1.0),
		"header_bg": Color(0.08, 0.08, 0.14, 1.0),
		"header_text": Color(0.65, 0.65, 0.75),
		"border": Color(0.2, 0.2, 0.35, 1.0),
		"input_bg": Color(0.08, 0.08, 0.12, 1.0),
		"accent": Color(0.4, 0.4, 0.6),
	},
	"kay": {
		"bg": Color(0.08, 0.04, 0.1, 1.0),
		"header_bg": Color(0.12, 0.05, 0.15, 1.0),
		"header_text": Color(0.77, 0.52, 0.75),
		"border": Color(0.35, 0.12, 0.4, 1.0),
		"input_bg": Color(0.08, 0.04, 0.1, 1.0),
		"accent": Color(0.6, 0.2, 0.65),
	},
	"reed": {
		"bg": Color(0.03, 0.08, 0.08, 1.0),
		"header_bg": Color(0.04, 0.1, 0.1, 1.0),
		"header_text": Color(0.31, 0.76, 0.91),
		"border": Color(0.1, 0.3, 0.35, 1.0),
		"input_bg": Color(0.03, 0.08, 0.08, 1.0),
		"accent": Color(0.15, 0.55, 0.6),
	},
}

signal voice_toggled(enabled: bool)
signal image_requested()
signal affect_changed(level: float)
signal warmup_requested()
signal nexus_toggle_requested(connect: bool)

@onready var header_bar: PanelContainer = %HeaderBar
@onready var title_label: Label = %TitleLabel
@onready var subtitle_label: Label = %SubtitleLabel
@onready var status_indicator: Label = %StatusIndicator
@onready var chat_display: RichTextLabel = %ChatDisplay
@onready var input_field: LineEdit = %InputField
@onready var send_button: Button = %SendButton
@onready var scroll_container: ScrollContainer = %ScrollContainer

## Control bar
@onready var control_bar: HBoxContainer = %ControlBar
@onready var voice_toggle: Button = %VoiceToggle
@onready var image_button: Button = %ImageButton
@onready var affect_slider: HSlider = %AffectSlider
@onready var affect_label: Label = %AffectLabel
@onready var warmup_button: Button = %WarmupButton

var _panel_id: String = "nexus"
var _theme_data: Dictionary = {}
var _embedded: bool = false  # True when inside a DockablePanel
var _nexus_connected: bool = false  # Nexus connection state (nexus panel only)
var _bg_texture_rect: TextureRect = null
var _bg_overlay: ColorRect = null
var _accent_texture_rect: TextureRect = null  # Thin header accent strip (inside layout)

## Per-panel background images
const BG_IMAGES = {
	"nexus": "res://assets/bg_nexus.png",
	"kay": "res://assets/bg_kay.png",
	"reed": "res://assets/bg_reed.png",
}

## Per-panel accent images (additive blend — black = invisible)
const ACCENT_IMAGES = {
	"nexus": "res://assets/accent_nexus.png",
	"kay": "res://assets/accent_kay.png",
	"reed": "res://assets/accent_reed.png",
}


func _ready() -> void:
	if send_button:
		send_button.pressed.connect(_on_send_pressed)
	if input_field:
		input_field.text_submitted.connect(_on_text_submitted)
	if chat_display:
		chat_display.bbcode_enabled = true
		chat_display.scroll_following = false  # We manage scroll ourselves
	# Control bar
	if voice_toggle:
		voice_toggle.toggled.connect(_on_voice_toggled)
	if image_button:
		image_button.pressed.connect(_on_image_pressed)
	if affect_slider:
		affect_slider.value_changed.connect(_on_affect_changed)
	if warmup_button:
		warmup_button.pressed.connect(_on_warmup_pressed)


func _setup_background() -> void:
	# Check for user-selected background first, fall back to defaults
	var bg_path = SettingsPanel.get_panel_bg(_panel_id)
	if bg_path.is_empty():
		bg_path = BG_IMAGES.get(_panel_id, "")
	if bg_path.is_empty():
		_setup_accent()
		return
	
	var tex = _load_texture(bg_path)
	if not tex:
		push_warning("ChatPanel: Could not load background: " + bg_path)
		_setup_accent()
		return
	
	# TextureRect - the actual image, drawn behind everything
	_bg_texture_rect = TextureRect.new()
	_bg_texture_rect.texture = tex
	_bg_texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_bg_texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_bg_texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bg_texture_rect)
	move_child(_bg_texture_rect, 0)  # Behind Layout
	
	# Dark overlay for text readability
	_bg_overlay = ColorRect.new()
	_bg_overlay.color = Color(0.0, 0.0, 0.02, 0.55)  # Dark semi-transparent
	_bg_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bg_overlay)
	move_child(_bg_overlay, 1)  # Between texture and Layout
	
	# Accent on top of overlay
	_setup_accent()


func _setup_accent() -> void:
	var accent_path = SettingsPanel.get_panel_accent(_panel_id)
	if accent_path.is_empty():
		accent_path = ACCENT_IMAGES.get(_panel_id, "")
	if accent_path.is_empty():
		print("[ACCENT] %s: no accent path found" % _panel_id)
		return
	
	print("[ACCENT] %s: loading accent from %s" % [_panel_id, accent_path])
	var tex = _load_texture(accent_path)
	if not tex:
		push_warning("ChatPanel: Could not load accent: " + accent_path)
		return
	
	print("[ACCENT] %s: texture loaded OK, size=%s" % [_panel_id, tex.get_size()])
	
	# Thin decorative strip under the header bar (inside layout flow)
	_accent_texture_rect = TextureRect.new()
	_accent_texture_rect.texture = tex
	_accent_texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_accent_texture_rect.stretch_mode = TextureRect.STRETCH_SCALE
	_accent_texture_rect.custom_minimum_size = Vector2(0, 6)
	_accent_texture_rect.size_flags_horizontal = Control.SIZE_FILL
	_accent_texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	
	# Insert into Layout VBox right after HeaderBar
	var layout = get_node_or_null("Layout")
	print("[ACCENT] %s: layout=%s header_bar=%s" % [_panel_id, layout, header_bar])
	if layout and header_bar:
		layout.add_child(_accent_texture_rect)
		layout.move_child(_accent_texture_rect, header_bar.get_index() + 1)
		print("[ACCENT] %s: accent inserted at index %d" % [_panel_id, _accent_texture_rect.get_index()])
	else:
		print("[ACCENT] %s: FAILED - layout or header_bar is null!" % _panel_id)


func _load_texture(path: String) -> Texture2D:
	"""Load a texture from res://, user://, or absolute path."""
	if path.begins_with("res://"):
		return load(path) as Texture2D
	# User-selected or absolute path — load via Image
	var abs_path = path
	if path.begins_with("user://"):
		abs_path = ProjectSettings.globalize_path(path)
	var img = Image.new()
	var err = img.load(abs_path)
	if err == OK:
		return ImageTexture.create_from_image(img)
	push_warning("ChatPanel: Image.load failed for: " + abs_path)
	return null


func reload_background(_custom_path: String = "") -> void:
	"""Hot-reload the panel background + accent. Pass empty string to revert to default."""
	# Remove existing layers immediately (not deferred)
	if _accent_texture_rect:
		_accent_texture_rect.get_parent().remove_child(_accent_texture_rect)
		_accent_texture_rect.free()
		_accent_texture_rect = null
	if _bg_overlay:
		remove_child(_bg_overlay)
		_bg_overlay.free()
		_bg_overlay = null
	if _bg_texture_rect:
		remove_child(_bg_texture_rect)
		_bg_texture_rect.free()
		_bg_texture_rect = null
	# Rebuild everything
	_setup_background()
	# Re-apply transparent panel style
	_apply_theme()


func configure(panel_id: String, embedded: bool = false) -> void:
	_panel_id = panel_id
	_embedded = embedded
	_theme_data = THEMES.get(panel_id, THEMES["nexus"])
	_setup_background()
	_apply_theme()
	_configure_controls()


func _apply_theme() -> void:
	if _theme_data.is_empty():
		return
	
	if _embedded:
		# Transparent background - DockablePanel draws the chrome
		var transparent = StyleBoxFlat.new()
		transparent.bg_color = Color(0, 0, 0, 0)
		add_theme_stylebox_override("panel", transparent)
		# Hide header - DockablePanel has its own
		if header_bar:
			header_bar.visible = false
		# Accent strip stays visible even when embedded
	else:
		# Standalone mode
		var panel_style = StyleBoxFlat.new()
		if _bg_texture_rect:
			# Image background loaded - make panel transparent, border only
			panel_style.bg_color = Color(0, 0, 0, 0)
		else:
			panel_style.bg_color = _theme_data["bg"]
		panel_style.border_color = _theme_data["border"]
		panel_style.set_border_width_all(2)
		panel_style.set_corner_radius_all(4)
		panel_style.content_margin_left = 4
		panel_style.content_margin_right = 4
		panel_style.content_margin_top = 0
		panel_style.content_margin_bottom = 4
		add_theme_stylebox_override("panel", panel_style)
		
		# Style header bar
		if header_bar:
			header_bar.visible = true
			var header_style = StyleBoxFlat.new()
			header_style.bg_color = _theme_data["header_bg"]
			header_style.corner_radius_top_left = 3
			header_style.corner_radius_top_right = 3
			header_style.content_margin_left = 10
			header_style.content_margin_right = 10
			header_style.content_margin_top = 6
			header_style.content_margin_bottom = 6
			header_bar.add_theme_stylebox_override("panel", header_style)
		
		# Title / subtitle
		if title_label:
			title_label.text = _theme_data.get("title", _panel_id.to_upper())
			title_label.add_theme_color_override("font_color", _theme_data["header_text"])
			title_label.add_theme_font_size_override("font_size", 14)
		if subtitle_label:
			subtitle_label.text = _theme_data.get("subtitle", "")
			var sub_color = _theme_data["header_text"]
			sub_color.a = 0.5
			subtitle_label.add_theme_color_override("font_color", sub_color)
			subtitle_label.add_theme_font_size_override("font_size", 11)
	
	# These apply in BOTH modes
	if status_indicator:
		status_indicator.text = "..."
		status_indicator.add_theme_color_override("font_color", Color(0.4, 0.4, 0.4))
		status_indicator.add_theme_font_size_override("font_size", 11)
		# In embedded mode, move status to bottom of chat or keep it small
		if _embedded:
			status_indicator.visible = false  # DockablePanel shows status
	
	# Input field
	if input_field:
		var input_style = StyleBoxFlat.new()
		input_style.bg_color = _theme_data.get("input_bg", Color(0.08, 0.08, 0.12))
		input_style.border_color = _theme_data.get("border", Color(0.2, 0.2, 0.35))
		input_style.set_border_width_all(1)
		input_style.set_corner_radius_all(3)
		input_style.content_margin_left = 8
		input_style.content_margin_right = 8
		input_style.content_margin_top = 6
		input_style.content_margin_bottom = 6
		input_field.add_theme_stylebox_override("normal", input_style)
		input_field.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))
		input_field.add_theme_color_override("font_placeholder_color", Color(0.35, 0.35, 0.4))
	
	# Send button
	if send_button:
		var btn_style = StyleBoxFlat.new()
		btn_style.bg_color = _theme_data.get("accent", Color(0.4, 0.4, 0.6))
		btn_style.set_corner_radius_all(3)
		btn_style.content_margin_left = 12
		btn_style.content_margin_right = 12
		btn_style.content_margin_top = 6
		btn_style.content_margin_bottom = 6
		send_button.add_theme_stylebox_override("normal", btn_style)
		send_button.add_theme_color_override("font_color", Color(0.9, 0.9, 0.95))
	
	# Chat display
	if chat_display:
		chat_display.add_theme_color_override("default_color", Color(0.78, 0.78, 0.82))


## ========================================================================
## Smart scroll - auto-scroll only when user is near the bottom
## ========================================================================

const SCROLL_THRESHOLD := 60  # pixels from bottom to count as "at bottom"

func _is_near_bottom() -> bool:
	if not scroll_container:
		return true
	var max_scroll = scroll_container.get_v_scroll_bar().max_value
	var visible_height = scroll_container.size.y
	var current_scroll = scroll_container.scroll_vertical
	return current_scroll >= (max_scroll - visible_height - SCROLL_THRESHOLD)


func _scroll_to_bottom() -> void:
	if not scroll_container:
		return
	# Deferred so layout updates first
	await get_tree().process_frame
	scroll_container.scroll_vertical = int(scroll_container.get_v_scroll_bar().max_value)


func set_status(text: String, color: Color = Color(0.4, 0.4, 0.4)) -> void:
	if status_indicator and status_indicator.visible:
		status_indicator.text = text
		status_indicator.add_theme_color_override("font_color", color)


func add_message(sender: String, content: String, msg_type: String = "chat",
		timestamp: String = "") -> void:
	var was_near_bottom = _is_near_bottom()
	var ts = _format_timestamp(timestamp)
	var color = COLORS.get(sender, COLORS["default"])
	
	match msg_type:
		"system":
			chat_display.append_text(
				"[color=#555555]--- %s ---[/color]\n" % content
			)
		"emote":
			chat_display.append_text(
				"[color=#666666]%s[/color] [color=%s]* %s %s[/color]\n" % [
					ts, color, sender, content
				]
			)
		"state_update":
			chat_display.append_text(
				"[color=#444444]  %s is now %s[/color]\n" % [sender, content]
			)
		"whisper":
			chat_display.append_text(
				"[color=#666666]%s[/color] [color=#6A9FB5][whisper] %s: %s[/color]\n" % [
					ts, sender, content
				]
			)
		_:
			chat_display.append_text(
				"[color=#666666]%s[/color] [b][color=%s]%s[/color][/b]: %s\n" % [
					ts, color, sender, content
				]
			)
	
	# Smart scroll: only auto-scroll if user was already at the bottom
	if was_near_bottom:
		_scroll_to_bottom()


func add_system_message(text: String) -> void:
	add_message("System", text, "system")


func clear_chat() -> void:
	if chat_display:
		chat_display.clear()


func focus_input() -> void:
	if input_field:
		input_field.grab_focus()


func _format_timestamp(iso_ts: String) -> String:
	if iso_ts.is_empty():
		var time = Time.get_time_dict_from_system()
		return "%02d:%02d" % [time["hour"], time["minute"]]
	if iso_ts.length() >= 16:
		return iso_ts.substr(11, 5)
	return "??:??"


func _on_send_pressed() -> void:
	_submit_input()


func _on_text_submitted(_text: String) -> void:
	_submit_input()


## ========================================================================
## Control bar
## ========================================================================

func _configure_controls() -> void:
	if not control_bar:
		return
	
	# Style the control bar
	var bar_style = StyleBoxFlat.new()
	bar_style.bg_color = _theme_data.get("input_bg", Color(0.08, 0.08, 0.12))
	bar_style.content_margin_left = 4
	bar_style.content_margin_right = 4
	bar_style.content_margin_top = 2
	bar_style.content_margin_bottom = 2
	
	# Nexus panel: repurpose warmup button as Connect/Disconnect toggle
	if _panel_id == "nexus":
		if affect_slider:
			affect_slider.visible = false
		if affect_label:
			affect_label.visible = false
		if warmup_button:
			# Repurpose as nexus connect toggle
			warmup_button.visible = true
			warmup_button.text = "▶ Connect"
			warmup_button.pressed.disconnect(_on_warmup_pressed)
			warmup_button.pressed.connect(_on_nexus_toggle_pressed)
			var btn_style = StyleBoxFlat.new()
			btn_style.bg_color = Color(0.2, 0.4, 0.3)
			btn_style.set_corner_radius_all(3)
			btn_style.content_margin_left = 10
			btn_style.content_margin_right = 10
			btn_style.content_margin_top = 3
			btn_style.content_margin_bottom = 3
			warmup_button.add_theme_stylebox_override("normal", btn_style)
			warmup_button.add_theme_font_size_override("font_size", 11)
	else:
		# Entity panels get all controls
		if warmup_button:
			warmup_button.visible = true
			var btn_style = StyleBoxFlat.new()
			btn_style.bg_color = _theme_data.get("accent", Color(0.4, 0.4, 0.6))
			btn_style.set_corner_radius_all(3)
			btn_style.content_margin_left = 8
			btn_style.content_margin_right = 8
			btn_style.content_margin_top = 3
			btn_style.content_margin_bottom = 3
			warmup_button.add_theme_stylebox_override("normal", btn_style)
			warmup_button.add_theme_font_size_override("font_size", 11)
	
	# Voice toggle styling
	if voice_toggle:
		voice_toggle.add_theme_font_size_override("font_size", 14)
		voice_toggle.custom_minimum_size = Vector2(32, 0)
	
	# Image button styling
	if image_button:
		image_button.add_theme_font_size_override("font_size", 14)
		image_button.custom_minimum_size = Vector2(32, 0)
	
	# Affect label styling
	if affect_label:
		affect_label.add_theme_font_size_override("font_size", 10)
		affect_label.add_theme_color_override("font_color", _theme_data.get("header_text", Color(0.5, 0.5, 0.5)))
		affect_label.custom_minimum_size = Vector2(24, 0)


func _on_voice_toggled(pressed: bool) -> void:
	voice_toggled.emit(pressed)
	if pressed:
		add_system_message("Voice input enabled (placeholder)")
	else:
		add_system_message("Voice input disabled")


func _on_image_pressed() -> void:
	image_requested.emit()
	add_system_message("Image upload (placeholder - not yet implemented)")


func _on_affect_changed(value: float) -> void:
	if affect_label:
		affect_label.text = "%.1f" % value
	affect_changed.emit(value)


func _on_warmup_pressed() -> void:
	warmup_requested.emit()
	add_system_message("Sending warmup signal...")


func _on_nexus_toggle_pressed() -> void:
	_nexus_connected = !_nexus_connected
	nexus_toggle_requested.emit(_nexus_connected)
	if _nexus_connected:
		add_system_message("Connecting to Nexus...")
	else:
		add_system_message("Disconnecting from Nexus...")


func set_nexus_state(connected: bool) -> void:
	_nexus_connected = connected
	if warmup_button and _panel_id == "nexus":
		if connected:
			warmup_button.text = "⏹ Disconnect"
			var btn_style = StyleBoxFlat.new()
			btn_style.bg_color = Color(0.5, 0.2, 0.2)
			btn_style.set_corner_radius_all(3)
			btn_style.content_margin_left = 10
			btn_style.content_margin_right = 10
			btn_style.content_margin_top = 3
			btn_style.content_margin_bottom = 3
			warmup_button.add_theme_stylebox_override("normal", btn_style)
		else:
			warmup_button.text = "▶ Connect"
			var btn_style = StyleBoxFlat.new()
			btn_style.bg_color = Color(0.2, 0.4, 0.3)
			btn_style.set_corner_radius_all(3)
			btn_style.content_margin_left = 10
			btn_style.content_margin_right = 10
			btn_style.content_margin_top = 3
			btn_style.content_margin_bottom = 3
			warmup_button.add_theme_stylebox_override("normal", btn_style)


func get_affect_level() -> float:
	if affect_slider:
		return affect_slider.value
	return 3.5


func _submit_input() -> void:
	if not input_field:
		return
	var text = input_field.text.strip_edges()
	if text.is_empty():
		return
	input_field.text = ""
	message_submitted.emit(text)
	input_field.grab_focus()
