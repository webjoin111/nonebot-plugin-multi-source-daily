from io import BytesIO
from typing import Optional

from nonebot import logger, get_plugin_config

from .. import HAS_HTMLRENDER
from ..config import Config
from .cache import weibo_screenshot_cache


class WeiboScreenshotError(Exception):
    """微博截图错误"""

    pass


if HAS_HTMLRENDER:
    from nonebot_plugin_htmlrender import get_new_page

try:
    from PIL import Image, ImageEnhance

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL模块不可用，图片优化功能将受限")


def _generate_image_processing_script(additional_datasets=None, lazy_classes=None, with_margin=False):
    """生成图片处理脚本"""
    additional_datasets = additional_datasets or []
    lazy_classes = lazy_classes or ["lazyload"]

    dataset_processing = "\n".join(
        [
            f"                if (img.dataset.{dataset}) {{\n                    img.src = img.dataset.{dataset};\n                }}"
            for dataset in ["original", "src"] + additional_datasets
        ]
    )

    lazy_class_removes = "\n".join(
        [f"                img.classList.remove('{cls}');" for cls in lazy_classes]
    )

    margin_style = "img.style.margin = '10px auto';" if with_margin else ""

    return f"""
            const images = content.querySelectorAll('img');
            images.forEach(img => {{
                // 修复可能的图片显示问题
                img.style.display = 'block';
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
                {margin_style}

                // 处理懒加载图片
{dataset_processing}

                // 移除懒加载类
{lazy_class_removes}

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {{
                    const src = img.src;
                    setTimeout(() => {{
                        img.src = '';
                        img.src = src;
                    }}, 100);
                }}
            }});"""


def _generate_wait_for_images_script(additional_datasets=None):
    """生成等待图片加载的脚本"""
    additional_datasets = additional_datasets or []
    dataset_processing = "\n".join(
        [
            f"                if (img.dataset.{dataset}) {{\n                    img.src = img.dataset.{dataset};\n                }}"
            for dataset in ["original", "src"] + additional_datasets
        ]
    )

    return f"""
        const waitForImages = () => {{
            const images = document.querySelectorAll('img');
            images.forEach(img => {{
                // 处理懒加载图片
{dataset_processing}

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {{
                    const src = img.src;
                    img.src = '';
                    img.src = src;
                }}
            }});
        }};

        // 执行图片加载优化
        waitForImages();"""


COMMON_IMAGE_SCRIPT = """
    // 处理所有图片，尝试优化加载
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        // 处理懒加载图片
        if (img.dataset.original) {
            img.src = img.dataset.original;
        }

        if (img.dataset.src) {
            img.src = img.dataset.src;
        }

        // 移除懒加载类
        if (img.classList.contains('lazyload')) {
            img.classList.remove('lazyload');
        }

        // 如果图片没有加载，尝试重新加载
        if (!img.complete) {
            const src = img.src;
            img.src = '';
            img.src = src;
        }

        // 确保图片样式正确
        img.style.display = 'block';
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
    });
"""

