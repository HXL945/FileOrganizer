import os
import shutil
import json
import argparse
from datetime import datetime

# ======================
# 配置系统 (可外部修改)
# ======================
DEFAULT_CONFIG = {
    "skip_files": [".ini", ".db", ".tmp", "~$"],  # 跳过系统/临时文件
    "backup_log": True,  # 是否创建恢复日志
    "categories": {
        "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
        "文档": [".pdf", ".docx", ".doc", ".xlsx", ".pptx", ".txt"],
        "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "代码": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp"],
        "可执行文件": [".exe", ".msi", ".bat", ".cmd"],
        "快捷方式": [".lnk", ".url", ".desktop"],
        "媒体": [".mp3", ".mp4", ".avi", ".mov", ".wav"]
    }
}

# ======================
# 核心功能函数
# ======================
def load_config(config_path=None):
    """加载配置文件，优先使用外部配置"""
    config = DEFAULT_CONFIG.copy()
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 深度合并配置
                for key in user_config:
                    if key in config and isinstance(config[key], dict):
                        config[key].update(user_config[key])
                    else:
                        config[key] = user_config[key]
        except Exception as e:
            print(f"⚠️ 配置文件错误: {e}, 使用默认配置")
    
    return config

def should_skip_file(filename, skip_patterns):
    """检查是否应跳过文件"""
    lower_name = filename.lower()
    # 跳过系统文件和临时文件
    for pattern in skip_patterns:
        if pattern.startswith('.') and lower_name.endswith(pattern):
            return True
        if pattern in lower_name:
            return True
    return False

def organize_files(config):
    """整理桌面文件主函数"""
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    
    # 用户确认
    if not config.get('silent_mode', False):
        input("⚠️ 警告：即将整理桌面文件。按回车键继续...")
    
    # 获取桌面文件
    all_items = os.listdir(desktop_path)
    files = [f for f in all_items if os.path.isfile(os.path.join(desktop_path, f))]
    
    # 过滤需要跳过的文件
    files = [f for f in files if not should_skip_file(f, config['skip_files'])]
    total_files = len(files)
    
    # 创建分类文件夹
    for category in config['categories']:
        os.makedirs(os.path.join(desktop_path, category), exist_ok=True)
    
    # 准备恢复日志
    backup_log = {
        "timestamp": datetime.now().isoformat(),
        "operations": [],
        "desktop_path": desktop_path
    }
    
    # 文件整理主循环
    print(f"\n📁 开始整理 {total_files} 个文件...")
    processed = 0
    
    for filename in files:
        try:
            src_path = os.path.join(desktop_path, filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            # 分类移动
            moved = False
            for category, extensions in config['categories'].items():
                if file_ext in extensions:
                    dst_folder = os.path.join(desktop_path, category)
                    dst_path = os.path.join(dst_folder, filename)
                    
                    # 处理同名文件
                    if os.path.exists(dst_path):
                        base, ext = os.path.splitext(filename)
                        new_name = f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
                        dst_path = os.path.join(dst_folder, new_name)
                    
                    shutil.move(src_path, dst_path)
                    
                    # 记录操作
                    if config['backup_log']:
                        backup_log['operations'].append({
                            "original": src_path,
                            "new_location": dst_path
                        })
                    
                    processed += 1
                    print(f"[{processed}/{total_files}] ✅ 已移动: {filename} → {category}/")
                    moved = True
                    break
            
            # 未分类文件处理
            if not moved:
                others_path = os.path.join(desktop_path, "其他")
                os.makedirs(others_path, exist_ok=True)
                dst_path = os.path.join(others_path, filename)
                shutil.move(src_path, dst_path)
                
                if config['backup_log']:
                    backup_log['operations'].append({
                        "original": src_path,
                        "new_location": dst_path
                    })
                
                processed += 1
                print(f"[{processed}/{total_files}] ⚠️ 未分类: {filename} → 其他/")

        except PermissionError:
            print(f"[{processed}/{total_files}] ❌ 权限不足，跳过: {filename}")
        except FileNotFoundError:
            print(f"[{processed}/{total_files}] ❌ 文件不存在: {filename}")
        except Exception as e:
            print(f"[{processed}/{total_files}] ❌ 处理失败: {filename} - 错误: {e}")
    
    # 保存恢复日志
    if config['backup_log'] and backup_log['operations']:
        log_path = os.path.join(desktop_path, "文件整理备份.json")
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(backup_log, f, indent=2, ensure_ascii=False)
        print(f"\n📝 备份日志已保存到: {log_path}")
    
    # 完成统计
    print(f"\n🎉 整理完成！成功处理 {processed}/{total_files} 个文件")
    if processed < total_files:
        print("⚠️ 注意：跳过/失败的文件请根据日志手动处理")

def restore_files(log_path=None):
    """恢复文件到原始位置"""
    # 自动查找日志文件
    if not log_path:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        log_path = os.path.join(desktop_path, "文件整理备份.json")
    
    if not os.path.exists(log_path):
        print("❌ 找不到备份日志文件")
        return
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            backup_log = json.load(f)
        
        operations = backup_log.get('operations', [])
        if not operations:
            print("⚠️ 备份日志中没有操作记录")
            return
        
        # 用户确认
        input(f"⚠️ 即将恢复 {len(operations)} 个文件. 按回车键继续...")
        
        # 反向恢复文件
        success_count = 0
        for op in reversed(operations):
            try:
                src = op["new_location"]
                dst = op["original"]
                
                # 确保目标目录存在
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                
                # 移动文件
                if os.path.exists(src):
                    shutil.move(src, dst)
                    success_count += 1
                    print(f"✅ 已恢复: {os.path.basename(dst)}")
                else:
                    print(f"⚠️ 文件不存在: {os.path.basename(src)}")
            
            except Exception as e:
                print(f"❌ 恢复失败 {os.path.basename(dst)}: {str(e)}")
        
        # 删除日志文件
        os.remove(log_path)
        print(f"\n🎉 恢复完成! 成功恢复 {success_count}/{len(operations)} 个文件")
    
    except json.JSONDecodeError:
        print("❌ 备份日志格式错误")
    except Exception as e:
        print(f"❌ 恢复过程中出错: {str(e)}")

# ======================
# 命令行接口
# ======================
def main():
    parser = argparse.ArgumentParser(description="文件整理工具 v2.0")
    parser.add_argument('--organize', action='store_true', help="整理桌面文件")
    parser.add_argument('--restore', action='store_true', help="恢复文件到原始位置")
    parser.add_argument('--config', type=str, default="", help="自定义配置文件路径")
    parser.add_argument('--silent', action='store_true', help="静默模式（无需确认）")
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    if args.silent:
        config['silent_mode'] = True
    
    # 执行操作
    if args.organize:
        organize_files(config)
    elif args.restore:
        restore_files()
    else:
        print("请指定操作: --organize 或 --restore")

if __name__ == "__main__":
    main()