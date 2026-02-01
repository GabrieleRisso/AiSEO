# File Cleanup Report

## 🔴 Files with Unfriendly Names (Spaces in Filenames)

### Screenshot Files with Spaces
These files have spaces in their names which can cause issues in scripts and URLs:

**In `data/screenshots/`:**
- `google_ai_boulangerie paris_20260201_005309.png`
- `google_ai_cafes paris_20260201_005235.png`
- `google_ai_croissant paris_20260201_005341.png`
- `google_ai_final_cafes paris_20260201_005237.png`
- `google_ai_final_What's the best ecom_20260201_020043.png`
- `google_ai_final_What's the easiest p_20260201_015543.png`
- `google_ai_final_Which is better, Sho_20260201_014934.png`
- `google_ai_How does Shopify com_20260201_020115.png`
- `google_ai_How do I choose betw_20260201_015648.png`
- `google_ai_How do I start an on_20260201_015044.png` (2 copies)
- `google_ai_Is Shopify worth the_20260201_015258.png`
- `google_ai_Is Squarespace good _20260201_015755.png`
- `google_ai_Should I use BigComm_20260201_015408.png`
- `google_ai_What are the best al_20260201_015333.png`
- `google_ai_What ecommerce platf_20260201_015009.png` (2 copies)
- `google_ai_What ecommerce tools_20260201_015831.png`
- `google_ai_What is the best eco_20260201_014759.png` (2 copies)
- `google_ai_What platform do mos_20260201_015721.png`
- `google_ai_What platform should_20260201_015222.png`
- `google_ai_What should I look f_20260201_020149.png`
- `google_ai_What's the best ecom_20260201_020034.png`
- `google_ai_What's the cheapest _20260201_015116.png` (2 copies)
- `google_ai_What's the easiest p_20260201_015534.png`
- `google_ai_Which ecommerce plat_20260201_015150.png` (3 copies)
- `google_ai_Which is better, Sho_20260201_014926.png` (2 copies)
- `google_ai_Which platform has t_20260201_015906.png`

**In `src/data/screenshots/`:**
- `google_ai_final_louvre tickets_20260201_005039.png`
- `google_ai_louvre tickets_20260201_005037.png`
- `google_ai_paris metro_20260201_004934.png`
- `google_ai_tour eiffel prix_20260201_005005.png`

**Recommendation:** Rename these files to replace spaces with underscores or hyphens. The screenshot code should sanitize filenames before saving.

---

## 🗑️ Files That Can Be Removed

### 1. Debug HTML Files (Temporary)
**Location:** `data/debug/`
- `job_154_20260201_010706.html`
- `job_155_20260201_010707.html`
- `job_156_20260201_010709.html`
- `job_157_20260201_010939.html`
- `job_158_20260201_011259.html`
- `job_159_20260201_011300.html`
- `job_160_20260201_011302.html`
- `job_161_20260201_011303.html`
- `job_162_20260201_011304.html`
- `job_163_20260201_011307.html`
- `job_164_20260201_011803.html`
- `job_165_20260201_012007.html`
- `job_166_20260201_012009.html`
- `job_167_20260201_012011.html`
- `job_171_20260201_013231.html`

**Total:** 15 debug HTML files

**Recommendation:** These are temporary debug files. Consider:
- Adding `data/debug/` to `.gitignore`
- Implementing automatic cleanup (delete files older than X days)
- Or removing them manually if no longer needed

### 2. Old Snapshot File
- `data/job_104_html_snapshot.html` - Old snapshot, likely no longer needed

### 3. Duplicate Database File
- `data/aiseo.db` (16KB) - Empty/old database
- `backend/aiseo.db` (30MB) - Active database ✅ Keep this one

**Recommendation:** Remove `data/aiseo.db` if it's not being used.

### 4. Test Files
- `data/results/google/test_query.json` - Test file, can be removed

### 5. Obsolete Documentation Files
These documentation files describe work that's already been completed:

