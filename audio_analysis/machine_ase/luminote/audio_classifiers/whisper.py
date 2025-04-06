import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import librosa
import numpy as np

class Whisper:
    def __init__(self, device: torch.device, model_id: str = "openai/whisper-large-v3-turbo"):
        self.device = device
        self.model_id = model_id
        
        self.processor: AutoProcessor = None
        self.model: AutoModelForSpeechSeq2Seq = None
        self.pipeline = None
        self.dtype = torch.float32# torch.float16 if self.device.type == 'cuda' else torch.float32
        
        self.ensure_model()

    def ensure_model(self):
        if self.processor is not None and self.model is not None:
            return
        
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(self.model_id, torch_dtype=self.dtype, low_cpu_mem_usage=True, use_safetensors=True)
        self.model.to(self.device)
        self.model.eval()

        self.pipeline = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=self.dtype,
            device=self.device,
        )

    def __call__(self, audio_data: np.ndarray, sampling_rate: int) -> str:
        self.ensure_model()
        
        # # Resample if necessary
        trg_sampling_rate = 16000  # Whisper expects 16kHz
        if sampling_rate != trg_sampling_rate:
            audio_data = librosa.resample(audio_data, orig_sr=sampling_rate, target_sr=trg_sampling_rate)

        # inputs = self.processor(audio_data, sampling_rate=trg_sampling_rate, return_tensors="pt").to(self.device)
        
        # with torch.no_grad():
        #     logits = self.model(**inputs).logits
        
        # predicted_ids = torch.argmax(logits, dim=-1)
        
        # transcription = self.processor.batch_decode(predicted_ids)[0]

        transcription = self.pipeline(audio_data)['text']
        
        return transcription