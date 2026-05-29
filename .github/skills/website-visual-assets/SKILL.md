---
name: website-visual-assets
description: Generate website HTML exports and screenshots using the repo's htmlrenderer and screenshotgenerator Go tools.
---

# Skill Instructions

## Purpose
Provide a repeatable workflow to generate HTML exports and screenshots for the website using real repository artifacts.

## Hard Rules
### Must
- [ ] Use `src-go/tools/htmlrenderer` to generate HTML from markdown reports.
- [ ] Use `src-go/tools/screenshotgenerator` (Playwright via go-playwright) to generate screenshots from those HTML exports.
- [ ] Store website screenshots under `website/src/assets/screenshots/`.
- [ ] Update the consuming website source when screenshot assets change (for example the relevant page in `website/src/pages/` or shared content data in `website/src/_data/`).

### Must Not
- [ ] Do not hand-edit screenshots or create "mock" screenshots that aren't generated from real HTML exports.

## Golden Example

```bash
# Preferred Method: Use the automated script
scripts/generate-screenshot.sh \
  --plan examples/firewall-with-static-analysis/plan.json \
  --output-prefix firewall-example \
  --selector "details:has(summary:has-text('azurerm_firewall_network_rule_collection'))" \
  --thumbnail-width 580 --thumbnail-height 400 \
  --lightbox-width 1200 --lightbox-height 900 \
  --render-target azdo \
  --open-details-selector "details"

# This generates 12 screenshot variants automatically:
# - Thumbnail and lightbox crops
# - Light and dark themes
# - 1x and 2x DPI versions
# - Azure DevOps rendering style

# Manual Method (for advanced use cases):
# Build the tools first
cd src-go
go build -o htmlrenderer ./tools/htmlrenderer
go build -o screenshotgenerator ./tools/screenshotgenerator
cd ..

# 1) Generate HTML (Azure DevOps flavor, wrapped)
./src-go/htmlrenderer \
  --input artifacts/comprehensive-demo.md \
  --flavor azdo \
  --output artifacts/comprehensive-demo.azdo.html

# 2) Capture a screenshot with details expanded
./src-go/screenshotgenerator \
  --input artifacts/comprehensive-demo.azdo.html \
  --output website/src/assets/screenshots/full-report-azdo.png \
  --open-details "details" \
  --full-page
```

## Actions
1. Pick the markdown report under `artifacts/` to use as the source.
2. Generate the required HTML exports with `src-go/tools/htmlrenderer`.
3. Generate screenshots from the exported HTML with `src-go/tools/screenshotgenerator`.
4. Place the generated screenshots in `website/src/assets/screenshots/`.
5. Update the consuming page or content source so it references the new screenshot asset.
6. Verify the relevant page in `website/dist/` uses the correct light or dark asset variants and that any lightbox or screenshot wrapper still works.
