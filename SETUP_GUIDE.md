# Review Plugin — Setup Guide

## Architecture

```
ohhsnapbooth.com (CloudCannon / Jekyll)
    │
    │  client-side JS fetch
    ▼
FastAPI Backend (deployed on Render/Railway/VPS)
    │
    ├── Google Business Profile API
    ├── Facebook Graph API
    └── Yelp Fusion API
```

The Jekyll site is static — the FastAPI backend runs separately and the
widget fetches reviews via JavaScript at page load.

---

## 1. Google Business Profile — API Setup

### Step 1: Create a Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click **Select a Project** → **New Project**
3. Name it (e.g., "OhhSnapBooth Reviews") → **Create**

### Step 2: Enable the API
1. Go to **APIs & Services** → **Library**
2. Search for **"My Business Account Management API"** → **Enable**
3. Search for **"My Business Business Information API"** → **Enable**

### Step 3: Create a Service Account
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Name it (e.g., "review-sync") → **Create**
4. Grant role **Owner** (or **Editor**) → **Done**
5. Click the service account → **Keys** tab → **Add Key** → **JSON**
6. Save the downloaded JSON file — this is your `GOOGLE_SERVICE_ACCOUNT_JSON`

### Step 4: Get Your Location ID
1. Go to https://business.google.com
2. Your business should be listed / verified
3. Use the API to list locations:
   ```
   GET https://mybusiness.googleapis.com/v4/accounts/{accountId}/locations
   ```
4. Or check the URL when viewing your business — the ID is in the URL

### .env values:
```
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service-account.json
GOOGLE_ACCOUNT_ID=accounts/123456789
GOOGLE_LOCATION_ID=locations/987654321
```

---

## 2. Facebook Page Reviews — API Setup

### Step 1: Create a Facebook App
1. Go to https://developers.facebook.com
2. Click **My Apps** → **Create App**
3. Choose **Business** type → fill in details → **Create**

### Step 2: Add Page Permissions
1. In your app dashboard, go to **Add Products** → **Facebook Login** → **Set Up**
2. Go to **App Review** → **Permissions and Features**
3. Request these permissions:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_read_user_content`
   - `pages_manage_engagement` (for replying)

### Step 3: Generate a Page Access Token
1. Go to **Graph API Explorer**: https://developers.facebook.com/tools/explorer/
2. Select your app
3. Click **Get Token** → **Get Page Access Token**
4. Select your business page
5. Copy the token

### Step 4: Make the Token Long-Lived
Short-lived tokens expire in ~1 hour. Exchange for a long-lived token:

```bash
curl "https://graph.facebook.com/v18.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_APP_ID&\
client_secret=YOUR_APP_SECRET&\
fb_exchange_token=YOUR_SHORT_TOKEN"
```

Then get a permanent page token:
```bash
curl "https://graph.facebook.com/v18.0/me/accounts?\
access_token=YOUR_LONG_LIVED_USER_TOKEN"
```

The `access_token` in the response for your page is permanent.

### Step 5: Get Your Page ID
- Visit your Facebook page → **About** → scroll to **Page ID**
- Or from the API response above

### .env values:
```
FACEBOOK_PAGE_ID=123456789012345
FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxxx...
```

---

## 3. Yelp — API Setup

### Step 1: Create a Yelp App
1. Go to https://www.yelp.com/developers/v3/manage_app
2. Sign in with your Yelp account
3. Click **Create New App**
4. Fill in the form:
   - **App Name**: "OhhSnapBooth Reviews"
   - **Industry**: Photography / Events
   - **Description**: "Review aggregation for our website"
5. Agree to terms → **Create New App**

### Step 2: Get Your API Key
- After creating, your **API Key** is shown on the app page
- Copy it — this is your `YELP_API_KEY`

### Step 3: Find Your Business ID
Search for your business:
```bash
curl "https://api.yelp.com/v3/businesses/search?term=Ohh+Snap+Booth&location=YOUR_CITY" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

The `id` field in the matching result is your `YELP_BUSINESS_ID`.
It looks like: `ohh-snap-booth-los-angeles` (a slug).

### .env values:
```
YELP_API_KEY=aBcDeFgHiJkLmNoPqRsTuVwXyZ
YELP_BUSINESS_ID=ohh-snap-booth-your-city
```

> **Note:** Yelp's API is read-only for reviews. You cannot reply to
> Yelp reviews via the API — you must reply on yelp.com directly.

---

## 4. Deploy the Backend

The FastAPI backend needs to run 24/7. Recommended free/cheap options:

### Option A: Render.com (recommended)
1. Push the `review plugin` code to a GitHub repo
2. Go to https://render.com → **New Web Service**
3. Connect your repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all `.env` variables in the **Environment** section
6. Deploy — you'll get a URL like `https://your-app.onrender.com`

### Option B: Railway.app
1. Go to https://railway.app → **New Project** → **Deploy from GitHub**
2. Add environment variables
3. Railway auto-detects Python and deploys

### Option C: Any VPS (DigitalOcean, Linode, etc.)
```bash
# On the server:
git clone your-repo
cd review-plugin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 5. Connect to Your Jekyll Site

### Step 1: Add to `_config.yml`
```yaml
review_plugin:
  api_url: "https://your-app.onrender.com"  # your deployed backend URL
  max_reviews: 6
  platforms:
    - google
    - facebook
    - yelp
    - website
  theme: "light"
  show_submit_form: true
  show_platform_filter: true
  show_stats: true
```

### Step 2: Copy files to your Jekyll project
```
_includes/reviews.html     → your-jekyll-site/_includes/reviews.html
assets/css/reviews.css     → your-jekyll-site/assets/css/reviews.css
assets/js/reviews.js       → your-jekyll-site/assets/js/reviews.js
```

### Step 3: Include on any page
In any Jekyll page or layout:
```liquid
{% include reviews.html %}
```

Or with overrides:
```liquid
{% include reviews.html max_reviews=10 theme="dark" show_form=false %}
```

---

## 6. Verify Everything Works

1. Start the backend: `uvicorn main:app --reload`
2. Open http://localhost:8000/docs — test the API
3. Trigger a sync: `POST /api/sync`
4. Check reviews: `GET /api/reviews`
5. Build your Jekyll site and verify the widget loads
