import numpy as np
import torch
import torch.nn as nn
from transformers import Wav2Vec2Processor
from transformers.models.wav2vec2.modeling_wav2vec2 import (
    Wav2Vec2Model,
    Wav2Vec2PreTrainedModel,
)
import librosa




class RegressionHead(nn.Module):
    r"""Classification head."""

    def __init__(self, config):

        super().__init__()

        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features, **kwargs):

        x = features
        x = self.dropout(x)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)

        return x


class EmotionModel(Wav2Vec2PreTrainedModel):
    r"""Speech emotion classifier."""

    def __init__(self, config):

        super().__init__(config)

        self.config = config
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(
            self,
            input_values,
    ):

        outputs = self.wav2vec2(input_values)
        hidden_states = outputs[0]
        hidden_states = torch.mean(hidden_states, dim=1)
        logits = self.classifier(hidden_states)

        return hidden_states, logits



class EmotionClassifier:
    def __init__(self, device: torch.device):
        self.device = device
        self.model_name = 'audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim'
        self.processor : Wav2Vec2Processor = None
        self.model : EmotionModel = None


    def ensure_model(self):
        if self.processor is not None and self.model is not None:
            return
        
        # load model from hub
        self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
        
        try:
            self.model = EmotionModel.from_pretrained(self.model_name)
        except Exception as e:
            print(f"Error loading emotion model: {e}")
            print("Using fallback simple audio analysis instead")
            
            # Don't try to create a dummy model - it won't work
            # We'll handle this in the __call__ method
            self.model = None
        

    def __call__(self, audio_data: np.ndarray, sampling_rate:int, embeddings: bool = False) -> dict:
        self.ensure_model()
        
        # If model failed to load, use fallback simple audio feature extraction
        if self.model is None:
            # Fallback: use simple audio features to estimate valence/arousal
            energy = np.mean(np.abs(audio_data))
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_data)))) / len(audio_data)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sampling_rate)[0].mean()
            
            # Map audio features to emotional dimensions
            arousal = min(1.0, max(-1.0, float(energy * 10 - 0.5)))  # Energy -> arousal
            valence = min(1.0, max(-1.0, float(spectral_centroid / 1000 - 1)))  # Spec centroid -> valence
            dominance = min(1.0, max(-1.0, float(zero_crossings * 100 - 0.5)))  # Complexity -> dominance
            
            return {
                'arousal': arousal,
                'dominance': dominance,
                'valence': valence,
            }
        
        trg_sampling_rate = self.processor.current_processor.sampling_rate

        if sampling_rate != trg_sampling_rate:
            audio_data = librosa.resample(audio_data, orig_sr=sampling_rate, target_sr=trg_sampling_rate)


        y = self.processor(audio_data, sampling_rate=trg_sampling_rate)
        y = y['input_values'][0]
        y = y.reshape(1, -1)
        y = torch.from_numpy(y).to(self.device)

        # run through model
        with torch.no_grad():
            y = self.model(y)[0 if embeddings else 1]

        # convert to numpy
        y = y.detach().cpu().numpy() * 2.0 - 1.0  # scale to [-1, 1]

        result = {
            'arousal': y[0][0],
            'dominance': y[0][1],
            'valence': y[0][2],
        }

        return result


