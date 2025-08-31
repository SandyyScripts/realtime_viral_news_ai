import pathlib, asyncio, logging
from jinja2 import Environment, FileSystemLoader
from app.parsers.news_parser import parse_news_content
from .image_utils import _process_background_image, _get_ist_timestamp, _determine_headline_size
from .themes import THEMES
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

async def render_post_html_to_image(html_content, output_path):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width":1080,"height":1350})
        await page.set_content(html_content)
        await page.screenshot(path=str(output_path), type="jpeg", quality=90)
        await browser.close()

def make_post_image(raw_content, model_name="claude"):
    items = parse_news_content(raw_content)
    if not items: return None
    item = items[0]  # single post per call

    category = "tech"  # or detect dynamically
    theme = THEMES.get(category, THEMES["default"])

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("post_template.html")

    html_content = template.render(
        title=item["title"],
        pov=item["comment"],
        background_data_uri=_process_background_image(item["images"], theme),
        model_name=model_name,
        timestamp_ist=_get_ist_timestamp(),
        category=category,
        category_title=theme["title"],
        headline_size=_determine_headline_size(item["title"]),
        theme=theme
    )

    output_path = OUTPUT_DIR / f"post-{category}.jpg"
    asyncio.run(render_post_html_to_image(html_content, output_path))
    return str(output_path)