## Main - Application entry point for JNSQ Companion Wrapper UI.
##
## MULTI-PERSONA ARCHITECTURE:
##   1. Launcher mode (default): Shows persona selection, user picks which to activate
##   2. Multi-persona mode: Each persona gets its own tab + backend process
##   3. Single-persona mode: Direct connection (backward compatible, --port argument)
##
## Each persona has:
##   - Its own Python backend process (main.py --ui --room-port PORT)
##   - Its own PrivateConnection WebSocket
##   - Its own ChatPanel tab
extends Control

const ChatPanelScene = preload("res://scenes/ChatPanel.tscn")
const LauncherScene = preload("res://scenes/Launcher.tscn")

## Mode flags
var _multi_persona_mode: bool = false
var _launcher_mode: bool = true
var _single_persona_port: int = 0  # 0 = not set

## Multi-persona state
var _connections: Dictionary = {}  # persona_name -> PrivateConnection
var _chat_panels: Dictionary = {}  # persona_name -> ChatPanel
var _persona_ports: Dictionary = {}  # persona_name -> port
var _active_persona: String = ""
var _tab_container: TabContainer

## Single-persona state (backward compatibility)
var _private: PrivateConnection
var _chat: ChatPanel

## Launcher reference
var _launcher: Launcher

## Panel manager (for single-persona mode)
@onready var panel_mgr: PanelManager = %PanelManager

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
var _user_name: String = "User"
var _room_url: String = "ws://localhost:8780"
var _reconnect_notice_shown: bool = false

## Curation response routing
var _curate_pending: bool = false


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		print("[JNSQ UI] Window close requested — shutting down backends")
		_shutdown_backends()
		get_tree().quit()


func _ready() -> void:
	get_tree().root.min_size = Vector2(800, 500)
	await get_tree().process_frame

	# Check command line arguments for direct port connection
	_parse_arguments()

	if _single_persona_port > 0:
		# Direct single-persona mode (backward compatible)
		_launcher_mode = false
		_multi_persona_mode = false
		_room_url = "ws://localhost:%d" % _single_persona_port
		_start_single_persona_mode()
	else:
		# Show launcher for persona selection
		_show_launcher()


func _parse_arguments() -> void:
	"""Parse command line arguments for --port."""
	var args = OS.get_cmdline_args()
	for i in range(args.size()):
		if args[i] == "--port" and i + 1 < args.size():
			_single_persona_port = int(args[i + 1])
			print("[JNSQ UI] Direct port mode: %d" % _single_persona_port)


## ========================================================================
## Launcher Mode
## ========================================================================

func _show_launcher() -> void:
	"""Show the persona selection launcher."""
	_launcher = LauncherScene.instantiate() as Launcher
	_launcher.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_launcher)

	_launcher.launch_requested.connect(_on_launch_personas)
	_launcher.create_requested.connect(_on_create_persona)


func _on_launch_personas(persona_names: Array[String]) -> void:
	"""Start backends and create UI for selected personas."""
	if persona_names.is_empty():
		return

	print("[JNSQ UI] Launching %d persona(s): %s" % [persona_names.size(), persona_names])

	# Hide launcher
	if _launcher:
		_launcher.queue_free()
		_launcher = null

	_launcher_mode = false

	if persona_names.size() == 1:
		# Single persona - use traditional layout
		_multi_persona_mode = false
		await _start_single_persona_from_launcher(persona_names[0])
	else:
		# Multiple personas - use tabbed layout
		_multi_persona_mode = true
		await _start_multi_persona_mode(persona_names)


func _on_create_persona() -> void:
	"""Open persona creation wizard."""
	# TODO: Launch setup_wizard.py or open config editor
	print("[JNSQ UI] Persona creation not yet implemented in UI")


## ========================================================================
## Single Persona Mode (Traditional Layout)
## ========================================================================

func _start_single_persona_mode() -> void:
	"""Start with traditional single-persona layout (backward compatible)."""
	_create_panels()
	_setup_sidebar()
	_setup_private_room()
	_setup_voice()
	await get_tree().process_frame
	panel_mgr.arrange_default()

	# Auto-connect to companion room
	_private.connect_to_room()


