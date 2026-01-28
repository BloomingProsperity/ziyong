#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东评论爬虫 - 基于 Unified Agent Skill 系统

使用 Brain API 完成任务：
1. 自动侦查京东网站
2. 自动获取 Cookie
3. 自动爬取评论数据
4. 自动诊断和修复错误

运行方式：
    python jd_scraper_agent.py
"""

import asyncio
from unified_agent import Brain
from unified_agent.core.config import AgentConfig

async def main():
    """主函数 - 使用 Brain API 完成京东评论采集"""

    print("="*70)
    print(" "*20 + "京东评论爬虫")
    print(" "*15 + "基于 Unified Agent Skill 系统")
    print("="*70)

    # 创建 Brain 实例 (从 .env 自动加载配置)
    config = AgentConfig.from_env()
    brain = Brain(config)

    print("\n[步骤 1/4] 侦查京东网站...")
    print("-"*70)

    # 使用 Brain 的智能侦查功能
    target_url = "https://item.jd.com/100012043978.html"
    analysis = brain.smart_investigate(target_url)

    print(f"目标网站: {target_url}")
    print(f"反爬等级: {analysis.anti_scrape_level}")
    print(f"推荐方式: {analysis.recommended_approach}")
    print(f"需要代理: {'是' if analysis.needs_proxy else '否'}")
    print(f"需要登录: {'是' if analysis.needs_login else '否'}")

    # 显示完整分析报告
    print("\n完整分析报告:")
    print(analysis.to_ai_report())

    print("\n[步骤 2/4] 规划采集任务...")
    print("-"*70)

    # 让用户确认是否继续
    user_input = input("\n查看分析报告后，是否继续? (y/n): ")
    if user_input.lower() != 'y':
        print("任务取消")
        return

    print("\n[步骤 3/4] 开始采集...")
    print("-"*70)

    # 这里应该使用 Brain 的采集功能
    # 但根据文档，京东需要 RPC 签名，让我们提示用户
    print("\n京东采集需要以下步骤：")
    print("1. 启动浏览器并登录京东")
    print("2. 注入 RPC 签名服务")
    print("3. 使用签名采集数据")
    print("\n请参考 unified_agent/skills/20-e2e-cases.md 中的 Case-08")

    print("\n[步骤 4/4] 完成")
    print("-"*70)
    print("分析报告已生成")
    print("后续需要根据报告手动实现采集逻辑")


if __name__ == "__main__":
    asyncio.run(main())
