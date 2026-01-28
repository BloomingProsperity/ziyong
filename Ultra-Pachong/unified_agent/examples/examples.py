"""
使用示例 (v2.0 智能版)

展示如何使用统一 Agent 进行网页抓取。
"""

import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ==================== 智能功能示例 (推荐) ====================

def example_smart_investigate():
    """
    示例1: 智能调查 (推荐)

    使用 Brain 的 smart_investigate 自动分析网站
    """
    from unified_agent import Brain, AgentConfig

    # 创建 Brain
    config = AgentConfig(proxy_enabled=False, headless=True)
    brain = Brain(config)

    # 智能调查
    print("正在智能分析网站...")
    analysis = brain.smart_investigate("https://quotes.toscrape.com/")

    # 打印 AI 友好的报告
    print("\n" + "=" * 50)
    print(analysis.to_ai_report())
    print("=" * 50)

    # 查看关键信息
    print(f"\n网站类型: {analysis.site_type}")
    print(f"反爬等级: {analysis.anti_scrape_level}")
    print(f"推荐方案: {analysis.recommended_approach}")
    print(f"\n下一步操作:")
    for step in analysis.next_steps:
        print(f"  - {step}")


def example_check_presets():
    """
    示例2: 查看预设配置

    查看内置的网站预设配置
    """
    from unified_agent import list_presets, get_preset, get_preset_info

    # 列出所有预设
    sites = list_presets()
    print(f"支持的预设网站 ({len(sites)} 个):")
    for site in sites:
        preset = get_preset(site)
        if preset:
            sig = "[需签名]" if preset.requires_signature else ""
            print(f"  {site:<12} {sig}")

    # 查看特定网站预设
    print("\n京东预设详情:")
    info = get_preset_info("jd.com")
    print(f"  找到预设: {info.get('found')}")
    print(f"  需要签名: {info.get('requires_signature')}")
    print(f"  签名参数: {info.get('signature_params')}")
    print(f"  反爬说明: {info.get('anti_scrape_notes')}")


def example_brain_api_call():
    """
    示例3: 使用 Brain 调用 API (带智能重试)

    当分析出 API 后，使用 Brain 直接调用
    """
    from unified_agent import Brain, AgentConfig, RetryConfig

    # 配置重试
    config = AgentConfig(proxy_enabled=False, headless=True)
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        jitter=True,
    )

    brain = Brain(config, retry_config)

    # 调用 API (带智能重试)
    result = brain.call_api(
        url="https://httpbin.org/get",
        method="GET",
        params={"test": "value"},
        retry=True,
    )

    # 查看结果
    print(result.to_ai_summary())
    if result.success:
        print(f"响应数据: {result.body}")


def example_batch_api_calls():
    """
    示例4: 批量 API 调用

    批量调用多个 API，自动控制频率
    """
    from unified_agent import Brain, AgentConfig

    brain = Brain(AgentConfig(proxy_enabled=False))

    # 批量调用
    requests = [
        {"url": "https://httpbin.org/get", "params": {"page": 1}},
        {"url": "https://httpbin.org/get", "params": {"page": 2}},
        {"url": "https://httpbin.org/get", "params": {"page": 3}},
    ]

    results = brain.batch_call_api(requests, delay_between=1.0)

    for i, result in enumerate(results, 1):
        print(f"请求 {i}: {result.to_ai_summary()}")


def example_brain_status():
    """
    示例5: 查看 Brain 状态

    监控 Brain 的运行状态和统计
    """
    from unified_agent import Brain, AgentConfig

    brain = Brain(AgentConfig(proxy_enabled=False))

    # 模拟一些操作
    brain.call_api("https://httpbin.org/get", retry=False)
    brain.call_api("https://httpbin.org/status/500", retry=False)

    # 查看状态
    stats = brain.get_stats()
    print(f"统计信息: {stats}")

    # 查看状态报告
    print("\n状态报告:")
    print(brain.get_status_report(use_emoji=False))

    # 重置
    brain.reset()
    print("\n已重置 Brain 状态")


# ==================== 基础功能示例 ====================

def example_basic_scrape():
    """
    示例6: 基础抓取

    自动分析页面结构并提取数据
    """
    from unified_agent import ScraperAgent, AgentConfig

    # 创建配置 (不使用代理)
    config = AgentConfig(
        proxy_enabled=False,
        headless=True,
        max_pages=3,
    )

    # 创建 Agent
    agent = ScraperAgent(config)

    # 抓取数据
    result = agent.scrape("https://quotes.toscrape.com/")

    print(f"抓取成功: {result.success}")
    print(f"提取数据: {result.total_items} 条")
    print(f"翻页数: {result.pages_scraped}")
    print(f"耗时: {result.duration_seconds} 秒")

    # 打印前3条数据
    for item in result.data[:3]:
        print(f"  - {item}")


