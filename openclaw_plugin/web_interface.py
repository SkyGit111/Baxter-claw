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

from flask import Flask, render_template_string, request, jsonify
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
import os

app = Flask(__name__)

# Get Qwen API key from environment or config
qwen_api_key = os.getenv('QWEN_API_KEY', 'sk-bd990626c84a4142b9581f13c5317522')

# Initialize plugin with LLM support
plugin = BaxterClawPlugin(
    bridge_url="http://localhost:8420",
    llm_provider="qwen",
    llm_api_key=qwen_api_key
)

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
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            width: 90%;
            max-width: 600px;
            height: 80vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 20px 20px 0 0;
            text-align: center;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
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
        #sendButton {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        #sendButton:hover {
            transform: scale(1.05);
        }
        #sendButton:active {
            transform: scale(0.95);
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
    <div class="container">
        <div class="header">
            <h1>🤖 Baxter-Claw</h1>
            <p>通过自然语言控制机器人</p>
        </div>

        <div class="chat-area" id="chatArea">
            <div class="message bot">
                <div class="message-content">
                    你好！我是 Baxter 机器人助手。你可以用自然语言告诉我要做什么。
                </div>
            </div>
        </div>

        <div class="input-area">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="输入命令，例如：帮我拿一下红色的杯子" />
                <button id="sendButton" onclick="sendMessage()">发送</button>
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

    <script>
        const chatArea = document.getElementById('chatArea');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const loading = document.getElementById('loading');

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

        function addMessage(text, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user' : 'bot');

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = text;

            messageDiv.appendChild(contentDiv);
            chatArea.appendChild(messageDiv);

            // 滚动到底部
            chatArea.scrollTop = chatArea.scrollHeight;
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
                addMessage(data.response, false);

            } catch (error) {
                addMessage('抱歉，发生了错误: ' + error.message, false);
            } finally {
                loading.style.display = 'none';
                sendButton.disabled = false;
                messageInput.focus();
            }
        }
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

        # 使用插件处理消息
        response = plugin.handle_message(user_message)

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