# -*- coding: utf-8 -*-
# 用于测试改进后的情感分析系统
import os
import pandas as pd
import sys
from overall_shape_emotion_analysis import run_analysis

# 确保正确处理编码
if sys.stdout.encoding != 'utf-8':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass  # 如果失败，继续使用默认编码

def print_separator(title=""):
    print("\n" + "=" * 50)
    if title:
        print(f" {title} ")
        print("=" * 50)
    print()

def main():
    print_separator("EMOTION ANALYSIS TEST")
    
    # 首先检查上传的音频文件
    uploads_dir = os.path.join(os.path.dirname(__file__), "audio")
    default_audio = os.path.join(uploads_dir, "uploaded_audio.wav")
    
    # 备选目录
    audio_dir = os.path.join(os.path.dirname(__file__), "../audio")
    
    # 决定使用哪个音频文件
    test_audio_path = None
    
    # 检查默认上传文件
    if os.path.exists(default_audio):
        test_audio_path = default_audio
    else:
        # 尝试查找音频文件
        audio_files = []
        for check_dir in [uploads_dir, audio_dir]:
            if os.path.exists(check_dir):
                for file in os.listdir(check_dir):
                    if file.lower().endswith((".wav", ".mp3", ".m4a", ".mp4")):
                        audio_files.append(os.path.join(check_dir, file))
        
        if audio_files:
            test_audio_path = audio_files[0]
    
    if not test_audio_path:
        print("No audio files found. Please place an audio file in the audio directory.")
        # 创建一个文本文件，作为占位符
        os.makedirs(audio_dir, exist_ok=True)
        placeholder_path = os.path.join(audio_dir, "upload_audio_here.txt")
        with open(placeholder_path, "w", encoding="utf-8") as f:
            f.write("Place audio files (.wav, .mp3, .m4a, .mp4) in this directory for testing")
        return
    
    # 使用找到的音频文件
    print(f"Using audio file: {test_audio_path}")
    
    # 运行情感分析
    print_separator("STARTING ANALYSIS")
    run_analysis(test_audio_path)
    
    # 查看生成的结果
    print_separator("ANALYSIS RESULTS")
    
    data_dir = os.path.join(os.path.dirname(__file__), "../public/data")
    
    # 读取并显示top2情感摘要
    top2_path = os.path.join(data_dir, "top2_emotion_summary.csv")
    if os.path.exists(top2_path):
        print("Top 2 Emotion Summary:")
        df_top2 = pd.read_csv(top2_path)
        print(df_top2)
        print()
    
    # 读取并显示arousal_100.csv部分内容
    arousal_path = os.path.join(data_dir, "arousal_100.csv")
    if os.path.exists(arousal_path):
        print("Arousal Track (First 10 points):")
        df_arousal = pd.read_csv(arousal_path)
        print(df_arousal.head(10))
        print(f"Total points: {len(df_arousal)}")
        print()
    
    # 读取并显示摘要段落内容
    segments_path = os.path.join(data_dir, "summary_per_segment.csv")
    if os.path.exists(segments_path):
        print("Segment Summary (First 5 rows):")
        df_segments = pd.read_csv(segments_path)
        # 筛选需要显示的列
        display_columns = ['start', 'end', 'emotion', 'valence', 'arousal', 'dominance']
        print(df_segments[display_columns].head(5))
        print(f"Total segments: {len(df_segments)}")
    
    print_separator("TEST COMPLETE")
    print("Analysis successful! Please check the results above.")
    print("All generated CSV files are located at:", data_dir)
    
if __name__ == "__main__":
    main() 