func _start_single_persona_from_launcher(persona_name: String) -> void:
	"""Start single persona mode after launcher selection."""
	var config = _launcher.get_persona_config(persona_name) if _launcher else {}

	# Start backend
	var port = await _start_backend(persona_name)
	if port <= 0:
		print("[JNSQ UI] Failed to start backend for %s" % persona_name)
		return

	_room_url = "ws://localhost:%d" % port
	_persona_ports[persona_name] = port
	_active_persona = persona_name

	# Use traditional layout
	_create_panels_for_persona(persona_name, config)
	_setup_sidebar()
	_setup_private_room_for_persona(persona_name, port)
	_setup_voice()
	await get_tree().process_frame
	panel_mgr.arrange_default()

	# Connect
	_private.connect_to_room()


func _create_panels_for_persona(persona_name: String, config: Dictionary) -> void:
	"""Create panels configured for a specific persona."""
	var screen = get_viewport_rect().size
	var display_name = config.get("name", persona_name).to_upper()
	var description = config.get("description", "your companion")

	# --- Main chat panel ---
	_chat = ChatPanelScene.instantiate() as ChatPanel
	panel_mgr.create_panel(
		persona_name, display_name, description,
		Vector2(10, 10),
		Vector2(screen.x * 0.75, screen.y - 50),
		_chat
	)
	_chat.configure(persona_name, true)
	_chat.message_submitted.connect(_on_message)
	_chat.warmup_requested.connect(_on_warmup)
	_chat.affect_changed.connect(_on_affect)
	_chat.image_upload_requested.connect(_on_image_upload)

	# Welcome messages
	_chat.add_system_message("%s UI initialized" % display_name)
	_chat.add_system_message("Drag panels to rearrange | Right sidebar: Sessions, Auto, Curate, Media, Settings")

	# --- Room panel ---
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

	# --- System dashboard ---
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

	# --- Face panel ---
	_face_panel = FacePanel.new()
	_face_panel.set_entity(persona_name)
	_chat.embed_face(_face_panel, persona_name)


func _setup_private_room_for_persona(persona_name: String, port: int) -> void:
	"""Setup private room connection for a specific persona."""
	_private = PrivateConnection.new()
	_private.name = "%sPrivate" % persona_name.capitalize()
	_private.server_url = "ws://localhost:%d" % port
	_private.entity_name = persona_name.capitalize()
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


## ========================================================================
## Multi-Persona Mode (Tabbed Layout)
## ========================================================================

func _start_multi_persona_mode(persona_names: Array[String]) -> void:
	"""Start multiple personas with tabbed interface."""
	# Hide panel manager for multi-persona mode
	if panel_mgr:
		panel_mgr.visible = false

	# Create tab container
	_tab_container = TabContainer.new()
	_tab_container.set_anchors_preset(Control.PRESET_FULL_RECT)
	_tab_container.tab_changed.connect(_on_tab_changed)
	add_child(_tab_container)

	# Start backends and create tabs for each persona
	for persona_name in persona_names:
		var port = await _start_backend(persona_name)
		if port <= 0:
			print("[JNSQ UI] Failed to start backend for %s" % persona_name)
			continue

		_persona_ports[persona_name] = port
		await _create_persona_tab(persona_name, port)

	# Set first tab as active
	if not persona_names.is_empty():
		_active_persona = persona_names[0]


