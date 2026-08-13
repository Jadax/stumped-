class_name AudioManager
extends Node
## Simple audio manager for Stumped! Godot client.
## Plays match sounds (boundary, wicket, crowd, etc.) using Godot's
## built-in audio system.

var _audio_players: Array = []
var _sound_cache: Dictionary = {}
var _volume: float = 1.0
var _muted: bool = false
var _procedural_cache: Dictionary = {}
var _ambience_player: AudioStreamPlayer
var _music_player: AudioStreamPlayer


func _ready() -> void:
	# Create audio players for different sound types
	for i in range(8):
		var player := AudioStreamPlayer.new()
		player.bus = "Master"
		add_child(player)
		_audio_players.append(player)
	# A quiet procedural stadium bed keeps the game alive even when optional
	# audio files are absent. It is generated at runtime, so no copyrighted
	# music or third-party sound pack is required for the Steam build.
	_ambience_player = AudioStreamPlayer.new()
	_ambience_player.bus = "Master"
	add_child(_ambience_player)
	_ambience_player.stream = _make_tone("ambience")
	_ambience_player.volume_db = -24.0
	_ambience_player.finished.connect(func():
		if not _muted:
			_ambience_player.play()
	)
	_ambience_player.play()
	_music_player = AudioStreamPlayer.new()
	_music_player.bus = "Master"
	add_child(_music_player)
	_music_player.stream = _make_tone("music")
	_music_player.volume_db = -30.0
	_music_player.finished.connect(func():
		if not _muted:
			_music_player.play()
	)
	_music_player.play()


func set_volume(vol: float) -> void:
	_volume = clampf(vol, 0.0, 1.0)


func set_muted(mute: bool) -> void:
	_muted = mute


func play_sound(sound_name: String, volume_scale: float = 1.0) -> void:
	if _muted:
		return
	var stream := _load_sound(sound_name)
	if stream:
		var player := _get_free_player()
		if player:
			player.stream = stream
			player.volume_db = linear_to_db(_volume * volume_scale)
			player.play()


func _load_sound(sound_name: String) -> AudioStream:
	if _sound_cache.has(sound_name):
		return _sound_cache[sound_name]
	var path := "res://assets/audio/%s.wav" % sound_name
	if ResourceLoader.exists(path):
		var stream = load(path)
		_sound_cache[sound_name] = stream
		return stream
	var generated := _make_tone(sound_name)
	_sound_cache[sound_name] = generated
	return generated


func _make_tone(sound_name: String) -> AudioStreamWAV:
	if _procedural_cache.has(sound_name):
		return _procedural_cache[sound_name]
	var rate := 22050
	var duration := 0.32
	var frequency := 520.0
	var amplitude := 0.22
	if sound_name == "boundary":
		frequency = 740.0
		duration = 0.55
		amplitude = 0.34
	elif sound_name == "six":
		frequency = 920.0
		duration = 0.7
		amplitude = 0.38
	elif sound_name == "wicket":
		frequency = 120.0
		duration = 0.65
		amplitude = 0.42
	elif sound_name == "applause":
		frequency = 260.0
		duration = 0.9
		amplitude = 0.16
	elif sound_name == "ambience":
		frequency = 92.0
		duration = 4.0
		amplitude = 0.045
	elif sound_name == "music":
		frequency = 196.0
		duration = 8.0
		amplitude = 0.055
	var count := int(rate * duration)
	var bytes := PackedByteArray()
	for i in range(count):
		var t := float(i) / float(rate)
		var envelope := 1.0 - (float(i) / float(count)) * 0.85
		var wave := sin(TAU * frequency * t) * amplitude * envelope
		if sound_name == "music":
			var notes := [196.0, 246.94, 293.66, 392.0, 293.66, 246.94]
			var note: float = float(notes[int(floor(t * 0.75)) % notes.size()])
			wave = (sin(TAU * note * t) + 0.35 * sin(TAU * note * 2.0 * t)) * amplitude * envelope
		if sound_name == "wicket":
			wave += sin(TAU * 57.0 * t) * 0.18 * envelope
		elif sound_name == "ambience":
			wave += sin(TAU * 137.0 * t) * 0.35 * amplitude
		var sample := int(clampf(wave, -1.0, 1.0) * 32767.0)
		bytes.append(sample & 0xff)
		bytes.append((sample >> 8) & 0xff)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.stereo = false
	stream.data = bytes
	_procedural_cache[sound_name] = stream
	return stream


func _get_free_player() -> AudioStreamPlayer:
	for player in _audio_players:
		if not player.playing:
			return player
	return _audio_players[0] if _audio_players.size() > 0 else null


func play_boundary() -> void:
	play_sound("boundary", 0.8)


func play_six() -> void:
	play_sound("six", 1.0)


func play_wicket() -> void:
	play_sound("wicket", 0.9)


func play_run() -> void:
	play_sound("run", 0.6)


func play_applause() -> void:
	play_sound("applause", 0.5)


func play_ambience() -> void:
	play_sound("ambience", 0.3)
