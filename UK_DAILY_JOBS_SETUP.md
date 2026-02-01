# UK Daily Scraping Jobs Setup

## ✅ Setup Complete

Successfully created **40 daily recurring scraping jobs** for UK market analysis.

### Configuration
- **Country**: UK (single country)
- **Frequency**: Daily (runs every 24 hours)
- **Proxy Layer**: Direct (VPN only - cheapest option, free)
- **Scrapers**: 
  - Google AI: 20 jobs
  - ChatGPT: 20 jobs

### Jobs Created

#### Google AI Jobs (20 queries)
1. What is the best ecommerce platform in 2026?
2. Which is better, Shopify or WooCommerce?
3. What ecommerce platform should I use for a small business?
4. How do I start an online store?
5. What's the cheapest way to sell products online?
6. Which ecommerce platform has the best SEO features?
7. What platform should I use for dropshipping?
8. Is Shopify worth the price?
9. What are the best alternatives to WooCommerce?
10. Should I use BigCommerce or Shopify for my store?
11. What's the easiest platform to set up an online shop?
12. Which ecommerce platform is best for beginners?
13. How do I choose between Wix and Shopify?
14. What platform do most successful online stores use?
15. Is Squarespace good for selling products?
16. What ecommerce tools do I need to start selling online?
17. Which platform has the lowest transaction fees?
18. What's the best ecommerce platform for digital products?
19. How does Shopify compare to other ecommerce platforms?
20. What should I look for in an ecommerce platform?

#### ChatGPT Jobs (20 queries)
Same queries as above, scraped via ChatGPT scraper.

### How It Works

1. **Scheduler**: The backend runs a scheduler loop that checks every minute for due jobs
2. **Execution**: When `next_run_at <= now`, the scheduler:
   - Creates a new job instance
   - Executes the scraping job
   - Updates `next_run_at` to 24 hours later
   - Saves results to database

3. **Database Population**: Each successful scrape creates:
   - **Prompt** record with query and AI response
   - **Source** records for cited websites
   - **PromptBrandMention** records tracking brand visibility
   - **PromptSource** links connecting prompts to sources

### Cost Configuration

Using **least expensive config**:
- **Proxy Layer**: `direct` (VPN only)
- **Cost**: Free (uses existing VPN infrastructure)
- **Success Rate**: ~70% (may hit CAPTCHA occasionally)
- **Fallback**: If direct fails, can upgrade to `unlocker` or `browser` layers

### Monitoring

Check job status via API:
```bash
# List all UK jobs
curl "http://localhost:8000/api/jobs?country=uk"

# Check scheduled jobs
curl "http://localhost:8000/api/jobs?status=scheduled&country=uk"

# Check running jobs
curl "http://localhost:8000/api/jobs?status=running&country=uk"

# Check completed jobs
curl "http://localhost:8000/api/jobs?status=completed&country=uk"
```

### Script Location

Setup script: `/home/user/startup/vpn/aiseo/backend/scripts/setup_daily_uk_jobs.sh`

To re-run setup (creates new jobs):
```bash
cd /home/user/startup/vpn/aiseo/backend
bash scripts/setup_daily_uk_jobs.sh
```

### Next Steps

1. **Monitor**: Jobs will start running automatically within the next minute
2. **Database**: Check database for populated prompts and brand mentions
3. **Dashboard**: View results in the frontend dashboard (when available)
4. **Adjust**: If success rate is low, consider upgrading to `unlocker` proxy layer

### Expected Daily Volume

- **40 jobs/day** (20 Google AI + 20 ChatGPT)
- **~28 successful scrapes/day** (assuming 70% success rate with direct VPN)
- **~280 prompts/month** (28 × 10 days)
- **Continuous data collection** for brand visibility tracking

---

**Status**: ✅ All 40 jobs scheduled and ready to run
**Started**: 2026-02-01
**Next Run**: Jobs will execute as soon as scheduler picks them up (within 1 minute)
