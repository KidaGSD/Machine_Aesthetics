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
        
        # Handle different transformers versions
        try:
            self.model = EmotionModel.from_pretrained(self.model_name)
        except NameError as e:
            if "init_empty_weights" in str(e):
                # For newer versions of transformers
                # Use different approach with no_init_weights context manager
                from transformers.modeling_utils import no_init_weights
                with no_init_weights():
                    self.model = EmotionModel.from_pretrained(self.model_name)
            else:
                # Fallback to using a simple workaround - load without custom class
                from transformers import AutoModel
                print("Using fallback model loading...")
                self.model = AutoModel.from_pretrained(self.model_name)
        
        self.model.to(self.device)
        self.model.eval()


    def __call__(self, audio_data: np.ndarray, sampling_rate:int, embeddings: bool = False) -> dict:
        self.ensure_model()
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


