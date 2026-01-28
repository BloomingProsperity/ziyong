"""
京东评论爬虫 - 网络拦截方案

通过拦截浏览器的真实API请求，捕获有效的h5st签名，
然后复用这些签名来获取更多评论数据。

核心思路：
1. 浏览器访问商品页并滚动到评论区
2. 浏览器会自动发起带有效h5st的API请求
3. 拦截这些请求，提取h5st签名
4. 复用签名参数请求更多页的评论
"""

import asyncio
import json
import hashlib
import random
import re
import csv
import logging
import sys
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import parse_qs, urlparse, urlencode

# Windows控制台UTF-8支持
if sys.platform == "win32":
    os.system("")  # 启用ANSI转义序列

logger = logging.getLogger(__name__)


def log(msg: str):
    """输出日志（确保flush）"""
    print(msg, flush=True)


@dataclass
class Comment:
    """评论数据"""
    user_id: str
    comment_time: str
    brand: str
    price: float
    content: str
    score: int
    comment_type: str
    sku_id: str = ""
    product_name: str = ""

    def to_homework_dict(self) -> Dict[str, Any]:
        return {
            "用户ID": self.user_id,
            "产品系列": self.brand,
            "产品款式": self.product_name,
            "产品价格": self.price,
            "评分": self.comment_type,
            "评论时间": self.comment_time,
            "评论内容": self.content,
        }


# 品牌SKU配置 - 使用有效的空调SKU
BRAND_SKUS = {
    "美的": ["100084572498", "100070680714"],
    "格力": ["100055091610", "100042428382"],
    "小米": ["100072912534", "100082457858"],
    "海尔": ["100055149416", "100070711618"],
    "海信": ["100055161524", "100070754804"],
    "TCL": ["100042595680", "100070758922"],
    "奥克斯": ["100042579776", "100070680726"],
    "新飞": ["100082432498"],
    "长虹": ["100042442392"],
    "松下": ["100042511956"],
}

# 请求延迟配置（秒）
DELAY_CONFIG = {
    "page_load": (8, 15),      # 页面加载后等待
    "scroll": (2, 4),          # 滚动间隔
    "click": (3, 6),           # 点击操作后等待
    "next_page": (4, 8),       # 翻页后等待
    "next_product": (15, 30),  # 产品间延迟
    "next_brand": (30, 60),    # 品牌间延迟
}


