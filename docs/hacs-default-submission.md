# HACS Default repository submission (issue #29)

Checklist for submitting this integration to the [HACS default](https://github.com/hacs/default) repository.

## In-repo (done)

- [x] **hacs.json** in repo root with: `name`, `render_readme`, `homeassistant` min version, `content_in_root: false`
- [x] **manifest.json** has: `version`, `name`, `codeowners`, `issue_tracker`, `documentation`, `domain`
- [x] **Structure**: single integration under `custom_components/yarbo/`
- [x] **README** has badges (HACS, release, CI, license, issues)

## Before submitting to HACS default

- [ ] **home-assistant/brands**: Integration added via [brands PR](#30-brands-pr) (required for HACS default)
- [ ] **Tagged release**: At least one release (e.g. `v1.0.0`) exists
- [ ] **CI**: `hassfest` and `hacs-validate` pass on main (or default branch)
- [ ] **PR**: Open PR to [hacs/default](https://github.com/hacs/default) adding this repo to the integrations list
- [ ] **Approval**: HACS maintainers approve and merge

## References

- [HACS publish documentation](https://hacs.xyz/docs/publish/integration)
- [Include default repositories](https://hacs.xyz/docs/publish/include/)
