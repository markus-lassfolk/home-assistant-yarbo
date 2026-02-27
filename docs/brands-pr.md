# Brands PR to home-assistant/brands (issue #30)

Checklist for submitting Yarbo branding to [home-assistant/brands](https://github.com/home-assistant/brands) so the integration conforms to Home Assistant UI standards.

## Asset spec

Create directory `core_integrations/yarbo/` in a fork of [home-assistant/brands](https://github.com/home-assistant/brands).

| File        | Size        | Notes                          |
|------------|-------------|--------------------------------|
| `icon.png` | 256×256 px  | Transparent background         |
| `icon@2x.png` | 512×512 px | 2× resolution for HiDPI       |
| `logo.png` | —           | Horizontal logo variant        |

- Follow the [brands repository style guide](https://github.com/home-assistant/brands).
- Use official Yarbo assets where possible (yarbo.com).

## Steps

1. Fork [home-assistant/brands](https://github.com/home-assistant/brands).
2. Create `core_integrations/yarbo/` and add the three asset files.
3. Open a PR against `home-assistant/brands` main branch.
4. Wait for review and merge.

## Blocking

Required for HACS default submission (#29) and for the integration to pass the “Check Brands” CI step.