def example_with_kuaidaili():
    """
    示例7: 使用快代理

    配置快代理隧道代理进行抓取
    """
    from unified_agent import ScraperAgent, AgentConfig

    # 方式1: 直接配置
    config = AgentConfig.for_kuaidaili(
        username="your_username",  # 替换为你的快代理用户名
        password="your_password",  # 替换为你的快代理密码
        headless=True,
        max_pages=5,
    )

    # 方式2: 从环境变量加载
    # 需要设置环境变量:
    #   KUAIDAILI_USERNAME=your_username
    #   KUAIDAILI_PASSWORD=your_password
    # config = AgentConfig.from_env()

    agent = ScraperAgent(config)

    # 检查代理健康状态
    if agent.proxy_manager.check_proxy_health_sync():
        print("代理连接正常")
    else:
        print("代理连接失败")
        return

    # 抓取数据
    result = agent.scrape("https://example.com/products")
    print(f"抓取成功: {result.success}")
    print(f"提取数据: {result.total_items} 条")


def example_custom_selector():
    """
    示例8: 使用自定义选择器

    精确控制要提取的字段
    """
    from unified_agent import ScraperAgent, AgentConfig, FieldConfig

    config = AgentConfig(proxy_enabled=False, headless=True)
    agent = ScraperAgent(config)

    # 定义字段配置
    fields = [
        {"name": "quote", "selector": ".text", "attr": "text"},
        {"name": "author", "selector": ".author", "attr": "text"},
        {"name": "tags", "selector": ".tags", "attr": "text"},
    ]

    result = agent.scrape_with_selector(
        url="https://quotes.toscrape.com/",
        item_selector=".quote",
        fields=fields,
        max_pages=2,
    )

    print(f"抓取成功: {result.success}")
    for item in result.data[:3]:
        print(f"  Quote: {item.get('quote', '')[:50]}...")
        print(f"  Author: {item.get('author')}")
        print()


def example_analyze_page():
    """
    示例9: 分析页面结构

    在抓取前先分析页面，了解页面结构
    """
    from unified_agent import ScraperAgent, AgentConfig

    config = AgentConfig(proxy_enabled=False, headless=True)
    agent = ScraperAgent(config)

    # 分析页面
    analysis = agent.analyze("https://quotes.toscrape.com/", take_screenshot=True)

    print(f"URL: {analysis.url}")
    print(f"标题: {analysis.title}")
    print(f"页面类型: {analysis.page_type}")
    print(f"检测到的列表:")
    for lst in analysis.lists:
        print(f"  - 选择器: {lst['itemSelector']}, 数量: {lst['itemCount']}")
    print(f"分页模式: {analysis.pagination.get('mode', 'none')}")

    # 保存截图
    if analysis.screenshot_b64:
        import base64
        screenshot_bytes = base64.b64decode(analysis.screenshot_b64)
        Path("analysis_screenshot.png").write_bytes(screenshot_bytes)
        print("截图已保存: analysis_screenshot.png")


def example_export_data():
    """
    示例10: 导出数据

    将抓取的数据导出为 JSON 或 CSV
    """
    from unified_agent import ScraperAgent, AgentConfig

    config = AgentConfig(proxy_enabled=False, headless=True)
    agent = ScraperAgent(config)

    result = agent.scrape("https://quotes.toscrape.com/", max_pages=2)

    if result.success and result.data:
        # 导出为 JSON
        json_path = agent.export_data(result.data, "quotes", format="json")
        print(f"JSON 导出: {json_path}")

        # 导出为 CSV
        csv_path = agent.export_data(result.data, "quotes", format="csv")
        print(f"CSV 导出: {csv_path}")


# ==================== Cookie池示例 ====================

def example_cookie_pool():
    """
    示例12: 免费Cookie池

    自动通过浏览器访问网站生成Cookie，无需购买。
    """
    import asyncio
    from unified_agent import CookiePool

    async def demo():
        # 创建Cookie池
        pool = CookiePool("quotes.toscrape.com")

        # 查看当前状态
        print(f"当前Cookie池状态: {pool.stats()}")

        # 自动生成Cookie（通过浏览器访问）
        print("\n正在自动生成Cookie...")
        generated = await pool.generate(
            count=3,  # 生成3个Cookie
            url="https://quotes.toscrape.com/",
            wait_seconds=2.0,  # 等待2秒让Cookie设置
        )
        print(f"成功生成 {generated} 个Cookie")

        # 获取一个Cookie使用
        session = pool.get()
        if session:
            print(f"\n获取到Cookie会话: {session.id}")
            print(f"  Cookie数量: {len(session.cookies)}")
            print(f"  User-Agent: {session.user_agent[:50]}...")

            # 使用后报告结果
            pool.mark_success(session.id)  # 或 pool.mark_failed(session.id)

        # 查看更新后的状态
        print(f"\n更新后状态: {pool.stats()}")

    asyncio.run(demo())


