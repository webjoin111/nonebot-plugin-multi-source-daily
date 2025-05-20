from io import BytesIO

from nonebot import logger

from .. import HAS_HTMLRENDER

if HAS_HTMLRENDER:
    from nonebot_plugin_htmlrender import get_new_page

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL模块不可用，图片优化功能将受限")

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
    "ithome": """
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

        for (const selector of elementsToHide) {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                if (el) el.style.display = 'none';
            }
        }

        // 优化文章内容元素的显示
        const content = document.querySelector('#dt > div.fl.content');
        if (content) {
            content.style.padding = '20px';
            content.style.margin = '0 auto';
            content.style.maxWidth = '100%';
            content.style.boxSizing = 'border-box';
            content.style.backgroundColor = '#ffffff';

            // 处理所有图片
            const images = content.querySelectorAll('img');
            images.forEach(img => {
                // 修复可能的图片显示问题
                img.style.display = 'block';
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
                img.style.margin = '10px auto';

                // 处理懒加载图片
                if (img.dataset.original) {
                    img.src = img.dataset.original;
                }

                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }

                // 移除懒加载类
                img.classList.remove('lazyload');

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {
                    const src = img.src;
                    setTimeout(() => {
                        img.src = '';
                        img.src = src;
                    }, 100);
                }
            });

            // 移除所有iframe
            const iframes = content.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                iframe.remove();
            });

            // 移除评论区和相关推荐
            const commentsAndRelated = content.querySelectorAll('#post_comm, .post_related, .post_comment, .post_next');
            commentsAndRelated.forEach(el => {
                el.remove();
            });
        }

        // 确保标题显示
        const title = document.querySelector('.title');
        if (title) {
            title.style.display = 'block';
            title.style.marginBottom = '20px';
            title.style.fontSize = '24px';
            title.style.fontWeight = 'bold';
        }

        // 等待所有图片加载完成
        const waitForImages = () => {
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                // 处理懒加载图片
                if (img.dataset.original) {
                    img.src = img.dataset.original;
                }

                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {
                    const src = img.src;
                    img.src = '';
                    img.src = src;
                }
            });
        };

        // 执行图片加载优化
        waitForImages();
    """,
    "知乎": """
        // 隐藏不需要的元素
        const elementsToHide = [
            '.Header', '.Sticky', '.Footer', '.CornerButtons',
            '.Topstory-container', '.Topstory-mainColumn', '.GlobalSideBar',
            '.Banner-link', '.Banner-image', '.Pc-word', '.Pc-feedAd',
            '.RichContent-actions', '.Post-topicsAndReviewer', '.Post-Sub',
            '.Post-NormalSub', '.Comments-container', '.RelatedReadings'
        ];

        for (const selector of elementsToHide) {
            const elements = document.querySelectorAll(selector);
            for (const el of elements) {
                if (el) el.style.display = 'none';
            }
        }

        // 优化文章内容元素的显示
        const content = document.querySelector('#root');
        if (content) {
            content.style.padding = '20px';
            content.style.margin = '0 auto';
            content.style.maxWidth = '100%';
            content.style.boxSizing = 'border-box';
            content.style.backgroundColor = '#ffffff';

            // 处理所有图片
            const images = content.querySelectorAll('img');
            images.forEach(img => {
                // 修复可能的图片显示问题
                img.style.display = 'block';
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
                img.style.margin = '10px auto';

                // 处理懒加载图片
                if (img.dataset.original) {
                    img.src = img.dataset.original;
                }

                if (img.dataset.actualsrc) {
                    img.src = img.dataset.actualsrc;
                }

                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }

                // 移除懒加载类
                img.classList.remove('lazy');

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {
                    const src = img.src;
                    setTimeout(() => {
                        img.src = '';
                        img.src = src;
                    }, 100);
                }
            });

            // 处理可能的iframe（视频等）
            const iframes = content.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                iframe.style.maxWidth = '100%';
                iframe.style.display = 'block';
                iframe.style.margin = '10px auto';
            });
        }

        // 确保标题显示
        const title = document.querySelector('.Post-Title, .QuestionHeader-title');
        if (title) {
            title.style.display = 'block';
            title.style.marginBottom = '20px';
            title.style.fontSize = '24px';
            title.style.fontWeight = 'bold';
        }

        // 等待所有图片加载完成
        const waitForImages = () => {
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                // 处理懒加载图片
                if (img.dataset.original) {
                    img.src = img.dataset.original;
                }

                if (img.dataset.actualsrc) {
                    img.src = img.dataset.actualsrc;
                }

                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }

                // 如果图片没有加载，尝试重新加载
                if (!img.complete) {
                    const src = img.src;
                    img.src = '';
                    img.src = src;
                }
            });
        };

        // 执行图片加载优化
        waitForImages();
    """,
}

SITE_SELECTORS = {"ithome": "#dt > div.fl.content", "知乎": "#root"}


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

            await page.set_viewport_size(
                {"width": viewport_width, "height": viewport_height}
            )

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
                        pic = await page.screenshot(
                            full_page=True, type="jpeg", quality=75
                        )
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
        logger.warning(
            f"PIL不可用，无法优化图片，原始大小: {len(image_data) / 1024:.1f}KB"
        )
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
