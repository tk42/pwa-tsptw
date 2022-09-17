from tsptw.const import PageId


class BasePage:
    def __init__(self, page_id: PageId, title: str) -> None:
        self.page_id = page_id.name
        self.title = title

    def render(self) -> None:
        pass
