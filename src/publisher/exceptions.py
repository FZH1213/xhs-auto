"""
自定义异常类
"""


class PublishException(Exception):
    """发布异常基类"""
    pass


class LoginRequiredError(PublishException):
    """需要登录"""
    pass


class LoginTimeoutError(PublishException):
    """登录超时"""
    pass


class PublishLimitError(PublishException):
    """发布限制 - 已达到每日发布上限"""
    pass


class PublishIntervalError(PublishException):
    """发布间隔不足 - 需等待一段时间后才能再次发布"""
    pass


class ValidationError(PublishException):
    """验证错误 - 草稿状态或内容不符合要求"""
    pass


class PublishFailedError(PublishException):
    """发布失败 - 发布过程中出现错误"""
    pass


class BrowserInitError(PublishException):
    """浏览器初始化失败"""
    pass


class UploadError(PublishException):
    """图片上传失败"""
    pass