class ReportException(Exception):
    """日报插件基础异常类"""

    def __init__(self, message: str = "日报插件发生错误"):
        self.message = message
        super().__init__(self.message)


class APIException(ReportException):
    """API相关异常"""

    def __init__(
        self,
        message: str = "API请求失败",
        status_code: int | None = None,
        api_url: str | None = None,
    ):
        self.status_code = status_code
        self.api_url = api_url
        error_msg = message
        if status_code:
            error_msg += f"，状态码: {status_code}"
        if api_url:
            error_msg += f"，URL: {api_url}"
        super().__init__(error_msg)


class APITimeoutException(APIException):
    """API请求超时异常"""

    def __init__(
        self,
        message: str = "API请求超时",
        api_url: str | None = None,
        timeout: float | None = None,
    ):
        error_msg = message
        if timeout:
            error_msg += f"，超时时间: {timeout}秒"
        super().__init__(error_msg, api_url=api_url)
        self.timeout = timeout


class APIResponseParseException(APIException):
    """API响应解析异常"""

    def __init__(
        self,
        message: str = "API响应解析失败",
        api_url: str | None = None,
        parser: str | None = None,
    ):
        error_msg = message
        if parser:
            error_msg += f"，解析器: {parser}"
        super().__init__(error_msg, api_url=api_url)
        self.parser = parser


class NoAvailableAPIException(APIException):
    """没有可用的API异常"""

    def __init__(
        self,
        message: str = "没有可用的API源",
        news_type: str | None = None,
    ):
        error_msg = message
        if news_type:
            error_msg += f"，日报类型: {news_type}"
        super().__init__(error_msg)
        self.news_type = news_type


class NewsTypeNotFoundException(ReportException):
    """日报类型未找到异常"""

    def __init__(
        self,
        message: str = "未知的日报类型",
        news_type: str | None = None,
        available_types: list[str] | None = None,
    ):
        error_msg = message
        if news_type:
            error_msg += f": {news_type}"
        if available_types:
            error_msg += f"，可用类型: {', '.join(available_types)}"
        super().__init__(error_msg)
        self.news_type = news_type
        self.available_types = available_types


class ScheduleException(ReportException):
    """定时任务相关异常"""

    def __init__(
        self,
        message: str = "定时任务操作失败",
        group_id: int | None = None,
        news_type: str | None = None,
    ):
        error_msg = message
        if group_id:
            error_msg += f"，群组: {group_id}"
        if news_type:
            error_msg += f"，日报类型: {news_type}"
        super().__init__(error_msg)
        self.group_id = group_id
        self.news_type = news_type


class InvalidTimeFormatException(ScheduleException):
    """无效的时间格式异常"""

    def __init__(
        self,
        message: str = "无效的时间格式",
        time_str: str | None = None,
    ):
        error_msg = message
        if time_str:
            error_msg += f": {time_str}"
        super().__init__(error_msg)
        self.time_str = time_str


class CacheException(ReportException):
    """缓存相关异常"""

    def __init__(
        self,
        message: str = "缓存操作失败",
        news_type: str | None = None,
        format_type: str | None = None,
    ):
        error_msg = message
        if news_type:
            error_msg += f"，日报类型: {news_type}"
        if format_type:
            error_msg += f"，格式: {format_type}"
        super().__init__(error_msg)
        self.news_type = news_type
        self.format_type = format_type


class FormatTypeException(ReportException):
    """格式类型相关异常"""

    def __init__(
        self,
        message: str = "不支持的格式类型",
        format_type: str | None = None,
        supported_formats: list[str] | None = None,
    ):
        error_msg = message
        if format_type:
            error_msg += f": {format_type}"
        if supported_formats:
            error_msg += f"，支持的格式: {', '.join(supported_formats)}"
        super().__init__(error_msg)
        self.format_type = format_type
        self.supported_formats = supported_formats
