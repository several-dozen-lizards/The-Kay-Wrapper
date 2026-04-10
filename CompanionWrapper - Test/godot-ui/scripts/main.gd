## Main - Application entry point for Companion Wrapper UI.
## Single-entity architecture: one chat panel, one private room connection.
##
## ARCHITECTURE:
##   Companion Room (ws://localhost:8780) — private 1:1 with companion
extends Control

const ChatPanelScene = preload("res://scenes/ChatPanel.tscn")

## Private room connection
var _private: PrivateConnection

@onready var panel_mgr: PanelManager = %PanelManager

## Chat panel reference
var _chat: ChatPanel

## Sidebar + feature panels
var _sidebar: Sidebar
var _feature_panel: FeaturePanel
var _easel_panel: EaselPanel
var _gallery_panel: GalleryPanel
var _room_panel: RoomPanel
var _system_dashboard: SystemDashboard
var _voice_mgr: VoiceManager
var _face_panel: FacePanel

## User info
var _user_name: String = "Re"
var _room_url: String = "ws://localhost:8780"
var _http_base: String = "http://localhost:8785"
var _reconnect_notice_shown: bool = false

## Curation response routing
var _curate_pending: bool = false


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		print("[COMPANION UI] Window close requested — accepting quit")
		get_tree().quit()


func _load_connection_config() -> void:
	## Load connection settings from connection.json or command line
	var config_path := "res://connection.json"
	var port: int = 8780
	var http_port: int = 8785

	# Check command line arguments first (--port=XXXX or --companion-port=XXXX)
	var args := OS.get_cmdline_args()
	for arg in args:
		if arg.begins_with("--port="):
			port = int(arg.split("=")[1])
		elif arg.begins_with("--companion-port="):
			port = int(arg.split("=")[1])
		elif arg.begins_with("--http-port="):
			http_port = int(arg.split("=")[1])

	# Try to load from connection.json
	if FileAccess.file_exists(config_path):
		var file := FileAccess.open(config_path, FileAccess.READ)
		if file:
			var json := JSON.new()
			var err := json.parse(file.get_as_text())
			file.close()
			if err == OK and json.data is Dictionary:
				var config: Dictionary = json.data
				# Only use config values if not overridden by command line
				if port == 8780:  # Default, not set via command line
					port = int(config.get("default_port", 8780))
				if http_port == 8785:  # Default, not set via command line
					http_port = int(config.get("default_http_port", 8785))
				print("[CONFIG] Loaded from connection.json: port=%d, http_port=%d" % [port, http_port])

	# Set the URLs
	_room_url = "ws://localhost:%d" % port
	_http_base = "http://localhost:%d" % http_port
	print("[CONFIG] Room URL: %s" % _room_url)
	print("[CONFIG] HTTP base: %s" % _http_base)


func _ready() -> void:
	get_tree().root.min_size = Vector2(800, 500)

	# Load connection configuration before setting up connections
	_load_connection_config()

	await get_tree().process_frame
	_create_panels()
	_setup_sidebar()
	_setup_private_room()
	_setup_voice()
	await get_tree().process_frame
	panel_mgr.arrange_default()

	# Auto-connect to companion room
	_private.connect_to_room()


## ========================================================================
## Panel creation
## ========================================================================

