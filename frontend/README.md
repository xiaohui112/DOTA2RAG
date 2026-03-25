# DOTA2 RAG 前端界面

简单的 Web 界面，用于与 DOTA2 知识问答系统交互。

## 使用方法

1. 确保后端服务正在运行：
   ```bash
   cd /Users/tal/CursorProjects/DOTA2RAG
   uvicorn src.api.main:app --reload
   ```

2. 打开前端页面：
   - 直接在浏览器中打开 `index.html` 文件
   - 或使用简单的 HTTP 服务器：
     ```bash
     cd frontend
     python -m http.server 8080
     ```
   - 然后访问 http://localhost:8080

## 功能

- 💬 实时问答对话
- 🎨 现代化 UI 设计
- 💡 示例问题快速入口
- ⚡ 异步请求处理
- 📱 响应式布局

## API 配置

默认后端地址：`http://localhost:8000/api/ask`

如需修改，编辑 `index.html` 中的 `API_URL` 变量。
