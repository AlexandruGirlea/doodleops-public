"""
Pricing: https://cloud.google.com/text-to-speech/pricing?hl=en
"""
import logging

from google.cloud import speech
from google.cloud import texttospeech

from core.settings import BUKET_BASE_URL, BUKET_GCP_URL
from common.other import upload_resp_file_content_to_bucket, random_name_generator


logger = logging.getLogger("APP_AI_V1_" + __name__)


def get_list_voices_text_to_speach():
	client = texttospeech.TextToSpeechClient()
	voices_response = client.list_voices()
	
	best_voices = {}
	
	def get_priority(voice) -> tuple:
		name = voice.name
		if "Polyglot" in name:
			name_rank = 1
		elif "Wavenet" in name:
			name_rank = 2
		elif "Standard" in name:
			name_rank = 3
		else:
			name_rank = 4
		
		gender_priority = 0 if voice.ssml_gender.name.upper() == "FEMALE" else 1
		
		return (name_rank, gender_priority)
	
	for voice in voices_response.voices:
		for lang in voice.language_codes:
			if lang not in best_voices:
				best_voices[lang] = voice
			else:
				if get_priority(voice) < get_priority(best_voices[lang]):
					best_voices[lang] = voice
	
	final_response = {}
	for lang, voice in best_voices.items():
		final_response[lang] = voice.name
	
	return final_response


def text_to_speach(text: str, language_code: str, voice_name: str) -> str:
	"""
	This function uses the Google Cloud Text-to-Speech API to convert the text
	to speech.
	
	It takes as input these parameters:
	- text: The text that should be converted to speech.
	- language_code: The language of the text, e.g. "en-US", "ro-RO".
	- voice_name: The name of the voice that should be used to convert the text
	to speech. For example: "en-US-Polyglot-1" or "ro-RO-Wavenet-A"
	
	Returns the link to the audio file that contains the speech in mp3 format
	and in the language specified.
	"""
	try:
		client = texttospeech.TextToSpeechClient()
		input_text = texttospeech.SynthesisInput({"text": text})
		voice = texttospeech.VoiceSelectionParams(
			{"language_code": language_code, "name": voice_name}
		)
		
		audio_config = texttospeech.AudioConfig(
			{"audio_encoding": texttospeech.AudioEncoding.OGG_OPUS}
		)
		
		response = client.synthesize_speech(
			request={
				"input": input_text, "voice": voice, "audio_config": audio_config
			}
		)
		
		return upload_resp_file_content_to_bucket(
			resp_file_content=response.audio_content,
			filename=random_name_generator() + ".ogg",
			content_type="audio/ogg"
		)
	except Exception as e:
		logger.error(f"Error in text_to_speach: {e}")
		return "Could not convert the text to speech."
		

def speech_to_text(language_code: str, media_file_link: str) -> str:
	"""
	This function uses the Google Cloud Speech-to-Text API to convert the audio
	file to text.
	
	It takes as input these parameters:
	- language_code: The language of the audio file, e.g. "en-US", "ro-RO".
	- media_file_link: The link to the audio file that should be processed.
	
	It returns the text transcription of the audio file.
	If the audio file could not be processed, it returns an empty string.
	"""
	if not media_file_link.endswith(".flac"):
		# this should be flac because of the `process_media_url` function
		return "Could not recognize the audio."
	
	audio_url = media_file_link.replace(BUKET_BASE_URL, BUKET_GCP_URL)
	
	client = speech.SpeechClient()
	
	config = speech.RecognitionConfig(
		{
			"language_code": language_code,
			"encoding": speech.RecognitionConfig.AudioEncoding.FLAC
		}
	)
	audio = speech.RecognitionAudio({"uri": audio_url})
	
	response = client.recognize(config=config, audio=audio)
	resp = ""
	for result in response.results:
		best_alternative = result.alternatives[0]
		resp += best_alternative.transcript
		resp += "\n"
	if resp:
		return resp[:-2]
	return ""
