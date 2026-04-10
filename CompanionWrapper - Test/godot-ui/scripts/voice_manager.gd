## VoiceManager - Handles voice input (STT) and output (TTS) for the Nexus UI.
## Records from microphone, sends to server for transcription.
## Receives TTS audio from server and plays it back.
class_name VoiceManager
extends Node

signal transcription_ready(text: String, panel_id: String)
signal playback_finished(panel_id: String)
signal voice_error(message: String)
signal voice_test_finished(entity: String, success: bool)

const SERVER_URL = "http://localhost:8785"

## Audio capture
var _mic_player: AudioStreamPlayer
var _capture_effect: AudioEffectCapture
var _capture_bus_idx: int = -1
var _recording: bool = false
var _recorded_frames: PackedVector2Array = PackedVector2Array()
var _active_panel: String = ""

## Audio playback
var _playback_player: AudioStreamPlayer
var _speaking: bool = false
var _speak_panel: String = ""

## HTTP clients
var _transcribe_http: HTTPRequest
var _synthesize_http: HTTPRequest
var _test_http: HTTPRequest
var _test_entity: String = ""


func _ready() -> void:
	_setup_audio_bus()
	_setup_mic_capture()
	_setup_playback()
	_setup_http()


func _setup_audio_bus() -> void:
	# Add a dedicated audio bus for voice capture
	_capture_bus_idx = AudioServer.bus_count
	AudioServer.add_bus(_capture_bus_idx)
	AudioServer.set_bus_name(_capture_bus_idx, "VoiceCapture")
	AudioServer.set_bus_mute(_capture_bus_idx, true)  # Don't play mic through speakers

	# Add capture effect to the bus
	var effect = AudioEffectCapture.new()
	AudioServer.add_bus_effect(_capture_bus_idx, effect)
	_capture_effect = AudioServer.get_bus_effect(_capture_bus_idx, 0)


func _setup_mic_capture() -> void:
	# Create microphone input player
	_mic_player = AudioStreamPlayer.new()
	_mic_player.stream = AudioStreamMicrophone.new()
	_mic_player.bus = "VoiceCapture"
	add_child(_mic_player)


func _setup_playback() -> void:
	# Create playback player for TTS
	_playback_player = AudioStreamPlayer.new()
	_playback_player.finished.connect(_on_playback_done)
	add_child(_playback_player)


func _setup_http() -> void:
	# Transcribe request
	_transcribe_http = HTTPRequest.new()
	_transcribe_http.request_completed.connect(_on_transcribe_response)
	add_child(_transcribe_http)

	# Synthesize request
	_synthesize_http = HTTPRequest.new()
	_synthesize_http.request_completed.connect(_on_synthesize_response)
	add_child(_synthesize_http)

	# Test voice request
	_test_http = HTTPRequest.new()
	_test_http.request_completed.connect(_on_test_voice_response)
	add_child(_test_http)


func _process(_delta: float) -> void:
	if _recording and _capture_effect:
		var frames = _capture_effect.get_buffer(_capture_effect.get_frames_available())
		if frames.size() > 0:
			_recorded_frames.append_array(frames)


## ============================================================
## Public API
## ============================================================

func start_recording(panel_id: String) -> void:
	if _recording:
		# Already recording - stop first
		stop_recording()

	_active_panel = panel_id
	_recorded_frames.clear()

	# Clear any buffered audio
	if _capture_effect:
		_capture_effect.clear_buffer()

	# Start mic capture
	_mic_player.play()
	_recording = true
	print("[VOICE] Recording started for panel: %s" % panel_id)
	# Debug: hit status endpoint so we see something in server log
	var debug_http = HTTPRequest.new()
	add_child(debug_http)
	debug_http.request_completed.connect(func(_r, _c, _h, _b): debug_http.queue_free())
	debug_http.request(SERVER_URL + "/voice/status")


func stop_recording() -> void:
	if not _recording:
		return

	_recording = false
	_mic_player.stop()

	var panel_id = _active_panel
	print("[VOICE] Recording stopped, captured %d frames" % _recorded_frames.size())

	if _recorded_frames.size() < 1600:  # Less than 0.1s at 16kHz
		voice_error.emit("Recording too short")
		_recorded_frames.clear()
		return

	# Encode to WAV and send to server
	var wav_data = _encode_wav(_recorded_frames)
	_recorded_frames.clear()

	if wav_data.size() < 100:
		voice_error.emit("Failed to encode audio")
		return

	_upload_audio(wav_data, panel_id)