func _create_panels() -> void:
	var screen = get_viewport_rect().size

	# --- Main chat panel (fills most of the screen) ---
	_chat = ChatPanelScene.instantiate() as ChatPanel
	panel_mgr.create_panel(
		"companion", "COMPANION", "your companion",
		Vector2(10, 10),
		Vector2(screen.x * 0.75, screen.y - 50),
		_chat
	)
	_chat.configure("companion", true)
	_chat.message_submitted.connect(_on_message)
	_chat.warmup_requested.connect(_on_warmup)
	_chat.affect_changed.connect(_on_affect)
	_chat.image_upload_requested.connect(_on_image_upload)

	# Welcome messages
	_chat.add_system_message("Companion UI initialized")
	_chat.add_system_message("Drag panels to rearrange | Right sidebar: Sessions, Auto, Curate, Media, Settings")

	# --- Room panel (spatial view - starts minimized) ---
	_room_panel = RoomPanel.new()
	panel_mgr.create_panel(
		"room", "ROOM", "spatial view",
		Vector2(screen.x * 0.55 + 20, 10),
		Vector2(screen.x * 0.4, screen.y * 0.3),
		_room_panel
	)
	var room_dock = panel_mgr.get_panel("room")
	if room_dock:
		room_dock._minimize_panel()

	# --- System dashboard (starts minimized) ---
	_system_dashboard = SystemDashboard.new()
	panel_mgr.create_panel(
		"system", "SYSTEM", "live dashboard",
		Vector2(10, screen.y * 0.5),
		Vector2(screen.x * 0.55, screen.y * 0.48),
		_system_dashboard
	)
	var system_dock = panel_mgr.get_panel("system")
	if system_dock:
		system_dock._minimize_panel()

	# --- Face panel (embedded in chat sidebar) ---
	_face_panel = FacePanel.new()
	_face_panel.set_entity("companion")
	_chat.embed_face(_face_panel, "companion")


## ========================================================================
## Sidebar + Feature Panels
## ========================================================================

func _setup_sidebar() -> void:
	# Sidebar icon strip — right edge
	_sidebar = Sidebar.new()
	_sidebar.name = "Sidebar"
	add_child(_sidebar)

	# Feature panel — slides out left of sidebar
	_feature_panel = FeaturePanel.new()
	_feature_panel.name = "FeaturePanel"
	add_child(_feature_panel)

	# Connect sidebar toggle to feature panel
	_sidebar.feature_toggled.connect(_on_sidebar_feature_toggled)
	_sidebar.dock_changed.connect(_on_sidebar_dock_changed)

	# Connect session browser signals
	_feature_panel.session_browser.session_load_requested.connect(_on_session_load)
	_feature_panel.session_browser.session_open_requested.connect(_on_session_open)

	# Connect auto panel signals
	_feature_panel.auto_panel.auto_session_requested.connect(_on_auto_session)

	# Connect curate panel signals
	_feature_panel.curate_panel.curate_action.connect(_on_curate_action)

	# Connect media panel signals
	_feature_panel.media_panel.file_import_requested.connect(_on_file_import)

	# Connect settings signals
	_feature_panel.settings_panel.setting_changed.connect(_on_setting_changed)

	# Create the easel as a managed panel (starts minimized)
	_easel_panel = EaselPanel.new()
	var screen = get_viewport_rect().size
	panel_mgr.create_panel(
		"easel", "EASEL", "canvas",
		Vector2(screen.x * 0.25, screen.y * 0.1),
		Vector2(480, screen.y * 0.8),
		_easel_panel
	)
	_easel_panel.clear_requested.connect(_on_canvas_clear_requested)
	var easel_dock = panel_mgr.get_panel("easel")
	if easel_dock:
		easel_dock._minimize_panel()

	# Create the gallery panel (starts minimized)
	_gallery_panel = GalleryPanel.new()
	panel_mgr.create_panel(
		"easel_gallery", "GALLERY", "all paintings",
		Vector2(screen.x * 0.3, screen.y * 0.05),
		Vector2(520, screen.y * 0.85),
		_gallery_panel
	)
	var gallery_dock = panel_mgr.get_panel("easel_gallery")
	if gallery_dock:
		gallery_dock._minimize_panel()

	# Position on resize
	get_viewport().size_changed.connect(_position_sidebar)
	_position_sidebar()


