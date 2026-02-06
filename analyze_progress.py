
import csv
import os
import glob
from pathlib import Path
from collections import defaultdict

def analyze_progress():
    print("\n" + "="*60)
    print("京东空调评论爬虫 - 进度分析报告")
    print("="*60 + "\n")

    # 1. 定义目标
    TARGET_PER_BRAND = 1500
    GOOD_RATIO = 0.9  # 1350
    BAD_RATIO = 0.1   # 150
    
    # 目标品牌列表
    TARGET_BRANDS = [
        "美的", "格力", "海尔", "小米", "TCL", 
        "奥克斯", "新飞", "海信", "长虹", "松下"
    ]
    
    # 2. 扫描数据文件
    data_dirs = [
        "data",
        "Ultra-Pachong/data",
        "data/jd_ac_comments",
        "Ultra-Pachong/data/jd_ac_comments",
        r"C:\Users\h\Desktop\jd\data\jd_ac_comments"  # 用户指定路径
    ]
    
    csv_files = []
    for d in data_dirs:
        if os.path.exists(d):
            found = glob.glob(os.path.join(d, "*.csv"))
            csv_files.extend(found)
    
    if not csv_files:
        print("[!] 未找到任何CSV数据文件")
        return

    print(f"找到 {len(csv_files)} 个数据文件:")
    for f in csv_files:
        print(f"  - {f}")
    print("-" * 60)

    # 3. 统计数据
    # brand -> type -> count
    stats = defaultdict(lambda: {"good": 0, "bad": 0, "total": 0, "files": set()})
    
    for filepath in csv_files:
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # 检查字段名
                headers = reader.fieldnames
                if not headers:
                    continue
                    
                # 确定字段映射
                field_brand = next((h for h in headers if "系列" in h or "brand" in h.lower()), None)
                field_type = next((h for h in headers if "评分" in h or "type" in h.lower() or "score" in h.lower()), None)
                
                if not field_brand or not field_type:
                    # print(f"[跳过] 文件 {os.path.basename(filepath)} 缺少必要字段")
                    continue
                
                for row in reader:
                    brand = row.get(field_brand, "").strip()
                    comment_type = row.get(field_type, "").strip()
                    
                    if not brand:
                        continue
                        
                    # 归一化品牌名
                    for target in TARGET_BRANDS:
                        if target in brand:
                            brand = target
                            break
                    
                    # 归一化评论类型
                    is_good = "好评" in comment_type or comment_type == "5" or comment_type == "3" or (comment_type.isdigit() and int(comment_type) >= 4)
                    is_bad = "差评" in comment_type or comment_type == "1" or (comment_type.isdigit() and int(comment_type) <= 2)
                    
                    stats[brand]["total"] += 1
                    stats[brand]["files"].add(os.path.basename(filepath))
                    
                    if is_good:
                        stats[brand]["good"] += 1
                    elif is_bad:
                        stats[brand]["bad"] += 1
                        
        except Exception as e:
            print(f"[错误] 读取文件 {filepath} 失败: {e}")

    # 4. 输出报告
    print(f"\n{'品牌':<8} | {'总数':<8} | {'进度':<8} | {'好评':<8} | {'差评':<8} | {'状态':<10}")
    print("-" * 75)
    
    total_progress = 0
    
    for brand in TARGET_BRANDS:
        data = stats.get(brand, {"good": 0, "bad": 0, "total": 0})
        total = data["total"]
        good = data["good"]
        bad = data["bad"]
        
        progress = min(100, int(total / TARGET_PER_BRAND * 100))
        total_progress += progress
        
        # 状态判断
        if total >= TARGET_PER_BRAND:
            status = "✅ 完成"
        elif total > 0:
            status = "🔄 进行中"
        else:
            status = "❌ 未开始"
            
        # 缺少的具体数据
        missing = []
        if good < 1350:
            missing.append(f"缺好评{1350-good}")
        if bad < 150:
            missing.append(f"缺差评{150-bad}")
            
        status_detail = status
        if missing:
            status_detail += f" ({', '.join(missing)})"
            
        print(f"{brand:<8} | {total:<8} | {progress}%{'':<5} | {good:<8} | {bad:<8} | {status_detail}")

    print("-" * 75)
    avg_progress = int(total_progress / len(TARGET_BRANDS))
    print(f"总体进度: {avg_progress}%")
    
    # 5. 生成下一步建议
    print("\n💡 下一步建议:")
    incomplete_brands = [b for b in TARGET_BRANDS if stats[b]["total"] < TARGET_PER_BRAND]
    if incomplete_brands:
        print(f"1. 优先爬取以下品牌: {', '.join(incomplete_brands)}")
        print("2. 运行命令:")
        print(f"   python -m unified_agent.examples.jd_comment_scraper --brands {' '.join(incomplete_brands)}")
    else:
        print("🎉 所有品牌数据已采集完成！可以进行最终的数据清洗和打包。")

if __name__ == "__main__":
    analyze_progress()
