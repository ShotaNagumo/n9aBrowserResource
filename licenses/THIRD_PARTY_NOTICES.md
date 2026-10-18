# Third-party notices

| Component | Version / revision | License / source |
|---|---|---|
| ElectronicObserverEN fleet formulas (adapted to Kotlin) and equipment, resource, item and ownership PNG icons (unchanged; additional item labels drawn separately) | 5b74e9ac449e892c3b64dae43fd2d75c98f544fb | MIT; https://github.com/ElectronicObserverEN/ElectronicObserver |
| KancolleSniffer legacy quest formation predicates (adapted to Kotlin and first fleet; Copyright (C) 2023 hATrayflood) | 9a4ebdea8976c84ac368f7a2197bb291f03dfe5d | Apache-2.0; https://bitbucket.org/kancollesniffer/kancollesniffer/src/9a4ebdea8976c84ac368f7a2197bb291f03dfe5d/KancolleSniffer/Model/QuestFleetChecker.cs |
| Kcanotify / NetGuard native engine and Packet | 874e414fb2d7c3e36f35ad75766e62a6c4c79c97 | GPL-3.0-or-later; https://github.com/antest1/kcanotify |
| Kcanotify node labels and submarine-node data (`edges.json`, `map_sub.json`) | 874e414fb2d7c3e36f35ad75766e62a6c4c79c97 | GPL-3.0-or-later; https://github.com/antest1/kcanotify/tree/874e414fb2d7c3e36f35ad75766e62a6c4c79c97/app/src/main/assets |
| Google Material Icons (menu, close, vpn_key, swap_horiz, refresh, volume_up, volume_off, photo_camera, timelapse, today, calendar_month; SVG paths converted to Android VectorDrawable, fill color changed) | downloaded 2026-09-22 | Apache-2.0; https://github.com/google/material-design-icons |
| AndroidX WebKit | 1.11.0 | Apache-2.0; https://android.googlesource.com/platform/frameworks/support/+/androidx-main/webkit/ |
| Kotlin standard library | 2.1.20 | Apache-2.0; https://github.com/JetBrains/kotlin |
| Kotlin Coroutines | 1.10.2 | Apache-2.0; https://github.com/Kotlin/kotlinx.coroutines |
| Gson | 2.12.1 | Apache-2.0; https://github.com/google/gson |
| Bouncy Castle PKIX | 1.80 | Bouncy Castle license; https://www.bouncycastle.org/licence.html |
| Bouncy Castle provider / utility | 1.80.2 | Bouncy Castle license; https://www.bouncycastle.org/licence.html |

Full license texts are included in `app/src/main/assets/licenses`. Game master data is obtained from observed responses and is not bundled. Community node mappings are bundled in `core/src/main/resources/map-edges.json` and `map-submarines.json`, unchanged from Kcanotify (Copyright (c) 2016-2026 antest1(IE10)). They can be updated by replacing both files from a reviewed, pinned upstream revision and updating this notice. Unmapped nodes are explicitly shown as unknown.

ElectronicObserverEN: Original work copyright (c) 2014 Andante; Translation work copyright (c) 2015 Ryuu Kitsune. Fleet calculations in `FleetStats.kt` adapt Calculator, FleetDataExtensions, NightEquipment and TpGaugeExtensions. The equipment images in `app/src/main/assets/equipment` are copied unchanged from ElectronicObserver.Avalonia/Assets/Equipment at the pinned revision. The application separately draws labels for consumable variants and an expansion-slot background. The full upstream MIT license is included as `ElectronicObserver-MIT.txt`.

User information icons in app/src/main/assets/userinfo are unchanged from ElectronicObserver.Avalonia/Assets/Resource, Item and Headquarters at the same pinned MIT revision. Headquarters/Ship and Headquarters/Equipment are renamed locally to ship and equipment. The counter implementation reads public API field conventions; no account data is bundled.

Aircraft proficiency images in app/src/main/assets/proficiency are copied unchanged from ElectronicObserver.Avalonia/Assets/Level/AircraftLevelTop1..7.png at the same pinned MIT revision.

The user information area now uses project-generated Material Design-inspired images in app/src/main/assets/userinfo_material, based on the former userinfo subjects. These are not official Google Material Icons. Prompts and source previews are retained in design/userinfo_material. Original upstream images remain in userinfo.

KancolleSniffer recurring quest specifications and event-counting semantics (`QuestCountList.cs`, `QuestSpec.cs`, `QuestCounter.cs`, `QuestFleetChecker.cs`, `CellInfo.cs`): Copyright (C) 2018–2019 Kazuhiro Fujieda; Copyright (C) 2021–2023 hATrayflood. Apache License 2.0. Revision 9a4ebdea8976c84ac368f7a2197bb291f03dfe5d. Adapted to Kotlin with observed-only lower-bound counts, persistent account/period separation, and app-local definitions. Source: https://bitbucket.org/kancollesniffer/kancollesniffer/src/9a4ebdea8976c84ac368f7a2197bb291f03dfe5d/KancolleSniffer/Model/

Expedition prediction rules and great-success probability models are adapted from ElectronicObserverEN MissionClearCondition.cs and ExpeditionCalculator/Extensions.cs at revision 5b74e9ac449e892c3b64dae43fd2d75c98f544fb (MIT). Conditions and stat coefficients were checked against KanColle Wiki on 2026-10-11. Unresolved formulas return unknown instead of inventing an exact result.

Base air-corps display air-power calculations are adapted from ElectronicObserverEN Utility/Data/Calculator.cs and EquipmentLevelExtensions.cs at revision 5b74e9ac449e892c3b64dae43fd2d75c98f544fb (MIT). The displayed value uses observed slot counts and the lower bound of internal proficiency; high-altitude area-wide defense corrections are not included.

Ship experience totals (1–188), reduced evasion/ASW parameter records in core/src/main/resources/ship-experience.json and ship-growth.json, and growth/accuracy calculations in ShipExperience.kt adapt ElectronicObserverEN ExpTable, ShipParameterRecord and ShipDataExtensions at revision 5b74e9ac449e892c3b64dae43fd2d75c98f544fb (MIT). Only numeric public reference records are bundled; no account data or game flavor text is included.