func _position_sidebar() -> void:
	var screen = get_viewport_rect().size
	var thick := _sidebar.get_thickness()  # 44
	var feat_w := 320
	var feat_h := 320  # For horizontal docks
	var dock = _sidebar.get_dock()
	var feat_open = _feature_panel.visible

	match dock:
		Sidebar.Dock.RIGHT:
			_sidebar.position = Vector2(screen.x - thick, 0)
			_sidebar.size = Vector2(thick, screen.y)
			_feature_panel.position = Vector2(screen.x - thick - feat_w, 0)
			_feature_panel.size = Vector2(feat_w, screen.y)
			panel_mgr.position = Vector2.ZERO
			panel_mgr.size = Vector2(
				screen.x - thick - (feat_w if feat_open else 0), screen.y
			)

		Sidebar.Dock.LEFT:
			_sidebar.position = Vector2.ZERO
			_sidebar.size = Vector2(thick, screen.y)
			_feature_panel.position = Vector2(thick, 0)
			_feature_panel.size = Vector2(feat_w, screen.y)
			var offset_x = thick + (feat_w if feat_open else 0)
			panel_mgr.position = Vector2(offset_x, 0)
			panel_mgr.size = Vector2(screen.x - offset_x, screen.y)

		Sidebar.Dock.TOP:
			_sidebar.position = Vector2.ZERO
			_sidebar.size = Vector2(screen.x, thick)
			_feature_panel.position = Vector2(0, thick)
			_feature_panel.size = Vector2(screen.x, feat_h)
			var offset_y = thick + (feat_h if feat_open else 0)
			panel_mgr.position = Vector2(0, offset_y)
			panel_mgr.size = Vector2(screen.x, screen.y - offset_y)

		Sidebar.Dock.BOTTOM:
			_sidebar.position = Vector2(0, screen.y - thick)
			_sidebar.size = Vector2(screen.x, thick)
			_feature_panel.position = Vector2(0, screen.y - thick - feat_h)
			_feature_panel.size = Vector2(screen.x, feat_h)
			panel_mgr.position = Vector2.ZERO
			panel_mgr.size = Vector2(
				screen.x, screen.y - thick - (feat_h if feat_open else 0)
			)


func _on_sidebar_feature_toggled(feature_id: String, show: bool) -> void:
	# Canvas gets its own managed panel
	if feature_id == "canvas":
		var easel_dock = panel_mgr.get_panel("easel")
		if not easel_dock:
			return
		if show:
			easel_dock.restore()
			_easel_panel.fetch_latest_canvas()
		else:
			easel_dock._minimize_panel()
		return
	# Gallery gets its own managed panel
	if feature_id == "gallery":
		var gallery_dock = panel_mgr.get_panel("easel_gallery")
		if not gallery_dock:
			return
		if show:
			gallery_dock.restore()
			_gallery_panel.fetch_gallery()
		else:
			gallery_dock._minimize_panel()
		return
	# Face panel - toggle embedded sidebar
	if feature_id == "face":
		if _chat:
			_chat.toggle_face_sidebar()
		return
	if show:
		_feature_panel.show_feature(feature_id)
	else:
		_feature_panel.hide_feature(feature_id)
	# Adjust panel manager layout when feature panel opens/closes
	_position_sidebar()


func _on_sidebar_dock_changed(_new_dock: int) -> void:
	_position_sidebar()


func _on_session_load(filename: String, messages: Array) -> void:
	# Display loaded session in chat as history
	_chat.clear_chat()
	_chat.add_system_message("=== Loaded session: %s ===" % filename)

	for msg in messages:
		if msg is Dictionary:
			var sender: String = msg.get("sender", "?")
			var content: String = msg.get("content", "")
			var msg_type: String = msg.get("type", "chat")
			if msg_type == "system":
				_chat.add_system_message(content)
			else:
				_chat.add_message(sender, content, msg_type)

	_chat.add_system_message("=== End of loaded session (%d messages) ===" % messages.size())


func _on_session_open(filename: String, messages: Array) -> void:
	# Open session in a separate viewer window (non-destructive)
	var viewer = SessionViewer.new()
	add_child(viewer)
	viewer.load_session(filename, messages)
	viewer.popup_centered()


func _on_auto_session(_entity: String, action: String) -> void:
	if action == "start":
		_chat.add_system_message("Starting autonomous session...")


func _on_canvas_clear_requested(_entity: String) -> void:
	# Send clear command to server via private room
	if _private.is_room_connected():
		_private.send_command("clear_canvas")


