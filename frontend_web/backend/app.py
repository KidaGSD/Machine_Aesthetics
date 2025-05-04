# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import shutil
import time
import logging
import sys
from overall_shape_emotion_analysis import run_analysis  # refactor your script into a callable

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../public")
CORS(app)

UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """处理音频上传并分析情绪"""
    logger.info("收到音频上传请求")
    
    if "file" not in request.files:
        logger.error("没有文件在请求中")
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == '':
        logger.error("没有选择文件")
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if file:
        try:
            # 保存上传的文件
            filename = file.filename
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            logger.info(f"文件保存至: {save_path}")
            
            # 运行分析
            logger.info("开始音频分析...")
            start_time = time.time()
            success = run_analysis(audio_path=save_path)
            processing_time = time.time() - start_time
            
            if success:
                logger.info(f"音频处理成功，耗时: {processing_time:.2f}秒")
                # 检查是否生成了必要的文件
                expected_files = [
                    "../public/data/top2_emotion_summary.csv",
                    "../public/data/summary_per_segment.csv",
                    "../public/data/arousal_100.csv"
                ]
                
                missing_files = [f for f in expected_files if not os.path.exists(os.path.join(os.path.dirname(__file__), f))]
                
                if missing_files:
                    logger.warning(f"分析成功但缺少以下文件: {missing_files}")
                
                return jsonify({
                    "status": "success", 
                    "message": "Audio processed successfully",
                    "processing_time": f"{processing_time:.2f}s"
                })
            else:
                logger.error("音频处理失败")
                return jsonify({
                    "status": "error", 
                    "message": "Failed to process audio"
                }), 500
                
        except Exception as e:
            logger.error(f"处理音频时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "status": "error", 
                "message": f"Error processing audio: {str(e)}"
            }), 500
    
    return jsonify({"status": "error", "message": "Unknown error"}), 400

@app.route("/api/process-audio", methods=["POST"])
def process_audio():
    """用于前端LampCreation.js的API端点"""
    logger.info("收到API处理音频请求")
    
    if "audioFile" not in request.files:
        logger.error("没有audioFile字段在请求中")
        return jsonify({'success': False, 'error': 'No audioFile field in request'}), 400
    
    file = request.files["audioFile"]
    if file.filename == '':
        logger.error("没有选择文件")
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if file:
        try:
            # 保存上传的文件
            filename = file.filename
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            logger.info(f"文件保存至: {save_path}")
            
            # 运行分析
            logger.info("开始音频分析...")
            start_time = time.time()
            success = run_analysis(audio_path=save_path)
            processing_time = time.time() - start_time
            
            if success:
                logger.info(f"音频处理成功，耗时: {processing_time:.2f}秒")
                
                # 尝试提取整体情绪
                overall_emotion = "neutral"
                try:
                    import pandas as pd
                    csv_path = os.path.join(os.path.dirname(__file__), "../public/data/top2_emotion_summary.csv")
                    if os.path.exists(csv_path):
                        df = pd.read_csv(csv_path)
                        if not df.empty:
                            overall_emotion = df.iloc[0]["emotion"]
                            logger.info(f"提取的整体情绪: {overall_emotion}")
                except Exception as e:
                    logger.error(f"读取整体情绪时出错: {e}")
                
                return jsonify({
                    'success': True, 
                    'csvPath': '/data/top2_emotion_summary.csv',
                    'overallEmotion': overall_emotion,
                    'processingTime': f"{processing_time:.2f}s"
                })
            else:
                logger.error("音频处理失败")
                return jsonify({'success': False, 'error': 'Failed to process audio'}), 500
                
        except Exception as e:
            logger.error(f"处理音频时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False, 'error': 'Unknown error'}), 400

# 添加服务静态文件的路由
@app.route('/data/<path:filename>')
def serve_data(filename):
    """提供data目录下的静态文件"""
    return send_from_directory(os.path.join(app.static_folder, 'data'), filename)

if __name__ == "__main__":
    logger.info("启动后端服务器在端口5001...")
    app.run(port=5001, debug=True)
