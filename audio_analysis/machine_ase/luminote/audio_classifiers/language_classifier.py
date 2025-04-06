from transformers import Wav2Vec2ForSequenceClassification, AutoFeatureExtractor
import torch
from . import language_codes
import librosa
import numpy as np

class LanguageClassifier:
    def __init__(self, device: torch.device):
        self.device = device
        self.model_id = "facebook/mms-lid-256"
        self.processor : AutoFeatureExtractor = None
        self.model : Wav2Vec2ForSequenceClassification = None

        self.language_names = {}
        

    def ensure_model(self):
        if self.processor is not None and self.model is not None:
            return
        
        self.processor = AutoFeatureExtractor.from_pretrained(self.model_id)
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(self.model_id)
        self.model.to(self.device)
        self.model.eval()

        for id in self.model.config.id2label.keys():
            code = self.model.config.id2label[int(id)]
            self.language_names[int(id)] = f'{code}:{language_codes.get_language_name(code)}'


    def __call__(self, audio_data: np.ndarray, sampling_rate:int, top_n:int) -> list[(str, int, float)]:
        self.ensure_model()
        trg_sampling_rate = self.processor.sampling_rate

        if sampling_rate != trg_sampling_rate:        
            audio_data = librosa.resample(audio_data, orig_sr=sampling_rate, target_sr=trg_sampling_rate)

        inputs = self.processor(audio_data, sampling_rate=trg_sampling_rate, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits

            #get softmax
            logits = torch.nn.functional.softmax(logits, dim=-1)* 100.0
            # Get the top_n predicted language IDs
            predicted_ids = torch.topk(logits, top_n).indices[0].tolist()
        
        result = []
        #print(f"Predicted language ID")
        for id in predicted_ids:
            logit = logits[0][id].item()
            label = self.language_names[id]
        #    print(f"{id}, {label} : {logit:.2f}%")
            result.append((label, id, logit))

        #print("__")

        return result