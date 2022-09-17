from .app import MultiPageApp
from .const import PageId
from .pages.base import BasePage

from .pages.top import TopPage
from .pages.edit import EditPage
from .pages.findroute import FindRoutePage


def init_pages() -> list[BasePage]:
    pages = [
        TopPage(page_id=PageId.TOP, title="トップ"),
        EditPage(page_id=PageId.EDIT, title="経由地点"),
        FindRoutePage(page_id=PageId.FIND_ROUTE, title="ルート探索"),
    ]
    return pages


def init_app(pages: list[BasePage]) -> MultiPageApp:
    app = MultiPageApp(pages)
    return app
