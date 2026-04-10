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
signal image_upload_requested(image_b64: String, filename: String, message: String)
signal affect_changed(level: float)
signal warmup_requested()
signal nexus_toggle_requested(connect: bool)
signal document_dropped(filepath: String, filename: String)

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
var _voice_active: bool = false
var _last_input_was_voice: bool = false  # Voice input mode active

## Message trimming — prevents OOM crash during long overnight sessions
const MAX_MESSAGES := 300   # Trim when this many messages accumulated
const TRIM_TO := 150        # Keep this many after trim
var _message_count: int = 0
var _face_panel: Control = null  # Embedded FacePanel
var _face_sidebar: VBoxContainer = null  # Sidebar container
var _face_entity: String = ""  # "kay" or "reed"
var _face_stats_label: Label = null  # Stats display under face
var _chat_area: HBoxContainer = null  # Wraps face sidebar + scroll container
var _bg_texture_rect: TextureRect = null
var _bg_overlay: ColorRect = null
var _accent_texture_rect: TextureRect = null  # Thin header accent strip (inside layout)

## Image upload state
var _image_dialog: FileDialog = null
var _pending_image_b64: String = ""
var _pending_image_filename: String = ""

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
		affect_slider.visible = false  # Dead code — affect system gutted
	if affect_label:
		affect_label.visible = false
	if warmup_button:
		warmup_button.pressed.connect(_on_warmup_pressed)
	# Drag-and-drop file support
	get_viewport().files_dropped.connect(_on_files_dropped)


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
	
	# Trim old messages to prevent memory growth during long sessions
	_message_count += 1
	if _message_count > MAX_MESSAGES:
		_trim_chat_history()


func add_system_message(text: String) -> void:
	add_message("System", text, "system")


## ========================================================================
## Image display in chat
## ========================================================================

func add_image_message(sender: String, image_path: String, caption: String = "") -> void:
	"""Display an image inline in the chat with optional caption."""
	var was_near_bottom = _is_near_bottom()

	# Load the image texture
	var tex: Texture2D = _load_texture(image_path)
	if not tex:
		add_system_message("Could not load image: %s" % image_path)
		return

	# Scale image to fit chat width (max ~400px wide)
	var max_width: float = 400.0
	var scale_factor: float = 1.0
	if tex.get_width() > max_width:
		scale_factor = max_width / tex.get_width()

	var display_width: int = int(tex.get_width() * scale_factor)
	var display_height: int = int(tex.get_height() * scale_factor)

	# Get sender color
	var color = COLORS.get(sender, COLORS["default"])

	# Build message with BBCode
	var ts = _format_timestamp("")
	chat_display.append_text("[color=#666666]%s[/color] [b][color=%s]%s[/color][/b]: " % [ts, color, sender])

	# Add caption if provided
	if not caption.is_empty():
		chat_display.append_text("%s\n" % caption)
	else:
		chat_display.append_text("\n")

	# Add the image using RichTextLabel's add_image
	chat_display.add_image(tex, display_width, display_height)
	chat_display.append_text("\n\n")

	# Smart scroll
	if was_near_bottom:
		_scroll_to_bottom()

	_message_count += 1
	if _message_count > MAX_MESSAGES:
		_trim_chat_history()


func add_image_from_base64(sender: String, b64_data: String, caption: String = "") -> void:
	"""Display a base64-encoded image inline in the chat."""
	var was_near_bottom = _is_near_bottom()

	var raw = Marshalls.base64_to_raw(b64_data)
	var img = Image.new()

	# Try loading as PNG first, then JPEG, then WebP
	var err = img.load_png_from_buffer(raw)
	if err != OK:
		err = img.load_jpg_from_buffer(raw)
	if err != OK:
		err = img.load_webp_from_buffer(raw)
	if err != OK:
		add_system_message("Could not decode image")
		return

	var tex = ImageTexture.create_from_image(img)

	# Scale to fit chat width
	var max_width: float = 400.0
	var scale_factor: float = 1.0
	if tex.get_width() > max_width:
		scale_factor = max_width / tex.get_width()

	var display_width: int = int(tex.get_width() * scale_factor)
	var display_height: int = int(tex.get_height() * scale_factor)

	# Get sender color
	var color = COLORS.get(sender, COLORS["default"])

	# Build message
	var ts = _format_timestamp("")
	chat_display.append_text("[color=#666666]%s[/color] [b][color=%s]%s[/color][/b]: " % [ts, color, sender])

	if not caption.is_empty():
		chat_display.append_text("%s\n" % caption)
	else:
		chat_display.append_text("\n")

	chat_display.add_image(tex, display_width, display_height)
	chat_display.append_text("\n\n")

	# Smart scroll
	if was_near_bottom:
		_scroll_to_bottom()

	_message_count += 1
	if _message_count > MAX_MESSAGES:
		_trim_chat_history()


