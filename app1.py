from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# ==========================
# 重要：GitHub Actions 环境没有 AI 密钥，先模拟返回，避免报错
# ==========================
USE_MOCK_AI = True  # 云端环境必须开启
try:
    from aicore_llm import AICoreClient
    client = AICoreClient.from_service_key_file("./service_key.json")
except:
    USE_MOCK_AI = True

# 前端聊天页面（纯HTML）
html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SAP AI 聊天</title>
    <style>
        body{max-width:700px;margin:20px auto;background:#f5f5f5}
        .chat{height:600px;overflow-y:auto;background:white;padding:20px;border-radius:10px}
        .msg{margin:10px 0;padding:10px 14px;border-radius:10px;max-width:70%}
        .user{background:#009efb;color:white;margin-left:auto}
        .ai{background:#e5e5ea;color:#111}
        .input{display:flex;margin-top:10px}
        input{flex:1;padding:12px;border-radius:20px;border:1px solid #ddd}
        button{padding:12px 20px;background:#009efb;color:white;border:none;border-radius:20px;margin-left:10px}
    </style>
</head>
<body>
    <div class="chat" id="box"></div>
    <div class="input">
        <input id="msg" placeholder="输入消息...">
        <button onclick="send()">发送</button>
    </div>

    <script>
        async function send() {
            let m = document.getElementById("msg").value.trim();
            if(!m) return;
            
            addMsg(m, "user");
            document.getElementById("msg").value = "";
            
            let res = await fetch("/api", {
                method:"POST",
                body: m
            });
            let reply = await res.text();
            addMsg(reply, "ai");
        }

        function addMsg(text, cls) {
            let d = document.createElement("div");
            d.className = "msg " + cls;
            d.innerText = text;
            document.getElementById("box").appendChild(d);
            document.getElementById("box").scrollTop = 99999;
        }
    </script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        msg = self.rfile.read(length).decode("utf-8")
        
        # AI 应答（云端环境用模拟数据）
        if USE_MOCK_AI:
            reply = f"[AI模拟回复] 收到：{msg}（GitHub Actions 测试模式）"
        else:
            reply = client.chat(msg)
        
        self.send_response(200)
        self.send_header("Content-type", "text/plain;charset=utf-8")
        self.end_headers()
        self.wfile.write(reply.encode("utf-8"))

    # 屏蔽日志，避免干扰 GitHub Actions
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    # ==========================
    # 修复：绑定 0.0.0.0 让外部能访问
    # ==========================
    server = HTTPServer(("0.0.0.0", 5000), Handler)
    print("✅ 聊天服务已启动 → http://0.0.0.0:5000")
    server.serve_forever()

    # ==========================
    # 修复：删除下面这行冲突代码
    # app.run(host='0.0.0.0', port=5000, debug=True)