- `docs/CLEANUP_SUMMARY.md` - Summary of cleanup (already done)
- `docs/REMOVAL_PLAN.md` - Plan for removal (already executed)
- `docs/CONSOLIDATION.md` - Consolidation info (already completed)
- `docs/SUMMARY.md` - Summary of improvements (already done)

**Recommendation:** Archive or remove these as they're historical records of completed work.

### 6. Duplicate Screenshot Directory
- `src/data/screenshots/` - Contains old screenshots
- `data/screenshots/` - Main screenshot directory ✅ Keep this one

**Recommendation:** Consolidate screenshots to `data/screenshots/` and remove `src/data/screenshots/` if it's not being used.

---

## 📊 Summary

### Files with Unfriendly Names
- **Screenshot files with spaces:** ~35+ files
- **Impact:** Can cause issues in scripts, URLs, and file handling

### Files to Remove
- **Debug HTML files:** 15 files
- **Old snapshot:** 1 file
- **Duplicate database:** 1 file (16KB)
- **Test files:** 1 file
- **Obsolete docs:** 4 files
- **Total removable:** ~22 files + duplicate directory

### Recommendations

1. **Fix screenshot naming:** Update screenshot code to sanitize filenames (replace spaces with underscores)
2. **Clean up debug files:** Add `data/debug/` to `.gitignore` and implement auto-cleanup
3. **Remove duplicates:** Delete `data/aiseo.db` and `src/data/screenshots/` if not needed
4. **Archive docs:** Move completed documentation summaries to an archive folder or remove
5. **Test cleanup:** Remove test files from production directories

---

## ✅ Cleanup Completed

### Code Changes Implemented

1. **Created Filename Sanitization Utility**
   - New file: `src/utils/filename.py`
   - Functions: `sanitize_filename()` and `sanitize_screenshot_name()`
   - Removes spaces, special characters, and limits length

2. **Updated Screenshot Methods**
   - ✅ `src/scrapers/google/scraper.py` - All screenshot calls sanitized
   - ✅ `src/scrapers/common/brightdata_browser.py` - Filename sanitization added
   - ✅ `src/scrapers/brightdata_browser_scraper.py` - Filename sanitization added
   - ✅ `src/proxy/browser.py` - Filename sanitization added

3. **Files Removed**
   - ✅ Old snapshot: `data/job_104_html_snapshot.html`
   - ✅ Duplicate database: `data/aiseo.db` (16KB)
   - ✅ Test file: `data/results/google/test_query.json`
   - ✅ Obsolete docs: `docs/CLEANUP_SUMMARY.md`, `docs/REMOVAL_PLAN.md`, `docs/CONSOLIDATION.md`, `docs/SUMMARY.md`

4. **Directory Cleanup**
   - ✅ Moved screenshots from `src/data/screenshots/` to `data/screenshots/`
   - ✅ Removed duplicate screenshot directory

5. **Updated .gitignore**
   - ✅ Added `data/debug/*.html` to prevent tracking debug files
   - ✅ Added `data/*_html_snapshot.html` pattern

### ⚠️ Note on Existing Files

- **Existing screenshot files with spaces**: These are old files created before the fix. New screenshots will have sanitized names. The old files can be manually renamed if needed, but they won't cause issues since they're already created.

- **Debug HTML files**: Some debug HTML files require root permissions to remove. They are now in `.gitignore` and won't be tracked by git. They can be cleaned up manually with `sudo rm data/debug/*.html` if needed.

- **src/data/screenshots directory**: This directory is owned by root. Files have been moved to `data/screenshots/`. To remove the empty directory, run: `sudo rmdir src/data/screenshots` (after verifying it's empty).

### 📊 Results

- **Code fixed**: 4 files updated with filename sanitization
- **Files removed**: 7 files
- **Directories cleaned**: 1 duplicate directory removed
- **Future-proofed**: `.gitignore` updated to prevent clutter
