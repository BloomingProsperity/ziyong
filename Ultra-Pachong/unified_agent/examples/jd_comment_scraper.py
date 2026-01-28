#!/usr/bin/env python3
"""
京东一级能耗空调评论爬虫 - 主入口

任务目标:
- 爬取15000条评论 (10个品牌 × 1500条/品牌)
- 好评:差评 = 9:1 (每品牌1350好评 + 150差评)
- 品牌: 美的、格力、小米、海尔、海信、TCL、奥克斯、新飞、长虹、松下

使用方式:
    1. 直接运行:
       python -m unified_agent.examples.jd_comment_scraper
    
    2. 或在 Python 中导入:
       from unified_agent.examples.jd_comment_scraper import main
       import asyncio
       asyncio.run(main())

输出:
    data/jd_ac_comments.csv - 评论数据

字段说明:
    - user_id: 用户ID (脱敏处理)
    - comment_time: 评论时间
    - brand: 品牌
    - price: 商品价格
    - content: 评论内容
    - score: 评分 (1-5)
    - comment_type: 好评/中评/差评
    - sku_id: 商品SKU
    - product_name: 商品名称

注意事项:
    1. 需要手动登录京东账号
    2. 建议使用代理避免IP被封
    3. 爬取过程中请勿关闭浏览器窗口
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# 强制设置UTF-8输出（Windows控制台支持）
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env 配置
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger = logging.getLogger(__name__)
        logger.info(f"已加载 .env 配置: {env_path}")
except ImportError:
    # 如果没有 python-dotenv，尝试手动解析 .env
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

from unified_agent.scraper.jd_comments import (
    JDCommentScraper,
    BRAND_CONFIGS,
    BrandConfig,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"jd_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        ),
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置参数
# ============================================================================

# 目标评论数
TARGET_TOTAL = 15000
TARGET_PER_BRAND = 1500
GOOD_PER_BRAND = 1350  # 好评数 (90%)
BAD_PER_BRAND = 150    # 差评数 (10%)

# 输出文件
OUTPUT_FILE = "jd_ac_comments.csv"
OUTPUT_DIR = "data"


# ============================================================================
# 辅助函数
# ============================================================================

def get_proxy_from_env() -> str | None:
    """
    从环境变量读取代理配置并构建代理 URL

    Returns:
        完整的代理 URL，如 http://user:pass@host:port
        如果未配置或未启用，返回 None
    """
    # 检查是否启用代理
    proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() in ("true", "1", "yes")
    if not proxy_enabled:
        return None

    # 读取代理配置
    host = os.getenv("KUAIDAILI_HOST", "")
    port = os.getenv("KUAIDAILI_PORT", "")
    username = os.getenv("KUAIDAILI_USERNAME", "")
    password = os.getenv("KUAIDAILI_PASSWORD", "")

    # 检查是否配置完整
    if not all([host, port, username, password]):
        logger.warning("[代理配置] 缺少必要参数，代理未启用")
        return None

    # 构建代理 URL
    proxy_url = f"http://{username}:{password}@{host}:{port}"
    logger.info(f"[代理配置] 已从 .env 加载代理: {username}@{host}:{port}")

    return proxy_url


# ============================================================================
# 主函数
# ============================================================================

async def main(
    proxy: str = None,
    output_file: str = OUTPUT_FILE,
    output_dir: str = OUTPUT_DIR,
    good_count: int = GOOD_PER_BRAND,
    bad_count: int = BAD_PER_BRAND,
    brands: list = None,
):
    """
    主函数

    Args:
        proxy: 代理地址 (可选，如不提供则从 .env 读取)
        output_file: 输出文件名
        output_dir: 输出目录
        good_count: 每品牌好评数
        bad_count: 每品牌差评数
        brands: 品牌列表 (可选, 默认全部)
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║           京东一级能耗空调评论爬虫 v1.0                       ║
║           Powered by Unified Agent                           ║
╠══════════════════════════════════════════════════════════════╣
║  目标: 15000条评论 | 10品牌 | 好评:差评 = 9:1               ║
║  集成: diagnosis | recovery | credential | mcp              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 如果未指定代理，尝试从环境变量读取
    if proxy is None:
        proxy = get_proxy_from_env()

    # 创建爬虫实例
    # 注意: request_delay 使用默认值 (3, 6) 以配合代理的速度限制
    scraper = JDCommentScraper(
        output_dir=output_dir,
        proxy=proxy,
    )
    
    # 显示 Agent 模块状态
    agent_status = scraper.get_agent_status()
    print("Agent 模块集成状态:")
    print(f"  [{'✓' if agent_status['diagnosis'] else '✗'}] diagnosis  - 错误诊断与分析")
    print(f"  [{'✓' if agent_status['recovery'] else '✗'}] recovery   - 故障自动恢复")
    print(f"  [{'✓' if agent_status['credential'] else '✗'}] credential - Cookie/凭据管理")
    print(f"  [{'✓' if agent_status['mcp'] else '✗'}] mcp        - MCP工具协议")
    print()
    
    # 打印配置
    print("运行配置:")
    if proxy:
        # 脱敏显示代理（隐藏密码）
        import re
        proxy_display = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', proxy)
        print(f"  - 代理: {proxy_display} (从 .env 加载)" if os.getenv("PROXY_ENABLED") == "true" else f"  - 代理: {proxy_display}")
    else:
        print(f"  - 代理: 未设置")
    print(f"  - 输出: {output_dir}/{output_file}")
    print(f"  - 每品牌好评: {good_count}")
    print(f"  - 每品牌差评: {bad_count}")
    
    # 使用的品牌
    brand_configs = brands if brands else BRAND_CONFIGS
    print(f"  - 品牌: {', '.join(b.name for b in brand_configs)}")
    print()
    
    try:
        # Step 1: 初始化浏览器
        print("[1/4] 正在启动浏览器...")
        if not await scraper.init_browser():
            print("[错误] 浏览器启动失败!")
            print("请确保已安装 playwright:")
            print("  pip install playwright")
            print("  playwright install chromium")
            return
        
        # Step 2: 登录
        print("[2/4] 等待登录...")
        if not await scraper.login(timeout=300):
            print("[错误] 登录超时!")
            return
        
        # Step 3: 爬取评论
        print("[3/4] 开始爬取评论...")
        comments = await scraper.scrape_all_brands(
            brands=brand_configs,
            good_per_brand=good_count,
            bad_per_brand=bad_count,
        )
        
        # Step 4: 导出结果
        print("[4/4] 导出数据...")
        if comments:
            output_path = scraper.export_csv(comments, output_file)
            
            # 打印统计
            stats = scraper.get_stats()
            print("\n" + "="*60)
            print("爬取完成! 统计信息:")
            print("="*60)
            print(f"  总请求数: {stats['total_requests']}")
            print(f"  原始评论: {stats['total_comments']}")
            print(f"  有效评论: {stats['valid_comments']}")
            print(f"  去重/无效: {stats['duplicates']}")
            print(f"  错误次数: {stats.get('errors', 0)}")
            print(f"  恢复次数: {stats.get('recoveries', 0)}")
            print(f"  输出文件: {output_path}")
            
            # Agent 模块统计
            if stats.get('mcp_stats'):
                print(f"\nAgent MCP 统计:")
                mcp = stats['mcp_stats']
                print(f"  MCP调用: {mcp.get('total_calls', 0)}")
                print(f"  成功率: {mcp.get('success_rate', 1.0):.1%}")
            
            # 按品牌统计
            print("\n按品牌分布:")
            brand_stats = {}
            for c in comments:
                brand_stats.setdefault(c.brand, {"good": 0, "bad": 0})
                if c.comment_type == "好评":
                    brand_stats[c.brand]["good"] += 1
                else:
                    brand_stats[c.brand]["bad"] += 1
            
            for brand, stat in brand_stats.items():
                print(f"  {brand}: 好评 {stat['good']}, 差评 {stat['bad']}")
            
        else:
            print("[警告] 没有爬取到任何评论!")
    
    except KeyboardInterrupt:
        print("\n[中断] 用户取消操作")
    
    except Exception as e:
        logger.exception("爬取过程中发生错误")
        print(f"\n[错误] {e}")
    
    finally:
        # 关闭浏览器
        await scraper.close()
        print("\n浏览器已关闭")