func _on_curate_action(_entity: String, action: String, data: Dictionary) -> void:
	# Route curation commands to wrapper
	_curate_pending = true
	_feature_panel.curate_panel.set_status("Processing %s..." % action)
	match action:
		"search":
			_private.send_chat("/memory search %s" % data.get("query", ""))
		"refresh":
			_private.send_chat("/memory list")
		"consolidate":
			_private.send_chat("/memory consolidate")
		"prune":
			_private.send_chat("/memory prune")
		"contradictions":
			_private.send_chat("/memory contradictions")
		"pending":
			_private.send_chat("/memory pending")
		"approve_all":
			_private.send_chat("/memory approve all")
		"curator_status":
			_private.send_chat("/memory curator")
		"auto_resolve":
			_private.send_chat("/memory auto_resolve")
		"curate":
			_private.send_chat("/memory curate")
		"sweep":
			_private.send_chat("/memory sweep")


func _on_file_import(path: String, _entity: String) -> void:
	# Read file and upload via HTTP POST
	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		_chat.add_system_message("Error: Could not read file: %s" % path)
		return

	var data = file.get_buffer(file.get_length())
	file.close()

	# Check file size (10MB limit for documents)
	if data.size() > 10 * 1024 * 1024:
		_chat.add_system_message("Error: File too large (max 10MB)")
		return

	var content_b64 = Marshalls.raw_to_base64(data)
	var filename = path.get_file()

	_chat.add_system_message("Uploading document: %s (%d KB)..." % [filename, data.size() / 1024])

	# Create HTTP request
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_document_upload_complete.bind(http, filename))

	var url = _room_url.replace("ws://", "http://") + "/chat/document"
	var headers = ["Content-Type: application/json"]
	var body = JSON.stringify({
		"content_b64": content_b64,
		"filename": filename
	})

	var error = http.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		_chat.add_system_message("Error: Failed to start upload request")
		http.queue_free()


func _on_document_upload_complete(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, http: HTTPRequest, filename: String) -> void:
	http.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		_chat.add_system_message("Error: Document upload failed (code: %d)" % response_code)
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.get("status") == "ok":
		_chat.add_system_message("Document sent for import: %s" % filename)
	else:
		var error_msg = json.get("error", "Unknown error") if json else "Invalid response"
		_chat.add_system_message("Error: %s" % error_msg)


func _on_setting_changed(key: String, value: Variant) -> void:
	match key:
		"font_size":
			pass  # TODO: propagate font size
		"reset_layout":
			panel_mgr.arrange_default()
			_position_sidebar()
		"save":
			_chat.add_system_message("Settings saved")
		"panel_bg_companion":
			_chat.reload_background()


## ========================================================================
## Private room connection (1:1 with companion)
## ========================================================================

func _setup_private_room() -> void:
	_private = PrivateConnection.new()
	_private.name = "CompanionPrivate"
	_private.server_url = _room_url
	_private.entity_name = "Companion"
	add_child(_private)

	_private.connected.connect(_on_connected)
	_private.disconnected.connect(_on_disconnected)
	_private.chat_received.connect(_on_chat)
	_private.emote_received.connect(_on_emote)
	_private.status_received.connect(_on_status)
	_private.system_received.connect(_on_system)
	_private.history_received.connect(_on_history)
	_private.room_updated.connect(_on_room_updated)
	_private.logs_received.connect(_on_logs_received)
	_private.log_received.connect(_on_log_received)


func _on_connected() -> void:
	_reconnect_notice_shown = false
	_chat.add_system_message("Connected to companion room")
	_chat.set_status("online", Color(0.3, 0.8, 0.4))


func _on_disconnected() -> void:
	_chat.add_system_message("Room disconnected — reconnecting...")
	_chat.set_status("offline", Color(0.5, 0.5, 0.5))


