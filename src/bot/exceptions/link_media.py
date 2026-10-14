from .media_tools import MediaToolError


class LinkMediaError(MediaToolError): ...


class LinkMediaTooLarge(LinkMediaError): ...
