# Changelog

## [2.3.5](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.3.4...v2.3.5) (2026-03-01)


### Features

* brand icon and logo for HA 2026.3 ([#147](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/147)) ([2c9f2ec](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/2c9f2ec5ad0b7596d0403acd583bc3adcbb0f02d))

## [2.3.4](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.3.3...v2.3.4) (2026-02-26)


### Bug Fixes

* sensor entity_id without duplicate domain, single source_slug, concise docs ([#146](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/146)) ([9d79bb8](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/9d79bb8830e968a98188220a372496c017ccc23f))


### CI

* run on push to any branch, PRs targeting main only ([#143](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/143)) ([01e1aae](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/01e1aae28aab182d2076b00354831b2ac565b902))


### Miscellaneous Chores

* **release-please:** add changelog sections for refactor, ci, chore, docs ([#144](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/144)) ([b9ddd1a](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/b9ddd1acfc9d4d64e09f005a82581ee69fb1ca10))

## [2.3.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.3.2...v2.3.3) (2026-02-26)


### Bug Fixes

* remove markdown from source_already_in_use error message ([#141](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/141)) ([505fc65](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/505fc653ba98f81e020a4374c05d87a89c67c054))

## [2.3.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.3.1...v2.3.2) (2026-02-26)


### Bug Fixes

* **options:** validate remove_previous when source unchanged ([#132](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/132)) ([e05887a](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/e05887a4f5b5c38b6c75f3605a307b00245ad6d4))

## [2.3.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.3.0...v2.3.1) (2026-02-26)


### Bug Fixes

* **options:** update source-entity checkbox label, remove empty descriptions ([#127](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/127)) ([377f56e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/377f56ebcd9a3719570686adbd318733c0f08e4c))

## [2.3.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.2.0...v2.3.0) (2026-02-26)


### Features

* enforce one sensor per config entry ([#113](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/113)) ([2249715](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/22497151968f4830449e17b7c5d7f77fcde56f7c))
* translations for defaults and dynamic window row labels ([#115](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/115)) ([d5165ea](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/d5165ea5c79e0f9391efaf37747b5a1aeb1e9fc4))

## [2.2.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.1.0...v2.2.0) (2026-02-26)


### Features

* entity ID follows source, update energy source form with checkbox (no confirm step) ([520b143](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/520b143068cc18a7472b19288059b1a13e881e36))

## [2.1.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.6...v2.1.0) (2026-02-26)


### Features

* add testing suite, CONTRIBUTING, CI, and pre-commit ([#107](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/107)) ([b1f5589](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/b1f5589278b0a57f02e8cd8d07aad8d05302b5d6))

## [2.0.6](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.5...v2.0.6) (2026-02-26)


### Bug Fixes

* **config:** storage imports + README review ([#105](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/105)) ([7b756f2](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/7b756f20481213b68b19503b00159b067130e5bf))

## [2.0.5](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.4...v2.0.5) (2026-02-26)


### Bug Fixes

* **config:** numberSelector step=0.001 to fix windows step schema ([#103](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/103)) ([6c9deff](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/6c9deff1b4453e6f3aa1c3b74e6e2bafc3ba6505))

## [2.0.4](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.3...v2.0.4) (2026-02-26)


### Bug Fixes

* **config:** entity selector normalization + logging for Unknown error ([#101](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/101)) ([89a805e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/89a805e318b8c3cae9db615bb59f79afc524d348))

## [2.0.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.2...v2.0.3) (2026-02-26)


### Bug Fixes

* **config:** revert vol.Any for source_entity to fix 500 on flow load ([#99](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/99)) ([b1c1c37](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/b1c1c37e169c5042587b8c4c6db8a1d2d795d744))

## [2.0.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.1...v2.0.2) (2026-02-25)


### Bug Fixes

* **config:** entity selector schema and normalization for 400 on add ([#97](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/97)) ([42718c0](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/42718c0bb512dbfe06134e8f7d7b1c1e7e945133))

## [2.0.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v2.0.0...v2.0.1) (2026-02-25)


### Bug Fixes

* **config:** normalize entity selector & docs: update README ([#95](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/95)) ([623595d](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/623595d9b38e701b84bfe4a778441208bd8fd44f))

## [2.0.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.8...v2.0.0) (2026-02-25)


### ⚠ BREAKING CHANGES

* **sensor:** source in entity_id and remove legacy keys ([#93](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/93))

### Features

* allow up to 5 decimal places for Cost per kWh ([#92](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/92)) ([5f147b5](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5f147b57c27a4f2d48a9a5c7d384447539935a3d))
* **sensor:** source in entity_id and remove legacy keys ([#93](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/93)) ([ab1331d](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/ab1331d8874e343885457b8157523fef1097c362))

## [1.14.8](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.7...v1.14.8) (2026-02-25)


### Bug Fixes

* rename source name to friendly name ([#90](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/90)) ([7090ce5](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/7090ce581b3632b202efd99d0fc70e5989efe00d))

## [1.14.7](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.6...v1.14.7) (2026-02-25)


### Bug Fixes

* friendly names ([#86](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/86)) ([025e702](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/025e702f5fc5b318f8d5d3d77e649acb3c893b51))

## [1.14.6](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.5...v1.14.6) (2026-02-25)


### Bug Fixes

* late snapshot, schedule save on loop, update only when value/status changes ([#84](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/84)) ([0cc5aef](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/0cc5aefd1a07bdb38d1f17c4bf415bdcf40bb0cb))

## [1.14.5](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.4...v1.14.5) (2026-02-24)


### Bug Fixes

* schedule save() on event loop from time handlers ([#82](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/82)) ([2e0ba0e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/2e0ba0ec98bfa36fc6991ab0695c74ac6b34530c))

## [1.14.4](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.3...v1.14.4) (2026-02-24)


### Bug Fixes

* schedule state write on event loop when callback runs from thread ([#80](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/80)) ([c013cec](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/c013cec08ffa25d047141792a4be338c8b9ad3e4))

## [1.14.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.2...v1.14.3) (2026-02-24)


### Bug Fixes

* initial Add Entry ([#78](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/78)) ([24c7b3d](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/24c7b3d55e271e0ad735912115bbbae99561b3ca))

## [1.14.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.1...v1.14.2) (2026-02-24)


### Bug Fixes

* update initial Add Entry screen copy ([#76](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/76)) ([796e9df](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/796e9df969754bb251aa7a041ad395e6219bc1a0))

## [1.14.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.14.0...v1.14.1) (2026-02-24)


### Bug Fixes

* preserve entity_id when updating energy source ([#73](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/73)) ([520e53e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/520e53edf1730bfcf4a5e2b2d915752acdd5df28))

## [1.14.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.13.3...v1.14.0) (2026-02-24)


### Features

* **config:** confirm before updating energy source; delete old data and entities on update ([#71](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/71)) ([84886bd](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/84886bde7fa7c58888d910e7dc3bb077ef049d8b))

## [1.13.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.13.2...v1.13.3) (2026-02-24)


### Bug Fixes

* empty window error ([#69](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/69)) ([e73b904](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/e73b9049748147e0d2a192f75eba5713ea4e6255))

## [1.13.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.13.1...v1.13.2) (2026-02-24)


### Bug Fixes

* update energy source name ([#67](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/67)) ([d44e62f](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/d44e62f07a365bcc655ab47e10f8d63125de6f2e))

## [1.13.1](https://github.com/thedeviousdev/ha-energy-tracker/compare/v1.13.0...v1.13.1) (2026-02-24)


### Bug Fixes

* rename offpeak ([#64](https://github.com/thedeviousdev/ha-energy-tracker/issues/64)) ([8bb6a62](https://github.com/thedeviousdev/ha-energy-tracker/commit/8bb6a6221b13e8c1674c09a3509c1740d0c59ba5))
* rename to window ([#66](https://github.com/thedeviousdev/ha-energy-tracker/issues/66)) ([db6b97f](https://github.com/thedeviousdev/ha-energy-tracker/commit/db6b97ff0ec24d3b6f2cc08383540ca9e35f9670))

## [1.13.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.12.2...v1.13.0) (2026-02-24)


### Features

* custom energy name ([#62](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/62)) ([5b52a7b](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5b52a7b87b5abe0f977421b71cd3c44f17416e33))

## [1.12.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.12.1...v1.12.2) (2026-02-24)


### Bug Fixes

* wrong name ([#60](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/60)) ([df6b058](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/df6b058c375653ff9bbdb7bda9591d3855ca2a02))

## [1.12.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.12.0...v1.12.1) (2026-02-24)


### Bug Fixes

* update strings ([#58](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/58)) ([5210f0b](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5210f0bd20fd3be201d7aaf60a3194391b4651fa))

## [1.12.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.11.0...v1.12.0) (2026-02-24)


### Features

* rename ([#55](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/55)) ([af3fe45](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/af3fe4507aea7b59f15d731321aa7931ed11cf90))

## [1.11.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.10.3...v1.11.0) (2026-02-24)


### Features

* add logo ([#52](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/52)) ([c3fac4d](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/c3fac4d61bf1b1f68cc54e0f6b4ae88db2e6260f))

## [1.10.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.10.2...v1.10.3) (2026-02-24)


### Bug Fixes

* update strings ([#49](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/49)) ([f602ba9](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/f602ba9cfc40e2715169856ff396ac9039b8d029))

## [1.10.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.10.1...v1.10.2) (2026-02-24)


### Bug Fixes

* edit error ([#47](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/47)) ([dc1d236](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/dc1d2367651eb2210cd605b7ef52aa265d3add86))

## [1.10.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.10.0...v1.10.1) (2026-02-24)


### Bug Fixes

* error for window list ([#45](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/45)) ([cb0d292](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/cb0d2926e30bac9c9dff2ef2c49c9f2770a5035a))

## [1.10.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.9.1...v1.10.0) (2026-02-24)


### Features

* reduce clicks to edit ([#43](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/43)) ([caff2d4](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/caff2d43af91c2c87ac40915cbbaeeb0c68cd546))

## [1.9.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.9.0...v1.9.1) (2026-02-24)


### Bug Fixes

* sensor ([#41](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/41)) ([9f661c6](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/9f661c6b21bc21ed5252a58c53b3530f193f8d4d))

## [1.9.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.8.1...v1.9.0) (2026-02-24)


### Features

* add sensor to home screen ([#39](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/39)) ([b3bd0c8](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/b3bd0c89d7bbeb46eedcdf8da0f75c97d7e01d7b))

## [1.8.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.8.0...v1.8.1) (2026-02-24)


### Bug Fixes

* fix labels ([#36](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/36)) ([71a4168](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/71a4168d5deedbf06b7616213545879bb89620a0))

## [1.8.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.7.0...v1.8.0) (2026-02-23)


### Features

* windows on their own page ([#34](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/34)) ([78e5425](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/78e5425d89500f0ab15a3bac0ad08c6434a0cb57))

## [1.7.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.6.2...v1.7.0) (2026-02-23)


### Features

* convert to buttons ([#32](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/32)) ([d2c255e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/d2c255e359e4681252e9f6329f2f4e59c40400a7))

## [1.6.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.6.1...v1.6.2) (2026-02-23)


### Bug Fixes

* update description ([#30](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/30)) ([cd1df84](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/cd1df8488e4dc878e0e9dd5c1422353e304c49c4))

## [1.6.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.6.0...v1.6.1) (2026-02-23)


### Bug Fixes

* 400 error ([#28](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/28)) ([cc1a62f](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/cc1a62feff40c59df1835b77f9dcb5810bedf090))

## [1.6.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.5.4...v1.6.0) (2026-02-23)


### Features

* restructure the form ([#26](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/26)) ([9b55b2c](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/9b55b2cabfaae9088acc755cbd330d8a884e7c32))

## [1.5.4](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.5.3...v1.5.4) (2026-02-23)


### Bug Fixes

* single source ([#24](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/24)) ([5473ac0](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5473ac0dffd9cc2517218b09ec8aa1507666ac2f))

## [1.5.3](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.5.2...v1.5.3) (2026-02-23)


### Bug Fixes

* read only self field ([#22](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/22)) ([32b2673](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/32b2673bf5a25af764a3bc03a26f96c3f2673de6))

## [1.5.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.5.1...v1.5.2) (2026-02-23)


### Bug Fixes

* read only field ([#20](https://github.com/thedeviousdev/ha-energy-window-tracker/issues/20)) ([134fccd](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/134fccdd82f38e6f306b45f3734ef0f3ea734972))

## [1.5.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.5.0...v1.5.1) (2026-02-23)


### Bug Fixes

* failing window validation ([0fda517](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/0fda5179e3658316637a942df40a06a7a8f8455d))
* failing window validation ([0fda517](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/0fda5179e3658316637a942df40a06a7a8f8455d))
* failing window validation ([8a6e8e2](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/8a6e8e224cacbecc653d1c749c8c525cd73d2080))

## [1.5.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.4.2...v1.5.0) (2026-02-23)


### Features

* update entity strategy ([678494a](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/678494a18ab77eb9c12f74d0db2cda8280f3113d))
* update entity strategy ([3b06164](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/3b061646499727adf9411901d250c488f056fc19))


### Bug Fixes

* add logging to api ([8dd6667](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/8dd66676f9129dd363d53fa9041f1e1cee80e2c2))

## [1.4.2](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.4.1...v1.4.2) (2026-02-23)


### Bug Fixes

* missing rows ([e850ac4](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/e850ac4c96c53016be4c1695955072ffbfa5e56f))
* missing rows ([e03162e](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/e03162e1a0f52b402f93b354a55df058369d937b))

## [1.4.1](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.4.0...v1.4.1) (2026-02-23)


### Bug Fixes

* flow not allowing multiple entries ([d2664a7](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/d2664a75588d33e76651e794e120bb8fec45b4c5))
* flow not allowing multiple entries ([2887742](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/2887742b83618ea87366c95ec9d8fc472a6ed5e8))

## [1.4.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.3.0...v1.4.0) (2026-02-23)


### Features

* add multiple entitites ([5d5f953](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5d5f9537c2213f2ed614037481f7f287a7ca02e5))
* add multiple entitites ([999aa97](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/999aa97459b218576f69e8457bc92b59981107ac))


### Bug Fixes

* release-please not triggering release ([ee4614d](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/ee4614d6cb218741726ec71d170998d338aa9281))

## [1.3.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.2.0...v1.3.0) (2026-02-23)


### Features

* revert back to single entry ([eded7e7](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/eded7e7607e3a2cdbe79f27eef583a2ef5fa44cf))
* revert back to single entry ([5f9d1dc](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/5f9d1dce01b2356c542bf1ebf16baf09a42f0d44))

## [1.2.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.1.0...v1.2.0) (2026-02-23)


### Features

* add lovelace integration for cards ([575e890](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/575e8901b061119457ff5da3ebe5ffa7cf36441a))
* add lovelace integration for cards ([f7c1d27](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/f7c1d27e4587acf1114ce33ac845de469b149c1d))

## [1.1.0](https://github.com/thedeviousdev/ha-energy-window-tracker/compare/v1.0.0...v1.1.0) (2026-02-22)


### Features

* add all inputs in one step ([78289f1](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/78289f10053dfc5c431d50a4dce82490ef1a1de9))
* add all inputs in one step ([bb81559](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/bb815596f6814d612ddd568222aedd01bff6e915))

## 1.0.0 (2026-02-22)


### Features

* dynamic energy windows ([405ca71](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/405ca71b76ce25b8e1fa18a3959cd204574d4b4c))
* initial config ([b205221](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/b205221ad11f9dd4b319b4ffcb550e903d856c74))
* setup release please ([c960694](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/c9606941298f1123aa47947096b579577abe8c14))
* track windows instead of excluding ([6eccc82](https://github.com/thedeviousdev/ha-energy-window-tracker/commit/6eccc8296646f8de934f40b1466d449c2dbdeed8))
