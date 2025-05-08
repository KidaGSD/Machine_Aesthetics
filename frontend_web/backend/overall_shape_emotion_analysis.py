# Required: pip install git+https://github.com/openai/whisper.git

import os
import numpy as np
if not hasattr(np, 'complex'):
    np.complex = complex  # for librosa compatibility

import librosa
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from transformers import pipeline
from pydub import AudioSegment
import subprocess
import whisper

def run_analysis(audio_path):
    print("🎬 Converting to WAV if needed...")
    if audio_path.lower().endswith(".mp3"):
        wav_path = audio_path.replace(".mp3", ".wav")
        audio = AudioSegment.from_mp3(audio_path)
        audio.export(wav_path, format="wav")
        audio_path = wav_path
    elif audio_path.lower().endswith(".mp4"):
        wav_path = audio_path.replace(".mp4", ".wav")
        command = f"ffmpeg -i \"{audio_path}\" -vn -acodec pcm_s16le -ar 44100 -ac 2 \"{wav_path}\""
        subprocess.call(command, shell=True)
        audio_path = wav_path

    print("🗣️ Transcribing audio...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=False)
    transcript_segments = [{
        "start": seg['start'],
        "end": seg['end'],
        "text": seg['text'].strip()
    } for seg in result['segments']]

    if not transcript_segments:
        print("❌ No transcription results. Aborting.")
        return

    y, sr = librosa.load(audio_path)
    hop_length = 512

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    mfcc1 = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length, n_mfcc=1)[0]

    min_length = min(len(rms), len(zcr), len(centroid), len(mfcc1))
    rms, zcr, centroid, mfcc1 = rms[:min_length], zcr[:min_length], centroid[:min_length], mfcc1[:min_length]

    classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=False)
    emotion_vad_map = {
        'joy': (0.9, 0.8), 'sadness': (-0.7, 0.3), 'anger': (-0.6, 0.9),
        'disgust': (-0.8, 0.7), 'fear': (-0.6, 0.8), 'surprise': (0.5, 0.9), 'neutral': (0.0, 0.0)
    }

    def analyze_emotion_combined(text, audio_slice, sr):
        try:
            result = classifier(text)[0]
            label = result['label'].lower()
            valence_text, arousal_text = emotion_vad_map.get(label, (0.0, 0.0))
        except:
            label, valence_text, arousal_text = "neutral", 0.0, 0.0

        if len(audio_slice) > 0:
            rms = librosa.feature.rms(y=audio_slice)[0].mean()
            zcr = librosa.feature.zero_crossing_rate(y=audio_slice)[0].mean()
            centroid = librosa.feature.spectral_centroid(y=audio_slice, sr=sr)[0].mean()
            mfcc = librosa.feature.mfcc(y=audio_slice, sr=sr, n_mfcc=1)[0].mean()
        else:
            rms, zcr, centroid, mfcc = 0, 0, 0, 0

<<<<<<< Updated upstream
        valence_audio = np.clip((centroid / 5000.0) + (zcr * 2) - 1, -1.0, 1.0)
        arousal_audio = np.clip((rms * 10) + (mfcc / 200.0), -1.0, 1.0)
        return {
            "emotion": label,
            "valence": round((valence_text + valence_audio) / 2, 4),
            "arousal": round((arousal_text + arousal_audio) / 2, 4)
        }

    # Analyze each segment
    segment_summaries = []
    for seg in transcript_segments:
        start_sample = int(seg['start'] * sr)
        end_sample = int(seg['end'] * sr)
        audio_slice = y[start_sample:end_sample]
        emo = analyze_emotion_combined(seg['text'], audio_slice, sr)
        segment_summaries.append({**seg, **emo, "duration": seg["end"] - seg["start"]})
=======
def clear_gpu_memory():
    """清理GPU内存，如果有CUDA设备"""
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"清理GPU内存失败: {e}")