SITE_SCRIPTS = {
    "ithome": f"""
        // 隐藏不需要的元素
        const elementsToHide = [
            '.header', '.nav', '.footer', '.sidebar',
            '.ad', '.advertisement', '#comment', '.comment',
            '.related', '.recommend', '.share', '.social',
            '.copyright', '.tags', '.author-info',
            '.dy-live-bar', '.ad-tips', '.lazyload-placeholder',
            '#dt > div.fr.fx', // 移除右侧浮动元素
            '#dt > div.fl.content > iframe', // 移除内容区域中的iframe
            '#post_comm' // 移除评论区
        ];

        for (const selector of elementsToHide) {{
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {{
                if (el) el.style.display = 'none';
            }}
        }}

        // 优化文章内容元素的显示
        const content = document.querySelector('#dt > div.fl.content');
        if (content) {{
            content.style.padding = '20px';
            content.style.margin = '0 auto';
            content.style.maxWidth = '100%';
            content.style.boxSizing = 'border-box';
            content.style.backgroundColor = '#ffffff';

            // 处理所有图片
{_generate_image_processing_script(with_margin=True)}

            // 移除所有iframe
            const iframes = content.querySelectorAll('iframe');
            iframes.forEach(iframe => {{
                iframe.remove();
            }});

            // 移除评论区和相关推荐
            const commentsAndRelated = content.querySelectorAll('#post_comm, .post_related, .post_comment, .post_next');
            commentsAndRelated.forEach(el => {{
                el.remove();
            }});
        }}

        // 确保标题显示
        const title = document.querySelector('.title');
        if (title) {{
            title.style.display = 'block';
            title.style.marginBottom = '20px';
            title.style.fontSize = '24px';
            title.style.fontWeight = 'bold';
        }}

        // 等待所有图片加载完成
{_generate_wait_for_images_script()}
    """,
    "知乎": f"""
        // 隐藏不需要的元素
        const elementsToHide = [
            '.Header', '.Sticky', '.Footer', '.CornerButtons',
            '.Topstory-container', '.Topstory-mainColumn', '.GlobalSideBar',
            '.Banner-link', '.Banner-image', '.Pc-word', '.Pc-feedAd',
            '.RichContent-actions', '.Post-topicsAndReviewer', '.Post-Sub',
            '.Post-NormalSub', '.Comments-container', '.RelatedReadings'
        ];

        for (const selector of elementsToHide) {{
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {{
                if (el) el.style.display = 'none';
            }}
        }}

        // 优化文章内容元素的显示
        const content = document.querySelector('#root');
        if (content) {{
            content.style.padding = '20px';
            content.style.margin = '0 auto';
            content.style.maxWidth = '100%';
            content.style.boxSizing = 'border-box';
            content.style.backgroundColor = '#ffffff';

            // 处理所有图片
{_generate_image_processing_script(additional_datasets=["actualsrc"], lazy_classes=["lazy"], with_margin=True)}

            // 处理可能的iframe（视频等）
            const iframes = content.querySelectorAll('iframe');
            iframes.forEach(iframe => {{
                iframe.style.maxWidth = '100%';
                iframe.style.display = 'block';
                iframe.style.margin = '10px auto';
            }});
        }}

        // 确保标题显示
        const title = document.querySelector('.Post-Title, .QuestionHeader-title');
        if (title) {{
            title.style.display = 'block';
            title.style.marginBottom = '20px';
            title.style.fontSize = '24px';
            title.style.fontWeight = 'bold';
        }}

        // 等待所有图片加载完成
{_generate_wait_for_images_script(["actualsrc"])}
    """,
    "微博热搜": f"""
        // 移除微博页面的干扰元素
        const elementsToRemove = [
            '.gn_nav', '.m-main-nav', '.main-side', '.gn_topmenulist',
            '.WB_frame_a', '.gn_header', '.m-box-center-a', '[class*="ad"]',
            '[class*="banner"]', '.WB_frame', '.gn_topmenu'
        ];

        elementsToRemove.forEach(selector => {{
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {{
                if (el && el.parentNode) {{
                    el.parentNode.removeChild(el);
                }}
            }});
        }});

        // 额外移除VIP图标容器
        const vipIcons = document.querySelectorAll('.user_vip_icon_container');
        vipIcons.forEach(el => {{
            if (el && el.parentNode) {{
                el.parentNode.removeChild(el);
            }}
        }});

        // 确保主要内容区域正确显示
        const feedlist = document.querySelector('#pl_feedlist_index');
        if (feedlist) {{
            feedlist.style.maxWidth = '100%';
            feedlist.style.padding = '20px';
            feedlist.style.backgroundColor = '#fff';
            feedlist.style.margin = '0 auto';
        }}

        // 优化微博卡片显示
        const cards = document.querySelectorAll('.card-wrap, .m-con-box, .card');
        cards.forEach(card => {{
            card.style.marginBottom = '15px';
            card.style.padding = '15px';
            card.style.border = '1px solid #e6e6e6';
            card.style.borderRadius = '8px';
            card.style.backgroundColor = '#fff';
        }});

        // 确保图片正确显示
        const images = document.querySelectorAll('img');
        images.forEach(img => {{
            if (img.dataset.src) {{
                img.src = img.dataset.src;
            }}
            img.style.maxWidth = '100%';
            img.style.height = 'auto';
        }});

        // 等待所有图片加载完成
{_generate_wait_for_images_script(["data-src", "src"])}
    """,
}

