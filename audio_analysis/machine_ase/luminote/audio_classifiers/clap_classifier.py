from transformers import  AutoTokenizer, ClapModel, ClapProcessor
import torch
import librosa
import numpy as np

class ClapClassifier:
    def __init__(self, device: torch.device, labels: list[str] = None):
        self.device = device
        self.model_id = "laion/clap-htsat-unfused"
        self.processor: ClapProcessor = None
        self.model: ClapModel = None

        self.tokenizer : AutoTokenizer = None #AutoTokenizer.from_pretrained(self.model_id)

        self.labels : list[str] = []
        self.label_vec : torch.Tensor = None

        if labels is not None:
            self.labels = labels

    def ensure_model(self):
        if self.processor is not None and self.model is not None:
            return
        
        self.tokenizer  = AutoTokenizer.from_pretrained(self.model_id)
        self.processor = ClapProcessor.from_pretrained(self.model_id)
        self.model = ClapModel.from_pretrained(self.model_id)
        self.model.to(self.device)
        self.model.eval()

        if len(self.labels) > 0:
            self.label_vec = self.encode_text(self.labels)



    def encode_text(self, text: str) -> torch.Tensor:
        self.ensure_model()
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        return self.model.get_text_features(**inputs)
    
    def encode_audio(self, audio_data: np.ndarray, sampling_rate:int) -> torch.Tensor:       
        self.ensure_model()
        trg_sampling_rate = self.processor.feature_extractor.sampling_rate

        if sampling_rate != trg_sampling_rate:
            audio_data = librosa.resample(audio_data, orig_sr=sampling_rate, target_sr=trg_sampling_rate)
 
        inputs = self.processor(audios = audio_data, sampling_rate=trg_sampling_rate, return_tensors="pt", padding=True).to(self.device)
        return self.model.get_audio_features(**inputs)
    
    def __call__(self, audio_data: np.ndarray, sampling_rate:int) -> torch.Tensor:
        audio_features = self.encode_audio(audio_data, sampling_rate)
        sim =  audio_features @ self.label_vec.T
        sim = sim[0]

        result = {}
        for i, label in enumerate(self.labels):
            result[label] = sim[i].item()

        return result
