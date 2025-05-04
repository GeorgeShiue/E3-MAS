import gradio as gr
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 用於儲存被監測的檔案路徑和內容
monitored_files = {}
last_update_time = {}

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path == self.file_path:
            self.callback(self.file_path)

def read_file_content(file_path):
    """讀取檔案內容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"無法讀取檔案: {str(e)}"

def update_file_content(file_path):
    """更新檔案內容"""
    content = read_file_content(file_path)
    monitored_files[file_path] = content
    last_update_time[file_path] = time.time()
    return content

def setup_file_monitoring(file_path, callback=update_file_content):
    """設置檔案監測"""
    # 初始讀取檔案內容
    update_file_content(file_path)
    
    # 創建觀察者和處理程序
    event_handler = FileChangeHandler(file_path, callback)
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(file_path), recursive=False)
    observer.start()
    return observer

# Gradio介面
with gr.Blocks() as demo:
    gr.Markdown("# 檔案監測顯示器")
    
    with gr.Row():
        file_path_input = gr.Textbox(
            label="要監測的檔案路徑",
            placeholder="例如: C:\\Users\\George\\Desktop\\專題Program\\專題\\Tutorial\\Gradio\\test.txt"
        )
        monitor_button = gr.Button("開始監測")
        refresh_button = gr.Button("手動刷新")
    
    file_content = gr.Textbox(label="檔案內容", lines=20)
    status_label = gr.Label(label="狀態")
    
    # 全域變數用於儲存觀察者和計時器
    observer = None
    current_file = None
    interval = 3  # 設定更新間隔為3秒
    timer = gr.Timer(value=interval)

    def start_monitoring(file_path):
        global observer, current_file, timer
        
        # 如果已經在監測其他檔案，先停止
        if observer:
            observer.stop()
            observer.join()
        
        if not os.path.exists(file_path):
            return None, f"找不到檔案: {file_path}"
        
        # 設定新的監測
        current_file = file_path
        observer = setup_file_monitoring(file_path)
        content = monitored_files.get(file_path, "檔案尚未讀取")
        
        return content, f"正在以每{interval}秒監測: {file_path}"
    
    def refresh_content():
        if current_file and os.path.exists(current_file):
            content = update_file_content(current_file)
            return content, f"已更新: {current_file} (於 {time.strftime('%H:%M:%S')})"
        return "", "沒有檔案正在監測"
    
    # 更新函數，用於定期檢查檔案內容
    # def update_ui():
    #     if current_file and current_file in monitored_files:
    #         return monitored_files[current_file], f"上次更新: {time.strftime('%H:%M:%S', time.localtime(last_update_time[current_file]))}"
    #     return "", "沒有檔案正在監測"

    monitor_button.click(
        fn=start_monitoring,
        inputs=[file_path_input],
        outputs=[file_content, status_label]
    )
    
    monitor_button.click(lambda: gr.Timer(active=True), None, timer) # *動態啟動計時器

    refresh_button.click(
        fn=refresh_content,
        inputs=[],
        outputs=[file_content, status_label]
    )
        
    # 設定定期更新
    timer.tick(
        fn=refresh_content, 
        inputs=[], 
        outputs=[file_content, status_label]
    )
    # demo.load(update_ui, [], [file_content, status_label])

# 啟動應用
if __name__ == "__main__":
    try:
        demo.queue().launch(share=True)
    finally:
        # 確保程式結束時停止觀察者
        if observer:
            observer.stop()
            observer.join()