SITE_SELECTORS = {"ithome": "#dt > div.fl.content", "知乎": "#root", "微博热搜": "#pl_feedlist_index"}


async def capture_webpage_screenshot(
    url: str,
    site_type: str | None = None,
    selector: str | None = None,
    custom_script: str | None = None,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    wait_time: int = 2000,
    timeout: int = 30000,
) -> bytes | None:
    """获取网页截图"""
    if not HAS_HTMLRENDER:
        logger.warning("htmlrender插件不可用，无法获取网页截图")
        return None

    try:
        if site_type and site_type.lower() in SITE_SELECTORS:
            selector = selector or SITE_SELECTORS[site_type.lower()]
            custom_script = custom_script or SITE_SCRIPTS[site_type.lower()]

        async with get_new_page() as page:
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception as timeout_e:
                logger.warning(f"页面加载超时，尝试继续处理: {timeout_e}")

            await page.set_viewport_size({"width": viewport_width, "height": viewport_height})

            await page.evaluate(COMMON_IMAGE_SCRIPT)

            await page.wait_for_timeout(wait_time)

            if custom_script:
                try:
                    await page.evaluate(custom_script)
                    await page.wait_for_timeout(wait_time // 2)
                except Exception as script_e:
                    logger.warning(f"执行自定义脚本失败: {script_e}")

            if selector:
                try:
                    try:
                        await page.wait_for_selector(selector, timeout=8000)
                    except Exception as selector_e:
                        logger.warning(f"等待选择器超时: {selector_e}，尝试继续处理")

                    element = await page.query_selector(selector)
                    if element:
                        await page.evaluate(
                            """(selector) => {
                            const element = document.querySelector(selector);
                            if (element) {
                                // 添加内边距
                                element.style.padding = '20px';
                                element.style.boxSizing = 'border-box';
                                element.style.width = '100%';
                            }
                        }""",
                            selector,
                        )

                        await page.wait_for_timeout(wait_time // 2)

                        pic = await element.screenshot(type="jpeg", quality=75)
                        return optimize_image(pic)
                    else:
                        logger.warning(f"未找到元素: {selector}")
                        pic = await page.screenshot(full_page=True, type="jpeg", quality=75)
                        return optimize_image(pic)
                except Exception as element_e:
                    logger.warning(f"截取元素失败: {element_e}，将截取整个页面")
                    pic = await page.screenshot(full_page=True, type="jpeg", quality=75)
                    return optimize_image(pic)
            else:
                pic = await page.screenshot(full_page=True, type="jpeg", quality=75)
                return optimize_image(pic)
    except Exception as e:
        logger.error(f"获取网页截图失败: {e}")
        return None


def optimize_image(image_data: bytes, max_size: int = 3 * 1024 * 1024) -> bytes:
    """优化图片大小"""
    if len(image_data) <= max_size:
        return image_data

    if not HAS_PIL:
        logger.warning(f"PIL不可用，无法优化图片，原始大小: {len(image_data) / 1024:.1f}KB")
        return image_data

    try:
        img = Image.open(BytesIO(image_data))

        quality = 75
        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        current_size = output.getbuffer().nbytes

        while current_size > max_size and quality > 30:
            quality -= 5
            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            current_size = output.getbuffer().nbytes

        if current_size > max_size:
            scale_factor = (max_size / current_size) ** 0.5
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)

            if new_width < 800:
                new_width = 800
                new_height = int(img.height * (800 / img.width))

            img = img.resize((new_width, new_height), Image.LANCZOS)

            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)

        original_size = len(image_data) / 1024
        new_size = output.getbuffer().nbytes / 1024
        logger.info(
            f"图片已优化: 原始大小={original_size:.1f}KB, 优化后大小={new_size:.1f}KB, 质量={quality}"
        )
        return output.getvalue()
    except Exception as e:
        logger.error(f"图片优化失败: {e}")
        return image_data