func _on_chat(sender: String, content: String) -> void:
	# Route curation responses to curate panel
	if _curate_pending:
		_curate_pending = false
		_feature_panel.curate_panel.display_results(content)
		_feature_panel.curate_panel.set_status("Done")
		# Also show in chat for context
		_chat.add_message(sender, content)
		return

	_chat.add_message(sender, content)

	# Auto-speak if voice mode is active OR last input was voice-initiated
	if _voice_mgr != null:
		var should_speak = false
		if _chat.has_method("is_voice_active") and _chat.is_voice_active():
			should_speak = true
		elif _chat.has_method("was_last_input_voice") and _chat.was_last_input_voice():
			should_speak = true
		if should_speak:
			_voice_mgr.speak(content, "companion", "companion")
			if _chat.has_method("clear_voice_input_flag"):
				_chat.clear_voice_input_flag()


func _on_emote(sender: String, content: String) -> void:
	_chat.add_message(sender, content, "emote")


func _on_status(status: String) -> void:
	_set_status(status)


func _on_system(content: String) -> void:
	_chat.add_system_message(content)


func _on_history(messages: Array) -> void:
	if messages.is_empty():
		return
	_chat.add_system_message("— session history —")
	for msg in messages:
		if msg is Dictionary:
			var sender = msg.get("sender", "?")
			var content = msg.get("content", "")
			var msg_type = msg.get("type", "chat")
			var timestamp = msg.get("timestamp", "")
			_chat.add_message(sender, content, msg_type, timestamp)
	_chat.add_system_message("— end history —")


func _on_room_updated(state: Dictionary) -> void:
	if _room_panel:
		_room_panel.update_room(state)


func _on_logs_received(entries: Array) -> void:
	if _system_dashboard:
		_system_dashboard.handle_logs(entries)


func _on_log_received(entity: String, tag: String, message: String, ts: float) -> void:
	if _system_dashboard:
		_system_dashboard.add_log(entity, tag, message, ts)


func _set_status(status: String) -> void:
	match status:
		"online":
			_chat.set_status("online", Color(0.3, 0.8, 0.4))
		"thinking":
			_chat.set_status("thinking...", Color(0.9, 0.7, 0.2))
		"typing":
			_chat.set_status("typing...", Color(0.5, 0.8, 0.9))
		"idle":
			_chat.set_status("idle", Color(0.6, 0.6, 0.6))
		"away":
			_chat.set_status("away", Color(0.5, 0.5, 0.5))
		_:
			_chat.set_status(status, Color(0.6, 0.6, 0.6))


## ========================================================================
## Voice setup
## ========================================================================

func _setup_voice() -> void:
	_voice_mgr = VoiceManager.new()
	_voice_mgr.name = "VoiceManager"
	add_child(_voice_mgr)

	# Connect voice toggle signals from chat panel
	if _chat:
		_chat.voice_toggled.connect(_on_voice_toggled)

	# Connect voice manager signals
	_voice_mgr.transcription_ready.connect(_on_transcription_ready)
	_voice_mgr.playback_finished.connect(_on_playback_finished)
	_voice_mgr.voice_error.connect(_on_voice_error)


func _on_voice_toggled(enabled: bool) -> void:
	# Update panel voice state
	if _chat:
		_chat.set_voice_active(enabled)

	if enabled:
		_voice_mgr.start_recording("companion")
	else:
		_voice_mgr.stop_recording()
		# Reset voice mode on wrapper when voice toggle is disabled
		_private.send_command("set_voice_mode", {"enabled": false})


func _on_transcription_ready(text: String, _panel_id: String) -> void:
	if text.strip_edges().is_empty():
		_chat.add_system_message("(no speech detected)")
		return

	# Send transcribed text as a regular chat message
	# Set voice mode BEFORE sending chat so wrapper uses fast path
	_private.send_command("set_voice_mode", {"enabled": true})
	_private.send_chat(text)
	_chat.add_message(_user_name, text)
	_chat.mark_voice_input()


func _on_playback_finished(_panel_id: String) -> void:
	if _chat:
		_chat.show_speaking_indicator(false)


func _on_voice_error(message: String) -> void:
	_chat.add_system_message("Voice error: " + message)


## ========================================================================
## User input handlers
## ========================================================================