def example_infrastructure_evaluation():
    """
    示例13: 基础设施自动评估

    Agent根据任务需求自动评估是否需要Cookie池等基础设施。
    """
    from unified_agent import Brain, AgentConfig

    brain = Brain(AgentConfig(proxy_enabled=False, headless=True))

    # 评估任务需求
    print("=" * 50)
    print("场景1: 爬取少量数据（100条）")
    print("=" * 50)
    advice = brain.evaluate_requirements(
        url="https://quotes.toscrape.com/",
        target_count=100,
        auto_analyze=False,  # 跳过网站分析，快速评估
    )
    print(advice)

    print("\n" + "=" * 50)
    print("场景2: 爬取大量京东数据（1000条）")
    print("=" * 50)
    advice = brain.evaluate_requirements(
        url="https://jd.com/search?q=手机",
        target_count=1000,
        auto_analyze=False,
    )
    print(advice)

    # 查看Cookie池状态
    print("\n" + "=" * 50)
    print("Cookie池状态")
    print("=" * 50)
    stats = brain.cookie_pool_stats("https://jd.com")
    print(f"京东Cookie池: {stats}")


def example_brain_with_cookie_pool():
    """
    示例14: Brain集成Cookie池

    使用Brain的Cookie池功能进行抓取。
    """
    import asyncio
    from unified_agent import Brain, AgentConfig

    async def demo():
        brain = Brain(AgentConfig(proxy_enabled=False, headless=True))

        url = "https://quotes.toscrape.com/"

        # 1. 准备Cookie池
        print("正在准备Cookie池...")
        await brain.prepare_cookie_pool(url, count=3)

        # 2. 使用Cookie池中的Cookie
        if brain.use_pool_cookie(url):
            print("已从Cookie池获取Cookie")

            # 3. 发起请求
            result = brain.call_api(url)
            print(f"请求结果: {result.to_ai_summary()}")

            # 4. 报告Cookie使用结果
            brain.report_cookie_result(result.success)
        else:
            print("Cookie池为空，需要先生成Cookie")

        # 5. 查看统计
        print(f"\nCookie池统计: {brain.cookie_pool_stats(url)}")

    asyncio.run(demo())


# ==================== 快捷函数示例 ====================

def example_quick_functions():
    """
    示例11: 使用快捷函数

    一行代码完成调查或抓取
    """
    from unified_agent import (
        quick_investigate,
        quick_smart_investigate,
        quick_scrape,
        get_site_info,
    )

    # 快速调查
    print("快速调查:")
    report = quick_investigate("https://quotes.toscrape.com/")
    print(report[:500] + "...")

    # 快速智能调查 (推荐)
    print("\n快速智能调查:")
    analysis = quick_smart_investigate("https://quotes.toscrape.com/")
    print(analysis[:500] + "...")

    # 查看网站信息
    print("\n网站预设信息:")
    info = get_site_info("jd.com")
    print(f"  京东: {info}")

    # 快速抓取
    print("\n快速抓取:")
    data = quick_scrape("https://quotes.toscrape.com/", max_pages=1)
    print(f"  获取 {len(data)} 条数据")


if __name__ == "__main__":
    print("=" * 60)
    print("Unified Agent v2.0 示例")
    print("=" * 60)

    print("\n" + "=" * 50)
    print("示例13: 基础设施自动评估 (重要!)")
    print("=" * 50)
    example_infrastructure_evaluation()

    print("\n" + "=" * 50)
    print("示例1: 智能调查 (推荐)")
    print("=" * 50)
    example_smart_investigate()

    print("\n" + "=" * 50)
    print("示例2: 查看预设配置")
    print("=" * 50)
    example_check_presets()

    print("\n" + "=" * 50)
    print("示例6: 基础抓取")
    print("=" * 50)
    example_basic_scrape()

    print("\n" + "=" * 50)
    print("示例8: 使用自定义选择器")
    print("=" * 50)
    example_custom_selector()

    print("\n" + "=" * 50)
    print("示例9: 分析页面结构")
    print("=" * 50)
    example_analyze_page()

    # 如需运行Cookie池示例，取消注释：
    # print("\n" + "=" * 50)
    # print("示例12: 免费Cookie池")
    # print("=" * 50)
    # example_cookie_pool()