class JDInterceptScraper:
    """
    京东评论拦截爬虫

    通过网络请求拦截获取真实的API响应数据
    """

    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.browser = None
        self.context = None
        self.page = None

        # 存储拦截到的评论数据
        self._intercepted_comments: List[Dict] = []
        self._seen_comments: set = set()

        # 统计
        self._stats = {
            "intercepted_requests": 0,
            "total_comments": 0,
            "valid_comments": 0,
        }

    async def init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        self.browser = await self._playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self.page = await self.context.new_page()

        # 设置请求拦截
        await self._setup_interception()

        log("[OK] 浏览器已启动，网络拦截已启用")
        return True

    async def _setup_interception(self):
        """设置网络请求拦截"""

        async def handle_response(response):
            """处理响应"""
            url = response.url

            # 拦截多种可能的评论API
            is_comment_api = (
                ("api.m.jd.com" in url and "getComment" in url) or
                ("club.jd.com" in url and "comment" in url.lower()) or
                ("api.m.jd.com" in url and "comment" in url.lower()) or
                ("sclub.jd.com" in url)
            )

            if is_comment_api:
                try:
                    self._stats["intercepted_requests"] += 1
                    log(f"    [拦截] 发现评论API: {url[:80]}...")

                    # 获取响应内容
                    body = await response.text()

                    # 尝试解析JSON
                    try:
                        data = json.loads(body)
                    except:
                        # 可能是JSONP格式
                        if body.startswith("fetchJSON"):
                            json_str = body[body.index("(")+1:body.rindex(")")]
                            data = json.loads(json_str)
                        else:
                            return

                    # 解析评论
                    comments = self._extract_comments_from_response(data)

                    if comments:
                        log(f"    [拦截] 捕获到 {len(comments)} 条评论")
                        self._intercepted_comments.extend(comments)
                    else:
                        log(f"    [拦截] API响应无评论数据")

                except Exception as e:
                    log(f"    [拦截] 解析失败: {e}")

        # 绑定响应事件
        self.page.on("response", handle_response)

    def _extract_comments_from_response(self, data: Dict) -> List[Dict]:
        """从API响应中提取评论"""
        comments = []

        # 尝试多种路径
        comment_list = None

        if data.get("comments"):
            comment_list = data["comments"]
        elif data.get("result", {}).get("comments"):
            comment_list = data["result"]["comments"]
        elif data.get("commentInfoList"):
            comment_list = data["commentInfoList"]
        elif data.get("data", {}).get("comments"):
            comment_list = data["data"]["comments"]

        if not comment_list:
            return []

        for item in comment_list:
            content = item.get("content", "").strip()

            # 过滤太短的评论
            if len(content) < 10:
                continue

            # 去重
            content_hash = hashlib.md5(content[:50].encode()).hexdigest()
            if content_hash in self._seen_comments:
                continue
            self._seen_comments.add(content_hash)

            comments.append({
                "content": content,
                "score": item.get("score", 5),
                "creationTime": item.get("creationTime", ""),
                "nickname": item.get("nickname", ""),
                "productName": item.get("referenceName", "") or item.get("productName", ""),
            })

        return comments

    async def login(self, timeout: int = 300):
        """登录京东"""
        # 尝试加载本地Cookie
        cookie_file = self.output_dir / "cookies.json"
        if cookie_file.exists():
            try:
                cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
                await self.context.add_cookies(cookies)
                log("[OK] 已加载本地Cookie")

                # 验证Cookie
                await self.page.goto("https://www.jd.com/", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                cookies = await self.context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in cookies}

                if cookie_dict.get("pin") or cookie_dict.get("pt_key"):
                    log(f"    用户: {cookie_dict.get('unick', '已登录')}")
                    return True

            except Exception as e:
                log(f"    Cookie失效: {e}")

        # 需要手动登录
        await self.page.goto("https://passport.jd.com/new/login.aspx", timeout=60000)

        log("\n" + "="*60)
        log("请在浏览器中手动登录京东账号")
        log("登录成功后会自动继续...")
        log("="*60 + "\n")

        try:
            await self.page.wait_for_url(
                lambda url: "jd.com" in url and "passport" not in url,
                timeout=300000,
            )
            await asyncio.sleep(3)

            # 保存Cookie
            cookies = await self.context.cookies()
            cookie_file.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
            log("[OK] 登录成功，Cookie已保存")
            return True

        except Exception as e:
            log(f"[X] 登录超时: {e}")
            return False

    async def _safe_evaluate(self, script: str, default=None):
        """安全执行JavaScript，处理导航中断等异常"""
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            if "Execution context was destroyed" in str(e):
                # 页面正在导航，等待稳定后重试
                await asyncio.sleep(2)
                try:
                    return await self.page.evaluate(script)
                except:
                    pass
            logger.debug(f"[JS执行] 失败: {e}")
            return default

    async def _extract_comments_from_dom(self, sku_id: str, brand: str) -> List[Dict]:
        """从页面DOM中提取评论"""
        comments = []
        try:
            # 使用JavaScript提取评论
            js_comments = await self._safe_evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();

                    // 方法1: 查找评论容器
                    const commentContainers = document.querySelectorAll(
                        '.comment-item, .comment-con, [class*="CommentItem"], ' +
                        '.J-comment-item, [data-tab="trigger"][data-anchor*="comment"]'
                    );

                    for (const container of commentContainers) {
                        // 查找评论内容
                        const contentEl = container.querySelector(
                            '.comment-con, p, [class*="content"], [class*="Content"]'
                        );
                        if (!contentEl) continue;

                        const content = contentEl.textContent.trim();
                        if (content.length < 15 || seen.has(content)) continue;
                        seen.add(content);

                        // 查找用户名
                        const userEl = container.querySelector('[class*="user"], [class*="User"], .user-info');
                        const user = userEl ? userEl.textContent.trim().substring(0, 20) : '';

                        // 查找时间
                        const timeEl = container.querySelector('[class*="time"], [class*="Time"], .comment-date');
                        const time = timeEl ? timeEl.textContent.trim() : '';

                        results.push({
                            content: content.substring(0, 500),
                            user: user,
                            time: time,
                            score: 5  // 默认好评
                        });
                    }

                    // 方法2: 直接查找长文本
                    if (results.length === 0) {
                        const commentRoot = document.querySelector('.comment-root, .comment, #comment, [id*="comment"]');
                        if (commentRoot) {
                            const paragraphs = commentRoot.querySelectorAll('p, div');
                            for (const p of paragraphs) {
                                const text = p.textContent.trim();
                                if (text.length > 20 && text.length < 500 && !seen.has(text)) {
                                    // 过滤掉明显不是评论的内容
                                    if (text.includes('评价') && text.length < 30) continue;
                                    if (text.match(/^\\d+人/)) continue;
                                    if (text.includes('追评') && text.length < 20) continue;

                                    seen.add(text);
                                    results.push({
                                        content: text,
                                        user: '',
                                        time: '',
                                        score: 5
                                    });
                                }
                            }
                        }
                    }

                    return results.slice(0, 50);
                }
            """, default=[])

            if js_comments:
                log(f"      从DOM提取到 {len(js_comments)} 条评论")
                for item in js_comments:
                    if item.get("content"):
                        comments.append({
                            "content": item["content"],
                            "nickname": item.get("user", ""),
                            "creationTime": item.get("time", ""),
                            "score": item.get("score", 5),
                            "productName": f"{brand}空调",
                        })

        except Exception as e:
            log(f"      DOM提取失败: {e}")

        return comments

    async def scrape_product_comments(
        self,
        sku_id: str,
        brand: str,
        target_good: int = 50,
        target_bad: int = 10,
    ) -> List[Comment]:
        """
        爬取单个商品的评论

        通过访问页面并滚动触发浏览器自动加载评论API
        """
        comments = []
        self._intercepted_comments.clear()

        product_url = f"https://item.jd.com/{sku_id}.html"
        log(f"\n  >>> SKU {sku_id} ({brand})")

        try:
            # 1. 访问商品页
            await self.page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(*DELAY_CONFIG["page_load"]))  # 页面加载后等待

            # 检查页面是否正常
            current_url = self.page.url
            if "item.jd.com" not in current_url:
                log(f"      [!] 页面被重定向，跳过")
                return []

            # 2. 模拟真实浏览行为 - 缓慢滚动到评论区
            log("      模拟浏览...")

            for scroll_pct in [0.2, 0.4, 0.6, 0.8]:
                await self._safe_evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct})")
                await asyncio.sleep(random.uniform(*DELAY_CONFIG["scroll"]))

            # 3. 点击评论标签
            await self._safe_evaluate("""
                () => {
                    // 尝试点击"商品评价"标签
                    const tabs = document.querySelectorAll('.tab-con li, [class*="tab"] li, nav li');
                    for (const tab of tabs) {
                        if (tab.textContent.includes('评价') || tab.textContent.includes('评论')) {
                            tab.click();
                            break;
                        }
                    }
                }
            """)
            await asyncio.sleep(random.uniform(*DELAY_CONFIG["click"]))

            # 4. 继续缓慢滚动触发评论加载
            for _ in range(3):
                await self._safe_evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(random.uniform(*DELAY_CONFIG["scroll"]))

            # 5. 点击好评/差评筛选并翻页
            for score_type in ["good", "bad"]:
                target = target_good if score_type == "good" else target_bad
                collected = 0

                # 点击筛选
                filter_text = "好评" if score_type == "good" else "差评"
                await self._safe_evaluate(f"""
                    () => {{
                        const elements = document.querySelectorAll('li, span, div, a');
                        for (const el of elements) {{
                            if (el.textContent.includes('{filter_text}') && el.textContent.length < 20) {{
                                el.click();
                                break;
                            }}
                        }}
                    }}
                """)
                await asyncio.sleep(random.uniform(*DELAY_CONFIG["click"]))

                # 翻页获取更多（减少翻页数量）
                max_pages = min(target // 10 + 1, 5)
                for page_num in range(max_pages):
                    # 滚动触发加载
                    await self._safe_evaluate("window.scrollBy(0, 300)")
                    await asyncio.sleep(random.uniform(*DELAY_CONFIG["scroll"]))

                    # 检查拦截到的评论数
                    if len(self._intercepted_comments) >= collected + 10:
                        collected = len(self._intercepted_comments)

                    # 点击下一页
                    next_clicked = await self._safe_evaluate("""
                        () => {
                            const nextBtns = document.querySelectorAll('.ui-pager-next, [class*="next"]');
                            for (const btn of nextBtns) {
                                if (!btn.classList.contains('disabled') && !btn.disabled) {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """, default=False)

                    if not next_clicked:
                        break

                    await asyncio.sleep(random.uniform(*DELAY_CONFIG["next_page"]))

            # 6. 如果拦截没有获取到评论，尝试从DOM提取
            if len(self._intercepted_comments) == 0:
                log("      尝试从页面DOM提取评论...")
                dom_comments = await self._extract_comments_from_dom(sku_id, brand)
                self._intercepted_comments.extend(dom_comments)

            log(f"      获取到 {len(self._intercepted_comments)} 条原始评论")

            for item in self._intercepted_comments:
                content = item.get("content", "").strip()
                if len(content) < 10:
                    continue

                # 过滤无效评论
                if any(x in content for x in ["此用户未填写", "默认好评", "系统默认"]):
                    continue

                score = item.get("score", 5)
                comment_type = "好评" if score >= 4 else ("中评" if score == 3 else "差评")

                nickname = item.get("nickname", "")
                user_id = hashlib.md5(nickname.encode()).hexdigest()[:12] if nickname else hashlib.md5(content[:20].encode()).hexdigest()[:12]

                comment = Comment(
                    user_id=user_id,
                    comment_time=item.get("creationTime", ""),
                    brand=brand,
                    price=0.0,
                    content=content,
                    score=score,
                    comment_type=comment_type,
                    sku_id=sku_id,
                    product_name=item.get("productName", f"{brand}空调"),
                )
                comments.append(comment)

            self._stats["total_comments"] += len(comments)
            self._stats["valid_comments"] += len(comments)

            log(f"      有效评论: {len(comments)} 条")

        except Exception as e:
            log(f"      [!] 错误: {e}")
            logger.error(f"[JDInterceptScraper] SKU {sku_id} 爬取失败: {e}")

        # 产品间延迟（较长，避免触发反爬）
        delay = random.uniform(*DELAY_CONFIG["next_product"])
        log(f"      等待 {delay:.0f} 秒后继续...")
        await asyncio.sleep(delay)

        return comments

    async def scrape_brand(
        self,
        brand: str,
        target_good: int = 1350,
        target_bad: int = 150,
    ) -> List[Comment]:
        """爬取单个品牌的评论"""
        sku_ids = BRAND_SKUS.get(brand, [])
        if not sku_ids:
            log(f"[!] 品牌 {brand} 没有配置SKU")
            return []

        log(f"\n{'='*50}")
        log(f"品牌: {brand} (目标: {target_good}好评 + {target_bad}差评)")
        log(f"{'='*50}")

        all_comments = []

        good_per_sku = target_good // len(sku_ids) + 1
        bad_per_sku = target_bad // len(sku_ids) + 1

        for sku_id in sku_ids:
            # 检查是否已达目标
            good_count = sum(1 for c in all_comments if c.comment_type == "好评")
            bad_count = sum(1 for c in all_comments if c.comment_type != "好评")

            if good_count >= target_good and bad_count >= target_bad:
                break

            need_good = max(0, target_good - good_count)
            need_bad = max(0, target_bad - bad_count)

            comments = await self.scrape_product_comments(
                sku_id=sku_id,
                brand=brand,
                target_good=min(need_good, good_per_sku),
                target_bad=min(need_bad, bad_per_sku),
            )
            all_comments.extend(comments)

        good_final = sum(1 for c in all_comments if c.comment_type == "好评")
        bad_final = sum(1 for c in all_comments if c.comment_type != "好评")
        log(f"\n  {brand} 完成: 好评{good_final}, 差评/中评{bad_final}")

        return all_comments

    async def scrape_all_brands(
        self,
        good_per_brand: int = 1350,
        bad_per_brand: int = 150,
    ) -> List[Comment]:
        """爬取所有品牌"""
        all_comments = []

        for brand in BRAND_SKUS.keys():
            comments = await self.scrape_brand(
                brand=brand,
                target_good=good_per_brand,
                target_bad=bad_per_brand,
            )
            all_comments.extend(comments)

            # 品牌间延迟（更长）
            delay = random.uniform(*DELAY_CONFIG["next_brand"])
            log(f"\n[休息] 品牌间延迟 {delay:.0f} 秒...")
            await asyncio.sleep(delay)

        return all_comments

    def export_csv(self, comments: List[Comment], filename: str = "jd_comments.csv") -> Path:
        """导出CSV"""
        output_path = self.output_dir / filename

        fieldnames = ["用户ID", "产品系列", "产品款式", "产品价格", "评分", "评论时间", "评论内容"]

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for comment in comments:
                writer.writerow(comment.to_homework_dict())

        log(f"\n[OK] 已导出: {output_path}")
        log(f"    总计: {len(comments)} 条评论")

        return output_path

    def get_stats(self) -> Dict:
        """获取统计"""
        return self._stats

    async def close(self):
        """关闭"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()


async def main():
    """主函数"""
    log("\n" + "="*60)
    log("  京东评论爬虫 - 网络拦截方案")
    log("="*60)

    scraper = JDInterceptScraper()

    try:
        # 初始化
        await scraper.init_browser()

        # 登录
        if not await scraper.login():
            return

        # 爬取
        comments = await scraper.scrape_all_brands()

        # 导出
        if comments:
            scraper.export_csv(comments)

            stats = scraper.get_stats()
            log(f"\n统计:")
            log(f"  - 拦截请求: {stats['intercepted_requests']}")
            log(f"  - 总评论: {stats['total_comments']}")
            log(f"  - 有效评论: {stats['valid_comments']}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
