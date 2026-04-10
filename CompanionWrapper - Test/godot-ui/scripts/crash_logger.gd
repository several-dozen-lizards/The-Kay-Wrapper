## CrashLogger - File-based logging for crash diagnosis.
## Autoload singleton - add to Project Settings > Autoload as "CrashLogger"
extends Node

## Log file location
const LOG_DIR := "user://logs"
const LOG_FILE := "user://logs/crash_log.txt"
const MAX_LOG_SIZE := 1048576  # 1MB max before rotation

var _log_file: FileAccess = null
var _log_enabled: bool = true


func _ready() -> void:
	_ensure_log_dir()
	_rotate_if_needed()
	_open_log_file()
	log_event("SESSION", "Godot UI started")


func _exit_tree() -> void:
	log_event("SESSION", "Godot UI closing")
	_close_log_file()


func _ensure_log_dir() -> void:
	if not DirAccess.dir_exists_absolute(LOG_DIR):
		var dir = DirAccess.open("user://")
		if dir:
			dir.make_dir("logs")


func _rotate_if_needed() -> void:
	if not FileAccess.file_exists(LOG_FILE):
		return
	var file = FileAccess.open(LOG_FILE, FileAccess.READ)
	if file:
		var size = file.get_length()
		file.close()
		if size > MAX_LOG_SIZE:
			# Rotate: rename old log
			var timestamp = Time.get_datetime_string_from_system().replace(":", "-")
			var backup_path = "user://logs/crash_log_%s.txt" % timestamp
			DirAccess.rename_absolute(LOG_FILE, backup_path)


func _open_log_file() -> void:
	_log_file = FileAccess.open(LOG_FILE, FileAccess.READ_WRITE)
	if _log_file == null:
		# File doesn't exist, create it
		_log_file = FileAccess.open(LOG_FILE, FileAccess.WRITE)
	else:
		# Seek to end for appending
		_log_file.seek_end()


func _close_log_file() -> void:
	if _log_file:
		_log_file.close()
		_log_file = null


func _get_timestamp() -> String:
	return Time.get_datetime_string_from_system()


## Log a generic event
func log_event(category: String, message: String) -> void:
	if not _log_enabled or _log_file == null:
		return
	var line = "[%s] [%s] %s\n" % [_get_timestamp(), category, message]
	_log_file.store_string(line)
	_log_file.flush()


## Log connection events
func log_connect(connection_name: String, url: String) -> void:
	log_event("CONNECT", "%s connected to %s" % [connection_name, url])


func log_disconnect(connection_name: String, reason: String = "") -> void:
	var msg = "%s disconnected" % connection_name
	if reason:
		msg += ": %s" % reason
	log_event("DISCONNECT", msg)


## Log large messages (potential memory issues)
func log_large_message(connection_name: String, size: int, msg_type: String) -> void:
	log_event("LARGE_MSG", "%s received %d bytes (%s)" % [connection_name, size, msg_type])


## Log parse errors
func log_parse_error(connection_name: String, error: String, raw_preview: String) -> void:
	log_event("PARSE_ERROR", "%s: %s | Preview: %s" % [connection_name, error, raw_preview.left(100)])


## Log signal emission issues
func log_signal_error(connection_name: String, signal_name: String, error: String) -> void:
	log_event("SIGNAL_ERROR", "%s.%s: %s" % [connection_name, signal_name, error])


## Log unexpected data type
func log_type_error(connection_name: String, field: String, expected: String, got: String) -> void:
	log_event("TYPE_ERROR", "%s.%s expected %s, got %s" % [connection_name, field, expected, got])


## Log generic warnings
func log_warning(connection_name: String, message: String) -> void:
	log_event("WARNING", "%s: %s" % [connection_name, message])


## Get the path to the log file (for debugging)
func get_log_path() -> String:
	return ProjectSettings.globalize_path(LOG_FILE)