func clear_chat() -> void:
	if chat_display:
		chat_display.clear()
	_message_count = 0


func _trim_chat_history() -> void:
	## Remove oldest messages from RichTextLabel to prevent memory growth.
	## Keeps TRIM_TO most recent lines.
	if not chat_display:
		return
	var text = chat_display.get_parsed_text()
	var lines = text.split("\n")
	if lines.size() <= TRIM_TO:
		_message_count = lines.size()
		return
	chat_display.clear()
	var keep = lines.slice(-TRIM_TO)
	# Add a separator so user knows history was trimmed
	chat_display.append_text("[color=#333333]--- earlier messages trimmed ---[/color]\n")
	for line in keep:
		if not line.is_empty():
			chat_display.append_text(line + "\n")
	_message_count = TRIM_TO


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
	_voice_active = pressed
	voice_toggled.emit(pressed)
	if pressed:
		add_system_message("Voice input active - speak now")
		if voice_toggle:
			voice_toggle.text = "rec"
			# Add recording indicator style
			var btn_style = StyleBoxFlat.new()
			btn_style.bg_color = Color(0.6, 0.2, 0.2)
			btn_style.set_corner_radius_all(3)
			btn_style.content_margin_left = 6
			btn_style.content_margin_right = 6
			btn_style.content_margin_top = 3
			btn_style.content_margin_bottom = 3
			voice_toggle.add_theme_stylebox_override("pressed", btn_style)
	else:
		add_system_message("Voice input stopped")
		if voice_toggle:
			voice_toggle.text = "mic"


func is_voice_active() -> bool:
	return _voice_active


func set_voice_active(active: bool) -> void:
	_voice_active = active
	if voice_toggle:
		voice_toggle.button_pressed = active


func mark_voice_input() -> void:
	_last_input_was_voice = true


func was_last_input_voice() -> bool:
	return _last_input_was_voice


func clear_voice_input_flag() -> void:
	_last_input_was_voice = false


func show_speaking_indicator(speaking: bool) -> void:
	if speaking:
		add_system_message("Speaking...")


func _on_image_pressed() -> void:
	image_requested.emit()
	# Open file dialog for image selection
	if not _image_dialog:
		_image_dialog = FileDialog.new()
		_image_dialog.title = "Select Image"
		_image_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
		_image_dialog.access = FileDialog.ACCESS_FILESYSTEM
		_image_dialog.filters = PackedStringArray(["*.png ; PNG", "*.jpg ; JPEG", "*.jpeg ; JPEG", "*.gif ; GIF", "*.webp ; WebP"])
		_image_dialog.file_selected.connect(_on_image_file_selected)
		_image_dialog.canceled.connect(_on_image_dialog_canceled)
		add_child(_image_dialog)
	_image_dialog.popup_centered(Vector2(600, 400))


func _on_image_file_selected(path: String) -> void:
	# Read file and encode to base64
	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		add_system_message("Error: Could not read image file")
		return

	var data = file.get_buffer(file.get_length())
	file.close()

	# Check file size (max 5MB)
	if data.size() > 5 * 1024 * 1024:
		add_system_message("Error: Image too large (max 5MB)")
		return

	# Encode to base64
	_pending_image_b64 = Marshalls.raw_to_base64(data)
	_pending_image_filename = path.get_file()

	# Show image preview in chat (not just text)
	add_image_message("You", path, "📷 %s (%d KB) — type message and Send, or just Send" % [
		_pending_image_filename,
		data.size() / 1024
	])

	# Focus input for optional message
	focus_input()


func _on_image_dialog_canceled() -> void:
	pass  # User canceled, do nothing


func has_pending_image() -> bool:
	return not _pending_image_b64.is_empty()


func get_pending_image() -> Dictionary:
	if _pending_image_b64.is_empty():
		return {}
	return {
		"image_b64": _pending_image_b64,
		"filename": _pending_image_filename
	}


func clear_pending_image() -> void:
	_pending_image_b64 = ""
	_pending_image_filename = ""


## ========================================================================
## Drag-and-drop file support
## ========================================================================

func _on_files_dropped(files: PackedStringArray) -> void:
	"""Handle files dragged from OS into the chat panel."""
	# Only handle if mouse is over this chat panel
	var mouse_pos = get_viewport().get_mouse_position()
	if not get_global_rect().has_point(mouse_pos):
		return

	for file_path in files:
		var ext = file_path.get_extension().to_lower()

		# Image files → upload as image
		if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
			_handle_dropped_image(file_path)

		# Document files → import as document
		elif ext in ["txt", "md", "json", "pdf", "docx"]:
			_handle_dropped_document(file_path)

		else:
			add_system_message("Unsupported file type: .%s" % ext)