func _create_persona_tab(persona_name: String, port: int) -> void:
	"""Create a chat panel tab for a persona."""
	# Create connection
	var conn = PrivateConnection.new()
	conn.server_url = "ws://localhost:%d" % port
	conn.entity_name = persona_name.capitalize()
	add_child(conn)
	_connections[persona_name] = conn

	# Create container for this tab
	var tab_content = VBoxContainer.new()
	tab_content.name = persona_name.capitalize()
	_tab_container.add_child(tab_content)

	# Create chat panel
	var chat = ChatPanelScene.instantiate() as ChatPanel
	chat.size_flags_vertical = Control.SIZE_EXPAND_FILL
	chat.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chat.configure(persona_name, true)
	tab_content.add_child(chat)
	_chat_panels[persona_name] = chat

	# Wire connection to this chat panel
	conn.connected.connect(func():
		chat.add_system_message("Connected to %s" % persona_name)
		chat.set_status("online", Color(0.3, 0.8, 0.4))
	)
	conn.disconnected.connect(func():
		chat.add_system_message("Disconnected — reconnecting...")
		chat.set_status("offline", Color(0.5, 0.5, 0.5))
	)
	conn.chat_received.connect(func(sender: String, content: String):
		chat.add_message(sender, content)
	)
	conn.emote_received.connect(func(sender: String, content: String):
		chat.add_message(sender, content, "emote")
	)
	conn.status_received.connect(func(status: String):
		_set_status_for_chat(chat, status)
	)
	conn.system_received.connect(func(content: String):
		chat.add_system_message(content)
	)
	conn.history_received.connect(func(messages: Array):
		_show_history_in_chat(chat, messages)
	)

	# Wire chat panel input to this connection
	chat.message_submitted.connect(func(text: String):
		if text.begins_with("/"):
			_handle_command_for_persona(text, persona_name)
		else:
			conn.send_chat(text)
			chat.add_message(_user_name, text)
	)
	chat.warmup_requested.connect(func():
		if conn.is_room_connected():
			conn.send_command("warmup")
			chat.add_system_message("Warming up...")
	)

	# Connect to backend
	conn.connect_to_room()

	# Welcome message
	chat.add_system_message("%s tab ready — connecting to backend on port %d" % [persona_name.capitalize(), port])


func _on_tab_changed(tab_idx: int) -> void:
	"""Handle tab change."""
	var tab_name = _tab_container.get_child(tab_idx).name.to_lower()
	_active_persona = tab_name
	print("[JNSQ UI] Active persona: %s" % _active_persona)


func _set_status_for_chat(chat: ChatPanel, status: String) -> void:
	"""Set status indicator for a chat panel."""
	match status:
		"online":
			chat.set_status("online", Color(0.3, 0.8, 0.4))
		"thinking":
			chat.set_status("thinking...", Color(0.9, 0.7, 0.2))
		"typing":
			chat.set_status("typing...", Color(0.5, 0.8, 0.9))
		"idle":
			chat.set_status("idle", Color(0.6, 0.6, 0.6))
		"away":
			chat.set_status("away", Color(0.5, 0.5, 0.5))
		_:
			chat.set_status(status, Color(0.6, 0.6, 0.6))


func _show_history_in_chat(chat: ChatPanel, messages: Array) -> void:
	"""Show history messages in a chat panel."""
	if messages.is_empty():
		return
	chat.add_system_message("— session history —")
	for msg in messages:
		if msg is Dictionary:
			var sender = msg.get("sender", "?")
			var content = msg.get("content", "")
			var msg_type = msg.get("type", "chat")
			var timestamp = msg.get("timestamp", "")
			chat.add_message(sender, content, msg_type, timestamp)
	chat.add_system_message("— end history —")


func _handle_command_for_persona(text: String, persona_name: String) -> void:
	"""Handle slash commands in multi-persona mode."""
	var chat = _chat_panels.get(persona_name) as ChatPanel
	var conn = _connections.get(persona_name) as PrivateConnection
	if not chat or not conn:
		return

	var parts = text.split(" ", false, 2)
	var cmd = parts[0].to_lower()

	match cmd:
		"/reconnect":
			chat.add_system_message("Reconnecting...")
			conn.disconnect_from_room()
			conn.connect_to_room()
		"/clear":
			chat.clear_chat()
		"/help":
			chat.add_system_message(
				"/reconnect — reconnect to backend\n" +
				"/clear — clear chat history\n" +
				"/help — this message"
			)
		_:
			chat.add_system_message("Unknown command: %s (try /help)" % cmd)


## ========================================================================
## Backend Process Management
## ========================================================================