func speak(text: String, entity: String, panel_id: String) -> void:
	if _speaking:
		_playback_player.stop()

	_speak_panel = panel_id
	_speaking = true

	# Request TTS from server
	var body = JSON.stringify({"text": text, "entity": entity})
	var headers = ["Content-Type: application/json"]
	var err = _synthesize_http.request(
		SERVER_URL + "/voice/synthesize",
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err != OK:
		voice_error.emit("Failed to request TTS")
		_speaking = false


func is_recording() -> bool:
	return _recording


func is_speaking() -> bool:
	return _speaking


func get_active_panel() -> String:
	return _active_panel if _recording else _speak_panel


func test_voice(text: String, entity: String, voice_id: String) -> void:
	"""
	Test a specific voice preset by synthesizing a sample line.
	Emits voice_test_finished when done.
	"""
	if _speaking:
		_playback_player.stop()

	_test_entity = entity
	_speaking = true

	var body = JSON.stringify({
		"text": text,
		"entity": entity,
		"voice": voice_id
	})
	var headers = ["Content-Type: application/json"]
	var err = _test_http.request(
		SERVER_URL + "/voice/test",
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err != OK:
		voice_error.emit("Failed to request voice test")
		_speaking = false
		voice_test_finished.emit(entity, false)


func _on_test_voice_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		voice_error.emit("Voice test request failed")
		_speaking = false
		voice_test_finished.emit(_test_entity, false)
		return

	if body.size() < 50:
		# Check for JSON error response
		var text = body.get_string_from_utf8()
		if text.begins_with("{"):
			var json = JSON.parse_string(text)
			if json and json is Dictionary and json.has("error"):
				voice_error.emit(str(json.get("error", "Test failed")))
		_speaking = false
		voice_test_finished.emit(_test_entity, false)
		return

	# Play the audio (same logic as synthesize response)
	var header = body.slice(0, 4)
	if header.get_string_from_ascii() == "RIFF":
		_play_wav_from_bytes(body)
	else:
		_play_mp3_from_bytes(body)

	# Note: voice_test_finished will be emitted when playback completes
	# We set _speak_panel to a special value so _on_playback_done knows this was a test
	_speak_panel = "__voice_test__"


## ============================================================
## WAV Encoding
## ============================================================

func _encode_wav(frames: PackedVector2Array) -> PackedByteArray:
	# Godot mix rate (usually 44100 or 48000)
	var src_rate: int = AudioServer.get_mix_rate()
	var dst_rate: int = 16000
	var ratio: float = float(src_rate) / float(dst_rate)
	var dst_len: int = int(frames.size() / ratio)

	if dst_len < 10:
		return PackedByteArray()

	# Convert to 16-bit PCM, mono, resampled to 16kHz
	var pcm := PackedByteArray()
	pcm.resize(dst_len * 2)  # 16-bit = 2 bytes per sample

	for i in range(dst_len):
		var src_idx: float = i * ratio
		var idx: int = int(src_idx)
		if idx >= frames.size():
			idx = frames.size() - 1
		# Downmix stereo to mono
		var sample: float = (frames[idx].x + frames[idx].y) / 2.0
		# Clamp and convert to int16
		var s16: int = clampi(int(sample * 32767.0), -32768, 32767)
		pcm.encode_s16(i * 2, s16)

	# Build WAV file header + data
	var wav := PackedByteArray()
	var data_size: int = pcm.size()
	var file_size: int = 36 + data_size

	# RIFF header
	wav.append_array("RIFF".to_ascii_buffer())
	var riff_pos = wav.size()
	wav.resize(wav.size() + 4)
	wav.encode_u32(riff_pos, file_size)
	wav.append_array("WAVE".to_ascii_buffer())

	# fmt chunk
	wav.append_array("fmt ".to_ascii_buffer())
	var fmt_start = wav.size()
	wav.resize(wav.size() + 20)
	wav.encode_u32(fmt_start, 16)        # chunk size
	wav.encode_u16(fmt_start + 4, 1)     # PCM format
	wav.encode_u16(fmt_start + 6, 1)     # mono
	wav.encode_u32(fmt_start + 8, dst_rate)   # sample rate
	wav.encode_u32(fmt_start + 12, dst_rate * 2)  # byte rate
	wav.encode_u16(fmt_start + 16, 2)    # block align
	wav.encode_u16(fmt_start + 18, 16)   # bits per sample

	# data chunk
	wav.append_array("data".to_ascii_buffer())
	var data_start = wav.size()
	wav.resize(wav.size() + 4)
	wav.encode_u32(data_start, data_size)
	wav.append_array(pcm)

	return wav


## ============================================================
## HTTP Handling
## ============================================================

func _upload_audio(wav_data: PackedByteArray, panel_id: String) -> void:
	# Build multipart form data
	var boundary = "----GodotVoiceBoundary"
	var body := PackedByteArray()
	body.append_array(("--%s\r\n" % boundary).to_utf8_buffer())
	body.append_array("Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n".to_utf8_buffer())
	body.append_array("Content-Type: audio/wav\r\n\r\n".to_utf8_buffer())
	body.append_array(wav_data)
	body.append_array(("\r\n--%s--\r\n" % boundary).to_utf8_buffer())

	var headers = [
		"Content-Type: multipart/form-data; boundary=%s" % boundary
	]

	# Store panel_id for response callback
	_transcribe_http.set_meta("panel_id", panel_id)

	var err = _transcribe_http.request_raw(
		SERVER_URL + "/voice/transcribe",
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err != OK:
		voice_error.emit("Failed to upload audio: %d" % err)


func _on_transcribe_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	var panel_id = _transcribe_http.get_meta("panel_id", _active_panel)

	if result != HTTPRequest.RESULT_SUCCESS:
		voice_error.emit("Transcribe request failed: %d" % result)
		return

	if code != 200:
		voice_error.emit("Transcribe server error: %d" % code)
		return

	var json = JSON.parse_string(body.get_string_from_utf8())
	if json == null or not json is Dictionary:
		voice_error.emit("Invalid transcribe response")
		return

	var text: String = json.get("text", "")
	var ok: bool = json.get("ok", false)

	if not ok:
		var error: String = json.get("error", "Unknown error")
		voice_error.emit("Transcription failed: %s" % error)
		return

	transcription_ready.emit(text, panel_id)


func _on_synthesize_response(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		voice_error.emit("TTS request failed")
		_speaking = false
		return

	if body.size() < 50:
		# Empty or invalid response
		_speaking = false
		playback_finished.emit(_speak_panel)
		return

	# Detect format: WAV starts with "RIFF", MP3 starts with ID3 or 0xFF sync
	var header = body.slice(0, 4)
	if header.get_string_from_ascii() == "RIFF":
		_play_wav_from_bytes(body)
	else:
		# Assume MP3 (Edge TTS, ElevenLabs default)
		_play_mp3_from_bytes(body)


func _play_mp3_from_bytes(mp3_bytes: PackedByteArray) -> void:
	var stream = AudioStreamMP3.new()
	stream.data = mp3_bytes
	_playback_player.stream = stream
	_playback_player.play()
	print("[VOICE] Playing MP3 audio (%d bytes)" % mp3_bytes.size())


func _play_wav_from_bytes(wav_bytes: PackedByteArray) -> void:
	if wav_bytes.size() < 44:
		_speaking = false
		playback_finished.emit(_speak_panel)
		return

	# Parse WAV header to get format info
	var sample_rate: int = 16000
	var stereo: bool = false
	var bits: int = 16

	# Check RIFF header
	if wav_bytes.slice(0, 4).get_string_from_ascii() != "RIFF":
		push_warning("Invalid WAV: no RIFF header")
		_speaking = false
		playback_finished.emit(_speak_panel)
		return

	# Find fmt chunk
	var pos: int = 12
	while pos < wav_bytes.size() - 8:
		var chunk_id = wav_bytes.slice(pos, pos + 4).get_string_from_ascii()
		var chunk_size = wav_bytes.decode_u32(pos + 4)

		if chunk_id == "fmt ":
			var channels = wav_bytes.decode_u16(pos + 10)
			sample_rate = wav_bytes.decode_u32(pos + 12)
			bits = wav_bytes.decode_u16(pos + 22)
			stereo = (channels == 2)
			break

		pos += 8 + chunk_size
		if chunk_size % 2 == 1:
			pos += 1  # Padding

	# Find data chunk
	pos = 12
	var data_start: int = 44
	var data_size: int = wav_bytes.size() - 44
	while pos < wav_bytes.size() - 8:
		var chunk_id = wav_bytes.slice(pos, pos + 4).get_string_from_ascii()
		var chunk_size = wav_bytes.decode_u32(pos + 4)

		if chunk_id == "data":
			data_start = pos + 8
			data_size = chunk_size
			break

		pos += 8 + chunk_size
		if chunk_size % 2 == 1:
			pos += 1

	# Create AudioStreamWAV
	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS if bits == 16 else AudioStreamWAV.FORMAT_8_BITS
	stream.mix_rate = sample_rate
	stream.stereo = stereo
	stream.data = wav_bytes.slice(data_start, data_start + data_size)

	_playback_player.stream = stream
	_playback_player.play()


func _on_playback_done() -> void:
	_speaking = false
	if _speak_panel == "__voice_test__":
		voice_test_finished.emit(_test_entity, true)
		_test_entity = ""
	else:
		playback_finished.emit(_speak_panel)
