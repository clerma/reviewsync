/**
 * Review Widget — Client-side JS for Jekyll / CloudCannon
 * Fetches reviews from FastAPI backend and renders them.
 */
(function () {
  "use strict";

  const widget = document.getElementById("review-widget");
  if (!widget) return;

  const API_URL = widget.dataset.apiUrl;
  const MAX_REVIEWS = parseInt(widget.dataset.maxReviews) || 6;
  const SHOW_FORM = widget.dataset.showForm === "true";
  const SHOW_FILTER = widget.dataset.showFilter === "true";
  const SHOW_STATS = widget.dataset.showStats === "true";
  const CACHE_KEY = "rw_reviews_cache";
  const CACHE_TTL = 15 * 60 * 1000; // 15 minutes

  let allReviews = [];
  let currentPlatform = "all";
  let displayedCount = 0;

  // ─── Cache ───
  function getCached() {
    try {
      const raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (Date.now() - cached.timestamp > CACHE_TTL) {
        sessionStorage.removeItem(CACHE_KEY);
        return null;
      }
      return cached.data;
    } catch {
      return null;
    }
  }

  function setCache(data) {
    try {
      sessionStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ data, timestamp: Date.now() })
      );
    } catch {}
  }

  // ─── API ───
  async function fetchReviews() {
    const cached = getCached();
    if (cached) return cached;

    const resp = await fetch(`${API_URL}/api/reviews?limit=200&sort=newest`);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    const data = await resp.json();
    setCache(data);
    return data;
  }

  async function fetchStats() {
    const resp = await fetch(`${API_URL}/api/reviews/stats`);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
  }

  async function submitReview(formData) {
    const resp = await fetch(`${API_URL}/api/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Failed to submit review");
    }
    return resp.json();
  }

  // ─── Rendering ───
  function stars(rating) {
    return "\u2605".repeat(rating) + "\u2606".repeat(5 - rating);
  }

  function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function renderCard(review) {
    const textPreview =
      review.text.length > 200
        ? review.text.substring(0, 200) + "..."
        : review.text;

    let replyHtml = "";
    if (review.reply) {
      replyHtml = `
        <div class="rw-card__reply">
          <div class="rw-card__reply-label">Owner Response</div>
          <div class="rw-card__reply-text">${escapeHtml(review.reply)}</div>
        </div>`;
    }

    return `
      <div class="rw-card" data-platform="${review.platform}">
        <div class="rw-card__header">
          <span class="rw-card__author">${escapeHtml(review.author)}</span>
          <span class="rw-card__badge rw-card__badge--${review.platform}">
            ${review.platform}
          </span>
        </div>
        <div class="rw-card__stars">${stars(review.rating)}</div>
        <div class="rw-card__text">${escapeHtml(textPreview)}</div>
        <div class="rw-card__date">${formatDate(review.date)}</div>
        ${replyHtml}
      </div>`;
  }

  function renderReviews() {
    const container = document.getElementById("rw-reviews");
    const loadMore = document.getElementById("rw-load-more");

    const filtered =
      currentPlatform === "all"
        ? allReviews
        : allReviews.filter((r) => r.platform === currentPlatform);

    if (filtered.length === 0) {
      container.innerHTML = `<div class="rw-empty">No reviews yet. Be the first!</div>`;
      if (loadMore) loadMore.style.display = "none";
      return;
    }

    const toShow = filtered.slice(0, displayedCount + MAX_REVIEWS);
    displayedCount = toShow.length;

    container.innerHTML = toShow.map(renderCard).join("");

    if (loadMore) {
      loadMore.style.display =
        displayedCount < filtered.length ? "block" : "none";
    }
  }

  function renderStats(stats) {
    if (!SHOW_STATS) return;

    const avgEl = document.getElementById("rw-avg-rating");
    const starsEl = document.getElementById("rw-avg-stars");
    const countEl = document.getElementById("rw-total-count");
    const platformsEl = document.getElementById("rw-platform-stats");

    if (avgEl) avgEl.textContent = stats.average_rating.toFixed(1);
    if (starsEl) starsEl.textContent = stars(Math.round(stats.average_rating));
    if (countEl)
      countEl.textContent = `Based on ${stats.total} review${stats.total !== 1 ? "s" : ""}`;

    if (platformsEl && stats.by_platform) {
      platformsEl.innerHTML = Object.entries(stats.by_platform)
        .map(
          ([platform, data]) =>
            `<span class="rw-stats__platform">
              <strong>${data.average_rating.toFixed(1)}</strong> ${platform}
              (${data.count})
            </span>`
        )
        .join("");
    }
  }

  // ─── Filters ───
  function initFilters() {
    if (!SHOW_FILTER) return;
    const filters = document.getElementById("rw-filters");
    if (!filters) return;

    filters.addEventListener("click", (e) => {
      const btn = e.target.closest(".rw-filter");
      if (!btn) return;

      filters
        .querySelectorAll(".rw-filter")
        .forEach((b) => b.classList.remove("rw-filter--active"));
      btn.classList.add("rw-filter--active");

      currentPlatform = btn.dataset.platform;
      displayedCount = 0;
      renderReviews();
    });
  }

  // ─── Load More ───
  function initLoadMore() {
    const btn = document.getElementById("rw-load-more-btn");
    if (!btn) return;
    btn.addEventListener("click", () => renderReviews());
  }

  // ─── Star Input ───
  function initStarInput() {
    const container = document.getElementById("rw-star-input");
    const hidden = document.getElementById("rw-rating");
    if (!container || !hidden) return;

    let selected = 5;
    updateStarDisplay(container, selected);

    container.addEventListener("click", (e) => {
      const btn = e.target.closest(".rw-star-btn");
      if (!btn) return;
      selected = parseInt(btn.dataset.rating);
      hidden.value = selected;
      updateStarDisplay(container, selected);
    });

    container.addEventListener("mouseover", (e) => {
      const btn = e.target.closest(".rw-star-btn");
      if (!btn) return;
      updateStarDisplay(container, parseInt(btn.dataset.rating));
    });

    container.addEventListener("mouseout", () => {
      updateStarDisplay(container, selected);
    });
  }

  function updateStarDisplay(container, rating) {
    container.querySelectorAll(".rw-star-btn").forEach((btn) => {
      btn.textContent =
        parseInt(btn.dataset.rating) <= rating ? "\u2605" : "\u2606";
    });
  }

  // ─── Form ───
  function initForm() {
    const form = document.getElementById("rw-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const msgEl = document.getElementById("rw-form-message");
      const submitBtn = document.getElementById("rw-submit-btn");

      const formData = {
        author: document.getElementById("rw-name").value.trim(),
        rating: parseInt(document.getElementById("rw-rating").value),
        text: document.getElementById("rw-text").value.trim(),
      };

      if (!formData.author) {
        showMessage(msgEl, "Please enter your name.", "error");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";

      try {
        const newReview = await submitReview(formData);
        allReviews.unshift(newReview);
        sessionStorage.removeItem(CACHE_KEY);
        renderReviews();
        form.reset();
        updateStarDisplay(document.getElementById("rw-star-input"), 5);
        document.getElementById("rw-rating").value = 5;
        showMessage(
          msgEl,
          "Thank you for your review!",
          "success"
        );
      } catch (err) {
        showMessage(msgEl, err.message || "Something went wrong.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Review";
      }
    });
  }

  function showMessage(el, text, type) {
    el.textContent = text;
    el.className = `rw-form__message rw-form__message--${type}`;
    setTimeout(() => {
      el.className = "rw-form__message";
      el.style.display = "none";
    }, 5000);
  }

  // ─── Utils ───
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // ─── Init ───
  async function init() {
    if (!API_URL) {
      document.getElementById("rw-reviews").innerHTML =
        '<div class="rw-empty">Review widget not configured. Set review_plugin.api_url in _config.yml</div>';
      return;
    }

    initFilters();
    initLoadMore();
    initStarInput();
    initForm();

    try {
      const [reviewsData, statsData] = await Promise.all([
        fetchReviews(),
        fetchStats(),
      ]);

      allReviews = reviewsData.reviews || [];
      renderStats(statsData);
      renderReviews();
    } catch (err) {
      console.error("Review widget error:", err);
      document.getElementById("rw-reviews").innerHTML =
        '<div class="rw-empty">Unable to load reviews. Please try again later.</div>';
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