class WeiboScreenshotTool:
    """微博截图工具类"""

    def __init__(self):
        self.viewport_width = 1400
        self.viewport_height = 900
        self.wait_time = 2000
        self.timeout = 20000
        self.short_timeout = 5000

    def _get_cookie(self) -> str:
        """获取微博Cookie"""
        config = get_plugin_config(Config)
        cookie = config.weibo_cookie.strip()
        logger.debug(f"微博Cookie: {cookie}")
        if not cookie:
            logger.warning("微博Cookie未配置，无法进行微博截图")
        return cookie

    def _is_cookie_valid(self, cookie: str) -> bool:
        """检查Cookie是否有效"""
        if not cookie:
            return False

        required_fields = ["SUB=", "SUBP="]
        return any(field in cookie for field in required_fields)

    def _get_weibo_optimization_script(self) -> str:
        """获取微博页面优化脚本"""
        return """
        (() => {
            // 简化的页面优化脚本
            try {
                // 移除微博页面的干扰元素
                const elementsToRemove = [
                    '.gn_nav', '.m-main-nav', '.main-side', '.gn_topmenulist',
                    '.WB_frame_a', '.gn_header', '.m-box-center-a',
                    '.WB_frame', '.gn_topmenu', '.gn_login',
                    '.user_vip_icon_container'  // 移除VIP图标容器
                ];

                elementsToRemove.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el && el.parentNode) {
                                el.style.display = 'none';
                            }
                        });
                    } catch (e) {
                        console.log('移除元素失败:', selector, e);
                    }
                });

                // 确保图片正确显示
                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    try {
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                        }
                        if (img.dataset.original) {
                            img.src = img.dataset.original;
                        }
                        img.style.maxWidth = '100%';
                        img.style.height = 'auto';
                    } catch (e) {
                        console.log('处理图片失败:', e);
                    }
                });

            } catch (e) {
                console.log('页面优化脚本执行失败:', e);
            }
        })()
        """

    def _optimize_image_quality(self, image_data: bytes) -> bytes:
        """优化图片质量"""
        if not HAS_PIL:
            logger.debug("PIL未安装，跳过图片质量优化")
            return image_data

        try:
            img = Image.open(BytesIO(image_data))

            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)

            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)

            output = BytesIO()
            img.save(output, format="PNG", optimize=True, quality=95)

            logger.debug("截图质量已优化")
            return output.getvalue()

        except Exception as e:
            logger.warning(f"图片质量优化失败: {e}")
            return image_data

    async def capture_weibo_screenshot(self, url: str) -> Optional[bytes]:
        """捕获微博页面截图"""
        if not HAS_HTMLRENDER:
            logger.error("htmlrender插件不可用，无法进行微博截图")
            return None

        cookie = self._get_cookie()
        if not self._is_cookie_valid(cookie):
            logger.error("微博Cookie无效或未配置，无法进行微博截图。请配置有效的微博Cookie后重试。")
            return None

        cached_data = weibo_screenshot_cache.get(url, "png")
        if cached_data:
            logger.info("使用缓存的微博截图")
            return cached_data

        try:
            weibo_screenshot_cache.cleanup_expired()
        except Exception as e:
            logger.debug(f"清理缓存时出错: {e}")

        try:
            async with get_new_page() as page:
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )

                await page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})

                logger.debug("设置微博Cookie...")
                for cookie_item in cookie.split(";"):
                    if "=" in cookie_item:
                        name, value = cookie_item.split("=", 1)
                        try:
                            await page.context.add_cookies(
                                [
                                    {
                                        "name": name.strip(),
                                        "value": value.strip(),
                                        "domain": ".weibo.com",
                                        "path": "/",
                                    }
                                ]
                            )
                        except Exception as cookie_e:
                            logger.debug(f"设置Cookie失败: {cookie_e}")

                logger.debug(f"正在访问微博页面: {url}")

                try:
                    logger.debug("开始加载页面...")
                    await page.goto(url, wait_until="load", timeout=self.timeout)
                    logger.debug("页面基本加载完成，等待动态内容...")

                    await page.wait_for_timeout(5000)

                    page_title = await page.title()
                    logger.debug(f"页面标题: {page_title}")

                except Exception as timeout_e:
                    logger.warning(f"页面加载超时，尝试继续处理: {timeout_e}")

                logger.debug("执行页面优化脚本...")
                try:
                    await page.evaluate(self._get_weibo_optimization_script())
                    logger.debug("页面优化脚本执行完成")
                except Exception as script_e:
                    logger.warning(f"执行优化脚本失败: {script_e}")

                logger.debug("等待页面最终稳定...")
                await page.wait_for_timeout(self.wait_time)

                logger.debug("尝试截取 #pl_feedlist_index 元素...")
                try:
                    logger.debug("等待 #pl_feedlist_index 元素出现...")
                    await page.wait_for_selector("#pl_feedlist_index", timeout=10000)
                    logger.debug("#pl_feedlist_index 元素已找到")

                    element = await page.query_selector("#pl_feedlist_index")
                    if element:
                        logger.debug("开始优化元素样式...")
                        await page.evaluate("""
                            (() => {
                                const element = document.querySelector('#pl_feedlist_index');
                                if (element) {
                                    element.style.padding = '20px';
                                    element.style.boxSizing = 'border-box';
                                    element.style.width = '100%';
                                    element.style.backgroundColor = '#fff';
                                    element.style.margin = '0 auto';
                                }
                            })()
                        """)

                        await page.wait_for_timeout(1000)

                        logger.debug("开始截取元素...")
                        pic = await element.screenshot(type="png")
                        logger.info("微博 #pl_feedlist_index 元素截图生成成功")

                        optimized_pic = self._optimize_image_quality(pic)

                        weibo_screenshot_cache.set(url, optimized_pic, "png")

                        return optimized_pic
                    else:
                        logger.warning("query_selector 返回了 None")

                except Exception as element_e:
                    logger.warning(f"截取 #pl_feedlist_index 元素失败: {element_e}")

                logger.debug("回退到全页面截图...")
                pic = await page.screenshot(full_page=True, type="png")
                logger.info("微博全页面截图生成成功")

                optimized_pic = self._optimize_image_quality(pic)

                weibo_screenshot_cache.set(url, optimized_pic, "png")

                return optimized_pic

        except Exception as e:
            logger.error(f"微博截图失败: {e}")
            return None


weibo_screenshot_tool = WeiboScreenshotTool()


async def capture_weibo_screenshot(url: str, raise_on_error: bool = False) -> Optional[bytes]:
    """获取微博截图"""
    try:
        result = await weibo_screenshot_tool.capture_weibo_screenshot(url)
        if result is None and raise_on_error:
            cookie = weibo_screenshot_tool._get_cookie()
            if not weibo_screenshot_tool._is_cookie_valid(cookie):
                raise WeiboScreenshotError("微博Cookie无效或未配置，请配置有效的微博Cookie后重试")
            else:
                raise WeiboScreenshotError("微博截图失败，请检查网络连接或稍后重试")
        return result
    except Exception as e:
        if raise_on_error:
            if isinstance(e, WeiboScreenshotError):
                raise
            else:
                raise WeiboScreenshotError(f"微博截图失败: {e}")
        else:
            logger.error(f"微博截图失败: {e}")
            return None


def clear_weibo_screenshot_cache() -> int:
    """清理所有微博截图缓存"""
    return weibo_screenshot_cache.clear_all()


def get_weibo_screenshot_cache_info() -> dict:
    """获取微博截图缓存信息"""
    return weibo_screenshot_cache.get_cache_info()
