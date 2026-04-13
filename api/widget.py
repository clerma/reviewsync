from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response

from providers.base import store

router = APIRouter(tags=["widget"])


@router.get("/widget", response_class=HTMLResponse)
async def widget_page(
    max_reviews: int = Query(5, ge=1, le=20),
    platform: str = Query("all"),
    theme: str = Query("light", description="light or dark"),
):
    reviews = store.get_all()
    if platform != "all":
        reviews = [r for r in reviews if r.platform == platform]

    reviews.sort(key=lambda r: r.date, reverse=True)
    reviews = reviews[:max_reviews]

    stars_html = ""
    for r in reviews:
        filled = "\u2605" * r.rating
        empty = "\u2606" * (5 - r.rating)
        text_preview = r.text[:200] + "..." if len(r.text) > 200 else r.text
        platform_badge = f'<span class="platform-badge {r.platform}">{r.platform.title()}</span>'
        stars_html += f"""
        <div class="review-card">
            <div class="review-header">
                <span class="author">{r.author}</span>
                {platform_badge}
            </div>
            <div class="stars">{filled}{empty}</div>
            <p class="review-text">{text_preview}</p>
            <span class="review-date">{r.date.strftime('%b %d, %Y')}</span>
        </div>
        """

    stats = store.stats()
    avg = stats.get("average_rating", 0)
    total = stats.get("total", 0)

    bg = "#ffffff" if theme == "light" else "#1a1a2e"
    text_color = "#333333" if theme == "light" else "#e0e0e0"
    card_bg = "#f8f9fa" if theme == "light" else "#16213e"

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {bg}; color: {text_color}; padding: 20px; }}
    .widget-header {{ text-align: center; margin-bottom: 20px; }}
    .widget-header .avg-rating {{ font-size: 2.5em; font-weight: bold; }}
    .widget-header .total {{ font-size: 0.9em; opacity: 0.7; }}
    .review-card {{ background: {card_bg}; border-radius: 12px; padding: 16px; margin-bottom: 12px; }}
    .review-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .author {{ font-weight: 600; }}
    .platform-badge {{ font-size: 0.75em; padding: 2px 8px; border-radius: 12px; color: white; }}
    .platform-badge.google {{ background: #4285f4; }}
    .platform-badge.facebook {{ background: #1877f2; }}
    .platform-badge.yelp {{ background: #d32323; }}
    .platform-badge.website {{ background: #28a745; }}
    .stars {{ color: #ffc107; font-size: 1.2em; margin-bottom: 6px; }}
    .review-text {{ font-size: 0.95em; line-height: 1.5; margin-bottom: 8px; }}
    .review-date {{ font-size: 0.8em; opacity: 0.6; }}
</style>
</head>
<body>
    <div class="widget-header">
        <div class="avg-rating">{avg} \u2605</div>
        <div class="total">Based on {total} reviews</div>
    </div>
    {stars_html}
</body>
</html>"""

    return HTMLResponse(content=html)


@router.get("/widget/embed.js", response_class=Response)
async def widget_embed_js(request: Request):
    base_url = str(request.base_url).rstrip("/")

    js = f"""
(function() {{
    var config = window.ReviewWidgetConfig || {{}};
    var maxReviews = config.maxReviews || 5;
    var platform = config.platform || 'all';
    var theme = config.theme || 'light';
    var container = config.container || 'review-widget';

    var iframe = document.createElement('iframe');
    iframe.src = '{base_url}/widget?max_reviews=' + maxReviews + '&platform=' + platform + '&theme=' + theme;
    iframe.style.width = '100%';
    iframe.style.border = 'none';
    iframe.style.minHeight = '400px';
    iframe.setAttribute('loading', 'lazy');

    var el = document.getElementById(container);
    if (el) {{
        el.appendChild(iframe);
    }}

    window.addEventListener('message', function(e) {{
        if (e.data && e.data.type === 'reviewWidgetResize') {{
            iframe.style.height = e.data.height + 'px';
        }}
    }});
}})();
"""

    return Response(content=js, media_type="application/javascript")