func _handle_dropped_image(path: String) -> void:
	"""Process a dropped image file."""
	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		add_system_message("Error: Could not read %s" % path.get_file())
		return

	var data = file.get_buffer(file.get_length())
	file.close()

	if data.size() > 5 * 1024 * 1024:
		add_system_message("Error: Image too large (max 5MB)")
		return

	_pending_image_b64 = Marshalls.raw_to_base64(data)
	_pending_image_filename = path.get_file()

	# Show preview
	add_image_message("You", path, "📷 %s (%d KB)" % [_pending_image_filename, data.size() / 1024])
	add_system_message("Image ready — press Send (or type a message first)")
	focus_input()


func _handle_dropped_document(path: String) -> void:
	"""Process a dropped document file."""
	add_system_message("📄 Importing: %s" % path.get_file())
	# Emit document import signal (main.gd handles the backend call)
	document_dropped.emit(path, path.get_file())


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

	# Check for pending image upload
	if has_pending_image():
		var img_data = get_pending_image()
		input_field.text = ""
		# Emit image upload signal (message can be empty)
		image_upload_requested.emit(img_data["image_b64"], img_data["filename"], text)
		clear_pending_image()
		add_message("Re", "[Image: %s]%s" % [img_data["filename"], " " + text if not text.is_empty() else ""], "chat")
		input_field.grab_focus()
		return

	if text.is_empty():
		return
	input_field.text = ""
	message_submitted.emit(text)
	input_field.grab_focus()



## ========================================================================
## Face sidebar (embedded face panel + stats)
## ========================================================================

func embed_face(face: Control, entity: String) -> void:
	"""Embed a FacePanel in a sidebar next to the chat display."""
	if not scroll_container or not scroll_container.get_parent():
		push_warning("Cannot embed face — scroll_container not ready")
		return
	
	_face_panel = face
	_face_entity = entity
	
	var layout = scroll_container.get_parent()  # The Layout VBoxContainer
	var scroll_idx = scroll_container.get_index()
	
	# Create the chat area (HBox: sidebar + chat)
	_chat_area = HBoxContainer.new()
	_chat_area.name = "ChatArea"
	_chat_area.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_chat_area.size_flags_vertical = Control.SIZE_EXPAND_FILL
	
	# Remove scroll_container from Layout, insert chat_area at same position
	layout.remove_child(scroll_container)
	layout.add_child(_chat_area)
	layout.move_child(_chat_area, scroll_idx)
	
	# Create sidebar
	_face_sidebar = VBoxContainer.new()
	_face_sidebar.name = "FaceSidebar"
	_face_sidebar.custom_minimum_size = Vector2(140, 0)
	_face_sidebar.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_face_sidebar.size_flags_vertical = Control.SIZE_EXPAND_FILL
	
	# Style the sidebar background
	var sidebar_bg = StyleBoxFlat.new()
	sidebar_bg.bg_color = Color(0.0, 0.0, 0.0, 0.3)
	sidebar_bg.set_corner_radius_all(4)
	var sidebar_panel = PanelContainer.new()
	sidebar_panel.add_theme_stylebox_override("panel", sidebar_bg)
	sidebar_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	
	var sidebar_inner = VBoxContainer.new()
	sidebar_inner.name = "SidebarInner"
	sidebar_panel.add_child(sidebar_inner)
	
	# Face panel (compact size)
	face.custom_minimum_size = Vector2(130, 150)
	face.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sidebar_inner.add_child(face)
	
	# Stats label
	_face_stats_label = Label.new()
	_face_stats_label.name = "FaceStats"
	_face_stats_label.text = "..."
	_face_stats_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_face_stats_label.add_theme_font_size_override("font_size", 10)
	_face_stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7, 0.8))
	_face_stats_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	sidebar_inner.add_child(_face_stats_label)
	
	_face_sidebar.add_child(sidebar_panel)
	
	# Add sidebar and scroll_container to chat_area
	_chat_area.add_child(_face_sidebar)
	_chat_area.add_child(scroll_container)
	scroll_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL


func toggle_face_sidebar() -> void:
	"""Toggle face sidebar visibility."""
	if _face_sidebar:
		_face_sidebar.visible = not _face_sidebar.visible


func update_face_stats(stats: Dictionary) -> void:
	"""Update the stats display under the face. Called from main.gd."""
	if not _face_stats_label:
		return
	var lines: PackedStringArray = []
	if stats.has("band"):
		lines.append("band: %s" % stats["band"])
	if stats.has("coherence"):
		lines.append("coh: %.0f%%" % (stats["coherence"] * 100))
	if stats.has("felt"):
		lines.append("felt: %s" % stats["felt"])
	if stats.has("tension"):
		lines.append("t: %.2f" % stats["tension"])
	if stats.has("emotions"):
		lines.append(stats["emotions"])
	_face_stats_label.text = "\n".join(lines) if lines.size() > 0 else "..."
