#!/usr/bin/env python
"""
简单的 Web 聊天界面，用于通过浏览器控制 Baxter 机器人

使用方法：
1. 确保 Bridge Server 正在运行
2. 安装 Flask: pip install flask
3. 运行此脚本: python web_interface.py
4. 在浏览器打开: http://localhost:5000
"""

import sys
sys.path.insert(0, '/home/cothink/Baxter-claw')

from flask import Flask, render_template_string, request, jsonify, send_file
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
import os
import requests
import io
import base64

app = Flask(__name__)

# Get Qwen API key from environment or config
qwen_api_key = os.getenv('QWEN_API_KEY', 'sk-bd990626c84a4142b9581f13c5317522')

# Initialize plugin with LLM support
plugin = BaxterClawPlugin(
    bridge_url="http://localhost:8420",
    llm_provider="qwen",
    llm_api_key=qwen_api_key
)

# Bridge server URL
BRIDGE_URL = "http://localhost:8420"

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Baxter-Claw 控制界面</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .main-container {
            display: flex;
            gap: 20px;
            width: 100%;
            max-width: 1400px;
            height: 85vh;
        }
        .container {
            flex: 1;
            min-width: 500px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
        }
        .camera-panel {
            width: 400px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            padding: 20px;
        }
        .camera-panel h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }
        .camera-selector {
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
        }
        .camera-btn {
            flex: 1;
            padding: 8px 12px;
            background: #f0f0f0;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
            color: #666;
        }
        .camera-btn:hover {
            background: #e8e8e8;
        }
        .camera-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }
        .camera-view {
            flex: 1;
            background: #f5f5f5;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }
        .camera-view img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .camera-placeholder {
            color: #999;
            text-align: center;
            padding: 20px;
        }
        .refresh-btn {
            margin-top: 15px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        .header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 20px 20px 0 0;
            text-align: center;
            position: relative;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        .voice-toggle {
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }
        .toggle-switch {
            position: relative;
            width: 44px;
            height: 24px;
            background: rgba(255,255,255,0.3);
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .toggle-switch.active {
            background: rgba(255,255,255,0.6);
        }
        .toggle-slider {
            position: absolute;
            top: 2px;
            left: 2px;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }
        .toggle-switch.active .toggle-slider {
            transform: translateX(20px);
        }
        .chat-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f5f5f5;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        .message.bot .message-content {
            background: white;
            color: #333;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .message-image {
            margin-top: 10px;
            border-radius: 8px;
            max-width: 100%;
            cursor: pointer;
        }
        .input-area {
            padding: 20px;
            background: white;
            border-radius: 0 0 20px 20px;
            border-top: 1px solid #eee;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #eee;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        #messageInput:focus {
            border-color: #667eea;
        }
        .btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .btn:active {
            transform: scale(0.95);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .voice-btn {
            padding: 12px 20px;
            background: #ff6b6b;
            min-width: 80px;
        }
        .voice-btn.listening {
            background: #51cf66;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .examples {
            margin-top: 10px;
            font-size: 12px;
            color: #666;
        }
        .example-btn {
            display: inline-block;
            margin: 5px 5px 0 0;
            padding: 5px 10px;
            background: #f0f0f0;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .example-btn:hover {
            background: #e0e0e0;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="container">
            <div class="header">
                <h1>🤖 Baxter-Claw</h1>
                <p>通过自然语言控制机器人</p>
                <div class="voice-toggle">
                    <span>语音反馈</span>
                    <div class="toggle-switch" id="voiceToggle" onclick="toggleVoiceFeedback()">
                        <div class="toggle-slider"></div>
                    </div>
                </div>
            </div>

            <div class="chat-area" id="chatArea">
                <div class="message bot">
                    <div class="message-content">
                        你好！我是 Baxter 机器人助手。你可以用自然语言或语音告诉我要做什么。
                    </div>
                </div>
            </div>

            <div class="input-area">
                <div class="input-group">
                    <input type="text" id="messageInput" placeholder="输入命令，例如：帮我拿一下红色的杯子" />
                    <button class="btn voice-btn" id="voiceBtn" onclick="toggleVoiceInput()">🎤 语音</button>
                    <button class="btn" id="sendButton" onclick="sendMessage()">发送</button>
                </div>
                <div class="examples">
                    <span>示例：</span>
                    <span class="example-btn" onclick="setMessage('帮我拿一下红色的杯子')">拿杯子</span>
                    <span class="example-btn" onclick="setMessage('pick the white box')">Pick box</span>
                    <span class="example-btn" onclick="setMessage('把它放到左边')">放到左边</span>
                    <span class="example-btn" onclick="setMessage('place it on the right')">Place right</span>
                    <span class="example-btn" onclick="setMessage('打开夹爪')">打开夹爪</span>
                    <span class="example-btn" onclick="setMessage('看看桌上有什么')">识别物体</span>
                </div>
                <div class="loading" id="loading">处理中...</div>
            </div>
        </div>

        <div class="camera-panel">
            <h2>📷 摄像头视图</h2>
            <div class="camera-selector">
                <button class="camera-btn" id="btnD455" onclick="selectCamera('d455')">D455</button>
                <button class="camera-btn active" id="btnRightHand" onclick="selectCamera('right_hand')">右手</button>
                <button class="camera-btn" id="btnLeftHand" onclick="selectCamera('left_hand')">左手</button>
            </div>
            <div class="camera-view" id="cameraView">
                <div class="camera-placeholder">
                    点击下方按钮刷新摄像头图像
                </div>
            </div>
            <button class="refresh-btn" onclick="refreshCamera()">刷新图像</button>
        </div>
    </div>

    <script>
        const chatArea = document.getElementById('chatArea');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const voiceBtn = document.getElementById('voiceBtn');
        const loading = document.getElementById('loading');
        const voiceToggle = document.getElementById('voiceToggle');
        const cameraView = document.getElementById('cameraView');

        let voiceFeedbackEnabled = false;
        let recognition = null;
        let isListening = false;
        let synthesis = window.speechSynthesis;
        let currentCamera = 'right_hand';

        // 初始化语音识别
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'zh-CN';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                messageInput.value = transcript;
                stopVoiceInput();
                // 自动发送
                sendMessage();
            };

            recognition.onerror = function(event) {
                console.error('语音识别错误:', event.error);
                stopVoiceInput();
            };

            recognition.onend = function() {
                stopVoiceInput();
            };
        } else {
            voiceBtn.disabled = true;
            voiceBtn.textContent = '不支持';
        }

        // 按 Enter 发送
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        function setMessage(text) {
            messageInput.value = text;
            messageInput.focus();
        }

        function toggleVoiceFeedback() {
            voiceFeedbackEnabled = !voiceFeedbackEnabled;
            voiceToggle.classList.toggle('active');
        }

        function toggleVoiceInput() {
            if (!recognition) return;

            if (isListening) {
                stopVoiceInput();
            } else {
                startVoiceInput();
            }
        }

        function startVoiceInput() {
            if (!recognition) return;
            isListening = true;
            voiceBtn.classList.add('listening');
            voiceBtn.textContent = '🎤 听取中';
            recognition.start();
        }

        function stopVoiceInput() {
            if (!recognition) return;
            isListening = false;
            voiceBtn.classList.remove('listening');
            voiceBtn.textContent = '🎤 语音';
            try {
                recognition.stop();
            } catch (e) {
                // 忽略停止错误
            }
        }

        function speak(text) {
            if (!voiceFeedbackEnabled || !synthesis) return;

            // 停止当前语音
            synthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            synthesis.speak(utterance);
        }

        function addMessage(text, isUser, imageData = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user' : 'bot');

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = text;

            messageDiv.appendChild(contentDiv);

            // 添加图片
            if (imageData && !isUser) {
                const img = document.createElement('img');
                img.src = 'data:image/jpeg;base64,' + imageData;
                img.className = 'message-image';
                img.onclick = function() {
                    window.open(this.src, '_blank');
                };
                contentDiv.appendChild(img);
            }

            chatArea.appendChild(messageDiv);

            // 滚动到底部
            chatArea.scrollTop = chatArea.scrollHeight;

            // 语音反馈
            if (!isUser) {
                speak(text);
            }
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // 显示用户消息
            addMessage(message, true);
            messageInput.value = '';

            // 显示加载状态
            loading.style.display = 'block';
            sendButton.disabled = true;
            voiceBtn.disabled = true;

            try {
                // 发送到后端
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                // 显示机器人回复
                addMessage(data.response, false, data.image);

                // 如果有图像相关的操作，自动刷新摄像头
                if (message.includes('看') || message.includes('识别') || message.includes('拿') ||
                    message.includes('pick') || message.includes('locate')) {
                    setTimeout(refreshCamera, 500);
                }

            } catch (error) {
                addMessage('抱歉，发生了错误: ' + error.message, false);
            } finally {
                loading.style.display = 'none';
                sendButton.disabled = false;
                voiceBtn.disabled = false;
                messageInput.focus();
            }
        }

        function selectCamera(camera) {
            currentCamera = camera;

            // 更新按钮状态
            document.querySelectorAll('.camera-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            const btnMap = {
                'd455': 'btnD455',
                'right_hand': 'btnRightHand',
                'left_hand': 'btnLeftHand'
            };

            document.getElementById(btnMap[camera]).classList.add('active');

            // 自动刷新图像
            refreshCamera();
        }

        async function refreshCamera() {
            try {
                cameraView.innerHTML = '<div class="camera-placeholder">加载中...</div>';

                const response = await fetch('/camera/image?camera=' + currentCamera);
                const data = await response.json();

                if (data.success && data.image) {
                    const img = document.createElement('img');
                    img.src = 'data:image/jpeg;base64,' + data.image;
                    img.alt = '摄像头图像';
                    cameraView.innerHTML = '';
                    cameraView.appendChild(img);
                } else {
                    cameraView.innerHTML = '<div class="camera-placeholder">无法获取图像<br>' +
                        (data.message || '') + '</div>';
                }
            } catch (error) {
                cameraView.innerHTML = '<div class="camera-placeholder">加载失败: ' +
                    error.message + '</div>';
            }
        }

        // 页面加载时自动刷新摄像头
        window.addEventListener('load', function() {
            setTimeout(refreshCamera, 1000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    """处理聊天消息"""
    try:
        data = request.json
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'response': '请输入消息'}), 400

        # 使用新的 skills-based 架构处理消息
        response = plugin.handle_message_with_skills(user_message)

        return jsonify({'response': response})

    except Exception as e:
        return jsonify({'response': f'错误: {str(e)}'}), 500

@app.route('/status')
def status():
    """检查服务状态"""
    try:
        result = plugin.execute_action('status', {})
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/camera/image')
def get_camera_image():
    """获取摄像头图像"""
    try:
        # 获取摄像头参数，默认为右手摄像头
        camera = request.args.get('camera', 'right_hand')

        # 从bridge服务器获取图像
        response = requests.get(f"{BRIDGE_URL}/camera?camera={camera}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'image' in data:
                # 返回base64编码的图像
                return jsonify({
                    'success': True,
                    'image': data['image'],
                    'camera': camera,
                    'timestamp': data.get('timestamp', '')
                })
        return jsonify({'success': False, 'message': '无法获取图像'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("="*60)
    print("Baxter-Claw Web 界面")
    print("="*60)
    print()
    print("启动中...")
    print()
    print("请在浏览器中打开: http://localhost:5000")
    print()
    print("按 Ctrl+C 停止服务器")
    print("="*60)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)