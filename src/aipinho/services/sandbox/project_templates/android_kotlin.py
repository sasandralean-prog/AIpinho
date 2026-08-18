from __future__ import annotations

from aipinho.services.sandbox.project_templates.asset_placeholders import vector_placeholder_xml


def android_kotlin_simple_game_template(
    *,
    project_name: str,
    package_name: str,
    character_asset: str = "character",
    obstacle_asset: str = "obstacle",
) -> dict[str, str]:
    package_path = package_name.replace(".", "/")
    return {
        "settings.gradle.kts": f'pluginManagement {{ repositories {{ google(); mavenCentral(); gradlePluginPortal() }} }}\ndependencyResolutionManagement {{ repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories {{ google(); mavenCentral() }} }}\nrootProject.name = "{project_name}"\ninclude(":app")\n',
        "build.gradle.kts": 'plugins {\n    id("com.android.application") version "8.5.2" apply false\n    id("org.jetbrains.kotlin.android") version "1.9.24" apply false\n}\n',
        "app/build.gradle.kts": (
            f'plugins {{ id("com.android.application"); id("org.jetbrains.kotlin.android") }}\n\n'
            "android {\n"
            f'    namespace = "{package_name}"\n'
            "    compileSdk = 35\n"
            f'    defaultConfig {{ applicationId = "{package_name}"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "1.0" }}\n'
            "    compileOptions {\n"
            "        sourceCompatibility = JavaVersion.VERSION_17\n"
            "        targetCompatibility = JavaVersion.VERSION_17\n"
            "    }\n"
            "    kotlinOptions {\n"
            '        jvmTarget = "17"\n'
            "    }\n"
            "}\n"
        ),
        "app/src/main/AndroidManifest.xml": f'<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:theme="@style/AppTheme" android:label="{project_name}"><activity android:name=".MainActivity" android:screenOrientation="portrait" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>\n',
        "app/src/main/res/values/styles.xml": '<resources><style name="AppTheme" parent="android:style/Theme.Material.NoActionBar"><item name="android:windowFullscreen">true</item><item name="android:fontFamily">sans</item><item name="android:colorAccent">#22d3ee</item></style></resources>\n',
        f"app/src/main/java/{package_path}/MainActivity.kt": f"""package {package_name}

import android.app.Activity
import android.os.Bundle

class MainActivity : Activity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContentView(GameView(this))
    }}
}}
""",
        f"app/src/main/java/{package_path}/GameView.kt": f"""package {package_name}

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.max
import kotlin.random.Random

class GameView(context: Context) : View(context) {{
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val spawnDelayMs = 10_000L
    private val gravity = 0.85f
    private val jumpVelocity = -18f
    private val obstacleSpeed = 9f
    private val minObstacleSpacingPx = 520f
    private val obstacles = mutableListOf<Obstacle>()
    private var gameStartedAt = System.currentTimeMillis()
    private var playerY = 0f
    private var velocityY = 0f
    private var score = 0
    private var lastSpawnX = 0f

    data class Obstacle(var x: Float, val width: Float, val height: Float, var scored: Boolean = false)

    override fun onDraw(canvas: Canvas) {{
        super.onDraw(canvas)
        if (playerY == 0f) playerY = height * 0.65f
        updateGame()
        drawGame(canvas)
        postInvalidateOnAnimation()
    }}

    override fun onTouchEvent(event: MotionEvent): Boolean {{
        if (event.action == MotionEvent.ACTION_DOWN) {{
            velocityY = jumpVelocity
            return true
        }}
        return true
    }}

    private fun updateGame() {{
        val floorY = height * 0.72f
        velocityY += gravity
        playerY = (playerY + velocityY).coerceAtMost(floorY)
        if (playerY == floorY && velocityY > 0f) velocityY = 0f
        if (System.currentTimeMillis() - gameStartedAt >= spawnDelayMs) spawnObstacleWhenSafe()
        obstacles.forEach {{ it.x -= obstacleSpeed }}
        obstacles.removeAll {{ it.x + it.width < 0f }}
        obstacles.forEach {{ obstacle ->
            if (!obstacle.scored && obstacle.x + obstacle.width < width * 0.22f) {{
                obstacle.scored = true
                score += 1
            }}
        }}
        if (hasCollision(floorY)) resetGame()
    }}

    private fun spawnObstacleWhenSafe() {{
        val newestX = obstacles.maxOfOrNull {{ it.x }} ?: 0f
        if (width - newestX < minObstacleSpacingPx) return
        val heightPx = Random.nextInt(max(90, height / 7), max(140, height / 4)).toFloat()
        obstacles += Obstacle(width + 80f, 92f, heightPx)
        lastSpawnX = width + 80f
    }}

    private fun hasCollision(floorY: Float): Boolean {{
        val playerLeft = width * 0.18f
        val playerRight = playerLeft + 78f
        val playerTop = playerY - 78f
        val playerBottom = playerY
        return obstacles.any {{ obstacle ->
            val left = obstacle.x
            val right = obstacle.x + obstacle.width
            val top = floorY - obstacle.height
            val bottom = floorY
            playerRight > left && playerLeft < right && playerBottom > top && playerTop < bottom
        }}
    }}

    private fun resetGame() {{
        score = 0
        obstacles.clear()
        velocityY = 0f
        playerY = height * 0.65f
        gameStartedAt = System.currentTimeMillis()
        lastSpawnX = 0f
    }}

    private fun drawGame(canvas: Canvas) {{
        canvas.drawColor(Color.rgb(7, 12, 26))
        val floorY = height * 0.72f
        paint.color = Color.rgb(34, 211, 238)
        canvas.drawRect(0f, floorY, width.toFloat(), floorY + 8f, paint)
        paint.color = Color.rgb(74, 222, 128)
        canvas.drawCircle(width * 0.22f, playerY - 38f, 42f, paint)
        paint.color = Color.rgb(22, 163, 74)
        obstacles.forEach {{ canvas.drawRect(it.x, floorY - it.height, it.x + it.width, floorY, paint) }}
        paint.color = Color.WHITE
        paint.textSize = 52f
        canvas.drawText("Score: $score", 42f, 78f, paint)
    }}
}}
""",
        f"app/src/main/res/drawable/{character_asset}.xml": vector_placeholder_xml(label=character_asset, color="#4ade80", shape="circle"),
        f"app/src/main/res/drawable/{obstacle_asset}.xml": vector_placeholder_xml(label=obstacle_asset, color="#16a34a", shape="rect"),
        "README.md": f"""# {project_name}

Android Kotlin simple game generated inside the governed AIpinho sandbox.

## Gameplay

- The player jumps when the screen is tapped.
- Obstacles spawn only after the first 10 seconds.
- Obstacles keep a minimum spacing intended to remain jumpable.
- Passing an obstacle increases the score by 1.
- Collision resets the game.

## Assets

The drawable files are local placeholders. Replace them with production PNG/vector assets when ready.

## Build

This project contains Gradle/Android files, but build execution depends on a local Android SDK/Gradle environment.
""",
    }