func _start_backend(persona_name: String) -> int:
	"""Start a Python backend for a persona. Returns port number or -1 on failure."""
	var wrapper_root = _get_wrapper_root()
	var port = _get_next_port()

	print("[JNSQ UI] Starting backend for %s on port %d" % [persona_name, port])

	# Call start_backend.py
	var output: Array = []
	var exit_code = OS.execute(
		"python",
		[wrapper_root.path_join("start_backend.py"), persona_name, str(port)],
		output, true, false
	)

	if exit_code != 0:
		print("[JNSQ UI] Backend start failed: %s" % str(output))
		return -1

	# Parse output JSON
	var output_text = "".join(output)
	var json = JSON.parse_string(output_text)
	if json == null or not json is Dictionary:
		print("[JNSQ UI] Invalid backend response: %s" % output_text)
		return -1

	if json.has("error"):
		print("[JNSQ UI] Backend error: %s" % json.get("error"))
		return -1

	var started_port = json.get("port", port)
	print("[JNSQ UI] Backend started: %s on port %d (pid: %s)" % [persona_name, started_port, json.get("pid", "?")])

	# Wait for backend to be ready
	await _wait_for_port(started_port, 15.0)

	return started_port


func _wait_for_port(port: int, timeout: float) -> bool:
	"""Wait for a port to become available. Returns true if connected."""
	var start_time = Time.get_ticks_msec()
	var timeout_ms = int(timeout * 1000)

	while Time.get_ticks_msec() - start_time < timeout_ms:
		# Try to connect briefly
		var tcp = StreamPeerTCP.new()
		var err = tcp.connect_to_host("127.0.0.1", port)
		if err == OK:
			# Wait a bit for connection to establish
			await get_tree().create_timer(0.5).timeout
			tcp.poll()
			if tcp.get_status() == StreamPeerTCP.STATUS_CONNECTED:
				tcp.disconnect_from_host()
				print("[JNSQ UI] Port %d ready" % port)
				return true
			tcp.disconnect_from_host()
		await get_tree().create_timer(0.5).timeout

	print("[JNSQ UI] Timeout waiting for port %d" % port)
	return false


func _get_next_port() -> int:
	"""Get next available port starting from 8780."""
	var base_port = 8780
	var used_ports: Array[int] = []
	for p in _persona_ports.values():
		used_ports.append(p)

	while base_port in used_ports:
		base_port += 1

	return base_port


func _shutdown_backends() -> void:
	"""Shutdown all running backends cleanly."""
	if _persona_ports.is_empty():
		return

	print("[JNSQ UI] Shutting down %d backend(s)..." % _persona_ports.size())

	var wrapper_root = _get_wrapper_root()

	# Call stop_backend.py --all
	var output: Array = []
	OS.execute(
		"python",
		[wrapper_root.path_join("stop_backend.py"), "--all"],
		output, true, false
	)

	print("[JNSQ UI] Backend shutdown complete")


func _get_wrapper_root() -> String:
	"""Get the wrapper root directory."""
	var exe_path = OS.get_executable_path()
	if exe_path.is_empty() or exe_path.contains("godot"):
		return ProjectSettings.globalize_path("res://").get_base_dir()
	else:
		return exe_path.get_base_dir().get_base_dir()


## ========================================================================
## Traditional Panel Creation (Single-Persona Mode)
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

	var url = "http://localhost:8770/chat/document"
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
## Private room connection (1:1 with companion) - Single Persona Mode
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

	var url = "http://localhost:8770/chat/image"
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
	# Skip keyboard handling in launcher mode
	if _launcher_mode:
		return

	if event is InputEventKey and event.pressed:
		var key = event as InputEventKey

		if key.keycode == KEY_ESCAPE:
			if _sidebar:
				_sidebar.close_all()
			if _feature_panel:
				_feature_panel.hide_all()
			get_viewport().set_input_as_handled()
		elif key.ctrl_pressed:
			match key.keycode:
				KEY_1:
					if _chat:
						_chat.focus_input()
					get_viewport().set_input_as_handled()
				KEY_0:
					if panel_mgr:
						panel_mgr.arrange_default()
					get_viewport().set_input_as_handled()
				KEY_E:
					# Toggle easel panel
					if panel_mgr:
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
					if panel_mgr:
						var room_dock = panel_mgr.get_panel("room")
						if room_dock:
							if room_dock.is_minimized():
								room_dock.restore()
							else:
								room_dock._minimize_panel()
					get_viewport().set_input_as_handled()
				KEY_D:
					# Toggle system dashboard (Ctrl+D)
					if panel_mgr:
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
