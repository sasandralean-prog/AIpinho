# Android Kotlin Template

The Android Kotlin template emits a minimal Gradle Android project for sandbox use.

Current generated structure:

- `settings.gradle.kts`
- root `build.gradle.kts`
- `app/build.gradle.kts`
- `AndroidManifest.xml`
- `MainActivity.kt`
- `GameView.kt`
- drawable XML placeholders for requested assets
- `README.md`
- `PROJECT_MANIFEST.json`

Current game template capabilities:

- touch-driven jump
- obstacle spawning
- initial delay before obstacles
- minimum obstacle spacing
- score increment after passing obstacle
- collision detection
- reset after collision

The template is intentionally lightweight. It performs structural validation in normal tests and documents when a full Android build was not executed in the runtime environment.