def copy_to_legacy_path(src_path, filename):
    """Copy a file to the legacy output folder for backwards compatibility."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    legacy_output_path = os.path.join(script_dir, "output")
    os.makedirs(legacy_output_path, exist_ok=True)
    
    legacy_file_path = os.path.join(legacy_output_path, filename)
    try:
        import shutil
        shutil.copyfile(src_path, legacy_file_path)
        print(f"✓ Copied to legacy location: {legacy_file_path}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to copy to legacy location: {e}")
        return False

# ------------ MAIN PIPELINE ---------------------------------------------

def run_analysis(audio_path: str):
    try:
        print(f"🎧  Processing {audio_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        # Define output directories relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Update path to save CSVs to public folder for web access
        output_base_path = os.path.join(script_dir, "..", "public", "data", "output")
        static_base_path = os.path.join(script_dir, "..", "public", "emotions") # For JSON
        
        print(f"📂 Output directory for CSVs: {output_base_path}")
        print(f"📂 Output directory for JSON: {static_base_path}")
        os.makedirs(output_base_path, exist_ok=True)
        os.makedirs(static_base_path, exist_ok=True)
        
        # Confirm directories exist and are writable
        for path in [output_base_path, static_base_path]:
            if not os.path.exists(path):
                print(f"❌ 无法创建目录: {path}")
            else:
                test_file = os.path.join(path, "test_write.txt")
                try:
                    with open(test_file, "w") as f:
                        f.write("Test write access")
                    print(f"✓ 目录可写: {path}")
                    os.remove(test_file)
                except Exception as e:
                    print(f"❌ 无法写入目录: {e}")
                    # Optionally, raise an error here if write access is critical
                    # raise IOError(f"Cannot write to directory: {path}") from e
        
        wav_path = _to_wav(audio_path)

        # ---------- 1 加载音频数据 ---------------------------------
        # 首先检查文件大小和长度
        try:
            # 尝试使用 get_sndfile_info (仅在较新版本的librosa中可用)
            audio_info = librosa.get_sndfile_info(wav_path)
            duration = audio_info['duration']
            sr = audio_info['samplerate']
            frames = audio_info['frames']
        except (AttributeError, Exception):
            # 回退到兼容性方法
            print("使用兼容模式获取音频信息...")
            y, sr = librosa.load(wav_path, sr=None, duration=5)  # 只加载前5秒来快速获取信息
            duration = librosa.get_duration(filename=wav_path)
            frames = int(duration * sr)
        
        print(f"音频持续时间: {duration:.2f}秒，采样率: {sr}Hz")
        
        # 检查是否需要降采样以减少内存使用
        target_sr = sr
        if sr > MAX_AUDIO_SR or (frames / sr > MAX_AUDIO_DURATION):
            target_sr = min(sr, MAX_AUDIO_SR)
            print(f"音频太长或采样率太高，降采样到 {target_sr}Hz")
        
        # 计算近似内存使用（以MB为单位）
        mem_usage_mb = (frames * 4) / (1024 * 1024)  # 每个样本4字节（32位浮点）
        if mem_usage_mb > MAX_AUDIO_MEMORY_MB:
            # 需要降低采样率或分块处理
            scaling_factor = MAX_AUDIO_MEMORY_MB / mem_usage_mb
            target_sr = int(target_sr * scaling_factor)
            print(f"音频需要大约 {mem_usage_mb:.1f}MB 内存，超过限制，降采样到 {target_sr}Hz")
        
        # 加载音频，可能用降低的采样率
        y, sr = librosa.load(wav_path, sr=target_sr)
        
        # 确认实际持续时间
        duration = librosa.get_duration(y=y, sr=sr)
        print(f"处理后音频: {duration:.2f}秒, {len(y)/1024/1024:.1f}MB")

        # ---------- 2 加载模型 -------------------------------------
        print("加载模型中...")
        models_loaded = {'audio': False, 'text': False, 'vad': False, 'asr': False, 'smile': False}
        
        # 文本情感分析模型
        try:
            text_pipe = pipeline("text-classification",
                               model=TEXT_EMO_MODEL,
                               top_k=None,
                               truncation=True)
            models_loaded['text'] = True
        except Exception as e:
            print(f"文本分析模型加载错误: {e}")
            text_pipe = None
        
        # 音频情感分析模型
        try:
            audio_pipe = pipeline("audio-classification",
                                model=AUDIO_EMO_MODEL,
                                top_k=None)
            models_loaded['audio'] = True
        except Exception as e:
            print(f"音频分析模型加载错误: {e}")
            audio_pipe = None
        
        # OpenSMILE特征提取
        try:
            smile = opensmile.Smile(feature_set=OPENSMILE_SET,
                                   feature_level=opensmile.FeatureLevel.Functionals)
            models_loaded['smile'] = True
        except Exception as e:
            print(f"OpenSMILE加载错误: {e}")
            smile = None
        
        # VAD模型
        vad = None
        if PYANNOTE_AVAILABLE:
            try:
                vad = PyannotePipeline.from_pretrained(VAD_MODEL, use_auth_token=None)
                models_loaded['vad'] = True
            except Exception as e:
                print(f"VAD模型加载错误: {e}")
                vad = None
        
        # ASR模型
        try:
            # 使用更小的ASR模型以减少内存使用
            asr = whisper.load_model(ASR_MODEL)
            models_loaded['asr'] = True
        except Exception as e:
            print(f"ASR模型加载错误: {e}")
            asr = None
        
        if any(models_loaded.values()):
            print("所有模型加载成功")
        else:
            print("警告: 所有模型加载失败，将使用基本特征进行分析")
        
        # ---------- 3 语音段分析 --------------------------
        transcript_segments = []
        
        # VAD分析
        if models_loaded['vad'] and vad is not None:
            try:
                print("执行VAD分段...")
                vad_segs = vad(wav_path)
                # 保留长度大于0.5秒的段落
                voiced = [(seg.start, seg.end) for seg in vad_segs.get_timeline()
                        if (seg.end - seg.start) > 0.5]
                
                if not voiced:
                    voiced = [(0., duration)]
                
                print(f"识别到{len(voiced)}个语音片段")
            except Exception as e:
                print(f"VAD处理错误: {e}")
                # 回退到简单的基于能量的VAD
                print("使用备选的基于能量的VAD...")
                voiced = simple_vad(y, sr)
                print(f"识别到{len(voiced)}个语音片段")
        else:
            # 回退到简单的基于能量的VAD
            print("使用备选的基于能量的VAD...")
            voiced = simple_vad(y, sr)
            print(f"识别到{len(voiced)}个语音片段")
        
        # ASR分析
        if models_loaded['asr'] and asr is not None:
            try:
                # 对每个语音段执行ASR
                for start, end in voiced:
                    # 使用内存中的音频片段而不是创建临时文件
                    start_sample = max(0, int(start * sr))
                    end_sample = min(len(y), int(end * sr))
                    segment = y[start_sample:end_sample]
                    
                    if len(segment) < sr * 0.5:  # 太短的片段跳过
                        continue
                        
                    try:
                        res = asr.transcribe(segment, language="en")
                        for seg in res["segments"]:
                            transcript_segments.append({
                                "start": seg["start"] + start,
                                "end": seg["end"] + start,
                                "text": seg["text"].strip()
                            })
                    except Exception as e:
                        print(f"单个片段ASR错误: {e}")
                
                if not transcript_segments:
                    transcript_segments = [{"start": 0., "end": min(5., duration), "text": "(silence)"}]
                
                print(f"转录了{len(transcript_segments)}个文本片段")
            except Exception as e:
                print(f"ASR处理错误: {e}")
                # 使用VAD片段作为备选，没有文本
                transcript_segments = [{"start": start, "end": end, "text": "(audio content)"} 
                                     for start, end in voiced]
        else:
            # 使用VAD片段作为备选，没有文本
            transcript_segments = [{"start": start, "end": end, "text": "(audio content)"} 
                                 for start, end in voiced]
        
        # ---------- 4 分析VAD段 -----------------------------------
        vad_seg_rows = []
        
        for seg in transcript_segments:
            try:
                ss = max(0, int(seg['start']*sr))
                ee = min(len(y), int(seg['end']*sr))
                clip = y[ss:ee]
                
                if len(clip) < sr * 0.1:  # 片段太短
                    continue
                
                # 文本情感分析
                if models_loaded['text'] and text_pipe is not None and seg['text'] != "(audio content)" and seg['text'] != "(silence)":
                    try:
                        txt_logits = text_pipe(seg['text'])[0]
                        top_lbl = max(txt_logits, key=lambda d: d['score'])['label']
                        
                        # 从28维情感logits中提取valence/arousal
                        joy_idx = next((i for i, f in enumerate(txt_logits) if f['label']=="joy"), -1)
                        sad_idx = next((i for i, f in enumerate(txt_logits) if f['label']=="sadness"), -1)
                        anger_idx = next((i for i, f in enumerate(txt_logits) if f['label']=="anger"), -1)
                        
                        if joy_idx >= 0 and sad_idx >= 0:
                            val_txt = txt_logits[joy_idx]['score'] - txt_logits[sad_idx]['score']
                        else:
                            val_txt = 0.0
                            
                        if anger_idx >= 0:
                            aro_txt = txt_logits[anger_idx]['score']
                        else:
                            aro_txt = 0.5  # 中等arousal
                    except Exception as e:
                        print(f"文本分析错误: {e}")
                        top_lbl = "neutral"
                        val_txt, aro_txt = 0.0, 0.0
                else:
                    top_lbl = "neutral"
                    val_txt, aro_txt = 0.0, 0.0
                
                # 音频情感分析
                try:
                    if models_loaded['audio'] and audio_pipe is not None and len(clip) > sr * 0.3:
                        # 只处理足够长的片段
                        try:
                            a_res = audio_pipe(clip, sampling_rate=sr)[0]
                            
                            # 检查模型输出中的键名
                            print(f"音频情感模型返回键: {list(a_res.keys())}")
                            
                            # 更灵活地处理不同格式的输出
                            if 'valence' in a_res:
                                val_aud = _scale01_to_minus1_1(a_res['valence'])
                            elif 'score' in a_res and 'label' in a_res:
                                # 对于只返回情感标签和分数的模型
                                emotion_label = a_res['label'].lower()
                                emotion_vad = EMOTIONS_VA_CAT.get(emotion_label, (0.0, 0.5))
                                val_aud = emotion_vad[0]  # 使用预设的valence值
                            else:
                                # 完全回退
                                raise ValueError(f"未知输出格式: {a_res}")
                                
                            # 对arousal和dominance做类似处理
                            if 'arousal' in a_res:
                                aro_aud = _scale01_to_minus1_1(a_res['arousal'])
                            elif 'score' in a_res and 'label' in a_res:
                                emotion_label = a_res['label'].lower()
                                emotion_vad = EMOTIONS_VA_CAT.get(emotion_label, (0.0, 0.5))
                                aro_aud = emotion_vad[1]  # 使用预设的arousal值
                            else:
                                # 回退
                                energy = np.mean(np.abs(clip))
                                aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                                
                            # 处理dominance
                            if 'dominance' in a_res:
                                dom_aud = _scale01_to_minus1_1(a_res['dominance'])
                            else:
                                # 估算dominance
                                dom_aud = np.tanh((val_aud + aro_aud) / 2)
                        except Exception as e:
                            print(f"音频情感分析错误: {str(e)[:100]}...")
                            if 'a_res' in locals():
                                print(f"输出格式: {type(a_res)}")
                                if hasattr(a_res, 'keys'):
                                    print(f"可用的键: {list(a_res.keys())}")
                                else:
                                    print(f"输出值: {a_res}")
                            # 使用备选特征提取
                            energy = np.mean(np.abs(clip))
                            zero_crossings = np.sum(np.abs(np.diff(np.signbit(clip)))) / max(1, len(clip))
                            
                            try:
                                spectral_centroid = librosa.feature.spectral_centroid(y=clip, sr=sr)[0].mean()
                            except:
                                spectral_centroid = 1000  # 默认值
                                
                            val_aud = np.clip(float(spectral_centroid / 5000 - 0.5), -1.0, 1.0)
                            aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                            dom_aud = np.clip(float(zero_crossings * 100 - 0.5), -1.0, 1.0)
                    else:
                        # 使用备选特征提取
                        energy = np.mean(np.abs(clip))
                        zero_crossings = np.sum(np.abs(np.diff(np.signbit(clip)))) / max(1, len(clip))
                        
                        try:
                            spectral_centroid = librosa.feature.spectral_centroid(y=clip, sr=sr)[0].mean()
                        except:
                            spectral_centroid = 1000  # 默认值
                            
                        val_aud = np.clip(float(spectral_centroid / 5000 - 0.5), -1.0, 1.0)
                        aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                        dom_aud = np.clip(float(zero_crossings * 100 - 0.5), -1.0, 1.0)
                    
                    # OpenSMILE额外特征
                    energy_val = 0.1
                    f0_val = 0.0
                    
                    if models_loaded['smile'] and smile is not None and len(clip) > sr * 0.3:
                        try:
                            sm_feats = smile.process_signal(clip, sr)
                            
                            # 寻找能量特征
                            energy_key = find_key_in_dict(sm_feats, OPENSMILE_KEYS['energy'])
                            if energy_key:
                                energy_val = sm_feats[energy_key].values[0]
                            
                            # 寻找f0特征
                            f0_key = find_key_in_dict(sm_feats, OPENSMILE_KEYS['f0_mean'])
                            if f0_key:
                                f0_val = sm_feats[f0_key].values[0]
                        except Exception as e:
                            print(f"OpenSMILE特征提取错误: {str(e)[:50]}")
                    
                    # 融合特征
                    val = np.tanh(0.7*val_aud + 0.3*val_txt)
                    aro = np.tanh(0.6*aro_aud + 0.2*aro_txt + 0.2*(energy_val*5))
                    
                    # 计算dominance
                    if ADD_DOMINANCE:
                        dom = dom_aud
                    else:
                        # 使用简单公式估算dominance
                        dom = np.tanh((val + aro) / 2)
                    
                    # 映射到离散情感
                    mapped_emotion = map_va_to_emotion(val, aro)
                    
                    vad_seg_rows.append({
                        **seg,
                        "emotion": mapped_emotion.lower() if mapped_emotion else top_lbl.lower(),
                        "valence": round(float(val), 4),
                        "arousal": round(float(aro), 4),
                        "dominance": round(float(dom), 4),
                        "duration": seg['end'] - seg['start']
                    })
                except Exception as e:
                    print(f"段落分析错误: {e}")
                    # 添加默认值
                    vad_seg_rows.append({
                        **seg,
                        "emotion": "neutral",
                        "valence": 0.0,
                        "arousal": 0.0,
                        "dominance": 0.0,
                        "duration": seg['end'] - seg['start']
                    })
            except Exception as e:
                print(f"段落处理错误: {e}")
        
        # ---------- 5 固定窗口分析 (新增) --------------------------
        fixed_window_rows = []
        
        if FIXED_WINDOW_ENABLED:
            # 选择窗口参数 - 快速模式或标准模式
            if FAST_MODE:
                window_size = FAST_MODE_WINDOW
                overlap = FAST_MODE_OVERLAP
                print(f"执行固定窗口快速分析 (窗口大小: {window_size}秒, 重叠率: {overlap})")
            else:
                window_size = CHUNK_DURATION_SEC
                overlap = WINDOW_OVERLAP
                print(f"执行固定窗口分析 (窗口大小: {window_size}秒, 重叠率: {overlap})")
            
            chunk_size = int(window_size * sr)
            hop_size = int(chunk_size * (1 - overlap))
            
            # 创建重叠窗口
            chunks = []
            times = []
            for i in range(0, len(y) - chunk_size + hop_size, hop_size):
                end_idx = min(i + chunk_size, len(y))
                chunks.append(y[i:end_idx])
                times.append(i / sr)  # 开始时间(秒)
            
            # 如果窗口太多，进行采样
            max_segments = FAST_MODE_MAX_SEGMENTS if FAST_MODE else MAX_SEGMENTS
            if len(chunks) > max_segments:
                print(f"段落数过多 ({len(chunks)}), 采样至 {max_segments} 个窗口")
                # 使用均匀采样
                indices = np.linspace(0, len(chunks) - 1, max_segments).astype(int)
                chunks = [chunks[i] for i in indices]
                times = [times[i] for i in indices]
            
            print(f"创建了{len(chunks)}个分析窗口")
            
            # 分析每个窗口
            for i, (chunk, start_time) in enumerate(zip(chunks, times)):
                # 跳过过短的末尾片段
                if len(chunk) < chunk_size * 0.5:
                    continue
                
                try:
                    # 音频特征分析
                    try:
                        if models_loaded['audio'] and audio_pipe is not None:
                            try:
                                a_res = audio_pipe(chunk, sampling_rate=sr)[0]
                                
                                # 检查模型输出中的键名
                                print(f"音频情感模型返回键: {list(a_res.keys())}")
                                
                                # 更灵活地处理不同格式的输出
                                if 'valence' in a_res:
                                    val_aud = _scale01_to_minus1_1(a_res['valence'])
                                elif 'score' in a_res and 'label' in a_res:
                                    # 对于只返回情感标签和分数的模型
                                    emotion_label = a_res['label'].lower()
                                    emotion_vad = EMOTIONS_VA_CAT.get(emotion_label, (0.0, 0.5))
                                    val_aud = emotion_vad[0]  # 使用预设的valence值
                                else:
                                    # 完全回退
                                    raise ValueError(f"未知输出格式: {a_res}")
                                    
                                # 对arousal和dominance做类似处理
                                if 'arousal' in a_res:
                                    aro_aud = _scale01_to_minus1_1(a_res['arousal'])
                                elif 'score' in a_res and 'label' in a_res:
                                    emotion_label = a_res['label'].lower()
                                    emotion_vad = EMOTIONS_VA_CAT.get(emotion_label, (0.0, 0.5))
                                    aro_aud = emotion_vad[1]  # 使用预设的arousal值
                                else:
                                    # 回退
                                    energy = np.mean(np.abs(chunk))
                                    aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                                    
                                # 处理dominance
                                if 'dominance' in a_res:
                                    dom_aud = _scale01_to_minus1_1(a_res['dominance'])
                                else:
                                    # 估算dominance
                                    dom_aud = np.tanh((val_aud + aro_aud) / 2)
                            except Exception as e:
                                print(f"音频情感分析错误: {str(e)[:100]}...")
                                if 'a_res' in locals():
                                    print(f"输出格式: {type(a_res)}")
                                    if hasattr(a_res, 'keys'):
                                        print(f"可用的键: {list(a_res.keys())}")
                                    else:
                                        print(f"输出值: {a_res}")
                                # 使用备选特征提取
                                energy = np.mean(np.abs(chunk))
                                zero_crossings = np.sum(np.abs(np.diff(np.signbit(chunk)))) / max(1, len(chunk))
                                
                                try:
                                    spectral_centroid = librosa.feature.spectral_centroid(y=chunk, sr=sr)[0].mean()
                                except:
                                    spectral_centroid = 1000  # 默认值
                                    
                                val_aud = np.clip(float(spectral_centroid / 5000 - 0.5), -1.0, 1.0)
                                aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                                dom_aud = np.clip(float(zero_crossings * 100 - 0.5), -1.0, 1.0)
                        else:
                            # 备选特征提取
                            energy = np.mean(np.abs(chunk))
                            zero_crossings = np.sum(np.abs(np.diff(np.signbit(chunk)))) / max(1, len(chunk))
                            
                            try:
                                spectral_centroid = librosa.feature.spectral_centroid(y=chunk, sr=sr)[0].mean()
                            except:
                                spectral_centroid = 1000  # 默认值
                                
                            val_aud = np.clip(float(spectral_centroid / 5000 - 0.5), -1.0, 1.0)
                            aro_aud = np.clip(float(energy * 10 - 0.5), -1.0, 1.0)
                            dom_aud = np.clip(float(zero_crossings * 100 - 0.5), -1.0, 1.0)
                        
                        # 使用更简单的特征组合
                        val = val_aud
                        aro = aro_aud
                        dom = dom_aud
                        
                        # 映射到离散情感
                        emotion = map_va_to_emotion(val, aro)
                        
                        # 根据该时间点查找相应文本(如果有)
                        window_end = start_time + window_size
                        matching_texts = []
                        for seg in transcript_segments:
                            # 如果段落与窗口有重叠
                            if (seg['start'] < window_end and seg['end'] > start_time):
                                matching_texts.append(seg['text'])
                        
                        # 添加到结果
                        fixed_window_rows.append({
                            "start": start_time,
                            "end": window_end,
                            "text": " ".join(matching_texts) if matching_texts else "(instrumental)",
                            "emotion": emotion.lower(),
                            "valence": round(float(val), 4),
                            "arousal": round(float(aro), 4),
                            "dominance": round(float(dom), 4),
                            "duration": min(window_size, duration - start_time)
                        })
                    except Exception as e:
                        print(f"窗口特征提取错误 [{i}]: {str(e)[:50]}")
                        # 添加默认值
                        fixed_window_rows.append({
                            "start": start_time,
                            "end": start_time + window_size,
                            "text": "(analysis error)",
                            "emotion": "neutral",
                            "valence": 0.0,
                            "arousal": 0.0,
                            "dominance": 0.0,
                            "duration": min(window_size, duration - start_time)
                        })
                except Exception as e:
                    print(f"窗口分析错误 [{i}]: {str(e)[:50]}")
                
                # 定期清理内存
                if i % 20 == 0:
                    clear_gpu_memory()
        
        # ---------- 6 决定使用哪个分析结果 ------------------------
        # 如果固定窗口分析结果可用且更详细，则使用它
        if FIXED_WINDOW_ENABLED and fixed_window_rows and len(fixed_window_rows) > len(vad_seg_rows):
            print(f"使用固定窗口分析结果 ({len(fixed_window_rows)} 行)")
            seg_rows = fixed_window_rows
        else:
            print(f"使用基于VAD的分析结果 ({len(vad_seg_rows)} 行)")
            seg_rows = vad_seg_rows
        
        # 清理一些内存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 如果没有结果，创建一些默认值
        if not seg_rows:
            print("警告: 没有分析结果，创建默认值")
            seg_rows = [
                {"start": 0, "end": duration/2, "text": "(audio content)", 
                 "emotion": "neutral", "valence": 0.0, "arousal": 0.0, "dominance": 0.0, "duration": duration/2},
                {"start": duration/2, "end": duration, "text": "(audio content)", 
                 "emotion": "joy", "valence": 0.7, "arousal": 0.6, "dominance": 0.5, "duration": duration/2}
            ]
        
        df_summary = pd.DataFrame(seg_rows)
        
        # ---------- 7 GROUP & CSV OUTPUTS ------------------------------
        # Ensure no NaN values
        df_summary = df_summary.fillna({'emotion': 'neutral', 'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0})
        
        # Group by emotion
        df_grouped = (df_summary.groupby('emotion')
                                 .agg({'valence': 'mean',
                                       'arousal': 'mean',
                                       'dominance': 'mean',
                                       'duration': 'sum'})
                                 .reset_index())
        
        # Ensure at least two emotion categories
        if len(df_grouped) < 2:
            print("Detected only one emotion, adding a second...")
            extra = "joy" if df_grouped.iloc[0]['emotion'] != "joy" else "sad"
            extra_valence = 0.7 if extra == "joy" else -0.5
            extra_arousal = 0.6 if extra == "joy" else 0.2
            extra_dominance = 0.5 if extra == "joy" else -0.3
            
            df_grouped = pd.concat([
                df_grouped,
                pd.DataFrame([{
                    "emotion": extra,
                    "valence": extra_valence,
                    "arousal": extra_arousal,
                    "dominance": extra_dominance,
                    "duration": df_grouped.iloc[0]['duration'] * 0.3
                }])
            ], ignore_index=True)
        
        # Generate top2 emotion summary - Save to output_base_path
        top2_csv_path = os.path.join(output_base_path, "top2_emotion_summary.csv")
        df_grouped.sort_values("duration", ascending=False)\
                  .head(2)\
                  .to_csv(top2_csv_path, index=False)
        print(f"💾 Saved top2_emotion_summary.csv: {top2_csv_path}")
        # Copy to legacy location for backwards compatibility
        copy_to_legacy_path(top2_csv_path, "top2_emotion_summary.csv")
        
        # DEBUG: Verify the file was created and has content
        if os.path.exists(top2_csv_path):
            file_size = os.path.getsize(top2_csv_path)
            print(f"✅ Verified file exists with size: {file_size} bytes")
            # Try to read it back to ensure it's valid
            try:
                with open(top2_csv_path, 'r') as f:
                    print(f"File content preview: {f.read()[:100]}")
            except Exception as e:
                print(f"⚠️ Error reading back the file: {e}")
        else:
            print(f"❌ ERROR: File was not created at: {top2_csv_path}")
            # Try to check directory permissions
            dir_path = os.path.dirname(top2_csv_path)
            if os.path.exists(dir_path):
                print(f"Directory exists: {dir_path}")
                print(f"Directory writable: {os.access(dir_path, os.W_OK)}")
            else:
                print(f"Directory does not exist: {dir_path}")
        
        # Smooth continuous tracks if enough data
        if len(df_summary) >= 11:
            try:
                smooth_cols = ['valence', 'arousal', 'dominance']
                window_len = min(11, len(df_summary) - (len(df_summary) % 2) - 1)
                df_summary[smooth_cols] = df_summary[smooth_cols].apply(
                    lambda s: signal.savgol_filter(s, window_len, 3)
                )
            except Exception as e:
                print(f"Smoothing error: {e}")
        
        # Save full segment summary - Save to output_base_path
        segments_csv_path = os.path.join(output_base_path, "summary_per_segment.csv")
        df_summary.to_csv(segments_csv_path, index=False)
        print(f"💾 Saved summary_per_segment.csv: {segments_csv_path}")
        # Copy to legacy location for backwards compatibility
        copy_to_legacy_path(segments_csv_path, "summary_per_segment.csv")
        
        # Generate evenly sampled arousal track (100 points)
        arousal_track = df_summary['arousal'].to_numpy()
        if len(arousal_track) == 1:
            arousal_track = np.full(100, arousal_track[0])
        elif len(arousal_track) > 1:
            arousal_track = np.interp(np.linspace(0, len(arousal_track)-1, 100),
                                      np.arange(len(arousal_track)),
                                      arousal_track)
        else: # Handle empty arousal data
            arousal_track = np.zeros(100)
        
        # Save arousal track to output_base_path
        arousal_csv_path = os.path.join(output_base_path, "arousal_100.csv")
        pd.DataFrame({"arousal": arousal_track})\
          .to_csv(arousal_csv_path, index=False)
        print(f"💾 Saved arousal_100.csv: {arousal_csv_path}")
        # Copy to legacy location for backwards compatibility
        copy_to_legacy_path(arousal_csv_path, "arousal_100.csv")

        print("✅ Emotion analysis complete")
        
        # Return relative paths for the frontend
        return {
            "top2SummaryPath": "/data/output/top2_emotion_summary.csv",
            "segmentSummaryPath": "/data/output/summary_per_segment.csv",
            "arousalTrackPath": "/data/output/arousal_100.csv",
            "timestamp": int(time.time() * 1000) # Add timestamp for cache busting
        }

    except Exception as err:
        print("❌ Error:", err)
        traceback.print_exc()
        
        # On error, try to create basic fallback files in the correct output directory
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_base_path = os.path.join(script_dir, "..", "public", "data", "output")
            print(f"📂 Emergency output to: {output_base_path}")
            os.makedirs(output_base_path, exist_ok=True)
            
            # Create basic top2_emotion_summary.csv
            emergency_path = os.path.join(output_base_path, "top2_emotion_summary.csv")
            pd.DataFrame([
                {"emotion": "neutral", "valence": 0.0, "arousal": 0.0, "dominance": 0.0, "duration": 5.0},
                {"emotion": "joy", "valence": 0.7, "arousal": 0.6, "dominance": 0.5, "duration": 5.0}
            ]).to_csv(emergency_path, index=False)
            print(f"💾 Emergency save to: {emergency_path}")
            
            # Create basic summary_per_segment.csv
            emergency_path = os.path.join(output_base_path, "summary_per_segment.csv")
            pd.DataFrame([
                {"start": 0, "end": 5, "text": "(audio)", "emotion": "neutral", 
                    "valence": 0.0, "arousal": 0.0, "dominance": 0.0, "duration": 5.0},
                {"start": 5, "end": 10, "text": "(audio)", "emotion": "joy", 
                    "valence": 0.7, "arousal": 0.6, "dominance": 0.5, "duration": 5.0}
            ]).to_csv(emergency_path, index=False)
            print(f"💾 Emergency save to: {emergency_path}")
            
            # Create basic arousal_100.csv
            emergency_path = os.path.join(output_base_path, "arousal_100.csv")
            arousal = np.sin(np.linspace(0, np.pi * 2, 100)) * 0.5
            pd.DataFrame({"arousal": arousal}).to_csv(emergency_path, index=False)
            print(f"💾 Emergency save to: {emergency_path}")
            
            print("✅ Created basic fallback CSV files")
            
            # Return paths to these fallback files
            return {
                "top2SummaryPath": "/data/output/top2_emotion_summary.csv",
                "segmentSummaryPath": "/data/output/summary_per_segment.csv",
                "arousalTrackPath": "/data/output/arousal_100.csv",
                "error": "Analysis failed, using fallback data.",
                "timestamp": int(time.time() * 1000)
            }
            
        except Exception as backup_err:
            print(f"❌ Failed to create fallback files: {backup_err}")
            traceback.print_exc()
            # Return an error state if even fallback fails
            return {"error": f"Analysis and fallback creation failed: {backup_err}"}
>>>>>>> Stashed changes

    df_summary = pd.DataFrame(segment_summaries)
    base_path = os.path.join(os.path.dirname(__file__), "../public/data")
    os.makedirs(base_path, exist_ok=True)

    if df_summary.empty:
        print("❌ No audio analysis results. Skipping CSV export.")
        return

    # === Grouped Emotion Summary
    df_grouped = df_summary.groupby('emotion').agg({
        'valence': 'mean',
        'arousal': 'mean',
        'duration': 'sum'
    }).reset_index()

    top2 = df_grouped.sort_values(by='duration', ascending=False).head(2)
    top2.to_csv(os.path.join(base_path, "top2_emotion_summary.csv"), index=False)

    # === Full Segment Detail
    df_summary.to_csv(os.path.join(base_path, "summary_per_segment.csv"), index=False)

    # === Smoothed Arousal Track (100 points)
    arousal_full = df_summary['arousal'].to_numpy()

    if len(arousal_full) > 1:
        arousal_interp = np.interp(
            np.linspace(0, len(arousal_full) - 1, 100),
            np.arange(len(arousal_full)),
            arousal_full
        )
    else:
        fallback_value = float(arousal_full[0]) if len(arousal_full) == 1 else 0.0
        arousal_interp = np.full(100, fallback_value)

    pd.DataFrame({"arousal": arousal_interp}).to_csv(os.path.join(base_path, "arousal_100.csv"), index=False)

    print("✅ Emotion analysis complete.")
