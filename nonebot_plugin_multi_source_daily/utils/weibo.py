"""微博详情获取工具"""

import re
import httpx
from typing import Optional
from nonebot import logger, get_plugin_config

from ..config import Config


class WeiboDetailFetcher:
    """微博详情获取器"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_cookie(self) -> str:
        """获取微博Cookie"""
        config = get_plugin_config(Config)
        cookie = config.weibo_cookie.strip()
        if not cookie:
            logger.warning("微博Cookie未配置，无法获取微博详情")
        return cookie

    def _is_cookie_valid(self, cookie: str) -> bool:
        """检查Cookie是否有效"""
        if not cookie:
            return False

        required_fields = ["SUB=", "SUBP="]
        return any(field in cookie for field in required_fields)

    async def get_weibo_detail(self, url: str) -> Optional[str]:
        """获取微博详情内容

        Args:
            url: 微博链接

        Returns:
            微博详情文本内容，如果获取失败返回None
        """
        cookie = self._get_cookie()
        if not self._is_cookie_valid(cookie):
            logger.warning("微博Cookie无效或未配置，无法获取详情")
            return None

        try:
            if "t.cn" in url or "weibo.cn" in url:
                url = await self._resolve_short_url(url, cookie)
                if not url:
                    return None

            weibo_id = self._extract_weibo_id(url)
            if not weibo_id:
                logger.error(f"无法从URL中提取微博ID: {url}")
                return None

            detail_url = f"https://weibo.com/ajax/statuses/show?id={weibo_id}"

            headers = self.headers.copy()
            headers["Cookie"] = cookie
            headers["Referer"] = "https://weibo.com/"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(detail_url, headers=headers)

                if response.status_code != 200:
                    logger.error(f"获取微博详情失败，状态码: {response.status_code}")
                    return None

                data = response.json()
                if not data.get("ok"):
                    logger.error(f"微博API返回错误: {data}")
                    return None

                weibo_data = data.get("data", {})
                return self._parse_weibo_content(weibo_data)

        except Exception as e:
            logger.error(f"获取微博详情时发生错误: {e}")
            return None

    async def _resolve_short_url(self, short_url: str, cookie: str) -> Optional[str]:
        """解析短链接为完整链接"""
        try:
            headers = self.headers.copy()
            headers["Cookie"] = cookie

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(short_url, headers=headers)
                return str(response.url)
        except Exception as e:
            logger.error(f"解析短链接失败: {e}")
            return None

    def _extract_weibo_id(self, url: str) -> Optional[str]:
        """从URL中提取微博ID"""
        patterns = [
            r"/(\d+)/([A-Za-z0-9]+)",
            r"weibo\.com/\d+/([A-Za-z0-9]+)",
            r"m\.weibo\.cn/detail/([A-Za-z0-9]+)",
            r"weibo\.com/ajax/statuses/show\?id=([A-Za-z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(-1)

        return None

    def _parse_weibo_content(self, weibo_data: dict) -> str:
        """解析微博内容"""
        try:
            text = weibo_data.get("text_raw", "") or weibo_data.get("text", "")
            user_info = weibo_data.get("user", {})
            user_name = user_info.get("screen_name", "未知用户")

            text = re.sub(r"<[^>]+>", "", text)

            retweeted_status = weibo_data.get("retweeted_status")
            if retweeted_status:
                retweeted_text = retweeted_status.get("text_raw", "") or retweeted_status.get("text", "")
                retweeted_text = re.sub(r"<[^>]+>", "", retweeted_text)
                retweeted_user = retweeted_status.get("user", {}).get("screen_name", "未知用户")

                content = f"【{user_name}】\n{text}\n\n转发自 @{retweeted_user}:\n{retweeted_text}"
            else:
                content = f"【{user_name}】\n{text}"

            attitudes_count = weibo_data.get("attitudes_count", 0)
            comments_count = weibo_data.get("comments_count", 0)
            reposts_count = weibo_data.get("reposts_count", 0)

            content += f"\n\n👍 {attitudes_count} | 💬 {comments_count} | 🔄 {reposts_count}"

            return content.strip()

        except Exception as e:
            logger.error(f"解析微博内容失败: {e}")
            return "解析微博内容失败"


weibo_detail_fetcher = WeiboDetailFetcher()


async def get_weibo_detail(url: str) -> Optional[str]:
    """获取微博详情的便捷函数"""
    return await weibo_detail_fetcher.get_weibo_detail(url)