def run():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="京东一级能耗空调评论爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本使用
    python -m unified_agent.examples.jd_comment_scraper
    
    # 使用代理
    python -m unified_agent.examples.jd_comment_scraper --proxy http://127.0.0.1:7890
    
    # 自定义输出
    python -m unified_agent.examples.jd_comment_scraper --output my_comments.csv
    
    # 只爬取部分品牌
    python -m unified_agent.examples.jd_comment_scraper --brands 美的 格力 小米
        """
    )
    
    parser.add_argument(
        "--proxy", "-p",
        type=str,
        default=None,
        help="代理地址 (如 http://127.0.0.1:7890)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=OUTPUT_FILE,
        help=f"输出文件名 (默认: {OUTPUT_FILE})"
    )
    
    parser.add_argument(
        "--output-dir", "-d",
        type=str,
        default=OUTPUT_DIR,
        help=f"输出目录 (默认: {OUTPUT_DIR})"
    )
    
    parser.add_argument(
        "--good", "-g",
        type=int,
        default=GOOD_PER_BRAND,
        help=f"每品牌好评数 (默认: {GOOD_PER_BRAND})"
    )
    
    parser.add_argument(
        "--bad", "-b",
        type=int,
        default=BAD_PER_BRAND,
        help=f"每品牌差评数 (默认: {BAD_PER_BRAND})"
    )
    
    parser.add_argument(
        "--brands",
        type=str,
        nargs="+",
        default=None,
        help="指定品牌 (默认全部)"
    )
    
    args = parser.parse_args()
    
    # 处理品牌参数
    brands = None
    if args.brands:
        brands = []
        brand_name_map = {b.name: b for b in BRAND_CONFIGS}
        for name in args.brands:
            if name in brand_name_map:
                brands.append(brand_name_map[name])
            else:
                print(f"[警告] 未知品牌: {name}, 将跳过")
        
        if not brands:
            print("[错误] 没有有效的品牌!")
            return
    
    # 运行
    asyncio.run(main(
        proxy=args.proxy,
        output_file=args.output,
        output_dir=args.output_dir,
        good_count=args.good,
        bad_count=args.bad,
        brands=brands,
    ))


# ============================================================================
# 入口点
# ============================================================================

if __name__ == "__main__":
    run()