func _on_message(text: String) -> void:
	if text.begins_with("/"):
		_handle_command(text)
		return
	if not _private.is_room_connected():
		_chat.add_system_message("Not connected — waiting for reconnect...")
		return
	_private.send_chat(text)
	_chat.add_message(_user_name, text)


func _on_warmup() -> void:
	if _private.is_room_connected():
		_private.send_command("warmup")
		_chat.add_system_message("Warming up...")
	else:
		_chat.add_system_message("Not connected")


func _on_affect(level: float) -> void:
	if _private.is_room_connected():
		_private.send_command("set_affect", {"value": level})


func _on_image_upload(image_b64: String, filename: String, message: String) -> void:
	## Upload image via HTTP POST
	_chat.add_system_message("Uploading image...")

	# Create HTTP request
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_image_upload_complete.bind(http))

	var url = _room_url.replace("ws://", "http://") + "/chat/image"
	var headers = ["Content-Type: application/json"]
	var body = JSON.stringify({
		"image_b64": image_b64,
		"filename": filename,
		"message": message if not message.is_empty() else "What do you see?"
	})

	var error = http.request(url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		_chat.add_system_message("Error: Failed to send image upload request")
		http.queue_free()


func _on_image_upload_complete(result: int, response_code: int, _headers: PackedStringArray,
		body: PackedByteArray, http: HTTPRequest) -> void:
	http.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		_chat.add_system_message("Error: Image upload failed (code %d)" % response_code)
		return

	# Parse response
	var json = JSON.parse_string(body.get_string_from_utf8())
	if json and json.has("status") and json["status"] == "ok":
		# Response will come through WebSocket
		_chat.add_system_message("Image sent")
	else:
		var error_msg = json.get("error", "Unknown error") if json else "Invalid response"
		_chat.add_system_message("Error: %s" % error_msg)


func _handle_command(text: String) -> void:
	var parts = text.split(" ", false, 2)
	var cmd = parts[0].to_lower()

	match cmd:
		"/reconnect":
			_chat.add_system_message("Reconnecting...")
			_private.disconnect_from_room()
			_private.connect_to_room()
		"/clear":
			_chat.clear_chat()
		"/save":
			_chat.add_system_message("Saving session...")
			_feature_panel.session_browser._save_current()
		"/sessions":
			_sidebar._on_feature_toggled(true, "sessions")
			if _sidebar._buttons.has("sessions"):
				_sidebar._buttons["sessions"].set_pressed_no_signal(true)
		"/help":
			_chat.add_system_message(
				"/reconnect — reconnect to companion room\n" +
				"/clear — clear chat history\n" +
				"/save — save current session\n" +
				"/sessions — open session browser\n" +
				"/help — this message"
			)
		_:
			_chat.add_system_message("Unknown command: %s (try /help)" % cmd)


## ========================================================================
## Keyboard shortcuts
## ========================================================================

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		var key = event as InputEventKey

		if key.keycode == KEY_ESCAPE:
			_sidebar.close_all()
			_feature_panel.hide_all()
			get_viewport().set_input_as_handled()
		elif key.ctrl_pressed:
			match key.keycode:
				KEY_1:
					_chat.focus_input()
					get_viewport().set_input_as_handled()
				KEY_0:
					panel_mgr.arrange_default()
					get_viewport().set_input_as_handled()
				KEY_E:
					# Toggle easel panel
					var easel_dock = panel_mgr.get_panel("easel")
					if easel_dock:
						if easel_dock.is_minimized():
							easel_dock.restore()
							_easel_panel.fetch_latest_canvas()
						else:
							easel_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_R:
					# Toggle room panel
					var room_dock = panel_mgr.get_panel("room")
					if room_dock:
						if room_dock.is_minimized():
							room_dock.restore()
						else:
							room_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_D:
					# Toggle system dashboard (Ctrl+D)
					var system_dock = panel_mgr.get_panel("system")
					if system_dock:
						if system_dock.is_minimized():
							system_dock.restore()
						else:
							system_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_F:
					# Toggle face sidebar (Ctrl+F)
					if _chat:
						_chat.toggle_face_sidebar()
					get_viewport().set_input_as_handled()
